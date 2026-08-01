"""A decisive record that names somebody else is not this agent's output.

The acceptance gate rosters a ledger to an agent and counted EVERY decisive row in it toward that
agent. That is right for a single-writer store and an over-credit otherwise.

Audited across all nine rostered ledgers on 2026-08-01:

    .scout_box.json        59 records   Shadow Kael 59
    .contradictions.json  300 records   Dame Elara 300
    .bounty.json           33 records   Sergeant Voss 21 | Claude (severe-test) 7 |
                                        Shadow Kael 4 | Claude (self red-team) 1
    (the other six name nobody at all)

So Sergeant Voss was creditable for twelve challenges he did not run. His PASS on the day this was
found did not rest on them -- both of his in-window records are his own, checked -- but the door was
open, and the gate is the instrument that decides whether the swarm is working.

The fix only ever REMOVES credit. An unnamed record still counts for the roster owner, which is the
correct reading for the six stores that name nobody. Applying it changed no verdict on the live data,
which is the point: it confirms the seven passes were already resting on their owners' own records.

Recorded for the same reason as the rest of this file's siblings: an hour before this, I nearly made
the opposite mistake -- pointing King Aldric's roster at `.predictions.json`, a store the tournament
path writes 200 of 242 records to, which would have shown him seven decisive outcomes that were not
his. Both directions are the same defect.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("sh", REPO / "probes" / "swarm_health.py")
sh = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(REPO / "server"))
_spec.loader.exec_module(sh)


def _rows(actor: str, decisive: bool = True):
    """One in-window row shaped the way `evaluate` consumes them."""
    return {"rec": {"verdict": "survived", "by": actor}, "ts": 9e9, "in_window": True,
            "decisive": decisive, "actor": actor, "grounding": "lab+measured"}


def test_the_guard_is_in_the_counting_loop():
    """THE CONTROL. If the check moves or is renamed, every assertion below stops examining it."""
    src = (REPO / "probes" / "swarm_health.py").read_text(encoding="utf-8")
    assert '_act.lower() != name.lower()' in src, (
        "the foreign-writer skip is gone from evaluate(); a rostered ledger credits its owner for "
        "every writer again")


def test_the_bounty_ledger_really_does_have_foreign_writers():
    """THE FIXTURE CONTROL, on live data. If this store becomes single-writer the defect described
    here stops existing and the guard is no longer load-bearing -- worth learning, not hiding."""
    p = REPO / "server" / ".bounty.json"
    if not p.exists():
        pytest.skip("no live bounty ledger on this machine")
    items = json.loads(p.read_text(encoding="utf-8"))
    items = items if isinstance(items, list) else items.get("items") or []
    foreign = [r for r in items if isinstance(r, dict)
               and (r.get("by") or "").strip()
               and (r.get("by") or "").strip().lower() != "sergeant voss"]
    assert foreign, ("`.bounty.json` no longer carries a foreign writer -- re-measure before trusting "
                     "that this guard still closes anything")
    print("\nforeign writers in .bounty.json: %d of %d" % (len(foreign), len(items)))


@pytest.mark.parametrize("actor,counted", [
    ("Sergeant Voss", True),
    ("sergeant voss", True),                  # case is not identity
    ("Claude (severe-test)", False),
    ("Shadow Kael", False),
    ("", True),                               # unnamed: the roster owner is the right reading
])
def test_only_the_owners_rows_count(actor, counted, monkeypatch):
    """Drives `evaluate` directly on a synthetic ledger so the assertion is about the counter, not
    about whatever the live stores happen to hold today."""
    name = "Sergeant Voss"
    led = {".bounty.json": {"rows": [_rows(actor)], "total": 1, "no_ts": 0}}
    db = {"per_agent": {name: {"discoveries": 0, "named": 0, "id_only": 0, "grounded": 0}},
          "rows_in_window": 0, "table_rows": 0, "unattributed_rows": 0}
    monkeypatch.setattr(sh, "ROSTER", ((("guard_l"), name, "Quality Assurance", (".bounty.json",)),))
    for other in [a for a in sh.ROSTER if a[1] != name]:
        db["per_agent"][other[1]] = {"discoveries": 0, "named": 0, "id_only": 0, "grounded": 0}
    out = sh.evaluate(db, led, 24.0)
    row = next(r for r in out if r["agent"] == name)
    assert (row["decisive"] >= 1) is counted, (
        "actor %r: decisive counted=%s, expected %s -- a foreign writer's verdict is being scored as "
        "this agent's work" % (actor, row["decisive"], counted))


def test_an_unnamed_store_still_credits_its_owner():
    """The over-correction guard. Six of the nine rostered ledgers name nobody; if the skip caught
    those, every one of their owners would drop to zero and the gate would report a dead swarm."""
    src = (REPO / "probes" / "swarm_health.py").read_text(encoding="utf-8")
    assert 'if _act and _act.lower() != name.lower():' in src, (
        "the skip no longer requires a NON-EMPTY actor, so unnamed records stop counting for anyone")
