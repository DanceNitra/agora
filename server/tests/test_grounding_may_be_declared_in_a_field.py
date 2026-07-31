"""Evidence declared in a FIELD is evidence. Requiring it in prose measures formatting.

The gate's bar is a Lab receipt PLUS a stated outcome, or a real citation. It read both halves out of
the record's joined TEXT, so it wanted the literal strings "lab <hex>" and "MEASURED:"/"VERDICT:".

Measured 2026-07-31: every `.theory.json` record carries `lab: "1d6e1a"` and
`verdict: "unmodelable"` -- the receipt and the outcome, each in its own column, which is the most
explicit form available -- and scored GROUNDED 0. `.analogies.json` passed on identical evidence
purely because it writes "[Lab 6ba1f0]" into its note text. Same organ, same run, opposite verdicts,
decided by prose style. High Priest Orin went from FAIL to PASS on data that had not changed.

This is NOT a softening, and the vocabulary check is what makes that true: an arbitrary string in a
field called `verdict` proves nothing, so a declared verdict counts only when its value is one of
THAT ledger's own words. Both halves are still required.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "probes"))
sys.path.insert(0, str(REPO / "server"))

import swarm_health as G  # noqa: E402

SPEC = dict(verdict_fields=("verdict", "outcome", "status"),
            decisive=("corroborated", "unmodelable", "survived"),
            inconclusive=("hypothesized", "queued"))


class _Parts(dict):
    """Only `grounding.is_cited` is consulted for the citation branch."""
    def __init__(self):
        from agora.execution import grounding
        super().__init__(grounding=grounding)


PARTS = _Parts()


def test_a_record_declaring_both_halves_is_grounded():
    rec = {"lab": "1d6e1a", "verdict": "unmodelable", "title": "Insight: alternative data alpha"}
    assert G.grounding_of(G.record_text(rec, SPEC), PARTS, rec, SPEC) == "lab+measured"


def test_prose_still_works():
    """The original form must keep passing -- this adds a second way, it does not replace the first."""
    txt = "MEASURED: rate 0.19 VERDICT: HOLDS (lab a1b2c3)"
    assert G.grounding_of(txt, PARTS, None, SPEC) == "lab+measured"


def test_a_lab_id_alone_is_not_grounding():
    """Both halves are still required: a receipt with no stated outcome is not a finding."""
    rec = {"lab": "1d6e1a", "title": "something happened"}
    assert G.grounding_of(G.record_text(rec, SPEC), PARTS, rec, SPEC) == ""


def test_a_verdict_alone_is_not_grounding():
    rec = {"verdict": "corroborated", "title": "something happened"}
    assert G.grounding_of(G.record_text(rec, SPEC), PARTS, rec, SPEC) == ""


def test_an_arbitrary_string_in_a_verdict_field_proves_nothing():
    """The guard against softening: the value must be one of the ledger's OWN words."""
    rec = {"lab": "1d6e1a", "verdict": "we had a look and it seemed fine"}
    assert G.grounding_of(G.record_text(rec, SPEC), PARTS, rec, SPEC) == ""


def test_a_lab_field_must_hold_a_real_id():
    """Six hex characters, the shape lab.py actually mints. Not a year, not a word."""
    for bad in ("2026", "pending", "n/a", "", "zzzzzz", "1d6e1a7"):
        assert G.declared_lab({"lab": bad}) == "", "accepted %r as a Lab id" % bad
    assert G.declared_lab({"lab": "1d6e1a"}) == "1d6e1a"
    assert G.declared_lab({"lab_id": " 432fe2 "}) == "432fe2"


def test_the_live_theory_records_are_now_grounded():
    """The case that motivated this, read from the live store rather than invented."""
    import json
    p = REPO / "server" / ".theory.json"
    if not p.exists():
        import pytest
        pytest.skip("no theory ledger")
    raw = json.loads(p.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else next((v for v in raw.values() if isinstance(v, list)), [])
    recs = [r for r in items if isinstance(r, dict) and r.get("lab")]
    if not recs:
        import pytest
        pytest.skip("no theory record carries a lab field")
    spec = G.LEDGERS[".theory.json"]
    grounded = [r for r in recs if G.grounding_of(G.record_text(r, spec), PARTS, r, spec)]
    assert grounded, ("no .theory.json record scores as grounded, yet %d carry a lab id and a "
                      "verdict in their own fields" % len(recs))
