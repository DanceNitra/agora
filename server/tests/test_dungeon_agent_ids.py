"""`DUNGEON_AGENT_IDS` must cover every NPC — a missing name silently files work under a name.

Measured on the live agora.db 2026-07-31 (read-only) BEFORE this was fixed: `DUNGEON_AGENT_IDS`
listed 6 of the 8 dungeon agents. Artificer Rooke and Cartographer Wren were absent, even though
both have always been in `agent_os.NPC_UUIDS` and both already had rows in `dungeon_npcs` and
`agent_identities`.

Every caller resolves a name the same way — `DUNGEON_AGENT_IDS.get(npc_name) or npc_name`
(agent_os_api.py:322 and ~40 sibling call sites). The `or` fallback is what makes the omission
silent: instead of raising, it put the literal NAME into `npc_id`. `_get_npc_name()` then matched
no `dungeon_npcs` row, and `_contribute_to_collective` wrote `contributor_name = ""`.

Result: of 17,467 `collective_knowledge` rows, 3,007 carried a blank contributor — 1,417 under
"Artificer Rooke" and 1,590 under "Cartographer Wren" — with a name in `contributor_id` where
every other row holds a UUID. Two of the eight agents' output was invisible to every join keyed
on UUID, and to the reverse `UUID_TO_NAME` maps built in economy.py, agents.py, physical_api.py
and agent_os_api.py.

These tests pin the invariant. Deleting either added entry must turn them RED.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agora.agent_os.agent_os import NPC_DEFS, NPC_UUIDS
from agora.api.dungeon import DUNGEON_AGENT_IDS, DUNGEON_AGENT_ROLES


def test_dungeon_agent_ids_covers_every_npc():
    """Every NPC in NPC_UUIDS must have an id entry — this is the falsification control."""
    missing = set(NPC_UUIDS) - set(DUNGEON_AGENT_IDS)
    assert not missing, (
        f"NPCs missing from DUNGEON_AGENT_IDS: {sorted(missing)} - their npc_id will fall back "
        f"to the literal name and their contributions will be stored with a blank contributor"
    )
    assert set(NPC_UUIDS) <= set(DUNGEON_AGENT_IDS)


def test_shared_names_map_to_the_same_uuid():
    """A name present in both maps must resolve to the SAME uuid in both."""
    disagreements = {
        name: (NPC_UUIDS[name], DUNGEON_AGENT_IDS[name])
        for name in set(NPC_UUIDS) & set(DUNGEON_AGENT_IDS)
        if NPC_UUIDS[name] != DUNGEON_AGENT_IDS[name]
    }
    assert not disagreements, f"uuid disagreement (NPC_UUIDS, DUNGEON_AGENT_IDS): {disagreements}"


def test_uuids_are_distinct():
    """Reverse maps are built as {uuid: name}; a duplicated uuid would drop an agent."""
    ids = list(DUNGEON_AGENT_IDS.values())
    assert len(ids) == len(set(ids)), f"duplicate uuid in DUNGEON_AGENT_IDS: {ids}"


def test_every_agent_has_an_explicit_role():
    """`_ensure_dungeon_agents_seeded` falls back to 'explorer' when the role is missing."""
    missing = set(DUNGEON_AGENT_IDS) - set(DUNGEON_AGENT_ROLES)
    assert not missing, f"agents with no explicit role (would seed as 'explorer'): {sorted(missing)}"


def test_roles_match_the_npc_definitions():
    """The role in DUNGEON_AGENT_ROLES must be the role the NPC is actually defined with."""
    mismatches = {
        name: (NPC_DEFS[name]["role"], DUNGEON_AGENT_ROLES[name])
        for name in set(NPC_DEFS) & set(DUNGEON_AGENT_ROLES)
        if NPC_DEFS[name]["role"] != DUNGEON_AGENT_ROLES[name]
    }
    assert not mismatches, f"role disagreement (NPC_DEFS, DUNGEON_AGENT_ROLES): {mismatches}"


def test_live_resolution_never_falls_back_to_a_name():
    """Reproduce the exact production expression and assert it yields a uuid for all 8 agents.

    This is the bug in its original shape: `.get(name) or name` cannot fail loudly, so the only
    way to catch it is to check that what comes out is a uuid and not the name that went in.
    """
    for name in NPC_UUIDS:
        npc_id = DUNGEON_AGENT_IDS.get(name) or name  # agent_os_api.py:322
        assert npc_id != name, f"{name} resolved to its own name - the id lookup fell through"
        assert npc_id == NPC_UUIDS[name]
