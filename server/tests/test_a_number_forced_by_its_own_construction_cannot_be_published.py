"""The publish path refuses a number the probe could not have contradicted.

On 2026-08-08 we posted, on openclaw/openclaw#7707, that "poison earns standing 100% of the time".
The probe called `measure(..., minja_p=1.0)`; `random() < 1.0` is always true; the poison record
never accrued `bad`; the guard that was meant to block it required `bad > good` and so could never
fire. The number was a definition. Our gate passed it, correctly, by its own definition: validate
asks that a number be backed by an artifact re-run this cycle, verify asks that it match. Neither
asks whether the artifact could have produced any other number.

`tools/construction_audit.py` closed the reasoning hole and shipped as a script whose docstring said
"wire it into the publish path, not into someone's memory" -- and then lived in memory. This file
tests the wiring, and it tests it in the direction that matters.

A gate is worth what it REFUSES. Every assertion below is paired: the gate must fire on a fixture
that reproduces the real defect AND stay silent on a clean one. Without the second half a gate that
refuses everything passes its own test; without the first half a gate that refuses nothing does too.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    assert spec and spec.loader, f"cannot load tools/{name}.py"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ca = _load("construction_audit")
pg = _load("publish_gate")

# The real thing. Not a paraphrase of it -- the file whose number we actually published.
SHIPPED_PROBE = ROOT / "research" / "probes" / "oracle_separation_density.py"


# ---------------------------------------------------------------- the fixture that must keep firing
def test_the_probe_we_actually_published_is_still_refused():
    """The live artifact, not a reconstruction of it.

    If this ever goes quiet, either the probe was fixed (then fix this test deliberately) or the
    auditor stopped seeing it. A green suite that cannot tell those apart has measured nothing.
    """
    assert SHIPPED_PROBE.exists(), f"{SHIPPED_PROBE} is gone -- the fixture no longer exists"
    findings = ca.audit(SHIPPED_PROBE)
    kinds = {f.kind for f in findings}
    assert "BOUNDARY-PROBABILITY" in kinds, (
        "the auditor no longer sees minja_p=1.0 passed POSITIONALLY into a random() comparison -- "
        f"got {sorted(kinds)}")
    assert "THIN-SEEDS" in kinds, f"the 6-seed loop is no longer seen -- got {sorted(kinds)}"
    boundary = [f for f in findings if f.kind == "BOUNDARY-PROBABILITY"]
    assert any("1.0" in f.detail for f in boundary), "the boundary value itself is not reported"


def test_a_positional_boundary_argument_is_caught_not_only_a_keyword(tmp_path):
    """The defect we shipped had no keyword. A kwargs-only check walks straight past it."""
    src = tmp_path / "positional.py"
    src.write_text(
        "import random\n"
        "def measure(facts, oracle, p=0.5):\n"
        "    rng = random.Random(0)\n"
        "    return (rng.random() < p)\n"
        "measure([], 'minja', 1.0)\n", encoding="utf-8")
    kinds = {f.kind for f in ca.audit(src)}
    assert "BOUNDARY-PROBABILITY" in kinds, f"positional boundary arg missed -- got {sorted(kinds)}"


def test_a_dead_counter_guard_is_still_caught_after_the_soundness_fix(tmp_path):
    """GUARD-ON-UNWRITTEN-KEY was narrowed twice on 2026-08-08 (it was wrong on 5 of 5 real
    artifacts: membership tests on data fields, then dicts built with variable keys). Narrowing a
    rule until it is silent everywhere is indistinguishable from deleting it, so this pins that it
    still fires on the shape it exists for -- a counter a guard compares and no path advances."""
    src = tmp_path / "dead_guard.py"
    src.write_text(
        "store = {'good': 0, 'bad': 0}\n"
        "def blocked():\n"
        "    return store['bad'] > store['good']\n"
        "store['good'] += 1\n"
        "print(blocked())\n", encoding="utf-8")
    kinds = {f.kind for f in ca.audit(src)}
    assert "DEAD-COUNTER-GUARD" in kinds, (
        f"the dead-counter rule has been narrowed into silence -- got {sorted(kinds)}")


def test_a_clean_probe_passes(tmp_path):
    """The other half. A gate that refuses everything would pass every test above."""
    src = tmp_path / "clean.py"
    src.write_text(
        "import random\n"
        "def measure(p=0.5):\n"
        "    rng = random.Random(0)\n"
        "    hits = 0\n"
        "    for seed in range(64):\n"
        "        hits += (rng.random() < p)\n"
        "    return hits\n"
        "print(measure(0.3))\n", encoding="utf-8")
    assert ca.audit(src) == [] or [f.kind for f in ca.audit(src)] == [], \
        f"clean probe flagged: {[str(f) for f in ca.audit(src)]}"


# ------------------------------------------------------------- the gate must refuse, not just report
def test_enforce_refuses_by_raising_not_by_returning(tmp_path):
    """enforce() exits; it does not hand back a value a caller can forget to check."""
    bad = tmp_path / "bad.py"
    bad.write_text(
        "import random\n"
        "def m(p=0.5):\n"
        "    rng = random.Random(0)\n"
        "    return rng.random() < p\n"
        "m(1.0)\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        pg.enforce([bad], "test")
    assert exc.value.code == 1


def test_an_empty_target_set_is_a_refusal_not_a_pass():
    """The expensive shape in this codebase: a check that never sees its target reports SAFE.

    A gate handed nothing must say so. This is the assertion that stops the whole mechanism from
    being satisfied by a resolver that silently returns [].
    """
    with pytest.raises(SystemExit) as exc:
        pg.enforce([], "nothing at all")
    assert exc.value.code == 1


def test_an_unresolved_artifact_is_a_refusal():
    """A publication that links a runnable model the reader cannot open is a broken receipt."""
    with pytest.raises(SystemExit) as exc:
        pg.enforce([], "post", unresolved=["DanceNitra/agora/research/probes/gone.py"])
    assert exc.value.code == 1


def test_a_crash_while_auditing_is_a_refusal_not_a_pass(tmp_path, monkeypatch):
    """A gate that raises has failed to run -- the one outcome that resembles neither pass nor fail.
    It must land on the refusing side. (The real crash: `os.environ.get("X", os.path.join(...))` put
    a Call where a Constant was assumed, on 2 of 39 Crucible artifacts.)"""
    p = tmp_path / "x.py"
    p.write_text("x = 1\n", encoding="utf-8")

    def boom(_path):
        raise ValueError("synthetic")

    monkeypatch.setattr(pg, "_audit_module", lambda: type("M", (), {"audit": staticmethod(boom)}))
    with pytest.raises(SystemExit) as exc:
        pg.enforce([p], "crashing")
    assert exc.value.code == 1


def test_the_environ_default_that_used_to_crash_the_auditor_now_reports():
    """Regression pin for that crash, on a real file rather than a fixture of one."""
    real = ROOT / "research" / "probes" / "reversibility_predictability_probe.py"
    if not real.exists():
        pytest.skip("artifact not in this checkout")
    kinds = {f.kind for f in ca.audit(real)}          # must not raise
    assert "UNSWEPT-KNOB" in kinds


# ------------------------------------------------------------------------- resolution and waivers
def test_a_link_into_another_repo_is_not_resolved_against_this_one():
    """A path is relative to its own repo. Measured: a repo-blind resolver called ramr's
    erasure_selfcheck.py 'missing' while it sat on disk, which would have blocked a good post."""
    text = "see https://github.com/SomeoneElse/theirrepo/blob/main/probes/thing.py for details"
    local, unresolved, external = pg.links_in_text(text)
    assert not local and not unresolved, "an unknown repo's path was resolved locally"
    assert external == ["SomeoneElse/theirrepo/probes/thing.py"]


def test_every_waiver_states_a_reason_and_a_date():
    """A waiver without a reason is the gate switched off in a place nobody looks."""
    data = json.loads((TOOLS / "construction_waivers.json").read_text(encoding="utf-8"))
    for path, w in data.items():
        if path.startswith("_"):
            continue
        assert w.get("kinds"), f"{path}: waiver names no finding kind"
        assert len(w.get("reason", "")) > 40, f"{path}: waiver reason is too thin to review"
        assert w.get("dated"), f"{path}: waiver carries no date"


def test_waivers_point_at_files_that_exist_and_still_have_the_finding():
    """A waiver for a finding that no longer occurs is stale permission sitting in the path.

    This is the control on the waiver file itself: it fails when a waiver stops being needed, which
    is the only way the list ever shrinks.
    """
    data = json.loads((TOOLS / "construction_waivers.json").read_text(encoding="utf-8"))
    foreign = []
    for path, w in data.items():
        if path.startswith("_"):
            continue
        # A WAIVER KEYED BY AN ABSOLUTE PATH LIVES IN THE WRONG FILE. Three entries point into
        # sibling repositories (ramr-pub, inspeximus-repo), so `ROOT / path` resolves to nonsense in
        # any checkout and this assertion could never hold off this one machine. They are counted
        # rather than ignored: if a fourth appears, the count moves and this fails, which is the only
        # thing keeping the exception from growing quietly. The real fix is to move them to those
        # repositories' own waiver files, and that is a change to how publish_gate resolves
        # cross-repo artifacts, not a test edit.
        if len(path) > 1 and path[1] == ":":
            foreign.append(path)
            continue
        p = ROOT / path
        assert p.exists(), f"waiver for {path} but the file is gone -- remove the waiver"
        kinds = {f.kind for f in ca.audit(p)}
        assert set(w["kinds"]) & kinds, (
            f"waiver for {path} lists {w['kinds']} but the audit now reports {sorted(kinds)} -- "
            "the waiver is stale, delete it")
    assert len(foreign) == 3, (
        f"{len(foreign)} waivers are keyed by an absolute path outside this repo, was 3 on "
        f"2026-08-27: {sorted(foreign)}. A waiver nothing here can resolve is permission with no "
        "check behind it, so the count is pinned until they move to their own repositories.")


# ------------------------------------------------------------------------------ the wiring itself
@pytest.mark.parametrize("renderer", ["render_crucible.py", "render_post.py"])
def test_the_renderers_call_the_gate_rather_than_mentioning_it(renderer):
    """The docstrings of both renderers carried 'PUBLISH GATE: run /stress-claim ...' for months.
    A sentence addressed to a human is what failed. Pin the CALL."""
    src = (TOOLS / renderer).read_text(encoding="utf-8", errors="replace")
    assert "import publish_gate" in src, f"{renderer} does not import the gate"
    assert "publish_gate.enforce(" in src or "_construction_gate(" in src, \
        f"{renderer} imports the gate but never calls it"
