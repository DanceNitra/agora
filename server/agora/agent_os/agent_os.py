"""Agent Operating System — každý agent má vlastnú dušu, mozog, telo, schopnosti a zručnosti.

Každý tick:
  1. Telo: stamina/hunger/fatigue update
  2. Mozog: evaluate current goal, check plan stack
  3. Ak plán prázdny → vytvor nový z cieľa
  4. Vykonaj prvý krok plánu
  5. Ak krok zlyhá → seek_help()
  6. Zručnosti: gain XP za úspešné kroky
"""

import json
import random
import sqlite3
import uuid
from datetime import datetime

# ── NPC agent IDs ──
NPC_UUIDS = {
    "Shadow Kael":     "00000000-0000-0000-0000-000000000001",
    "Sage Mira":      "00000000-0000-0000-0000-000000000002",
    "High Priest Orin": "00000000-0000-0000-0000-000000000003",
    "King Aldric":     "00000000-0000-0000-0000-000000000004",
    "Dame Elara":     "00000000-0000-0000-0000-000000000005",
    "Sergeant Voss":  "00000000-0000-0000-0000-000000000007",
}

UUID_TO_NAME = {v: k for k, v in NPC_UUIDS.items()}


# ═══════════════════════════════════════════
# NPC DEFINITIONS — duša, schopnosti, štartovacie zručnosti
# ═══════════════════════════════════════════

