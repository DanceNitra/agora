"""A survival with no evidence is indistinguishable from a challenge that could never have killed.

The bounty record used to be `{verdict, kill, target, by, ts}` and nothing else. So "survived" asserted
that a belief had been attacked while keeping no trace of WHAT it survived, which is exactly the failure
Voss's own academy lesson names: a challenge that could not kill is not a test. It also made the record
unusable to the acceptance gate, which asks for a lab id or a citation and correctly found neither.

An `evidence` field was threaded through the organ, the endpoint and the ledger. Measured 2026-08-01:
**0 of 32 records carry it.** The plumbing landed after the last challenge ran, so the whole path had
never once executed -- code that looks right and has never been exercised, which is the shape this repo
keeps paying for. Verified here by driving it on a COPY of the ledger rather than trusting the reading.

The last assertion is the one that matters: it checks the evidence against the SAME grounding detector
the acceptance gate uses, so "the field is populated" cannot pass while "the gate can read it" fails.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "server"))

from agora.execution import bounty as B  # noqa: E402
from agora.execution.grounding import is_measured, lab_id  # noqa: E402

EVIDENCE = "lab c9dbc6 | observed_delta=0.1900, n=100, p=0.0078, 20000 trials"


@pytest.fixture()
def ledger(tmp_path, monkeypatch):
    """A COPY. The live ledger is the owner's record of every challenge ever resolved."""
    p = tmp_path / "bounty.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(B, "_STORE", p)
    return p


def test_the_evidence_survives_the_round_trip(ledger):
    B.record_challenge("survived", "insight-some-belief", "Sergeant Voss", evidence=EVIDENCE)
    rec = json.loads(ledger.read_text(encoding="utf-8"))[-1]
    assert rec.get("evidence"), "the receipt was dropped between the call and the file"
    assert "c9dbc6" in rec["evidence"]


def test_the_gate_can_read_what_was_stored(ledger):
    """THE ASSERTION THAT MATTERS. A populated field the acceptance gate cannot parse is not grounding;
    this checks it with the gate's own detector rather than a local rule."""
    B.record_challenge("survived", "insight-some-belief", "Sergeant Voss", evidence=EVIDENCE)
    ev = json.loads(ledger.read_text(encoding="utf-8"))[-1]["evidence"]
    assert lab_id(ev) == "c9dbc6", "the shared grounding detector cannot find the lab id in %r" % ev
    assert is_measured(ev)


def test_an_unevidenced_challenge_is_still_recorded_but_reads_as_ungrounded(ledger):
    """The organ must stay able to record an honest ruling it could not ground. What must NOT happen
    is that ruling looking grounded."""
    B.record_challenge("survived", "insight-other", "Sergeant Voss", evidence="")
    rec = json.loads(ledger.read_text(encoding="utf-8"))[-1]
    assert rec["verdict"] == "survived", "an unevidenced ruling was silently discarded"
    assert not is_measured(rec.get("evidence") or ""), "an empty receipt reads as measured"


def test_prose_is_not_mistaken_for_a_receipt(ledger):
    """The over-correction guard: the endpoint falls back to `reason` when no explicit evidence is
    passed, and `reason` is prose. Prose must not read as a measurement."""
    B.record_challenge("survived", "insight-third", "Sergeant Voss",
                       evidence="the argument holds up well under scrutiny and seems robust")
    ev = json.loads(ledger.read_text(encoding="utf-8"))[-1]["evidence"]
    assert lab_id(ev) is None
    assert not is_measured(ev), "a prose reason was accepted as a measured result"


def test_a_kill_is_flagged_and_keeps_its_receipt(ledger):
    B.record_challenge("retired", "insight-dead", "Sergeant Voss", evidence=EVIDENCE)
    rec = json.loads(ledger.read_text(encoding="utf-8"))[-1]
    assert rec["kill"] is True
    assert lab_id(rec["evidence"]) == "c9dbc6"


def test_the_live_ledger_shows_the_path_had_never_run():
    """THE CONTROL, and it is allowed to go stale in ONE direction. It documents the measurement that
    motivated this file: 0 of 32 live records carried evidence. Once Voss runs a challenge under the
    fixed path this will start finding some, which is the point -- so it asserts only that the file is
    readable and reports the count, and fails only if the field vanishes from the schema entirely."""
    p = REPO / "server" / ".bounty.json"
    if not p.exists():
        pytest.skip("no live bounty ledger on this machine")
    items = json.loads(p.read_text(encoding="utf-8"))
    items = items if isinstance(items, list) else items.get("items") or []
    assert items, "the live ledger is empty; this control is examining nothing"
    evidenced = [r for r in items if isinstance(r, dict) and r.get("evidence")]
    print("\nlive bounty ledger: %d records, %d carry evidence" % (len(items), len(evidenced)))
    for r in evidenced:
        assert isinstance(r["evidence"], str), "the evidence field changed type under us"
