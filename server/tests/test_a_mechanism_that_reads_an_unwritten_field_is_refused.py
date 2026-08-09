"""A shipped mechanism whose gating field is never populated must be refused, not reported SAFE.

On 2026-08-08 four defects turned out to be one defect wearing four hats:

  * the construction audit was built and tested, and lived in someone's memory instead of the publish path
  * `with_warrant` existed in the library and nowhere in the MCP server, so no agent could obtain it
  * `strict_corroboration` counts distinct verified keys; `attested_key` was populated on 0 of 111,264
  * `credit_requires_warrant` counts warranted credit; `good_warranted > 0` was 0 of 60,077

and before them, `slash(scope='source')` returning ok on 261,673 records because its default scope
resolved on a field no writer ever set.

Every one is "the code is correct and unreached". Our tests prove a mechanism works GIVEN its input.
Nothing asked whether the input ever arrives — and a guard with no input never fires, so it reports
SAFE forever. `tools/mechanism_coverage.py` asks that question against PRODUCTION data.

These tests are paired, because a coverage checker has both failure directions available to it: it can
miss a dead mechanism, and it can cry wolf on a healthy one. The second is what gets it deleted.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "mechanism_coverage.py"


def _load():
    spec = importlib.util.spec_from_file_location("mechanism_coverage", TOOL)
    assert spec and spec.loader, f"cannot load {TOOL}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mc = _load()

# Captured before the autouse fixture replaces them. Without this the discovery tests below call the
# fixture's stub and assert against `[]` — measuring the mock instead of the code, which is the exact
# failure this file is about. It cost two red tests to notice, which is the cheap way to find out.
_REAL_WRITER_STORE = mc._writer_store
_REAL_DISCOVERED = mc._discovered


def _store(tmp_path, records, name="store.json"):
    p = tmp_path / name
    p.write_text(json.dumps(records), encoding="utf-8")
    return p


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch):
    """Keep the fixtures hermetic after 2026-08-09.

    The gate now (a) discovers stores under ROOT and (b) always reads the deployment's writer store —
    both deliberately outside the caller's control, which is the point. But that means a test that
    patches STORES alone would quietly be measuring this machine's real 219k-record production corpus
    and passing on data it never declared. Every test below therefore starts from "discovery finds
    nothing, and the writer store IS the fixture"; the tests that exercise those two paths override it.
    """
    monkeypatch.setattr(mc, "_discovered", lambda declared: [])
    monkeypatch.setattr(mc, "_writer_store", lambda: mc.STORES[0] if mc.STORES else None)


# ------------------------------------------------------------------ must REFUSE a dead mechanism
def test_a_field_no_record_populates_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, [
        {"id": "1", "text": "a", "source": {"doc": "x"}, "key": "k1"},
        {"id": "2", "text": "b", "source": {"doc": "y"}, "key": "k2"},
    ])])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 1, "a mechanism reading a never-written field must be refused"


def test_the_refusal_names_the_field_and_the_consequence(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, [{"id": "1", "text": "a", "source": "s", "key": "k"}])])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    mc.main()
    out = capsys.readouterr().out
    assert "attested_key" in out and "UNREACHABLE" in out
    assert "consequence:" in out, "a refusal that does not say what breaks is a number, not a finding"


# ------------------------------------------------------------------- must NOT cry wolf when healthy
def test_a_fully_populated_store_passes(tmp_path, monkeypatch):
    """The other half. A checker that refuses everything would pass both tests above."""
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, [
        {"id": "1", "text": "a", "source": {"doc": "x"}, "key": "k1",
         "attested_key": "aa" * 32, "good_warranted": 2.0},
    ])])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 0, "every mechanism has a write path here; refusing is a false alarm"


def test_partial_coverage_is_not_treated_as_zero(tmp_path, monkeypatch):
    """One attested record in a hundred still means the write path EXISTS. The gate asks whether the
    field is reachable, not whether it is universal — conflating those would make it unusable the day
    after a fix ships, which is exactly when it must stay green."""
    recs = [{"id": str(i), "text": "t", "source": "s", "key": "k", "good_warranted": 1.0}
            for i in range(100)]
    recs[0]["attested_key"] = "bb" * 32
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, recs)])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 0


def test_a_deliberate_exception_needs_naming_the_field(tmp_path, monkeypatch):
    """An escape hatch that is a blanket --force would be the gate switched off; it is per-field."""
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, [
        {"id": "1", "text": "a", "source": "s", "key": "k", "good_warranted": 1.0}])])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py", "--allow-zero", "attested_key"])
    assert mc.main() == 0
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py", "--allow-zero", "some_other_field"])
    assert mc.main() == 1, "allowing an unrelated field must not excuse the dead one"


# --------------------------------------------------------------- the check must SEE something at all
def test_no_readable_store_is_a_refusal_not_a_pass(monkeypatch):
    """The failure this whole file exists to prevent, applied to the checker itself: reading nothing
    must never report OK."""
    monkeypatch.setattr(mc, "STORES", [Path("does") / "not" / "exist.json"])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 1


# ------------------------------------------------------- the writer store, which is where signing lands
#
# 2026-08-09. inspeximus 2.3.0 shipped `writer_key`, the MCP server was restarted with it, and a write
# was verified ON DISK to carry `attested_key`. This gate still printed `attested_key 0 0.0000%` over
# 215,023 records — because `STORES` was a hand-written literal of ten repo files and the store the MCP
# server writes was not one of them. The zero was structurally guaranteed: identical whether signing
# worked or not. These tests pin the store list's completeness, not just the counting.


def test_the_writer_store_is_read_even_when_it_is_not_declared(tmp_path, monkeypatch):
    """THE regression test. `attested_key` lives only in the writer store; if the gate reads around it,
    the count is 0 and the refusal is fiction. Passing here REQUIRES that store to have been opened."""
    declared = _store(tmp_path, [{"id": "1", "text": "a", "source": "s", "key": "k",
                                  "good_warranted": 1.0}], "declared.json")
    writer = _store(tmp_path, [{"id": "2", "text": "b", "source": "s", "key": "k",
                                "attested_key": "cc" * 32, "ts": 1.0}], "writer.json")
    monkeypatch.setattr(mc, "STORES", [declared])
    monkeypatch.setattr(mc, "_writer_store", lambda: writer)
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 0, "the only attested record is in the writer store; refusing means it went unread"


def test_a_writer_store_that_cannot_be_read_is_refused(tmp_path, monkeypatch, capsys):
    """The control, and the harder half: every DECLARED store is perfectly healthy here. A gate that
    merely counts would report OK. Not looking where the field is written is itself the finding."""
    healthy = _store(tmp_path, [{"id": "1", "text": "a", "source": "s", "key": "k",
                                 "attested_key": "dd" * 32, "good_warranted": 1.0}])
    monkeypatch.setattr(mc, "STORES", [healthy])
    monkeypatch.setattr(mc, "_writer_store", lambda: tmp_path / "never" / "written.json")
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 1, "coverage computed without reading the writer store is not a measurement"
    assert "writer store was not read" in capsys.readouterr().out


def test_an_unresolvable_writer_store_is_refused(tmp_path, monkeypatch, capsys):
    """'I could not find where writes go' must not degrade into 'nothing to report'."""
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, [
        {"id": "1", "text": "a", "source": "s", "key": "k",
         "attested_key": "ee" * 32, "good_warranted": 1.0}])])
    monkeypatch.setattr(mc, "_writer_store", lambda: None)
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 1
    assert "unresolvable" in capsys.readouterr().out


def test_freshness_is_reported_separately_from_corpus_coverage(tmp_path, monkeypatch, capsys):
    """A corpus of legacy records can never be retro-filled, so one populated write pins coverage above
    zero forever — and the gate would stay green straight through an outage. The recent-writes line is
    the number that can still fall."""
    recs = [{"id": str(i), "text": "t", "source": "s", "key": "k", "good_warranted": 1.0,
             "ts": float(i)} for i in range(200)]
    recs[0]["attested_key"] = "ff" * 32          # oldest record signed, nothing since
    writer = _store(tmp_path, recs, "writer.json")
    monkeypatch.setattr(mc, "STORES", [writer])
    monkeypatch.setattr(mc, "_writer_store", lambda: writer)
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 0, "the write path does exist; this line informs, it does not gate"
    out = capsys.readouterr().out
    assert "most recent writer-store records: 0" in out
    assert "not reaching new writes" in out


def test_every_new_write_only_field_gets_a_freshness_line(tmp_path, monkeypatch, capsys):
    """The freshness denominator was applied to `attested_key` and NOT to `good_warranted`, so the
    corpus zero for the second field read as "nothing writes this" when the truth was "every record
    predates the writer that can". Caught in review 2026-08-09 — the defect this file is about, inside
    the tool, one field over from where it had just been fixed. Fixing the instance is not fixing the
    class, so this asserts the LIST, not one member of it."""
    recs = [{"id": str(i), "text": "t", "source": "s", "key": "k",
             "attested_key": "ee" * 32, "good_warranted": 1.0, "ts": float(i)} for i in range(10)]
    writer = _store(tmp_path, recs, "writer.json")
    monkeypatch.setattr(mc, "STORES", [writer])
    monkeypatch.setattr(mc, "_writer_store", lambda: writer)
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    mc.main()
    out = capsys.readouterr().out
    assert mc.NEW_WRITE_ONLY, "the list is empty; this test would pass vacuously"
    for field in mc.NEW_WRITE_ONLY:
        assert ("%s " % field) in out and "most recent writer-store records" in out, (
            "%s is declared new-write-only but gets no freshness line, so its corpus zero is "
            "indistinguishable from an outage" % field)


# ------------------------------------------------------------------- discovery, and its false positives
def test_discovery_finds_a_store_the_literal_omits(tmp_path, monkeypatch):
    monkeypatch.setattr(mc, "ROOT", tmp_path)
    (tmp_path / ".inspeximus").mkdir()
    real = tmp_path / ".inspeximus" / "coding_memory.json"
    real.write_text("[]", encoding="utf-8")
    assert real.resolve() in {p.resolve() for p in _REAL_DISCOVERED(set())}


def test_a_tombstone_sidecar_is_not_a_store(tmp_path, monkeypatch):
    """Found by running it: `.agent_memory/*.json` also matches `king.json.tombstones.json`, and the
    first run named eight of them. A discovery pass that cries wolf eight times is one nobody reads."""
    monkeypatch.setattr(mc, "ROOT", tmp_path)
    (tmp_path / ".agent_memory").mkdir()
    (tmp_path / ".agent_memory" / "king.json").write_text("[]", encoding="utf-8")
    (tmp_path / ".agent_memory" / "king.json.tombstones.json").write_text("[]", encoding="utf-8")
    names = {p.name for p in _REAL_DISCOVERED(set())}
    assert "king.json" in names
    assert "king.json.tombstones.json" not in names


def test_an_already_declared_store_is_not_discovered_twice(tmp_path, monkeypatch):
    """Double-counting a store would inflate every denominator and quietly weaken the percentages."""
    monkeypatch.setattr(mc, "ROOT", tmp_path)
    (tmp_path / ".inspeximus").mkdir()
    p = tmp_path / ".inspeximus" / "coding_memory.json"
    p.write_text("[]", encoding="utf-8")
    assert _REAL_DISCOVERED({p.resolve()}) == []


def test_this_deployment_resolves_a_writer_store_that_exists():
    """Assert the target EXISTS and RESOLVES — the rule the tool broke. Skips where no MCP server is
    configured (CI), because there the absence is honest rather than a stale literal."""
    w = _REAL_WRITER_STORE()
    if w is None:
        import pytest as _p
        _p.skip("no inspeximus MCP store configured on this machine")
    assert w.exists(), f"writer store resolves to {w}, which does not exist — the gate would refuse"


def test_it_runs_as_a_script_against_the_real_stores():
    """Pin the entry point too: a gate that only works when imported is not wired into anything."""
    r = subprocess.run([sys.executable, "-X", "utf8", str(TOOL)],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode in (0, 1), f"the gate crashed instead of ruling: {r.stderr[-400:]}"
    assert "coverage" in r.stdout, "the gate produced no coverage table"
