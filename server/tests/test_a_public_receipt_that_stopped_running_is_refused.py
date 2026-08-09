"""A receipt we publicly offered must still run — and exit 0 is not the question.

Origin, 2026-08-09. Our comment on openclaw#35203 ended "Happy to share the runnable replications for
any of these". Running one of them for the first time in months printed:

    RESULT: poison_blocked=True  legit_graduates=False  sybil_blocked=True  -> FAIL

and **exited 0**. The claim it backed was still true; the artifact behind it was not runnable. Anyone
taking us up on the offer would have run a failing probe of ours.

`publish_gate.py` reads these files as text (AST) — it catches a result forced by construction, which
is visible without running anything. It cannot catch ROT: a moved threshold, a guard added upstream, a
trigger that migrated from the recall path to consolidate(). Only execution catches that.

So the single most important assertion in this file is `test_a_fail_printed_with_exit_zero_is_a_fail`.
Everything else is scaffolding around it.

Paired throughout: each "must refuse" sits beside a "must not cry wolf", because a receipt checker that
flags healthy artifacts is one that gets switched off after the second false alarm.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "public_receipts.py"


def _load():
    spec = importlib.util.spec_from_file_location("public_receipts", TOOL)
    assert spec and spec.loader, f"cannot load {TOOL}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pr = _load()


# ------------------------------------------------------------------ THE trap that started all this
def test_a_fail_printed_with_exit_zero_is_a_fail():
    """corroboration_poison.py printed `-> FAIL` and returned 0. Exit-code checking calls that green."""
    verdict, _ = pr.classify(0, "RESULT: poison_blocked=True  legit_graduates=False  -> FAIL", False)
    assert verdict == "FAIL"


def test_exit_zero_with_no_verdict_is_unknown_not_pass():
    """Silence is the other way a dead receipt looks healthy."""
    verdict, detail = pr.classify(0, "loading data...\nwrote results.json\n", False)
    assert verdict == "UNKNOWN"
    assert "not a pass" in detail


# ------------------------------------------------------------------------------- the other outcomes
def test_a_traceback_is_a_crash():
    out = 'Traceback (most recent call last):\n  File "x.py", line 1\nValueError: boom'
    assert pr.classify(1, out, False)[0] == "CRASHED"


def test_a_missing_resource_is_reported_as_such_not_as_a_crash():
    """'it needs our GPU' is a fact about the receipt, so it is named rather than folded into CRASHED
    — but it still counts against us, because a reader cannot run it either."""
    out = ('Traceback (most recent call last):\n'
           'urllib.error.URLError: <urlopen error [Errno 111] Connection refused> 11434')
    assert pr.classify(1, out, False)[0] == "NEEDS-RESOURCE"


def test_a_timeout_is_a_refusal():
    assert pr.classify(-1, "", True)[0] == "TIMEOUT"


def test_a_real_pass_is_a_pass():
    """The other half: a healthy receipt must come back clean, or the tool is unusable."""
    out = "RESULT: poison_blocked=True  legit_graduates=True  sybil_blocked=True  -> PASS"
    assert pr.classify(0, out, False)[0] == "PASS"


def test_a_pass_word_inside_a_failing_line_does_not_rescue_it():
    """FAIL is checked before PASS on purpose: 'passed 3 of 5 ... -> FAIL' is a failure."""
    assert pr.classify(0, "passed 3 of 5 checks -> FAIL", False)[0] == "FAIL"


def test_a_negative_scientific_verdict_is_a_working_receipt_not_rot():
    """The false positive that made this tool wrong on 2 of 12 real artifacts on its first run.

    A replication ledger legitimately contains FAILED verdicts. `founder_survivorship_null.py` prints
    "VERDICT (mechanism): FAILED" because that IS its published finding — the receipt ran and reported.
    The question this tool asks is whether the receipt still RUNS, never whether we liked the answer;
    conflating the two would have us "fixing" probes whose null result is the whole point."""
    out = ("VERDICT (mechanism): FAILED -- index construction of a higher-variance cohort reproduces "
           "most of the 3.1x with no skill")
    assert pr.classify(0, out, False)[0] == "PASS"


def test_an_infra_spawn_failure_is_not_blamed_on_the_receipt():
    """Also measured on the first run: a TimeoutExpired kill was followed by four consecutive 0.0s
    'crashes' with exit 0xC0000142, and all four probes ran fine standalone. Reporting those as CRASHED
    would have been four false accusations produced entirely by our own harness."""
    assert pr.classify(3221225794, "", False)[0] == "INFRA"
    # and a REAL crash with real output must still be a crash
    assert pr.classify(3221225794, "Traceback (most recent call last):\nValueError: x", False)[0] == "CRASHED"


# ------------------------------------------------------------------- the checker must SEE something
def test_discovering_no_artifact_is_a_refusal(monkeypatch):
    """This tool's own disease: a receipt runner that finds nothing to run has verified nothing."""
    monkeypatch.setattr(pr, "discover", lambda: {})
    monkeypatch.setattr(sys, "argv", ["public_receipts.py"])
    assert pr.main() == 1


def test_discovery_actually_finds_the_publicly_linked_artifacts():
    """Pin the wiring: if link extraction silently returns [], every test above passes vacuously."""
    found = pr.discover()
    assert len(found) >= 5, f"expected the public posts to link several artifacts, got {len(found)}"
    assert all(isinstance(v, list) and v for v in found.values()), "each artifact must name its posts"


# --------------------------------------------------------------------------------------- waivers
def test_the_receipt_gate_is_actually_STARTED_not_merely_defined():
    """The whole point, applied to this gate itself.

    `construction_audit.py` was built, tested, and shipped with a docstring telling a human to wire it
    into the publish path — and then lived in someone's memory for a day. A gate nobody calls is
    indistinguishable from a gate that does not exist, and `async def ... _loop` sitting in a module
    reads exactly like a running organ to anyone skimming.

    So this asserts BOTH halves: the organ is defined, AND `lifespan` creates a task for it.
    """
    main_py = (ROOT / "server" / "agora" / "main.py").read_text(encoding="utf-8", errors="replace")
    assert "async def receipt_rot_loop" in main_py, "the receipt organ is gone"
    assert "loop.create_task(receipt_rot_loop(app))" in main_py, (
        "receipt_rot_loop is DEFINED but never STARTED — a gate nobody calls is not a gate")


def test_the_organ_reports_only_state_changes_not_a_daily_all_clear():
    """A daily 'all good' is a message nobody reads by week three, and then the one that matters
    arrives in the same shape as the noise. Pin that it speaks on transitions."""
    main_py = (ROOT / "server" / "agora" / "main.py").read_text(encoding="utf-8", errors="replace")
    organ = main_py.split("async def receipt_rot_loop", 1)[1].split("\nasync def ", 1)[0]
    assert "if broke or healed:" in organ, "the organ would message on every run, not on change"
    assert "prev.get(" in organ, "no previous state is consulted, so nothing can be a transition"


def test_every_waiver_states_a_reason_and_a_date():
    p = ROOT / "tools" / "receipt_waivers.json"
    if not p.exists():
        pytest.skip("no waivers yet")
    for path, w in json.loads(p.read_text(encoding="utf-8")).items():
        if path.startswith("_"):
            continue
        assert w.get("verdicts"), f"{path}: waiver names no verdict"
        assert len(w.get("reason", "")) > 40, f"{path}: reason too thin to review"
        assert w.get("dated"), f"{path}: no date"