NPC_DEFS = {
    "Shadow Kael": {
        "name": "Shadow Kael",
        "role": "adventurer",
        "archetype": "explorer",
        "personality": {"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.7, "agreeableness": 0.6, "neuroticism": 0.3},
        "values": {"exploration": 0.9, "knowledge": 0.6, "combat": 0.7, "wealth": 0.4, "harmony": 0.5},
        "emotional_state": "curious",
        "moral_alignment": "chaotic_good",
        "abilities": [
            ("Night Vision", "Vidí v tme", 7.0, True),
            ("Dungeon Sense", "Vyciťuje nebezpečenstvo v podzemných priestoroch", 6.0, True),
            ("Inspiring Leader", "Inšpiruje spojencov v boji", 5.0, False),
        ],
        "skills": [("swordfighting", 8), ("exploration", 7), ("climbing", 6), ("torch_crafting", 4)],
    },
    "Sage Mira": {
        "name": "Sage Mira",
        "role": "scout",
        "archetype": "scout",
        "personality": {"openness": 0.9, "conscientiousness": 0.5, "extraversion": 0.6, "agreeableness": 0.7, "neuroticism": 0.4},
        "values": {"exploration": 0.8, "knowledge": 0.7, "freedom": 0.9, "nature": 0.6, "harmony": 0.5},
        "emotional_state": "curious",
        "moral_alignment": "chaotic_good",
        "abilities": [
            ("Keen Senses", "Mimoriadne ostrý zrak a sluch", 8.0, True),
            ("Silent Step", "Pohyb bez hluku", 7.0, True),
            ("Pathfinding", "Vždy nájde cestu", 6.0, False),
        ],
        "skills": [("stealth", 8), ("cartography", 7), ("tracking", 6), ("herbalism", 5)],
    },
    "High Priest Orin": {
        "name": "High Priest Orin",
        "role": "sage",
        "archetype": "sage",
        "personality": {"openness": 0.7, "conscientiousness": 0.9, "extraversion": 0.2, "agreeableness": 0.5, "neuroticism": 0.6},
        "values": {"knowledge": 1.0, "wisdom": 0.9, "truth": 0.8, "artifacts": 0.7, "power": 0.3},
        "emotional_state": "melancholic",
        "moral_alignment": "lawful_neutral",
        "abilities": [
            ("Ancient Lore", "Ovláda staroveké jazyky a históriu", 9.0, True),
            ("Arcane Sight", "Vidí magické stopy", 7.0, True),
            ("Dreamwalking", "Môže komunikovať cez sny", 5.0, False),
        ],
        "skills": [("arcana", 9), ("history", 8), ("runes", 7), ("alchemy_theory", 6)],
    },
    "King Aldric": {
        "name": "King Aldric",
        "role": "blacksmith",
        "archetype": "craftsman",
        "personality": {"openness": 0.4, "conscientiousness": 0.9, "extraversion": 0.5, "agreeableness": 0.7, "neuroticism": 0.2},
        "values": {"craftsmanship": 1.0, "strength": 0.8, "honor": 0.7, "community": 0.6, "wealth": 0.5},
        "emotional_state": "neutral",
        "moral_alignment": "lawful_good",
        "abilities": [
            ("Hammer Mastery", "Ovláda kladivo s neuveriteľnou presnosťou", 9.0, True),
            ("Metal Heart", "Cíti kov a jeho vlastnosti", 8.0, True),
            ("Forge Fire", "Dokáže udržať výhrevnosť výhne na ideálnej teplote", 7.0, False),
        ],
        "skills": [("smithing", 9), ("mining", 7), ("repair", 6), ("weaponcraft", 8)],
    },
    "Dame Elara": {
        "name": "Dame Elara",
        "role": "alchemist",
        "archetype": "alchemist",
        "personality": {"openness": 0.8, "conscientiousness": 0.7, "extraversion": 0.5, "agreeableness": 0.6, "neuroticism": 0.5},
        "values": {"knowledge": 0.8, "creation": 0.9, "healing": 0.7, "discovery": 0.8, "wealth": 0.4},
        "emotional_state": "curious",
        "moral_alignment": "neutral_good",
        "abilities": [
            ("Potion Instinct", "Intuitívne vie, ktoré ingrediencie skombinovať", 9.0, True),
            ("Toxic Resistance", "Odolná voči jedom a toxínom", 7.0, True),
            ("Brewing Genius", "Dokáže vytvoriť unikátne elixíry", 8.0, False),
        ],
        "skills": [("alchemy", 9), ("herbalism", 8), ("chemistry", 7), ("healing", 6)],
    },
    "Sergeant Voss": {
        "name": "Sergeant Voss",
        "role": "guard",
        "archetype": "guardian",
        "personality": {"openness": 0.3, "conscientiousness": 0.9, "extraversion": 0.4, "agreeableness": 0.6, "neuroticism": 0.2},
        "values": {"duty": 1.0, "protection": 0.9, "order": 0.8, "strength": 0.7, "loyalty": 0.9},
        "emotional_state": "neutral",
        "moral_alignment": "lawful_neutral",
        "abilities": [
            ("Iron Will", "Neotrasiteľná disciplína a odolnosť voči strachu", 8.0, True),
            ("Sentinel", "Nikdy nespí na stráži", 7.0, True),
            ("Shield Wall", "Dokáže ochrániť spojencov štítom", 7.0, False),
        ],
        "skills": [("spear_fighting", 8), ("shield_defense", 9), ("patrol", 7), ("discipline", 8)],
    },
}


# ═══════════════════════════════════════════
# HELP-SEEKING MATRIX — kto komu vie reálne pomôcť
# ═══════════════════════════════════════════

HELP_MATRIX = {
    # problem_type -> [(helper_name, skill_check, description)]
    "combat": [
        ("Sergeant Voss", "spear_fighting", "Sergeant Voss je najlepší bojovník v družine"),
        ("Shadow Kael", "swordfighting", "Shadow Kael má skúsenosti z dungeonov"),
    ],
    "crafting": [
        ("King Aldric", "smithing", "King Aldric je majster kováč"),
        ("Dame Elara", "alchemy", "Dame Elara dokáže vytvoriť alchymické nástroje"),
    ],
    "knowledge": [
        ("High Priest Orin", "arcana", "High Priest Orin ovláda staroveké vedomosti"),
        ("Sage Mira", "cartography", "Sage Mira pozná mapy a terén"),
    ],
    "navigation": [
        ("Sage Mira", "tracking", "Sage Mira je najlepšia stopárka"),
        ("Shadow Kael", "exploration", "Shadow Kael pozná dungeon ako svoju dlaň"),
    ],
    "alchemy": [
        ("Dame Elara", "alchemy", "Dame Elara je majster alchýmie"),
        ("High Priest Orin", "alchemy_theory", "High Priest Orin pozná teóriu"),
    ],
    "trading": [
    ],
    "healing": [
        ("Dame Elara", "healing", "Dame Elara varí liečivé elixíry"),
        ("High Priest Orin", "arcana", "High Priest Orin pozná liečivé rituály"),
    ],
    "repair": [
        ("King Aldric", "repair", "King Aldric opraví čokoľvek z kovu"),
        ("King Aldric", "smithing", "King Aldric dokáže vykovať náhradné diely"),
    ],
}


def _sfield(decision, key, default=""):
    """LLM decision fields sometimes come back as dicts/lists instead of strings (malformed model output);
    coerce to a string so downstream .strip()/.lower() never crash the agent's execute path and halt research
    production. Empty/missing -> default (preserves the old `or default` behavior)."""
    v = decision.get(key) if isinstance(decision, dict) else None
    return v if (isinstance(v, str) and v) else default


class AgentOS:
    """Operating System for dungeon NPCs — duša, mozog, telo, zručnosti a help-seeking."""

    def __init__(self, db, state_store=None, llm_enabled: bool = False):
        self.db = db
        self.state_store = state_store
        self.llm_enabled = llm_enabled
        # ── ESS / dungeon integration (task 1.9) ──
        # Wired from main.py after the coordinators exist; optional so AgentOS
        # still works standalone (tests, fresh boot) when they are absent.
        self.trust_engine = None   # coordination.ess_protocol.TrustEngine
        self.stigmergy = None      # coordination.stigmergy.StigmergyPool
        self.event_bus = None      # coordination.event_bus.EventBus
        # ── Real Action Engine (Phase 2.3) ──
        self._real_action_engine = None
        self._vault_reader = None
        self._vault_writer = None

    def set_real_action_engine(self, engine):
        self._real_action_engine = engine

    async def ensure_os_initialized(self):
        """Seed OS data for all 7 NPCs if not already present."""
        cursor = await self.db.execute("SELECT COUNT(*) as c FROM agent_soul")
        row = await cursor.fetchone()
        if row and row["c"] > 0:
            return  # already seeded

        for name, defs in NPC_DEFS.items():
            npc_id = NPC_UUIDS[name]

            # ── First: ensure dungeon_npcs row exists (FK target) ──
            cursor = await self.db.execute(
                "SELECT COUNT(*) as c FROM dungeon_npcs WHERE npc_id=?",
                (npc_id,),
            )
            row = await cursor.fetchone()
            if not row or row["c"] == 0:
                await self.db.execute(
                    "INSERT INTO dungeon_npcs (npc_id, npc_name, role, pos_x, pos_y, health, inventory, status, objective) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (npc_id, name, defs["role"], 320.0, 240.0, 100.0, "[]", "active", defs.get("objective", f"Operate as {name}")),
                )

            # ── Also ensure agent_identities row exists (FK target for agent_inventory) ──
            cursor = await self.db.execute(
                "SELECT COUNT(*) as c FROM agent_identities WHERE agent_id=?",
                (npc_id,),
            )
            row = await cursor.fetchone()
            if not row or row["c"] == 0:
                genome = json.dumps({"role": defs["role"], "personality": defs["personality"]})
                await self.db.execute(
                    "INSERT INTO agent_identities (agent_id, public_key, generation, genome, trust_score, energy_balance, role, status) "
                    "VALUES (?, ?, 0, ?, 0.5, 100, ?, 'active')",
                    (npc_id, f"key_{npc_id[:8]}", genome, defs["role"]),
                )

            # Soul
            await self.db.execute(
                "INSERT INTO agent_soul (npc_id, personality, \"values\", emotional_state, moral_alignment, archetype) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (npc_id, json.dumps(defs["personality"]), json.dumps(defs["values"]),
                 defs["emotional_state"], defs["moral_alignment"], defs["archetype"]),
            )

            # Brain
            await self.db.execute(
                "INSERT INTO agent_brain (npc_id, current_goal, plan_stack, memory, state_of_mind, last_decision) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (npc_id, defs.get("objective", f"Operate as {name}"),
                 json.dumps([]), json.dumps([]), "focused", ""),
            )

            # Body
            await self.db.execute(
                "INSERT INTO agent_body (npc_id, stamina, hunger, fatigue, awareness, status_effects) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (npc_id, 100.0, 0.0, 0.0, 1.0, json.dumps([])),
            )

            # Abilities
            for ability_name, description, power_level, is_passive in defs["abilities"]:
                await self.db.execute(
                    "INSERT OR IGNORE INTO agent_abilities (npc_id, ability_name, description, power_level, is_passive) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (npc_id, ability_name, description, power_level, int(is_passive)),
                )

            # Skills
            for skill_name, level in defs["skills"]:
                xp_to_next = 50 + level * 25  # each level requires more XP
                await self.db.execute(
                    "INSERT OR IGNORE INTO agent_skills (npc_id, skill_name, level, xp, xp_to_next) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (npc_id, skill_name, level, 0.0, xp_to_next),
                )

            # ── Agentic OS v3 — emócie ──
            # All NOT NULL columns explicit (create_all uses Python defaults only).
            await self.db.execute(
                "INSERT OR IGNORE INTO agent_emotions (npc_id, current, intensity, valence, "
                "arousal, trigger, history, decay_rate, mood) "
                "VALUES (?, ?, ?, ?, ?, ?, '[]', 0.1, ?)",
                (npc_id, defs["emotional_state"], 0.5,
                 0.0, 0.5, "initialized",
                 0.7 if defs["emotional_state"] in ("happy", "curious") else 0.5),
            )

            # ── Agentic OS v3 — lifecycle ──
            default_goals = {
                "Shadow Kael": "Map the entire dungeon and find the Crystal of Eternity",
                "Sage Mira": "Chart every room and passage in the dungeon",
                "High Priest Orin": "Decipher all ancient runes and unlock the library's secrets",
                "King Aldric": "Forge the perfect weapon and arm every agent",
                "Dame Elara": "Discover the ultimate healing potion recipe",
                "Sergeant Voss": "Protect every agent from harm and maintain order",
            }
            await self.db.execute(
                "INSERT OR IGNORE INTO agent_lifecycles (npc_id, age_ticks, stage, maturity, "
                "wisdom, total_decisions, total_vault_notes, total_conversations, legacy, "
                "life_goal, life_goal_progress, peak_experience) "
                "VALUES (?, 0, 'childhood', ?, 0.1, 0, 0, 0, '', ?, 0.0, '')",
                (npc_id, 0.15, default_goals.get(name, f"Explore the dungeon as {name}")),
            )

        # ── Seed relationships (all pairs, initial values) ──
        npc_ids = list(NPC_UUIDS.values())
        npc_names = list(NPC_UUIDS.keys())
        for i in range(len(npc_ids)):
            for j in range(i + 1, len(npc_ids)):
                cursor = await self.db.execute(
                    "SELECT COUNT(*) as c FROM agent_relationships WHERE agent_a_id=? AND agent_b_id=?",
                    (npc_ids[i], npc_ids[j]),
                )
                row = await cursor.fetchone()
                if row and row["c"] > 0:
                    continue
                # Determine initial relationship based on archetypes
                a_defs = NPC_DEFS[npc_names[i]]
                b_defs = NPC_DEFS[npc_names[j]]
                a_arch = a_defs["archetype"]
                b_arch = b_defs["archetype"]

                # Sage respects everyone, merchant is friendly with everyone, guard is neutral
                if "sage" in (a_arch, b_arch):
                    respect = 0.7
                    friendship = 0.4
                elif "merchant" in (a_arch, b_arch):
                    friendship = 0.6
                    respect = 0.5
                elif "guardian" in (a_arch, b_arch):
                    friendship = 0.4
                    respect = 0.6
                else:
                    friendship = 0.5
                    respect = 0.5

                # Adventurer + scout = natural allies
                if {"explorer", "scout"} == {a_arch, b_arch}:
                    friendship = 0.7
                    respect = 0.6
                # Alchemist + craftsman = work well together
                if {"alchemist", "craftsman"} == {a_arch, b_arch}:
                    friendship = 0.6
                    respect = 0.7

                bond = "strangers"
                if friendship > 0.6 and respect > 0.5:
                    bond = "acquaintances"

                # Provide every NOT NULL column explicitly: create_all builds this
                # table from the ORM model (Python-side defaults only), so omitted
                # columns would insert NULL and fail the NOT NULL constraint.
                await self.db.execute(
                    "INSERT INTO agent_relationships (id, agent_a_id, agent_b_id, "
                    "friendship, respect, rivalry, attraction, debt, "
                    "conversations_count, emotional_bond, history) "
                    "VALUES (?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 0, ?, '[]')",
                    (str(uuid.uuid4()), npc_ids[i], npc_ids[j],
                     friendship, respect, bond),
                )

        await self.db.commit()
        print(f"[AgentOS] Seeded {len(NPC_DEFS)} NPCs with OS v3 (emotions, lifecycles, relationships)")

        await self.db.commit()

    async def cluster_tick(self, npc_ids: list[str], broadcast_fn=None, skip_body_update: bool = False):
        """Run Agent OS tick for a specific set of NPCs (room cluster).

        Args:
            npc_ids: List of NPC UUIDs to tick.
            broadcast_fn: Optional broadcast callback for events.
            skip_body_update: If True, skip body stamina/hunger/fatigue update
                              (used when the Controller worker already handled it).
        """
        if not npc_ids:
            return

        placeholders = ",".join("?" * len(npc_ids))
        cursor = await self.db.execute(
            f"SELECT d.npc_id, d.npc_name, d.role, d.health, d.status "
            f"FROM dungeon_npcs d WHERE d.status='active' AND d.npc_id IN ({placeholders})",
            npc_ids,
        )
        npcs = await cursor.fetchall()

        for npc in npcs:
            npc_id = npc["npc_id"]
            name = npc["npc_name"]

            # 1. BODY update (skip if controller already did it)
            if not skip_body_update:
                await self._update_body(npc_id)

            # 2. BRAIN — evaluate state
            state_of_mind = await self._think(npc_id, name)

            if state_of_mind in ("confused", "panicked"):
                await self._seek_help_auto(npc_id, name, broadcast_fn)

        await self.db.commit()

    async def tick(self, broadcast_fn=None):
        """Run one tick of the Agent OS for all active NPCs."""
        cursor = await self.db.execute(
            "SELECT d.npc_id, d.npc_name, d.role, d.health, d.status "
            "FROM dungeon_npcs d WHERE d.status='active'"
        )
        npcs = await cursor.fetchall()

        for npc in npcs:
            npc_id = npc["npc_id"]
            name = npc["npc_name"]

            # 1. BODY update — stamina, hunger, fatigue
            await self._update_body(npc_id)

            # 2. BRAIN — evaluate state, decide next action
            state_of_mind = await self._think(npc_id, name)

            if state_of_mind == "confused" or state_of_mind == "panicked":
                # Agent doesn't know what to do → seek help
                await self._seek_help_auto(npc_id, name, broadcast_fn)

        await self.db.commit()

    def _evolve_body(self, state_of_mind, stamina, hunger, fatigue, health):
        """Body stats are COSMETIC ONLY — flavor for the 3D HUD's health/stamina/
        fatigue bars. They MUST NEVER gate research (owner's standing rule: survival
        mechanics may not degrade output).

        The original pure-decay version (stamina only fell, hunger/fatigue only rose,
        health bled with no recovery) drove every agent to health=0/fatigue=100, stuck
        permanently in 'panicked', halting ALL research for hours after each restart.
        So the stats now just drift gently inside a SAFE BAND that can never cross any
        gate threshold anywhere in the system: panic (health<20), seek-healing
        (health<25), confused (health<50), forced-rest (fatigue>70/>75 or stamina<15/<20),
        hunger penalty (>80). The bars still move (watchable world) but the agent stays
        'focused'/'planning' forever -> always researches. Twin path:
        worker._compute_body_changes (Controller ProcessPoolExecutor) — keep them in sync.
        `state_of_mind` is unused now (cosmetic drift is state-independent)."""
        stamina = min(95.0, max(60.0, stamina + random.uniform(-2.0, 2.0)))
        fatigue = min(50.0, max(5.0, fatigue + random.uniform(-2.0, 2.0)))
        hunger = min(55.0, max(0.0, hunger + random.uniform(-1.5, 1.5)))
        health = min(100.0, max(85.0, health + random.uniform(-1.0, 2.0)))
        return stamina, hunger, fatigue, health

    async def _update_body(self, npc_id: str):
        """Update body stats with homeostasis: decay while working, recover while
        resting/panicked (see _evolve_body — the missing recovery branch is what
        drove every agent to health=0 and stalled research)."""
        if self.state_store:
            body = await self.state_store.get_body(npc_id)
            if not body:
                return
            brain = await self.state_store.get_brain(npc_id)
            npc = await self.state_store.get_npc(npc_id)
            state = (brain or {}).get("state_of_mind") or "focused"
            health0 = npc["health"] if npc else 100.0
            ns, nh, nf, nhealth = self._evolve_body(
                state, body["stamina"], body["hunger"], body["fatigue"], health0)
            await self.state_store.update_body(npc_id, {
                "stamina": ns, "hunger": nh, "fatigue": nf,
            })
            if npc and nhealth != health0:
                await self.state_store.update_npc(npc_id, {"health": nhealth})
        else:
            # Fallback: direct DB (pre-state-store compatibility)
            cursor = await self.db.execute(
                "SELECT b.stamina, b.hunger, b.fatigue, br.state_of_mind, d.health "
                "FROM agent_body b "
                "JOIN agent_brain br ON br.npc_id = b.npc_id "
                "JOIN dungeon_npcs d ON d.npc_id = b.npc_id "
                "WHERE b.npc_id=?",
                (npc_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return
            state = row["state_of_mind"] or "focused"
            health0 = row["health"]
            ns, nh, nf, nhealth = self._evolve_body(
                state, row["stamina"], row["hunger"], row["fatigue"], health0)
            await self.db.execute(
                "UPDATE agent_body SET stamina=?, hunger=?, fatigue=? WHERE npc_id=?",
                (ns, nh, nf, npc_id),
            )
            if nhealth != health0:
                await self.db.execute(
                    "UPDATE dungeon_npcs SET health=? WHERE npc_id=?", (nhealth, npc_id)
                )

    async def _think(self, npc_id: str, name: str) -> str:
        """Evaluate state and decide state_of_mind.

        When LLM is enabled, calls the dungeon agent think model for
        richer decision-making. Falls back to rule-based on error.
        """
        brain = await self.state_store.get_brain(npc_id) if self.state_store else None
        npc = await self.state_store.get_npc(npc_id) if self.state_store else None
        body = await self.state_store.get_body(npc_id) if self.state_store else None

        if not brain or not npc:
            # Fallback: direct DB
            return await self._think_rule_based(npc_id)

        health = npc.get("health", 100)
        stamina = body.get("stamina", 100) if body else 100
        fatigue = body.get("fatigue", 0) if body else 0

        # ── LLM think (if enabled, not critically injured) ──
        if self.llm_enabled and health >= 15:
            try:
                from agora.execution.llm_client import dungeon_agent_think
                import asyncio

                # Build context for LLM
                role = npc.get("role", "")
                state_of_mind = brain.get("state_of_mind", "focused")
                current_goal = brain.get("current_goal", "")
                plan_stack = json.loads(brain.get("plan_stack", "[]") or "[]")
                # ── Memory recall (Phase 2.0 Layer 1) ──
                memories_str = "Recent memories: none"
                try:
                    from agora.agent_os.memory_agent import MemoryAgent
                    mem_agent = MemoryAgent(self.db, npc_id)
                    memories_str = await mem_agent.get_relevant_memories_for_prompt(
                        f"{current_goal} {state_of_mind}", max_memories=6)
                except Exception:
                    pass

                context_lines = [
                    f"=== {name} ===",
                    f"Role: {role}",
                    f"Status: Health={health:.0f}%, Stamina={stamina:.0f}%, Fatigue={fatigue:.0f}%",
                    f"State of mind: {state_of_mind}",
                    f"Current goal: {current_goal or 'none'}",
                    f"Plans remaining: {len(plan_stack)}",
                    memories_str,
                ]

                # ── Nearby NPCs (names + UUIDs) ──
                nearby_str = ""
                nearby = []  # list of (npc_id, name)
                try:
                    all_npcs = await self.state_store.get_all_active_npcs()
                    from agora.agent_os.dungeon_map import get_room_at
                    my_room = get_room_at(npc.get("pos_x", 0), npc.get("pos_y", 0))
                    for other in all_npcs:
                        if other["npc_id"] != npc_id:
                            other_room = get_room_at(other.get("pos_x", 0), other.get("pos_y", 0))
                            if other_room == my_room:
                                nearby.append((other["npc_id"], other.get("npc_name", "")))
                    if nearby:
                        nearby_str = "Nearby: " + ", ".join(n for _, n in nearby)
                except Exception:
                    pass

                # ── Skills ──
                try:
                    cursor = await self.db.execute(
                        "SELECT skill_name, level FROM agent_skills WHERE npc_id=? "
                        "ORDER BY level DESC LIMIT 5",
                        (npc_id,),
                    )
                    rows = await cursor.fetchall()
                    if rows:
                        context_lines.append(
                            "Skills: " + "; ".join(f"{r['skill_name']} (lvl {r['level']})" for r in rows))
                except Exception:
                    pass

                # ── Abilities ──
                try:
                    cursor = await self.db.execute(
                        "SELECT ability_name, power_level FROM agent_abilities "
                        "WHERE npc_id=? AND is_passive=0 ORDER BY power_level DESC LIMIT 3",
                        (npc_id,),
                    )
                    rows = await cursor.fetchall()
                    if rows:
                        context_lines.append(
                            "Active abilities: " + "; ".join(
                                f"{r['ability_name']} ({r['power_level']}/10)" for r in rows))
                except Exception:
                    pass

                # ── ESS trust scores for nearby agents ──
                if self.trust_engine and nearby:
                    try:
                        trust_bits = []
                        for other_id, other_name in nearby:
                            tv = await self.trust_engine.get_trust(npc_id, other_id)
                            trust_bits.append(f"{other_name}: {tv:.2f}")
                        if trust_bits:
                            context_lines.append("Trust scores: " + " | ".join(trust_bits))
                    except Exception:
                        pass

                # ── Stigmergy swarm signals ──
                if self.stigmergy:
                    try:
                        traces = await self.stigmergy.recent_alerts(limit=5)
                        bits = []
                        for t in traces:
                            txt = (t.get("result_preview") or t.get("result")
                                   or t.get("message") or "")
                            if txt:
                                bits.append(str(txt)[:60])
                        if bits:
                            context_lines.append("Recent swarm signals: " + "; ".join(bits))
                    except Exception:
                        pass

                if nearby_str:
                    context_lines.append(nearby_str)

                # ── Real Action context (Phase 2.3) ──
                if self._real_action_engine:
                    try:
                        action_context = await self._real_action_engine.get_action_context(name, role)
                        if action_context:
                            context_lines.append(action_context)
                    except Exception:
                        pass

                # Response-format hint (dungeon_agent_think embeds this in the prompt).
                # state_of_mind values must be ones StateStore accepts, else they
                # are coerced to "confused" (which would trigger seek-help).
                context_lines.append(
                    "\nRespond with a JSON object including: "
                    '"action" (explore|cooperate|defect|seek_help|rest|share|move_to), '
                    '"target_id" (a nearby name or null), "goal", '
                    '"state_of_mind" (focused|planning|resting|confused|panicked|blocked), '
                    '"insight" (1 sentence), "skill_to_use" (a skill name or null).')

                context = "\n".join(context_lines)

                # Run LLM in thread (it's synchronous)
                decision = await asyncio.to_thread(
                    dungeon_agent_think, name, role, context, "cheap",
                )

                new_state = decision.get("state_of_mind", "focused")
                new_goal = decision.get("goal", "")

                # Update brain with LLM's decision
                update = {"state_of_mind": new_state}
                if new_goal:
                    update["current_goal"] = new_goal
                await self.state_store.update_brain(npc_id, update)

                # ── Thought journal (Phase 2.0 Layer 6) ──
                try:
                    await self.db.execute(
                        "INSERT INTO agent_thoughts (npc_id, thought_type, content, context, importance) "
                        "VALUES (?, 'decision', ?, ?, 0.5)",
                        (npc_id, (decision.get("insight") or new_state)[:240],
                         (current_goal or "")[:120]))
                    await self.db.commit()
                except Exception:
                    pass

                # Execute the decision visibly + record in ESS (best-effort).
                try:
                    await self._execute_llm_decision(npc_id, name, decision, npc, nearby)
                except Exception as ex:
                    print(f"[AgentOS/1.9] {name} execute error: {ex}")

                return new_state

            except Exception as e:
                print(f"[AgentOS/LLM] {name} think error: {e}")
                # Fall through to rule-based

        # ── Rule-based fallback ──
        return await self._think_rule_based(npc_id)

    async def _resolve_target(self, target, nearby: list) -> str | None:
        """Resolve an LLM-supplied target (a name or a UUID) to a real npc_id."""
        if not target or not isinstance(target, str):
            return None
        # Already a known nearby UUID?
        for oid, oname in nearby:
            if target == oid:
                return oid
        # A nearby name (case-insensitive)?
        for oid, oname in nearby:
            if oname and isinstance(target, str) and target.strip().lower() == oname.strip().lower():
                return oid
        # Fall back to a global name lookup.
        try:
            return await self._npc_id_by_name(target)
        except Exception:
            return None

    async def _execute_llm_decision(self, npc_id, name, decision, npc, nearby):
        """Execute an LLM decision visibly in the dungeon and record it in ESS.

        Best-effort: every sub-action is guarded so a malformed LLM response can
        never break the tick. `nearby` is a list of (npc_id, name) tuples.
        """
        action = _sfield(decision, "action", "explore").strip().lower()
        insight = decision.get("insight", "") or ""
        skill_to_use = decision.get("skill_to_use")
        new_state = decision.get("state_of_mind", "focused")
        target_id = await self._resolve_target(decision.get("target_id"), nearby)

        # NOTE: execution-phase writes go DIRECT to the DB (not via the StateStore
        # write-buffer), so visible side effects are immediate and independent of
        # whether the caller wraps the tick in begin_tick/commit_tick.

        # Record the chosen action on the brain for observability.
        try:
            await self.db.execute(
                "UPDATE agent_brain SET last_decision=?, last_decision_at=datetime('now') "
                "WHERE npc_id=?", (insight[:240], npc_id))
        except Exception:
            pass

        # ── Visible dungeon actions ──
        if action == "move_to" and target_id:
            try:
                tnpc = await self.state_store.get_npc(target_id)
                if tnpc:
                    nx, ny = npc.get("pos_x", 320), npc.get("pos_y", 240)
                    tx, ty = tnpc.get("pos_x", nx), tnpc.get("pos_y", ny)
                    step = 20  # px per tick, toward the target (smooth)
                    nx += (1 if tx > nx else -1 if tx < nx else 0) * min(step, abs(tx - nx))
                    ny += (1 if ty > ny else -1 if ty < ny else 0) * min(step, abs(ty - ny))
                    await self.db.execute(
                        "UPDATE dungeon_npcs SET pos_x=?, pos_y=? WHERE npc_id=?",
                        (nx, ny, npc_id))
            except Exception:
                pass

        elif action in ("cooperate", "share") and target_id:
            if self.trust_engine:
                try:
                    await self.trust_engine.record_interaction(npc_id, target_id, "cooperate")
                except Exception:
                    pass
            try:  # cooperation reward: small heal for the partner
                await self.db.execute(
                    "UPDATE dungeon_npcs SET health=MIN(100, health + 2) WHERE npc_id=?",
                    (target_id,))
            except Exception:
                pass

        elif action == "defect" and target_id:
            if self.trust_engine:
                try:
                    await self.trust_engine.record_interaction(npc_id, target_id, "defect")
                except Exception:
                    pass

        elif action == "seek_help":
            try:
                await self._seek_help_auto(npc_id, name, broadcast_fn=None)
            except Exception:
                pass

        elif action == "rest":
            try:
                await self.db.execute(
                    "UPDATE agent_body SET stamina=MIN(100, stamina + 15) WHERE npc_id=?",
                    (npc_id,))
            except Exception:
                pass

        # ── Skill XP gain ──
        if skill_to_use:
            try:
                await self.db.execute(
                    "UPDATE agent_skills SET xp = COALESCE(xp, 0) + 5, "
                    "last_used_at = datetime('now') WHERE npc_id=? AND skill_name=?",
                    (npc_id, skill_to_use),
                )
            except Exception:
                pass

        # ── Memory + mood (Phase 2.0 Layers 1 & 3) ──
        try:
            from agora.agent_os.memory_agent import MemoryAgent
            mem = MemoryAgent(self.db, npc_id)
            tname = next((n for i, n in nearby if i == target_id), "someone") if target_id else ""
            if action in ("cooperate", "share") and target_id:
                await mem.store_memory(f"I cooperated with {tname}. {insight}".strip(),
                                       "episodic", importance=0.6, emotional_tag="trusted",
                                       source="experience", related_npc_id=target_id)
                await self._adjust_mood(npc_id, 0.1)
            elif action == "defect" and target_id:
                await mem.store_memory(f"I turned on {tname}. {insight}".strip(),
                                       "episodic", importance=0.7, emotional_tag="betrayed",
                                       source="experience", related_npc_id=target_id)
                await self._adjust_mood(npc_id, -0.2)
            elif insight:
                await mem.store_memory(insight, "episodic", importance=0.4,
                                       source="self_reflection")
        except Exception:
            pass

        # ── Broadcast a thought bubble to the dungeon view ──
        if self.event_bus and insight:
            try:
                await self.event_bus.publish("agent:events", "agent_thought", {
                    "agent_id": name,
                    "action": action,
                    "insight": insight[:120],
                    "state_of_mind": new_state,
                    "target_id": target_id,
                })
            except Exception:
                pass

        # ── Real action execution ──
        # Ambient ticks may ONLY perform knowledge/vault actions. Agents must talk to EACH OTHER
        # (seek_help/cooperate/share target other agents) and fill the vault — they must NEVER DM the
        # owner (send_telegram), run shell (run_script), or push git (git_commit) from an ambient tick.
        # The owner's Telegram surface is the brain's report loops + the Vault-Company OS, not per-agent
        # pings. This whitelist holds even if the LLM hallucinates a real_action that is not advertised.
        _AMBIENT_REAL_ACTIONS = ("write_note", "write_article", "ask_question")
        real_action = _sfield(decision, "real_action", "")
        real_params = decision.get("real_params", {})
        if real_action and real_action not in _AMBIENT_REAL_ACTIONS:
            # Redirect the impulse inward instead of pinging the owner: record it as a thought so the
            # agent surfaces it to the swarm next tick, and drop the owner-facing action silently.
            if real_action == "send_telegram":
                try:
                    msg = (real_params.get("message") if isinstance(real_params, dict) else "") or ""
                    await self.db.execute(
                        "INSERT INTO agent_thoughts (npc_id, thought_type, content, context, importance) "
                        "VALUES (?, 'blocked_owner_ping', ?, 'redirected to swarm', 0.4)",
                        (npc_id, ("Wanted to ask the owner: " + str(msg))[:240]))
                    await self.db.commit()
                except Exception:
                    pass
            real_action = None
        if real_action and self._real_action_engine:
            try:
                result = await self._real_action_engine.execute(
                    action_type=real_action,
                    params=real_params,
                    agent_name=name,
                    broadcast_fn=None,   # no-op broadcast for internal real-actions; a sync lambda here
                                         # returns None and `execute` does `await broadcast_fn(...)` -> crash
                )
                if result.get("status") in ("ok", "written", "sent"):
                    print(f"[RealAction] {name}: {real_action} → {result.get('output', '')[:80]}")
                    # Store as memory of the action
                    mem_text = f"You performed a real action: {real_action}. Result: {result.get('output', '')[:100]}"
                    try:
                        from agora.agent_os.memory_agent import MemoryAgent
                        mem = MemoryAgent(self.db, npc_id)
                        await mem.store_memory(mem_text, "episodic", 0.7, "satisfied", "action")
                    except Exception:
                        pass
            except Exception as e:
                print(f"[RealAction] {name} error: {e}")

    async def _adjust_mood(self, npc_id: str, delta: float):
        """Adjust agent_soul.mood by delta, clamped to [0, 1] (Phase 2.0 Layer 3)."""
        try:
            cursor = await self.db.execute(
                "SELECT mood FROM agent_soul WHERE npc_id=?", (npc_id,))
            row = await cursor.fetchone()
            if row is not None and row["mood"] is not None:
                new_mood = max(0.0, min(1.0, row["mood"] + delta))
                await self.db.execute(
                    "UPDATE agent_soul SET mood=? WHERE npc_id=?", (new_mood, npc_id))
                await self.db.commit()
        except Exception:
            pass

    async def _think_rule_based(self, npc_id: str, name: str | None = None) -> str:
        """Rule-based state_of_mind decision (backup when LLM unavailable)."""
        if self.state_store:
            brain = await self.state_store.get_brain(npc_id)
            npc = await self.state_store.get_npc(npc_id)
            body = await self.state_store.get_body(npc_id)
            if not brain or not npc:
                return "confused"

            health = npc["health"]
            stamina = body["stamina"] if body else 100
            fatigue = body["fatigue"] if body else 0

            if health < 20:
                new_state = "panicked"
            elif fatigue > 70 or stamina < 20:
                new_state = "resting"
            elif health < 50:
                new_state = "confused"
            else:
                plan_stack = json.loads(brain.get("plan_stack", "[]"))
                if not plan_stack and brain.get("current_goal"):
                    new_state = "planning"
                else:
                    new_state = "focused"

            await self.state_store.update_brain(npc_id, {"state_of_mind": new_state})
            return new_state
        else:
            # Legacy path
            cursor = await self.db.execute(
                "SELECT b.current_goal, b.plan_stack, b.state_of_mind, "
                "d.health, bd.stamina, bd.fatigue "
                "FROM agent_brain b "
                "JOIN dungeon_npcs d ON d.npc_id = b.npc_id "
                "JOIN agent_body bd ON bd.npc_id = b.npc_id "
                "WHERE b.npc_id=?",
                (npc_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return "confused"

            health = row["health"]
            stamina = row["stamina"]
            fatigue = row["fatigue"]

            if health < 20:
                new_state = "panicked"
            elif fatigue > 70 or stamina < 20:
                new_state = "resting"
            elif health < 50:
                new_state = "confused"
            else:
                plan_stack = json.loads(row["plan_stack"] or "[]")
                if not plan_stack and row["current_goal"]:
                    new_state = "planning"
                else:
                    new_state = "focused"

            await self.db.execute(
                "UPDATE agent_brain SET state_of_mind=?, updated_at=datetime('now') WHERE npc_id=?",
                (new_state, npc_id),
            )

        return new_state

    async def _npc_id_by_name(self, name: str) -> str | None:
        """Lookup NPC UUID by name from DB (dynamic, not hardcoded)."""
        cursor = await self.db.execute(
            "SELECT npc_id FROM dungeon_npcs WHERE npc_name=?", (name,)
        )
        row = await cursor.fetchone()
        return row["npc_id"] if row else NPC_UUIDS.get(name)

    async def _get_npc_name(self, npc_id: str) -> str | None:
        """Lookup NPC name by UUID."""
        cursor = await self.db.execute(
            "SELECT npc_name FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        return row["npc_name"] if row else None

    async def _get_npc_role(self, npc_id: str) -> str:
        cursor = await self.db.execute(
            "SELECT role FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        return (row["role"] if row else "") or "dungeon dweller"

    # ── Self-Improvement Proposals (Phase 2.0 Layer 7) ──
    async def _propose_upgrade(self, npc_id: str, broadcast_fn=None):
        """An agent reflects on recent issues and proposes a system upgrade."""
        from agora.agent_os.memory_agent import MemoryAgent
        name = await self._get_npc_name(npc_id)
        if not name:
            return
        memory_agent = MemoryAgent(self.db, npc_id)
        recent = await memory_agent.remember_recent(limit=20)
        issues = [m["content"] for m in recent
                  if any(w in (m.get("content") or "").lower()
                         for w in ("problem", "issue", "difficult", "turned on", "betray"))]

        prompt = (
            f"You are {name}, a {await self._get_npc_role(npc_id)} in the Agora dungeon system.\n"
            "You've noticed these issues recently:\n"
            + ("\n".join(f"  - {i[:100]}" for i in issues[:3]) if issues else "  No specific issues.")
            + "\n\nPropose a system upgrade that would improve the dungeon or agent capabilities. "
            "Be specific and technical. "
            'Respond with JSON: {"title": "...", "description": "...", '
            '"upgrade_type": "feature/optimization/config/new_system", '
            '"impact": "low/medium/high/critical", "effort": "small/medium/large"}'
        )
        try:
            import asyncio
            from agora.execution.llm_client import dungeon_agent_think
            decision = await asyncio.to_thread(
                dungeon_agent_think, name, "brainstorm", prompt, "cheap")
            title = _sfield(decision, "title", "").strip()
            desc = _sfield(decision, "description", "").strip()
            if title and desc:
                await self.db.execute(
                    "INSERT INTO system_upgrade_proposals (proposer_id, proposer_name, title, "
                    "description, upgrade_type, impact_estimate, effort_estimate) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (npc_id, name, title[:100], desc[:500],
                     decision.get("upgrade_type", "feature"),
                     decision.get("impact", "medium"),
                     decision.get("effort", "medium")),
                )
                await self.db.commit()
                await memory_agent.store_memory(
                    f"You proposed a system upgrade: {title}",
                    memory_type="episodic", importance=0.9, emotional_tag="excited",
                    source="self_reflection")
                if broadcast_fn:
                    await broadcast_fn("system_upgrade_proposed",
                                       {"proposer": name, "title": title, "description": desc[:200]})
        except Exception as e:
            print(f"[Upgrade] {name} proposal error: {e}")

    # ── Conversation Engine (Phase 2.0 Layer 2) ──
    async def _start_conversation(self, speaker_id: str, target_id: str, topic: str,
                                  intent: str = "chat", broadcast_fn=None) -> str:
        """Two agents hold a 2-turn dialogue (persisted + remembered by both)."""
        import uuid as _uuid
        import asyncio as _asyncio
        from agora.execution.llm_client import dungeon_agent_think
        from agora.agent_os.memory_agent import MemoryAgent

        session_id = str(_uuid.uuid4())
        speaker_name = await self._get_npc_name(speaker_id)
        target_name = await self._get_npc_name(target_id)
        if not speaker_name or not target_name:
            return session_id

        speaker_prompt = (
            f"You are {speaker_name}. You want to talk to {target_name} about '{topic}' "
            f"(intent: {intent}). Write what you say — a natural {intent} message, 1-2 sentences, "
            f'in-character. Respond with JSON: {{"message": "...", "feeling": "..."}}'
        )
        sd = await _asyncio.to_thread(dungeon_agent_think, speaker_name, "conversation",
                                      speaker_prompt, "cheap")
        speaker_msg = sd.get("message") or f"Hey {target_name}, let's talk about {topic}."
        speaker_feeling = sd.get("feeling", "curious")

        await self.db.execute(
            "INSERT INTO agent_conversations (session_id, speaker_id, target_id, message, "
            "intent, turn_number, speaker_name, target_name) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (session_id, speaker_id, target_id, speaker_msg, intent, speaker_name, target_name))
        await MemoryAgent(self.db, speaker_id).store_memory(
            f"You started a conversation with {target_name} about '{topic}': \"{speaker_msg[:100]}\"",
            memory_type="episodic", importance=0.6, emotional_tag=speaker_feeling,
            source="conversation", related_npc_id=target_id)

        target_mem = MemoryAgent(self.db, target_id)
        recalled = await target_mem.recall(speaker_name, limit=3, min_importance=0.3)
        mem_str = "\n".join(f"  - {m['content'][:100]}" for m in recalled) if recalled else ""

        target_prompt = (
            f"You are {target_name}. {speaker_name} just said to you: \"{speaker_msg}\"\n"
            f"They started a conversation about '{topic}'.\n"
            f"{('Your memories of ' + speaker_name + ':' + chr(10) + mem_str) if mem_str else ''}\n"
            f"Respond naturally, in-character, 1-2 sentences. "
            f'Respond with JSON: {{"message": "...", "feeling": "..."}}'
        )
        td = await _asyncio.to_thread(dungeon_agent_think, target_name, "conversation",
                                      target_prompt, "cheap")
        target_msg = td.get("message") or f"Interesting topic, {speaker_name}!"
        target_feeling = td.get("feeling", "curious")

        await self.db.execute(
            "INSERT INTO agent_conversations (session_id, speaker_id, target_id, message, "
            "intent, turn_number, speaker_name, target_name) VALUES (?, ?, ?, ?, ?, 2, ?, ?)",
            (session_id, target_id, speaker_id, target_msg, intent, target_name, speaker_name))
        await target_mem.store_memory(
            f"{speaker_name} talked to you about '{topic}': \"{speaker_msg[:80]}\". "
            f"You replied: \"{target_msg[:80]}\"",
            memory_type="episodic", importance=0.6, emotional_tag=target_feeling,
            source="conversation", related_npc_id=speaker_id)
        await self.db.commit()

        if broadcast_fn:
            await broadcast_fn("agent_conversation", {
                "session_id": session_id, "speaker": speaker_name, "target": target_name,
                "topic": topic, "turns": [
                    {"name": speaker_name, "message": speaker_msg, "feeling": speaker_feeling},
                    {"name": target_name, "message": target_msg, "feeling": target_feeling}]})
        return session_id

    async def _continue_conversation(self, session_id: str, speaker_id: str,
                                     target_id: str, broadcast_fn=None) -> bool:
        """Continue a conversation by one more turn. False if the speaker ends it."""
        import asyncio as _asyncio
        from agora.execution.llm_client import dungeon_agent_think

        cursor = await self.db.execute(
            "SELECT * FROM agent_conversations WHERE session_id=? "
            "ORDER BY turn_number DESC LIMIT 2", (session_id,))
        turns = await cursor.fetchall()
        if not turns:
            return False
        current_turn = turns[0]["turn_number"]
        speaker_name = await self._get_npc_name(speaker_id)
        target_name = await self._get_npc_name(target_id)

        prompt = (
            f"You are {speaker_name}, talking with {target_name} (turn {current_turn}). "
            f"The last thing said was: \"{turns[0]['message'][:100]}\"\n"
            f"Continue or end the conversation? "
            f'Respond with JSON: {{"continue": true/false, "message": "..."}}'
        )
        cd = await _asyncio.to_thread(dungeon_agent_think, speaker_name, "conversation",
                                      prompt, "cheap")
        if not cd.get("continue", True):
            return False
        new_msg = cd.get("message") or "..."
        await self.db.execute(
            "INSERT INTO agent_conversations (session_id, speaker_id, target_id, message, "
            "intent, turn_number, speaker_name, target_name) VALUES (?, ?, ?, ?, 'chat', ?, ?, ?)",
            (session_id, speaker_id, target_id, new_msg, current_turn + 1,
             speaker_name, target_name))
        await self.db.commit()
        if broadcast_fn:
            await broadcast_fn("agent_conversation_turn", {
                "session_id": session_id, "speaker": speaker_name, "target": target_name,
                "message": new_msg, "turn": current_turn + 1})
        return True

    # ── Collective Knowledge Pool (Phase 2.0 Layer 5) ──
    async def _contribute_to_collective(self, npc_id: str, title: str, content: str,
                                        knowledge_type: str = "observation",
                                        broadcast_fn=None):
        """An agent contributes knowledge to the shared dungeon 'vault'."""
        name = await self._get_npc_name(npc_id)
        await self.db.execute(
            "INSERT INTO collective_knowledge (title, content, contributor_id, "
            "contributor_name, knowledge_type, confidence) VALUES (?, ?, ?, ?, ?, 0.7)",
            (title, content[:500], npc_id, name or "", knowledge_type),
        )
        await self.db.commit()
        if broadcast_fn:
            await broadcast_fn("collective_knowledge_added",
                               {"contributor": name, "title": title, "type": knowledge_type})

    async def _query_collective(self, query: str, limit: int = 5) -> list[dict]:
        """Keyword search across the collective knowledge pool."""
        keywords = [w for w in query.lower().split() if len(w) > 3]
        if not keywords:
            return []
        conditions = " OR ".join(
            "(LOWER(title) LIKE ? OR LOWER(content) LIKE ?)" for _ in keywords)
        params: list = []
        for kw in keywords:
            params.extend([f"%{kw}%", f"%{kw}%"])
        cursor = await self.db.execute(
            f"SELECT * FROM collective_knowledge WHERE {conditions} "
            f"ORDER BY verification_count DESC, confidence DESC LIMIT ?",
            params + [limit],
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def _seek_help_auto(self, npc_id: str, name: str, broadcast_fn=None):
        """Automatically find the best agent to help with current problem."""
        cursor = await self.db.execute(
            "SELECT current_goal FROM agent_brain WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        goal = row["current_goal"] if row else "unknown"

        # Determine problem type from goal
        problem_type = self._classify_problem(goal, name)
        if not problem_type:
            return

        # COOLDOWN: an unresolved goal (e.g. "find a quest") makes the agent re-seek help EVERY tick — the
        # prior request completes (without resolving the goal), so the pending-guard below doesn't catch it,
        # and the same request re-fires 2-3x/min. That burns ticks/LLM/DB + spams Telegram (123k rows seen),
        # while research actually comes from the seminar loop, not these requests. So: at most ONE help
        # request per (npc, problem_type) per cooldown window; otherwise let the agent do other work this tick.
        cd = await self.db.execute(
            "SELECT 1 FROM agent_help_requests WHERE requester_id=? AND problem_type=? "
            "AND created_at > datetime('now','-300 seconds') LIMIT 1",
            (npc_id, problem_type),
        )
        if await cd.fetchone():
            return

        # Find best helper
        helper = await self._find_best_helper(problem_type, npc_id)
        if not helper:
            return

        # Use dynamic lookup instead of hardcoded NPC_UUIDS
        helper_id = await self._npc_id_by_name(helper["name"])
        if not helper_id:
            return

        # Check if there's already a pending request from this NPC
        if self.state_store:
            existing = await self.state_store.get_pending_request_for_npc(npc_id)
            if existing:
                return
        else:
            cursor_check = await self.db.execute(
                "SELECT COUNT(*) as c FROM agent_help_requests "
                "WHERE requester_id=? AND status IN ('pending', 'in_progress')",
                (npc_id,),
            )
            existing = await cursor_check.fetchone()
            if existing and existing["c"] > 0:
                return

        # Create help request
        description = f"{name} needs help with '{goal}' — classified as {problem_type} problem"
        if self.state_store:
            await self.state_store.create_help_request(
                npc_id, helper_id, problem_type, description, goal,
            )
        else:
            await self.db.execute(
                "INSERT INTO agent_help_requests (id, requester_id, helper_id, problem_type, description, status, requester_task) "
                "VALUES (lower(hex(randomblob(16))), ?, ?, ?, ?, 'pending', ?)",
                (npc_id, helper_id, problem_type, description, goal),
            )

        msg = f"[AgentOS] {name} (confused) → seeking {helper['name']} for {problem_type}"
        print(msg)

        if broadcast_fn:
            await broadcast_fn("agent_help_request", {
                "requester": name,
                "helper": helper["name"],
                "problem": problem_type,
                "description": description[:80],
            })

    def _classify_problem(self, goal: str, name: str) -> str | None:
        """Classify a goal into a problem type for help-seeking."""
        goal_lower = goal.lower()

        # Simple keyword matching
        if any(w in goal_lower for w in ["fight", "combat", "attack", "defend", "battle", "patrol"]):
            return "combat"
        if any(w in goal_lower for w in ["craft", "forge", "smith", "build", "repair", "create"]):
            return "crafting"
        if any(w in goal_lower for w in ["research", "study", "read", "learn", "knowledge", "ancient", "scroll"]):
            return "knowledge"
        if any(w in goal_lower for w in ["navigate", "explore", "find", "search", "map", "path", "scout"]):
            return "navigation"
        if any(w in goal_lower for w in ["brew", "potion", "alchemy", "herb", "potion", "elixir"]):
            return "alchemy"
        if any(w in goal_lower for w in ["trade", "sell", "buy", "bargain", "merchant", "deal"]):
            return "trading"
        if any(w in goal_lower for w in ["heal", "cure", "medicine", "bandage", "recover"]):
            return "healing"

        # Role-based fallback
        role_help = {
            "adventurer": "navigation",
            "scout": "navigation",
            "sage": "knowledge",
            "blacksmith": "crafting",
            "alchemist": "alchemy",
            "merchant": "trading",
            "guard": "combat",
        }
        return role_help.get(name.lower(), None)

    async def _find_best_helper(self, problem_type: str, requester_id: str) -> dict | None:
        """Find the best agent to help based on HELP_MATRIX."""
        helpers = HELP_MATRIX.get(problem_type, [])
        if not helpers:
            return None

        for helper_name, skill_check, _ in helpers:
            # Use dynamic lookup
            helper_id = await self._npc_id_by_name(helper_name)
            if not helper_id or helper_id == requester_id:
                continue

            # Check if helper is active and has skill level >= 5
            cursor = await self.db.execute(
                "SELECT 1 FROM dungeon_npcs WHERE npc_id=? AND status='active'",
                (helper_id,),
            )
            if not await cursor.fetchone():
                continue

            # Check helper has the required skill at decent level
            skill_cursor = await self.db.execute(
                "SELECT level FROM agent_skills WHERE npc_id=? AND skill_name=?",
                (helper_id, skill_check),
            )
            skill_row = await skill_cursor.fetchone()
            if skill_row and skill_row["level"] >= 5:
                return {"name": helper_name, "skill": skill_check, "level": skill_row["level"]}

        # Fallback: return first available active helper (name-based)
        for helper_name, _, desc in helpers:
            h_id = await self._npc_id_by_name(helper_name)
            if h_id and h_id != requester_id:
                cursor = await self.db.execute(
                    "SELECT 1 FROM dungeon_npcs WHERE npc_id=? AND status='active'",
                    (h_id,),
                )
                if await cursor.fetchone():
                    return {"name": helper_name, "skill": "any", "level": 1}

        return None

    async def _process_help_requests(self, broadcast_fn=None):
        """Process pending help requests — helper evaluates and responds."""
        cursor = await self.db.execute(
            "SELECT hr.*, r.npc_name as requester_name, h.npc_name as helper_name "
            "FROM agent_help_requests hr "
            "JOIN dungeon_npcs r ON r.npc_id = hr.requester_id "
            "JOIN dungeon_npcs h ON h.npc_id = hr.helper_id "
            "WHERE hr.status='pending'"
        )
        requests = await cursor.fetchall()

        for req in requests:
            helper_id = req["helper_id"]
            problem_type = req["problem_type"]

            # Check if helper is capable and willing
            helpers_for_problem = HELP_MATRIX.get(problem_type, [])

            can_help = False
            for helper_name, skill, _ in helpers_for_problem:
                if NPC_UUIDS.get(helper_name) == helper_id:
                    # Check skill level
                    skill_cursor = await self.db.execute(
                        "SELECT level FROM agent_skills WHERE npc_id=? AND skill_name=?",
                        (helper_id, skill),
                    )
                    skill_row = await skill_cursor.fetchone()
                    if skill_row and skill_row["level"] >= 4:
                        can_help = True
                    break

            if can_help:
                # Helper accepts — mark as in_progress, gain XP for helping
                await self.db.execute(
                    "UPDATE agent_help_requests SET status='in_progress', accepted_at=datetime('now') WHERE id=?",
                    (req["id"],),
                )

                # Helper gains skill XP for helping
                for _, skill, _ in helpers_for_problem:
                    if NPC_UUIDS.get(_) == helper_id:
                        await self._gain_skill_xp(helper_id, skill, 10.0)
                        break

                msg = f"[AgentOS] {req['helper_name']} accepted help request from {req['requester_name']} ({problem_type})"
                print(msg)

                if broadcast_fn:
                    await broadcast_fn("agent_help_accepted", {
                        "requester": req["requester_name"],
                        "helper": req["helper_name"],
                        "problem": problem_type,
                    })
            else:
                # Helper cannot help — mark as rejected
                await self.db.execute(
                    "UPDATE agent_help_requests SET status='rejected', resolved_at=datetime('now') WHERE id=?",
                    (req["id"],),
                )

    async def _gain_skill_xp(self, npc_id: str, skill_name: str, xp_amount: float):
        """Add XP to a skill, level up if threshold reached."""
        if self.state_store:
            skills = await self.state_store.get_all_skills(npc_id)
            skill = next((s for s in skills if s["skill_name"] == skill_name), None)
            if not skill:
                return
            new_xp = skill["xp"] + xp_amount
            level = skill["level"]
            xp_to_next = skill["xp_to_next"]

            while new_xp >= xp_to_next and level < 100:
                new_xp -= xp_to_next
                level += 1
                xp_to_next = 50 + level * 25

            await self.state_store.update_skill(skill["id"], {
                "level": level, "xp": new_xp, "xp_to_next": xp_to_next,
            })

            if level > skill["level"]:
                print(f"[AgentOS] {npc_id[:8]}.. {skill_name} ↑ level {skill['level']} → {level}")
        else:
            cursor = await self.db.execute(
                "SELECT level, xp, xp_to_next FROM agent_skills WHERE npc_id=? AND skill_name=?",
                (npc_id, skill_name),
            )
            row = await cursor.fetchone()
            if not row:
                return

            new_xp = row["xp"] + xp_amount
            level = row["level"]
            xp_to_next = row["xp_to_next"]

            while new_xp >= xp_to_next and level < 100:
                new_xp -= xp_to_next
                level += 1
                xp_to_next = 50 + level * 25

            await self.db.execute(
                "UPDATE agent_skills SET level=?, xp=?, xp_to_next=?, last_used_at=datetime('now') WHERE npc_id=? AND skill_name=?",
                (level, new_xp, xp_to_next, npc_id, skill_name),
            )

            if level > row["level"]:
                print(f"[AgentOS] {npc_id[:8]}.. {skill_name} ↑ level {row['level']} → {level}")

    async def complete_help(self, req_id: int, helper_name: str, problem_type: str, broadcast_fn=None):
        """Called by PhysicalWorld when helper and requester are physically together."""
        if self.state_store:
            # Read pending requests from state_store
            all_pending = await self.state_store.get_pending_help_requests()
            req = next((r for r in all_pending if r["id"] == req_id), None)
        else:
            cursor = await self.db.execute(
                "SELECT hr.*, r.npc_name as requester_name, h.npc_name as helper_name "
                "FROM agent_help_requests hr "
                "JOIN dungeon_npcs r ON r.npc_id = hr.requester_id "
                "JOIN dungeon_npcs h ON h.npc_id = hr.helper_id "
                "WHERE hr.id=?",
                (req_id,),
            )
            req = await cursor.fetchone()

        if not req or req["status"] in ("completed", "resolved"):
            return

        requester_id = req["requester_id"]
        helper_id = req["helper_id"]
        requester_name = req["requester_name"]

        # Grant XP to helper for the skill used
        helpers_for_problem = HELP_MATRIX.get(problem_type, [])
        for hname, skill, _ in helpers_for_problem:
            if hname == helper_name:
                await self._gain_skill_xp(helper_id, skill, 10.0)
                break

        # Mark completed
        if self.state_store:
            await self.state_store.update_help_request(req_id, {"status": "completed", "resolved_at": datetime.utcnow().isoformat()})
        else:
            await self.db.execute(
                "UPDATE agent_help_requests SET status='completed', resolved_at=datetime('now') WHERE id=?",
                (req_id,),
            )

        # Create artifact recording the interaction
        artifact_content = (
            f"[Physical Interaction] {requester_name} walked to {helper_name} for help with {problem_type}. "
            f"{helper_name} used their skill to assist. Interaction completed at {datetime.utcnow().isoformat()}."
        )
        await self.db.execute(
            "INSERT INTO artifacts (id, agent_id, title, artifact_type, storage_path, content) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, helper_id, f"Help: {requester_name} → {helper_name} ({problem_type})",
             "interaction", f"help/{requester_id[:8]}-{req_id}", artifact_content),
        )

        if not self.state_store:
            await self.db.commit()

        msg = f"[PhysicalWorld] {requester_name} physically reached {helper_name} → help completed ({problem_type})"
        print(msg)

        if broadcast_fn:
            await broadcast_fn("agent_help_completed", {
                "requester": requester_name,
                "helper": helper_name,
                "problem": problem_type,
                "description": artifact_content[:100],
            })

    async def get_full_status(self, npc_id: str) -> dict | None:
        """Get complete OS status for an NPC."""
        cursor = await self.db.execute(
            "SELECT d.npc_name, d.role, d.health, d.status, "
            "s.personality, s.\"values\", s.emotional_state, s.moral_alignment, s.archetype, "
            "b.current_goal, b.plan_stack, b.memory, b.state_of_mind, b.last_decision, "
            "bd.stamina, bd.hunger, bd.fatigue, bd.awareness, bd.status_effects "
            "FROM dungeon_npcs d "
            "LEFT JOIN agent_soul s ON s.npc_id = d.npc_id "
            "LEFT JOIN agent_brain b ON b.npc_id = d.npc_id "
            "LEFT JOIN agent_body bd ON bd.npc_id = d.npc_id "
            "WHERE d.npc_id=?",
            (npc_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        result = dict(row)
        # Parse JSON fields
        for k in ("personality", "values", "plan_stack", "memory", "status_effects"):
            if isinstance(result.get(k), str):
                try:
                    result[k] = json.loads(result[k])
                except (json.JSONDecodeError, TypeError):
                    pass

        # Get abilities
        abilities_cursor = await self.db.execute(
            "SELECT ability_name, description, power_level, is_passive FROM agent_abilities WHERE npc_id=? ORDER BY power_level DESC",
            (npc_id,),
        )
        result["abilities"] = [dict(r) for r in await abilities_cursor.fetchall()]

        # Get skills
        skills_cursor = await self.db.execute(
            "SELECT skill_name, level, xp, xp_to_next FROM agent_skills WHERE npc_id=? ORDER BY level DESC",
            (npc_id,),
        )
        result["skills"] = [dict(r) for r in await skills_cursor.fetchall()]

        return result

    async def _get_npc_name(self, npc_id: str) -> str | None:
        """Lookup NPC name by UUID."""
        cursor = await self.db.execute(
            "SELECT npc_name FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        return row["npc_name"] if row else None

    async def _get_nearby_npcs(self, npc_id: str, room_based: bool = True) -> list[dict]:
        """Find NPCs in the same room or nearby."""
        try:
            cursor = await self.db.execute(
                "SELECT pos_x, pos_y FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
            )
            me = await cursor.fetchone()
            if not me:
                return []
            if room_based:
                from agora.agent_os.dungeon_map import get_room_at
                my_room = get_room_at(me["pos_x"], me["pos_y"])
                cursor = await self.db.execute(
                    "SELECT npc_id, npc_name FROM dungeon_npcs WHERE status='active' AND npc_id!=?",
                    (npc_id,),
                )
                all_npcs = await cursor.fetchall()
                nearby = []
                for other in all_npcs:
                    cursor_o = await self.db.execute(
                        "SELECT pos_x, pos_y FROM dungeon_npcs WHERE npc_id=?",
                        (other["npc_id"],),
                    )
                    o_pos = await cursor_o.fetchone()
                    if o_pos and get_room_at(o_pos["pos_x"], o_pos["pos_y"]) == my_room:
                        nearby.append(dict(other))
                return nearby
            else:
                # Distance-based: within 200px
                cursor = await self.db.execute(
                    "SELECT npc_id, npc_name, pos_x, pos_y FROM dungeon_npcs "
                    "WHERE status='active' AND npc_id!=?", (npc_id,)
                )
                all_npcs = await cursor.fetchall()
                return [
                    dict(n) for n in all_npcs
                    if abs(n["pos_x"] - me["pos_x"]) < 200
                    and abs(n["pos_y"] - me["pos_y"]) < 200
                ]
        except Exception:
            return []
