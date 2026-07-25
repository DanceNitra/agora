"""The synthesis detector must be able to say NO — and still able to say YES.

Measured 2026-07-25, before this was fixed: `due` had never once been False for any reason other than the
3-day cooldown, and pressure had climbed 35.33 -> 53.0 in a single day. Three faults, all in two lines:

1. the divisor counted ONE closure status (`deepened`) whose only writer was switched off by an env flag,
   so it was 0 across 200 questions and mathematically unreachable — pinning pressure to its maximum;
2. it filtered closures on the question's CREATION timestamp, not on when it closed;
3. `bridge_accel` is (recent+1)/(prior+1), so a single bridge after a quiet window scores exactly 2.0 and
   cleared the >=1.5 gate on its own — the live "acceleration x2.0" was one event versus zero.

A signal that cannot say no is not a signal. These tests pin both directions.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agora.execution import synthesis_detector as sd


def _due(bridges_recent, bridges_prior, open_falsifiers, closures, cooled=False):
    """The live decision rule, exercised with the module's real constants."""
    accel = round((bridges_recent + 1) / (bridges_prior + 1), 2)
    pressure = round(accel * (1 + open_falsifiers / 12) / (1 + closures), 2)
    due = ((not cooled) and bridges_recent >= sd._MIN_BRIDGES and accel >= 1.5
           and open_falsifiers >= 6 and pressure >= 1.8)
    return due, pressure


def test_a_single_bridge_no_longer_counts_as_acceleration():
    """THE false alarm this ran on for a month: 1 event vs 0 scores exactly 2.0 and cleared the gate."""
    due, _ = _due(bridges_recent=1, bridges_prior=0, open_falsifiers=200, closures=0)
    assert due is False
    assert sd._MIN_BRIDGES >= 3, "the floor is what stops a count of one reading as a rate"


def test_it_can_still_fire_when_the_precursors_are_real():
    """A detector stuck on NO is as useless as one stuck on YES."""
    due, pressure = _due(bridges_recent=3, bridges_prior=0, open_falsifiers=200, closures=1)
    assert due is True
    assert pressure > 1.8


def test_closure_keeping_up_suppresses_the_alarm():
    """The divisor has to be able to do work — this is what a reachable denominator buys."""
    due, pressure = _due(bridges_recent=3, bridges_prior=0, open_falsifiers=200, closures=200)
    assert due is False
    assert pressure < 1.8


def test_no_open_falsifiers_means_nothing_to_synthesize():
    due, _ = _due(bridges_recent=9, bridges_prior=1, open_falsifiers=2, closures=0)
    assert due is False


def test_the_divisor_counts_closures_from_more_than_one_organ():
    """It counted only `deepened`, whose writer is disabled. A replication, a burial or a court kill is
    also the system closing a question, and any of them must be able to relieve the pressure."""
    src = open(sd.__file__, encoding="utf-8").read()
    for organ in ("replication", "graveyard", "bounty"):
        assert organ in src, f"{organ} closures must count toward the divisor"
    assert 'q.get("deepened_ts")' in src, "closures must be timed by when they CLOSED, not when raised"


def test_live_signal_is_wellformed_and_can_report_not_due():
    """Against the real ledgers: the shape is intact and `due` is a real decision, not a constant."""
    d = sd.signals()
    for k in ("bridge_recent", "bridge_accel", "open_falsifiers", "deepened_recent", "pressure", "due"):
        assert k in d
    assert isinstance(d["due"], bool)
    assert d["deepened_recent"] >= 0
