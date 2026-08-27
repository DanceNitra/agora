"""The organ registry must not be able to go silently blind.

Every failure this module has ever produced was the same shape: an organ that WAS working read as
idle, because the registry did not speak its language, and the error was then reported to the owner
as a broken agent. It happened to Wren (11 decisive, read as 0), Orin (10, read as 1), Elara (93 in
one day, read as 0), and on 2026-07-31 to Kael (55 scout-box records, read as 0 -- every one of them
dropped by the window filter because the store writes found_ts/taken_ts/closed_ts and never `ts`).

The defect is always a MISSING ENTRY, and a missing entry looks exactly like an honest zero. These
tests make it look like a red test instead:

  1. every organ in _ORGANS has a vocabulary in _DECISIVE  -- no organ can report idle for lack of words
  2. every agent named is one of the 8 canonical NPC_UUIDS names -- no organ can be owned by a typo
  3. all 8 agents are covered, with the right dungeon eid -- no agent can fall out of the registry
  4. the inconclusive guard still says NO -- an alarm that cannot say no is not an alarm
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agora.agent_os.agent_os import NPC_UUIDS
from agora.execution import repair_ledger as rl


def test_every_organ_has_a_decisive_vocabulary():
    """THE regression this file exists for: an organ with no words reports a working agent as idle."""
    missing = [store for store in rl._ORGANS if not rl._DECISIVE.get(store)]
    assert missing == [], (
        f"{missing} have no _DECISIVE vocabulary -- every record in them will read as inconclusive "
        f"and their owner will be reported to the owner as producing nothing")


def test_decisive_has_no_vocabulary_for_an_organ_that_does_not_exist():
    """The other direction: a stale vocabulary key is a rename nobody finished."""
    orphans = sorted(set(rl._DECISIVE) - set(rl._ORGANS))
    assert orphans == [], f"{orphans} have a vocabulary but no organ in _ORGANS"


def test_every_agent_named_is_a_canonical_roster_name():
    """A name that is not in NPC_UUIDS joins to nothing -- not to the DB `contributor_name`, not to
    the dungeon. The Seminar is the one deliberate non-member: it is all eight, co-producing."""
    named = {o.agent for o in rl._ORGANS.values()} - {rl.SEMINAR}
    assert named <= set(NPC_UUIDS), f"not canonical NPC_UUIDS names: {sorted(named - set(NPC_UUIDS))}"


def test_the_roster_constant_matches_npc_uuids():
    """ROSTER is duplicated here rather than imported (agent_os pulls in the DB layer). This is the
    pin that stops the duplicate from drifting."""
    assert set(rl.ROSTER) == set(NPC_UUIDS)
    assert len(rl.ROSTER) == 8


def test_all_eight_agents_have_an_organ():
    """Half the roster went unwatched once, and an agent absent from the registry cannot starve
    VISIBLY -- the silence read as 'produces nothing'."""
    covered = {o.agent for o in rl._ORGANS.values()}
    assert set(rl.ROSTER) - covered == set(), f"unwatched: {sorted(set(rl.ROSTER) - covered)}"
    assert rl.starvation_report()["unwatched_agents"] == []


def test_agent_eid_covers_the_roster_and_matches_the_dungeon_ids():
    """The eid is the join key a sibling probe imports instead of duplicating this map."""
    assert set(rl.AGENT_EID) == set(rl.ROSTER)
    assert rl.AGENT_EID == {"Shadow Kael": "thief", "Sage Mira": "scholar",
                            "High Priest Orin": "priest", "King Aldric": "king",
                            "Dame Elara": "guard_r", "Sergeant Voss": "guard_l",
                            "Artificer Rooke": "artificer", "Cartographer Wren": "cartographer"}


def test_each_organ_can_actually_score_its_own_verdicts():
    """A vocabulary that is present but unreachable is the same bug wearing a coat. One synthetic
    record per organ, built from that organ's OWN first word, must read decisive."""
    for store, words in rl._DECISIVE.items():
        if store == ".contributions.json":
            assert rl._is_decisive({"claim": "x", "verified": True}, store) is True
            assert rl._is_decisive({"claim": "x", "verified": False}, store) is False
            continue
        for w in words:
            assert rl._is_decisive({"outcome": w}, store) is True, f"{store} cannot score {w!r}"


