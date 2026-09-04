"""The Map-maker's domains must come from MEANING, because vocabulary measures the template.

`find_hole` maps the OWNER'S vault taxonomy. That map is real but it is not the research frontier,
and the consumer's board gate refuses every pair it yields — measured 2026-07-31, 0 of 47 domain
labels matched the board and all 68 accumulated charts were off-mission.

Five replacement corpora were measured and rejected before this one; the fifth is the reason these
tests exist. Sharing a WORD looked like a superb signal: over 999 Lab records, questions mentioning
"agent" and questions mentioning "recall" had **zero** overlap, verified twice by raw substring. The
cause was not a research gap — the two sets are different method templates (`method:info-cascade`
vs `method:bandit-regret`). Word co-occurrence measures which template ran, not what was studied.

So domains are embedding clusters, and both thresholds are calibrated rather than chosen:
cluster 0.42 collapses 188 of 225 questions into one blob and 0.58 fragments to 36% coverage, so
0.50 (12 domains, 84% covered); bridge 0.45 leaves 0 holes of 66 and 0.70 leaves 61, so 0.60 (24).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agora.execution import cartography as C  # noqa: E402


def test_the_template_prefix_is_stripped_from_a_question():
    """The artifact that killed approach 5. A `method:<slug>` prefix must never reach the embedder,
    or the clusters reproduce the template partition instead of the subject."""
    qs = C._measured_questions()
    if not qs:
        pytest.skip("no lab ledger on this machine")
    assert not any(q["q"].startswith("method:") for q in qs), (
        "a template slug survived into the corpus: %s"
        % [q["q"][:40] for q in qs if q["q"].startswith("method:")][:3])


def test_questions_are_deduplicated():
    qs = C._measured_questions()
    if not qs:
        pytest.skip("no lab ledger")
    keys = [q["q"].lower()[:80] for q in qs]
    assert len(keys) == len(set(keys)), "the same question was mapped twice"


def test_the_thresholds_stay_where_they_were_calibrated():
    """Pins the two numbers to the sweep that produced them. Moving either without re-running it is
    how a gate stops meaning anything -- 0.45 makes every pair bridged, 0.70 makes none."""
    assert C._CLUSTER_THR == 0.50
    assert C._BRIDGE_THR == 0.60
    assert C._BRIDGE_THR > C._CLUSTER_THR, (
        "a bridge must be a STRICTER claim than membership; otherwise every member of a cluster "
        "also bridges to its neighbour and no hole can exist")


def test_a_missing_embedder_starves_rather_than_invents(monkeypatch):
    """An unreachable embedder must produce NO map. A guessed map is worse than none: the organ
    would chart holes that were never measured and the receipts would point at nothing."""
    import agora.execution.semantic_index as si
    # PRECONDITION, CHECKED BEFORE THE PATCH, NEVER AFTER THE ASSERTION. research_map() returns
    # early with "too few measured questions to map" when the store has no measurements, which is
    # the state of any fresh checkout, so the embedder branch is never reached and this test would
    # report a failure about a code path it never entered. Skipping on the input rather than on the
    # outcome is the difference between an honest skip and a hidden one.
    if "too few measured questions" in (C.research_map().get("note") or ""):
        pytest.skip("no measured questions in this environment; the embedder branch is unreachable")
    monkeypatch.setattr(si, "_embed_batch", lambda texts: None)
    m = C.research_map()
    assert m["domains"] == []
    assert "embedder" in (m.get("note") or "").lower()
    assert C.find_research_hole() is None


def test_a_hole_carries_receipts(tmp_path):
    """A charted hole must name the Lab ids behind both sides, or it is an assertion rather than a
    finding -- the same bar every other organ is held to."""
    h = C.find_research_hole()
    if h is None:
        pytest.skip("no workable hole on this corpus right now")
    assert h["a_size"] >= C._MIN_DOMAIN and h["b_size"] >= C._MIN_DOMAIN
    assert h["a_labs"] and h["b_labs"], "a hole with no lab receipts is not evidence"
    assert h["bridges"] == 0 or h["score"] < 1.0


def test_a_hole_can_pass_the_gate_that_will_receive_it():
    """The failure this whole source exists to end: charting work the consumer must refuse. The
    previous source produced 68 such charts and the selector re-offered the same eight forever."""
    h = C.find_research_hole()
    if h is None:
        pytest.skip("no workable hole right now")
    from agora.execution.board import priorities_text
    from agora.execution.methods import board_priority_terms, _theme_tokens
    prio = board_priority_terms(priorities_text())
    if not prio:
        pytest.skip("no board set")
    # exactly the string the consumer gates on, truncated the way record_charted truncates it
    assert _theme_tokens("%s x %s" % (h["a"][:40], h["b"][:40])) & prio, (
        "charted a hole the board gate will refuse: %s x %s" % (h["a"][:40], h["b"][:40]))


def test_retirement_is_reversible_and_dry_by_default(tmp_path, monkeypatch):
    store = tmp_path / "c.json"
    store.write_text(json.dumps([{"id": "a1", "a": "X", "b": "Y", "outcome": "hypothesized"}]),
                     encoding="utf-8")
    monkeypatch.setattr(C, "_STORE", store)
    assert C.retire_off_board("why")["applied"] is False
    assert json.loads(store.read_text(encoding="utf-8"))[0]["outcome"] == "hypothesized"
    C.retire_off_board("why", apply=True)
    rec = json.loads(store.read_text(encoding="utf-8"))[0]
    assert rec["outcome"] == "off-board" and rec["resolved_ts"] > 0
    assert "why" in rec["note"], "a retirement must record its reason"
