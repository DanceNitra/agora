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
from datetime import datetime

# ── NPC agent IDs ──
NPC_UUIDS = {
    "Kael":     "00000000-0000-0000-0000-000000000001",
    "Lyra":     "00000000-0000-0000-0000-000000000002",
    "Mordecai": "00000000-0000-0000-0000-000000000003",
    "Grom":     "00000000-0000-0000-0000-000000000004",
    "Zara":     "00000000-0000-0000-0000-000000000005",
    "Finn":     "00000000-0000-0000-0000-000000000006",
    "Guard":    "00000000-0000-0000-0000-000000000007",
}

UUID_TO_NAME = {v: k for k, v in NPC_UUIDS.items()}


# ═══════════════════════════════════════════
# NPC DEFINITIONS — duša, schopnosti, štartovacie zručnosti
# ═══════════════════════════════════════════

NPC_DEFS = {
    "Kael": {
        "name": "Kael",
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
    "Lyra": {
        "name": "Lyra",
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
    "Mordecai": {
        "name": "Mordecai",
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
    "Grom": {
        "name": "Grom",
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
    "Zara": {
        "name": "Zara",
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
    "Finn": {
        "name": "Finn",
        "role": "merchant",
        "archetype": "merchant",
        "personality": {"openness": 0.7, "conscientiousness": 0.6, "extraversion": 0.9, "agreeableness": 0.8, "neuroticism": 0.3},
        "values": {"wealth": 1.0, "connections": 0.9, "knowledge": 0.5, "bargaining": 0.9, "harmony": 0.6},
        "emotional_state": "happy",
        "moral_alignment": "neutral",
        "abilities": [
            ("Silver Tongue", "Dokáže presvedčiť kohokoľvek", 9.0, True),
            ("Trade Instinct", "Vyciťuje výhodné obchody", 8.0, True),
            ("Networker", "Pozná ľudí a ich potreby", 7.0, False),
        ],
        "skills": [("bargaining", 9), ("appraisal", 8), ("persuasion", 7), ("logistics", 6)],
    },
    "Guard": {
        "name": "Guard",
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
        ("Guard", "spear_fighting", "Guard je najlepší bojovník v družine"),
        ("Kael", "swordfighting", "Kael má skúsenosti z dungeonov"),
    ],
    "crafting": [
        ("Grom", "smithing", "Grom je majster kováč"),
        ("Zara", "alchemy", "Zara dokáže vytvoriť alchymické nástroje"),
    ],
    "knowledge": [
        ("Mordecai", "arcana", "Mordecai ovláda staroveké vedomosti"),
        ("Lyra", "cartography", "Lyra pozná mapy a terén"),
    ],
    "navigation": [
        ("Lyra", "tracking", "Lyra je najlepšia stopárka"),
        ("Kael", "exploration", "Kael pozná dungeon ako svoju dlaň"),
    ],
    "alchemy": [
        ("Zara", "alchemy", "Zara je majster alchýmie"),
        ("Mordecai", "alchemy_theory", "Mordecai pozná teóriu"),
    ],
    "trading": [
        ("Finn", "bargaining", "Finn je najlepší vyjednávač"),
        ("Finn", "appraisal", "Finn pozná cenu všetkého"),
    ],
    "healing": [
        ("Zara", "healing", "Zara varí liečivé elixíry"),
        ("Mordecai", "arcana", "Mordecai pozná liečivé rituály"),
    ],
    "repair": [
        ("Grom", "repair", "Grom opraví čokoľvek z kovu"),
        ("Grom", "smithing", "Grom dokáže vykovať náhradné diely"),
    ],
}


class AgentOS:
    """Operating System for dungeon NPCs — duša, mozog, telo, zručnosti a help-seeking."""

    def __init__(self, db):
        self.db = db

    async def ensure_os_initialized(self):
        """Seed OS data for all 7 NPCs if not already present."""
        cursor = await self.db.execute("SELECT COUNT(*) as c FROM agent_soul")
        row = await cursor.fetchone()
        if row and row["c"] > 0:
            return  # already seeded

        for name, defs in NPC_DEFS.items():
            npc_id = NPC_UUIDS[name]

            # Soul
            await self.db.execute(
                "INSERT INTO agent_soul (npc_id, personality, \"values\", emotional_state, moral_alignment, archetype) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (npc_id, json.dumps(defs["personality"]), json.dumps(defs["values"]),
                 defs["emotional_state"], defs["moral_alignment"], defs["archetype"]),
            )

            # Brain
            await self.db.execute(
                "INSERT INTO agent_brain (npc_id, current_goal, plan_stack, memory, state_of_mind) "
                "VALUES (?, ?, ?, ?, ?)",
                (npc_id, defs.get("objective", f"Operate as {name}"),
                 json.dumps([]), json.dumps([]), "focused"),
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

        await self.db.commit()
        print(f"[AgentOS] Seeded {len(NPC_DEFS)} NPCs (soul, brain, body, abilities, skills)")

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

        # Process pending help requests
        await self._process_help_requests(broadcast_fn)

        await self.db.commit()

    async def _update_body(self, npc_id: str):
        """Update body stats: stamina decreases, hunger/fatigue increase."""
        cursor = await self.db.execute(
            "SELECT stamina, hunger, fatigue FROM agent_body WHERE npc_id=?",
            (npc_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return

        # Passive changes per tick
        new_stamina = min(100.0, max(0.0, row["stamina"] - random.uniform(0.5, 2.0)))
        new_hunger = min(100.0, row["hunger"] + random.uniform(0.2, 0.8))
        new_fatigue = min(100.0, row["fatigue"] + random.uniform(0.3, 1.0))

        await self.db.execute(
            "UPDATE agent_body SET stamina=?, hunger=?, fatigue=?, updated_at=datetime('now') WHERE npc_id=?",
            (new_stamina, new_hunger, new_fatigue, npc_id),
        )

        # If starving or exhausted → impact health
        health_cursor = await self.db.execute(
            "SELECT health FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
        )
        health_row = await health_cursor.fetchone()
        if health_row:
            new_health = health_row["health"]
            if new_hunger > 80:
                new_health = max(0, new_health - 0.5)
            if new_fatigue > 80:
                new_health = max(0, new_health - 0.3)
            if new_stamina < 10:
                new_health = max(0, new_health - 0.2)

            await self.db.execute(
                "UPDATE dungeon_npcs SET health=? WHERE npc_id=?", (new_health, npc_id)
            )

    async def _think(self, npc_id: str, name: str) -> str:
        """Evaluate state and decide state_of_mind."""
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

        # Determine state based on body stats
        if health < 20:
            new_state = "panicked"
        elif fatigue > 70 or stamina < 20:
            new_state = "resting"
        elif health < 50:
            new_state = "confused"
        else:
            # Has a goal and energy → focused
            plan_stack = json.loads(row["plan_stack"] or "[]")
            if not plan_stack and row["current_goal"]:
                # Need to create a plan
                new_state = "planning"
            else:
                new_state = "focused"

        await self.db.execute(
            "UPDATE agent_brain SET state_of_mind=?, updated_at=datetime('now') WHERE npc_id=?",
            (new_state, npc_id),
        )

        return new_state

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

        # Find best helper
        helper = await self._find_best_helper(problem_type, npc_id)
        if not helper:
            return

        helper_id = NPC_UUIDS[helper["name"]]

        # Create help request
        description = f"{name} needs help with '{goal}' — classified as {problem_type} problem"
        await self.db.execute(
            "INSERT INTO agent_help_requests (requester_id, helper_id, problem_type, description, status, requester_task) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
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
            helper_id = NPC_UUIDS.get(helper_name)
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

        # Fallback: return first available active helper
        for helper_name, _, desc in helpers:
            helper_id = NPC_UUIDS.get(helper_name)
            if helper_id and helper_id != requester_id:
                cursor = await self.db.execute(
                    "SELECT 1 FROM dungeon_npcs WHERE npc_id=? AND status='active'",
                    (helper_id,),
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
            xp_to_next = 50 + level * 25  # harder each level

        await self.db.execute(
            "UPDATE agent_skills SET level=?, xp=?, xp_to_next=?, last_used_at=datetime('now') WHERE npc_id=? AND skill_name=?",
            (level, new_xp, xp_to_next, npc_id, skill_name),
        )

        if level > row["level"]:
            print(f"[AgentOS] {npc_id[:8]}.. {skill_name} ↑ level {row['level']} → {level}")

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