def test_no_inconclusive_word_is_a_prefix_of_a_decisive_one():
    """THE CLASS, not the instance. The guard matches with startswith, so a short inconclusive word
    silently eats a longer decisive one: "draft" (press, work started) swallowed "drafted" (scout,
    a contribution written), and a working organ would have read as idle again -- this time caused
    by an EXTRA word rather than a missing one. Splitting _INCONCLUSIVE per organ fixed the case;
    this pins every future case."""
    for store, words in rl._DECISIVE.items():
        guards = rl._INCONCLUSIVE_ANY + rl._INCONCLUSIVE.get(store, ())
        for w in words:
            eaten = [g for g in guards if w.startswith(g)]
            assert eaten == [], f"{store}: decisive {w!r} is swallowed by inconclusive {eaten}"


def test_boolean_flags_are_read_as_verdicts():
    """`kill: true` stringified to 'True' and matched nothing, so the flag that literally says a
    belief was killed was invisible to the word scan."""
    assert rl._is_decisive({"verdict": "", "kill": True}, ".bounty.json") is True
    assert rl._is_decisive({"beat_market": True}, ".oracle.json") is True
    assert rl._is_decisive({"beat_market": False}, ".oracle.json") is False


def test_the_inconclusive_guard_still_says_no():
    """Work STARTED is not work DECIDED. An instrument that cannot say no is not an instrument."""
    assert rl._is_decisive({"outcome": "hypothesized", "status": "charted"}, ".cartography.json") is False
    assert rl._is_decisive({"status": "taken"}, ".scout_box.json") is False
    assert rl._is_decisive({"status": "draft"}, ".press.json") is False
    assert rl._is_decisive({"status": "open"}, ".oracle.json") is False


def test_confirming_verdicts_are_decisive_but_not_corrective():
    """The distinction the ledger was built on: a stream of confirmations is not the same
    contribution as one refutation. Adding 'reproduced'/'survived' to the vocabulary must not merge
    them."""
    assert rl._is_decisive({"outcome": "REPRODUCED"}, ".replications.json") is True
    assert rl._is_corrective({"outcome": "REPRODUCED"}, ".replications.json") is False
    assert rl._is_corrective({"outcome": "FAILED"}, ".replications.json") is True
    assert rl._is_decisive({"verdict": "survived"}, ".bounty.json") is True
    assert rl._is_corrective({"verdict": "survived"}, ".bounty.json") is False


def test_a_store_without_a_ts_field_still_reaches_the_ledger():
    """Kael's 55 scout-box records were dropped by the window filter for want of a `ts` -- the same
    'reads idle while working' failure, arriving through the clock instead of the vocabulary."""
    organ = rl._ORGANS[".scout_box.json"]
    assert "ts" not in organ.ts_fields
    now = 1_800_000_000.0
    assert rl._ts({"found_ts": now}, organ.ts_fields) == now
    assert rl._ts({"found_ts": 1.0, "closed_ts": now}, organ.ts_fields) == now, "newest field wins"
    assert rl._ts({}, organ.ts_fields) == 0.0


def test_the_eid_belongs_to_who_acted_not_to_the_store():
    """Voss kills beliefs that are buried in Aldric's graveyard, so `killed_by` names Voss on
    Aldric's store. Reading the eid off the organ gave Voss the eid 'king'."""
    assert rl.AGENT_EID["Sergeant Voss"] == "guard_l"
    assert rl._ORGANS[".graveyard.json"].eid == "king"
    assert rl._ORGANS[".graveyard.json"].actor_field == "killed_by"


def test_the_report_is_ascii(tmp_path, monkeypatch):
    """The Telegram path and a cp1250 console both choke on anything else."""
    monkeypatch.setattr(rl, "_ROOT", tmp_path)      # no stores -> the empty-ledger branch
    out = rl.format_repair_ledger(14.0)
    out.encode("ascii")
    assert "NOBODY repaired anything" in out
