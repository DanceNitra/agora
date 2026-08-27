"""Durable state is written atomically, and the Canon cannot be replaced by a truncated merge.

Two hygiene defects with the same shape: a failure mode that produces a SMALLER, still-parseable
result and is therefore invisible to every guard that only asks "is this valid?".

  * Every durable file the dungeon keeps was written with a bare `Path.write_text`, which truncates
    at open and then writes. The brain's watchdog relaunches that process with p.kill() —
    TerminateProcess, no graceful stop — so a kill inside the window leaves a truncated file, and
    every reader catches the parse error and resets to empty, silently. The file's own comments
    record the cost: losing `_recent_intents` produced the "8x-duplicate output monoculture", and a
    reset `loop_n` restarts every `% N` generator's countdown, which starved the Claude inbox for
    hours.

  * The Canon — the vault's single statement of belief, budgeted at ~7,000 characters — was
    replaced wholesale behind `len(content) < 200`, an absolute constant never compared against the
    document it replaces. Empty is caught; truncated-at-500 is not, and truncated is the likelier
    outcome for a model that stops early. That would have replaced ~93% of the document and then
    stamped a fresh `updated:`, so the next intake would not re-offer what was lost.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

spec = importlib.util.spec_from_file_location("canon_under_test",
                                              ROOT / "server/agora/execution/canon.py")
canon = importlib.util.module_from_spec(spec)
sys.modules["canon_under_test"] = canon
spec.loader.exec_module(canon)

MCP = ROOT / "agora-game-server/mcp_server.py"


# ------------------------------------------------------------------------- atomic durable writes
def test_no_state_file_is_written_with_a_bare_write_text():
    """Pinned by source inspection: importing mcp_server would start a server. The five sites were
    .pipeline_state.json, .recent_intents.json, agent_standing.json, .organ_state.json and
    .dungeon_heartbeat."""
    src = MCP.read_text(encoding="utf-8", errors="replace")
    body = src[src.index("def _atomic_write"):]
    body = body[body.index("os.replace(tmp, p)"):]          # everything AFTER the helper itself
    offenders = [ln.strip() for ln in body.splitlines() if ".write_text(" in ln]
    assert offenders == [], f"a durable write bypasses _atomic_write: {offenders}"
    assert src.count("_atomic_write(") >= 6, "the helper is defined but barely used"


def test_the_helper_replaces_rather_than_truncates(tmp_path, monkeypatch):
    """Behavioural, not just structural: the target must never be observed truncated, and a failed
    write must leave the ORIGINAL intact rather than an empty file."""
    sys.path.insert(0, str(ROOT / "agora-game-server"))
    ns: dict = {}
    src = MCP.read_text(encoding="utf-8", errors="replace")
    start = src.index("def _atomic_write")
    end = src.index("\n\n", src.index("os.replace(tmp, p)"))
    exec("import os\nfrom pathlib import Path\n" + src[start:end], ns)
    atomic = ns["_atomic_write"]

    target = tmp_path / "state.json"
    target.write_text(json.dumps({"loop_n": 1}), encoding="utf-8")
    atomic(target, json.dumps({"loop_n": 2}))
    assert json.loads(target.read_text(encoding="utf-8")) == {"loop_n": 2}
    assert not (tmp_path / "state.json.tmp").exists(), "the temp file was left behind"

    # A write that dies mid-way hits the TEMP file; the real one is untouched.
    monkeypatch.setattr(ns["os"], "replace", lambda *a: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError):
        atomic(target, json.dumps({"loop_n": 3}))
    assert json.loads(target.read_text(encoding="utf-8")) == {"loop_n": 2}, \
        "a failed write destroyed the previous state — the whole point of the temp file"


# ---------------------------------------------------------------------------- the Canon shrink bound
@pytest.fixture
def vault(tmp_path, monkeypatch):
    monkeypatch.setattr(canon, "canon_path", lambda _v: tmp_path / "Canon.md")
    full = "---\ntitle: Canon\nupdated: 2026-01-01\n---\n\n" + ("belief paragraph. " * 400)
    (tmp_path / "Canon.md").write_text(full, encoding="utf-8")
    return tmp_path, full


def test_a_truncated_merge_is_refused(vault):
    d, full = vault
    r = canon.write_canon("ignored", "---\ntitle: Canon\n---\n\n" + ("belief paragraph. " * 20))
    assert isinstance(r, dict) and "refused" in r["error"], r
    assert (d / "Canon.md").read_text(encoding="utf-8") == full, "the Canon was overwritten anyway"


def test_a_full_merge_still_writes(vault):
    """The other half — a gate that refused every merge would pass the test above forever."""
    d, full = vault
    r = canon.write_canon("ignored", "---\ntitle: Canon\n---\n\n" + ("belief paragraph. " * 380))
    assert isinstance(r, str), r
    assert "belief paragraph." in (d / "Canon.md").read_text(encoding="utf-8")


def test_a_deliberate_shrink_is_possible_with_force(vault):
    """A bound with no override is a bound someone eventually comments out."""
    d, _ = vault
    r = canon.write_canon("ignored", "---\ntitle: Canon\n---\n\nshort on purpose. " * 3, force=True)
    assert isinstance(r, str), r


def test_the_outgoing_version_is_kept_beside_the_file(vault):
    d, full = vault
    canon.write_canon("ignored", "---\ntitle: Canon\n---\n\n" + ("belief paragraph. " * 380))
    prev = d / "Canon.md.prev"
    assert prev.exists() and prev.read_text(encoding="utf-8") == full, \
        "recovery would depend on a push having happened"


def test_the_endpoint_propagates_the_refusal_instead_of_reporting_written():
    src = (ROOT / "server/agora/api/agent_os_api.py").read_text(encoding="utf-8", errors="replace")
    i = src.index('if len(content) < 200:')
    block = src[i:i + 900]
    assert '"status": "refused"' in block, "a refused merge would still report written"
    assert "force=bool(b.get(\"force\"))" in block, "the deliberate-shrink escape hatch is unwired"
