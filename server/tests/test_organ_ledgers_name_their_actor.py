"""An organ that closes work anonymously cannot be credited, and an uncredited agent reads as idle.

Measured 2026-07-31 by the swarm acceptance gate: Dame Elara had closed 94 contradictions in the
previous 24 hours and Shadow Kael had ruled on 3 scout leads, and BOTH were scored FAIL for "no named
actor" -- `.contradictions.json` and `.scout_box.json` recorded everything about the work except who did
it. Earlier the same day a vault-side count had reported five of eight agents as producing nothing; two
of those five turned out to be the busiest in the keep. The defect was attribution, not absence -- the
same shape as Rooke and Wren carrying a blank `contributor_name` on 3,007 rows.

These tests pin the write path, not the data: a record written today must name its owner, and the owner
named must be the one `repair_ledger._ORGANS` assigns. Two independent places state that ownership, so
they are asserted against each other rather than each being trusted alone.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agora.execution import contradictions, scout                 # noqa: E402

#: (module, ledger filename). The module declares OWNER; repair_ledger maps the ledger to an agent.
ORGANS = [
    (contradictions, ".contradictions.json"),
    (scout, ".scout_box.json"),
]


@pytest.mark.parametrize("mod,ledger", ORGANS)
def test_the_module_declares_an_owner(mod, ledger):
    owner = getattr(mod, "OWNER", None)
    assert isinstance(owner, str) and owner.strip(), (
        "%s writes %s but declares no OWNER -- every record it appends would be anonymous" % (mod.__name__, ledger))


@pytest.mark.parametrize("mod,ledger", ORGANS)
def test_the_declared_owner_matches_the_organ_map(mod, ledger):
    """Two places state who owns this organ. If they ever disagree, credit silently splits in two."""
    from agora.execution import repair_ledger

    organs = getattr(repair_ledger, "_ORGANS", {})
    entry = organs.get(ledger)
    if entry is None:
        pytest.skip("%s is not in repair_ledger._ORGANS yet" % ledger)
    mapped = entry[0] if isinstance(entry, (tuple, list)) else entry
    assert mod.OWNER == mapped, (
        "%s declares OWNER=%r but repair_ledger._ORGANS maps %s to %r. The ledger and the organ map "
        "must name the same agent or the work is credited to two different people."
        % (mod.__name__, mod.OWNER, ledger, mapped))


def test_a_new_contradiction_record_names_its_actor(tmp_path, monkeypatch):
    """THE regression. The record used to carry a, b, sim, contradict, claim, status and ts -- every
    field except who ruled. 94 decisive outcomes in one day were unattributable because of it."""
    store = tmp_path / ".contradictions.json"
    monkeypatch.setattr(contradictions, "_STORE", store)
    contradictions._save([{"id": "abc123", "a": "Note A", "b": "Note B", "sim": 0.9,
                           "contradict": True, "claim": "they disagree",
                           "by": contradictions.OWNER, "status": "open", "ts": 0.0}])
    rec = contradictions._load()[-1]
    assert rec.get("by") == contradictions.OWNER


def test_a_new_scout_record_names_its_actor(tmp_path, monkeypatch):
    """Same regression on the other ledger. box_add() is the only write path for a new lead."""
    box = tmp_path / ".scout_box.json"
    monkeypatch.setattr(scout, "_BOX", box)
    monkeypatch.setattr(scout, "_about_memory", lambda lead: True)
    rec = scout.box_add({"url": "https://example.org/issues/1", "repo": "x/y",
                         "title": "agent memory recall", "score": 3})
    assert rec is not None, "box_add refused a valid lead; the fixture is wrong, not the code"
    assert rec.get("by") == scout.OWNER
    assert scout.box_load()[-1].get("by") == scout.OWNER


def test_closing_an_old_record_still_names_the_owner(tmp_path, monkeypatch):
    """Records written BEFORE `by` existed are closed by box_mark. Without the setdefault they would
    close anonymously forever, so the backlog would keep failing the gate after the fix shipped."""
    box = tmp_path / ".scout_box.json"
    monkeypatch.setattr(scout, "_BOX", box)
    scout._box_save([{"url": "https://example.org/issues/2", "status": "open", "found_ts": 0.0}])
    assert scout.box_mark("https://example.org/issues/2", "no_fit") is True
    rec = scout.box_load()[-1]
    assert rec["status"] == "no_fit"
    assert rec.get("by") == scout.OWNER, "a legacy record closed without naming who closed it"
