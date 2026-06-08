"""
Quest Manager — assigns quests to NPCs, injects quest context into LLM,
and automatically progresses quests when NPCs talk to the right targets.
"""
import json
import random
from typing import Any

# ── Quest chain definition ──

# Which NPC is the "quest-doer" for each quest
QUEST_ASSIGNMENTS = {
    # ── Shadow Kael's chain (main quest) ──
    "talk_to_sage": {
        "agent": "Shadow Kael",
        "target_npc": "High Priest Orin",
        "target_x": 20 * 32,
        "target_y": 16 * 32,
        "required_action": "talk",
        "progress_step": "Consulted the Sage",
    },
    "map_dungeon": {
        "agent": "Shadow Kael",
        "target_npc": "Sage Mira",
        "target_x": 3 * 32,
        "target_y": 17 * 32,
        "required_action": "talk",
        "progress_step": "Got the Dungeon Map",
    },
    "forge_key": {
        "agent": "Shadow Kael",
        "target_npc": "King Aldric",
        "target_x": 5 * 32,
        "target_y": 10 * 32,
        "required_action": "talk",
        "progress_step": "Forged the Ancient Key",
    },
    "find_crystal": {
        "agent": "Shadow Kael",
        "target_npc": None,
        "target_x": 22 * 32,
        "target_y": 18 * 32,
        "required_action": "explore",
        "progress_step": "Found the Crystal of Eternity",
    },
    # ── Sage Mira's chain (scout) ──
    "explore_crypt": {
        "agent": "Sage Mira",
        "target_npc": None,
        "target_x": 30 * 32,  # Crypt center
        "target_y": 15 * 32,
        "required_action": "explore",
        "progress_step": "Explored the crypt",
    },
    "map_catacombs": {
        "agent": "Sage Mira",
        "target_npc": "Shadow Kael",
        "target_x": 10 * 32,
        "target_y": 16 * 32,
        "required_action": "talk",
        "progress_step": "Delivered crypt map to Shadow Kael",
    },
    "scout_treasury": {
        "agent": "Sage Mira",
        "target_npc": None,
        "target_x": 28 * 32,  # Treasury
        "target_y": 9 * 32,
        "required_action": "explore",
        "progress_step": "Scouted the treasury",
    },
    # ── High Priest Orin's chain (sage) ──
    "study_runes": {
        "agent": "High Priest Orin",
        "target_npc": None,
        "target_x": 34 * 32,  # Library
        "target_y": 3 * 32,
        "required_action": "explore",
        "progress_step": "Studied ancient runes in the library",
    },
    "decipher_scroll": {
        "agent": "High Priest Orin",
        "target_npc": "Shadow Kael",
        "target_x": 10 * 32,
        "target_y": 16 * 32,
        "required_action": "talk",
        "progress_step": "Deciphered scroll for Shadow Kael",
    },
    "unlock_vault": {
        "agent": "High Priest Orin",
        "target_npc": None,
        "target_x": 29 * 32,  # Treasury vault
        "target_y": 9 * 32,
        "required_action": "explore",
        "progress_step": "Unlocked the ancient vault",
    },
    # ── King Aldric's chain (blacksmith) ──
    "collect_ore": {
        "agent": "King Aldric",
        "target_npc": None,
        "target_x": 35 * 32,  # Crypt - ore deposits
        "target_y": 16 * 32,
        "required_action": "explore",
        "progress_step": "Collected iron ore from the crypt",
    },
    "forge_weapons": {
        "agent": "King Aldric",
        "target_npc": "Dame Elara",
        "target_x": 15 * 32,
        "target_y": 3 * 32,
        "required_action": "talk",
        "progress_step": "Got quenching potion from Dame Elara",
    },
    "arm_guard": {
        "agent": "King Aldric",
        "target_npc": "Sergeant Voss",
        "target_x": 19.5 * 32,
        "target_y": 9 * 32,
        "required_action": "talk",
        "progress_step": "Armed the Sergeant Voss with new weapons",
    },
    # ── Dame Elara's chain (alchemist) ──
    "gather_herbs": {
        "agent": "Dame Elara",
        "target_npc": None,
        "target_x": 28 * 32,  # Crypt - glowing mushrooms
        "target_y": 16 * 32,
        "required_action": "explore",
        "progress_step": "Gathered glowing herbs from the crypt",
    },
    "heal_npcs": {
        "agent": "Dame Elara",
        "target_npc": "King Aldric",
        "target_x": 5 * 32,
        "target_y": 10 * 32,
        "required_action": "talk",
        "progress_step": "Delivered healing potions to King Aldric",
    },
}

# What the target NPC should say when asked about a quest
QUEST_RESPONSES = {
    "High Priest Orin": {
        "talk_to_sage": (
            "Ah, you seek the Crystal of Eternity! I have studied the ancient texts. "
            "To find it, you must first map the dungeon. Speak with Sage Mira the scout — "
            "she has explored the eastern chambers and can give you a map."
        ),
    },
    "Sage Mira": {
        "map_dungeon": (
            "I've mapped most of the dungeon! But there's a sealed door in the "
            "northern corridor that requires an ancient key. King Aldric the blacksmith "
            "knows how to forge one, but he needs materials."
        ),
    },
    "King Aldric": {
        "forge_key": (
            "An ancient key, eh? I can forge one, but I need iron ingots from the "
            "crypt and a quenching potion from Dame Elara. Bring those and I'll make the key."
        ),
        "heal_npcs": (
            "Thank you, Dame Elara! These healing potions will keep the expedition alive. "
            "The Sergeant Voss especially needed them after that scuffle in the treasury."
        ),
    },
    "Dame Elara": {
        "forge_weapons": (
            "A quenching potion? Of course! I've been brewing just the thing. "
            "Tell King Aldric to use it sparingly — a few drops are enough for the strongest steel."
        ),
        "brew_potion": (
            "The glowing stag horn and crystallized honey would make a powerful healing draught."
        ),
    },
    "Sergeant Voss": {
        "arm_guard": (
            "New weapons! About time. These goblins in the crypt have been getting bolder. "
            "Thank King Aldric for me — this spear is perfectly balanced."
        ),
    },
    "Shadow Kael": {
        "map_catacombs": (
            "Excellent work, Sage Mira! This map of the crypt is exactly what I needed. "
            "Now finish scouting the treasury while I prepare the expedition."
        ),
        "decipher_scroll": (
            "High Priest Orin, you've done it! With this translation, we can finally open the vault. "
            "The Crystal of Eternity must be close."
        ),
    },
}

# What the quest-doer learns (stored as memory/inventory)
QUEST_OUTCOMES = {
    "talk_to_sage": {
        "memory": "High Priest Orin told me I need to map the dungeon first. Sage Mira can help.",
        "inventory_add": [],
    },
    "map_dungeon": {
        "memory": "Sage Mira gave me the Dungeon Map. The sealed door needs an ancient key from King Aldric.",
        "inventory_add": ["Dungeon Map"],
    },
    "forge_key": {
        "memory": "King Aldric forged the Ancient Key! Now I can open the sealed door.",
        "inventory_add": ["Ancient Key"],
    },
    "find_crystal": {
        "memory": "I found the legendary Crystal of Eternity in the deepest chamber!",
        "inventory_add": ["Crystal of Eternity"],
    },
    # ── Sage Mira ──
    "explore_crypt": {
        "memory": "I mapped the crypt — dangerous but full of ancient secrets. Need to tell Shadow Kael.",
        "inventory_add": ["Crypt Map"],
    },
    "map_catacombs": {
        "memory": "Delivered the crypt map to Shadow Kael. He wants me to scout the treasury next.",
        "inventory_add": [],
    },
    "scout_treasury": {
        "memory": "The treasury is heavily guarded but contains valuable artifacts. Ready for next mission.",
        "inventory_add": ["Treasury Key"],
    },
    # ── High Priest Orin ──
    "study_runes": {
        "memory": "The library's runes describe a vault beneath the treasury. I must decipher the scroll for Shadow Kael.",
        "inventory_add": ["Rune Translation"],
    },
    "decipher_scroll": {
        "memory": "Shadow Kael has the translation now. The vault location is clear — beneath the treasury.",
        "inventory_add": [],
    },
    "unlock_vault": {
        "memory": "I unlocked the ancient vault! The secrets within are beyond anything I imagined.",
        "inventory_add": ["Ancient Relic"],
    },
    # ── King Aldric ──
    "collect_ore": {
        "memory": "Found rich iron deposits in the crypt walls. Enough to forge weapons for everyone.",
        "inventory_add": ["Iron Ore"],
    },
    "forge_weapons": {
        "memory": "Dame Elara's quenching potion worked perfectly. The steel is the finest I've ever forged.",
        "inventory_add": ["Quenching Potion"],
    },
    "arm_guard": {
        "memory": "The Sergeant Voss is properly armed now. The expedition is much safer with upgraded weapons.",
        "inventory_add": ["Forged Spear"],
    },
    # ── Dame Elara ──
    "gather_herbs": {
        "memory": "Found rare glowing mushrooms in the crypt. Perfect for healing potions.",
        "inventory_add": ["Glowing Herbs"],
    },
    "heal_npcs": {
        "memory": "King Aldric and the Sergeant Voss have their healing potions. The whole expedition is grateful.",
        "inventory_add": [],
    },
}

# ── Public API ──

_quests_assigned = False


async def auto_assign_quests(db) -> None:
    """Assign the first quest in each chain to the appropriate NPC at startup."""
    global _quests_assigned
    if _quests_assigned:
        return

    try:
        first_quests = {
            "kael": "talk_to_sage",
            "lyra": "explore_crypt",
            "mordecai": "study_runes",
            "grom": "collect_ore",
            "zara": "gather_herbs",
        }

        for npc_id, quest_id in first_quests.items():
            # Check if NPC already has an active quest
            cursor = await db.execute(
                "SELECT 1 FROM dungeon_quest_progress WHERE npc_id=? AND status='active'",
                (npc_id,),
            )
            if await cursor.fetchone():
                continue

            # Check if quest exists in DB
            cursor = await db.execute(
                "SELECT quest_id FROM dungeon_quests WHERE quest_id=?",
                (quest_id,),
            )
            if not await cursor.fetchone():
                continue

            await db.execute(
                """INSERT INTO dungeon_quest_progress (npc_id, quest_id, status, progress, started_at)
                   VALUES (?, ?, 'active', '{}', datetime('now'))
                   ON CONFLICT(npc_id, quest_id) DO UPDATE SET status='active'""",
                (npc_id, quest_id),
            )
            print(f"[QuestManager] Assigned {quest_id} to {npc_id}")

        await db.commit()
        _quests_assigned = True
    except Exception as e:
        print(f"[QuestManager] auto_assign error: {e}")


async def inject_quest_context(db, agent_name: str, context: str) -> tuple[str, dict | None]:
    """Inject quest info into LLM context.
    Returns (updated_context, active_quest_info_or_None).
    """
    if agent_name not in ("Shadow Kael", "Sage Mira", "High Priest Orin", "King Aldric", "Dame Elara", "Sergeant Voss"):
        return context, None

    npc_id = agent_name.lower()
    active_quest = None

    try:
        cursor = await db.execute(
            """SELECT qp.*, dq.title, dq.description, dq.quest_type, dq.starting_npc
               FROM dungeon_quest_progress qp
               JOIN dungeon_quests dq ON qp.quest_id = dq.quest_id
               WHERE qp.npc_id=? AND qp.status='active'
               ORDER BY qp.started_at DESC LIMIT 1""",
            (npc_id,),
        )
        row = await cursor.fetchone()
        if row:
            active_quest = {
                "quest_id": row["quest_id"],
                "title": row["title"],
                "description": row["description"],
                "quest_type": row["quest_type"],
                "starting_npc": row["starting_npc"],
                "progress": json.loads(row["progress"]) if isinstance(row["progress"], str) else {},
            }

            # Get assignment details
            assignment = QUEST_ASSIGNMENTS.get(row["quest_id"])
            if assignment:
                target = assignment["target_npc"] or "the deepest chamber"
                action = assignment["required_action"]
                step = assignment["progress_step"]

                # Forceful quest context — this is the #1 priority
                context += (
                    f"\n\n🔥 YOUR #1 PRIORITY — ACTIVE QUEST: {row['title']}\n"
                    f"   Description: {row['description']}\n"
                    f"   Your objective: Complete this quest NOW.\n"
                    f"   Progress needed: {step}\n"
                    f"   Action required: IMMEDIATELY go to {target} and {action} to them\n"
                )

                if assignment["target_npc"]:
                    context += (
                        f"\n   >>> USE action='talk' with target_npc=\"{assignment['target_npc']}\" <<<\n"
                        f"   >>> Walk toward {assignment['target_npc']} first, then talk <<<\n"
                    )

                # Override objective to be quest-focused
                context += f"\nYour CURRENT OBJECTIVE: Complete '{row['title']}' — {step} by going to {target}.\n"

                # Help with navigation — tell NPC where the target is
                if assignment["target_npc"]:
                    target_pos = {
                        "High Priest Orin": "(20*32, 16*32) — southeast area",
                        "Sage Mira": "(3*32, 17*32) — near the chest",
                        "King Aldric": "(5*32, 10*32) — near the anvil",
                        "Shadow Kael": "(10*32, 16*32) — center area",
                        "Dame Elara": "(15*32, 3*32) — near the cauldron",
                        "Sergeant Voss": "(19.5*32, 9*32) — near the door",
                    }.get(assignment["target_npc"], "somewhere in the dungeon")
                    context += f"\n📍 {assignment['target_npc']} is at {target_pos}. Go there and talk to them.\n"

                # Add completed quests context
                cursor2 = await db.execute(
                    """SELECT qp.*, dq.title FROM dungeon_quest_progress qp
                       JOIN dungeon_quests dq ON qp.quest_id = dq.quest_id
                       WHERE qp.npc_id=? AND qp.status='completed'
                       ORDER BY qp.completed_at DESC LIMIT 3""",
                    (npc_id,),
                )
                completed = await cursor2.fetchall()
                if completed:
                    context += "\n✅ Completed quests:\n"
                    for c in completed:
                        context += f"  ✅ {c['title']}\n"

    except Exception as e:
        print(f"[QuestManager] inject error: {e}")

    return context, active_quest


async def override_decision_for_quest(
    db, agent_name: str, decision: dict, current_pos: tuple[float, float] = (0, 0)
) -> tuple[dict, bool]:
    """If NPC has an active quest step and their decision doesn't progress it,
    override the decision. Returns (decision, was_overridden)."""
    if agent_name not in ("Shadow Kael", "Sage Mira", "High Priest Orin", "King Aldric", "Dame Elara"):
        return decision, False

    npc_id = agent_name.lower()

    try:
        cursor = await db.execute(
            "SELECT qp.* FROM dungeon_quest_progress qp "
            "WHERE qp.npc_id=? AND qp.status='active' LIMIT 1",
            (npc_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return decision, False

        quest_id = row["quest_id"]
        assignment = QUEST_ASSIGNMENTS.get(quest_id)
        if not assignment:
            return decision, False

        # Check if the decision already progresses the quest
        action = decision.get("action", "")
        target_npc = decision.get("target_npc", "")

        if assignment["required_action"] == "talk":
            if action == "talk" and target_npc == assignment["target_npc"]:
                return decision, False  # Already doing the right thing

            # Check distance to target
            tx, ty = assignment.get("target_x", 640), assignment.get("target_y", 512)
            cx, cy = current_pos
            dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
            target = assignment["target_npc"] or "the deepest chamber"
            print(f"[QuestManager] Override: {agent_name} forced for quest {quest_id} (dist={dist:.0f}px to {target})")

            if dist < 48:
                # Close enough — force talk
                return {
                    "action": "talk",
                    "target_npc": assignment["target_npc"],
                    "message": f"I seek your wisdom regarding the {quest_id.replace('_', ' ')}.",
                    "thought": f"I must complete my quest by speaking with {target}.",
                    "_quest_override": True,
                }, True
            else:
                # Still far — force move toward target
                return {
                    "action": "move",
                    "target_x": tx,
                    "target_y": ty,
                    "message": f"I need to find {target} to complete my quest.",
                    "thought": f"I have a quest to complete — must reach {target}.",
                    "_quest_override": True,
                }, True

        elif assignment["required_action"] == "explore":
            # Force NPC to move toward the target area
            tx = assignment.get("target_x", 704)
            ty = assignment.get("target_y", 576)
            return {
                "action": "move",
                "target_x": tx,
                "target_y": ty,
                "message": "I must reach the deepest chamber for my quest.",
                "thought": "Pushing deeper into the dungeon to find the Crystal.",
                "_quest_override": True,
            }, True

    except Exception as e:
        print(f"[QuestManager] override error: {e}")

    return decision, False


async def check_quest_progress(
    db, agent_name: str, decision: dict, npc_positions: dict[str, tuple[float, float]]
) -> dict | None:
    """After an LLM decision, check if the NPC progressed their quest.
    Returns a quest update dict or None.
    """
    if agent_name not in ("Shadow Kael", "Sage Mira", "High Priest Orin", "King Aldric", "Dame Elara", "Sergeant Voss"):
        return None

    npc_id = agent_name.lower()

    try:
        # Get active quest
        cursor = await db.execute(
            "SELECT qp.*, dq.prerequisites FROM dungeon_quest_progress qp "
            "JOIN dungeon_quests dq ON qp.quest_id = dq.quest_id "
            "WHERE qp.npc_id=? AND qp.status='active' LIMIT 1",
            (npc_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        quest_id = row["quest_id"]
        assignment = QUEST_ASSIGNMENTS.get(quest_id)
        if not assignment:
            return None

        action = decision.get("action", "")
        target_npc = decision.get("target_npc", "")
        target_x = decision.get("target_x")
        target_y = decision.get("target_y")

        progress_made = False
        progress_data = json.loads(row["progress"]) if isinstance(row["progress"], str) else {}

        # Check if this action progresses the quest
        if assignment["required_action"] == "talk":
            # Must talk to the right NPC
            if action == "talk" and target_npc == assignment["target_npc"]:
                progress_made = True
                progress_data["talked_to"] = assignment["target_npc"]
                progress_data["message"] = decision.get("message", "")
        elif assignment["required_action"] == "explore":
            # Must reach the target area
            agent_pos = npc_positions.get(agent_name, (0, 0))
            target = (assignment["target_x"], assignment["target_y"])
            dist = ((agent_pos[0] - target[0]) ** 2 + (agent_pos[1] - target[1]) ** 2) ** 0.5
            if dist < 64:  # Within 2 tiles
                progress_made = True
                progress_data["reached"] = True

        if progress_made:
            # Update progress in DB
            outcome = QUEST_OUTCOMES.get(quest_id, {})
            progress_json = json.dumps(progress_data)

            # Complete the quest
            await db.execute(
                "UPDATE dungeon_quest_progress SET status='completed', progress=?, completed_at=datetime('now') "
                "WHERE npc_id=? AND quest_id=?",
                (progress_json, npc_id, quest_id),
            )

            # Add inventory items
            for item in outcome.get("inventory_add", []):
                # Store in quest progress data
                progress_data["inventory_reward"] = outcome.get("inventory_add", [])
                # Save to NPC persistence if running
                try:
                    # Update NPC inventory in dungeon_npcs table
                    cursor2 = await db.execute(
                        "SELECT inventory FROM dungeon_npcs WHERE npc_id=?",
                        (npc_id,),
                    )
                    npc_row = await cursor2.fetchone()
                    if npc_row:
                        inv = json.loads(npc_row["inventory"])
                        if item not in inv:
                            inv.append(item)
                        await db.execute(
                            "UPDATE dungeon_npcs SET inventory=?, updated_at=datetime('now') WHERE npc_id=?",
                            (json.dumps(inv), npc_id),
                        )
                except Exception:
                    pass  # NPC might not be in DB yet

            await db.commit()

            # Auto-start next quest in chain
            next_quest = _get_next_quest(quest_id)
            if next_quest:
                next_assignment = QUEST_ASSIGNMENTS.get(next_quest)
                if next_assignment and next_assignment["agent"] == agent_name:
                    await db.execute(
                        """INSERT INTO dungeon_quest_progress (npc_id, quest_id, status, progress, started_at)
                           VALUES (?, ?, 'active', '{}', datetime('now'))
                           ON CONFLICT(npc_id, quest_id) DO UPDATE SET status='active'""",
                        (npc_id, next_quest),
                    )
                    await db.commit()

            return {
                "quest_completed": quest_id,
                "next_quest": next_quest,
                "reward": outcome,
                "message": outcome.get("memory", f"Completed {quest_id}!"),
            }

    except Exception as e:
        print(f"[QuestManager] progress check error: {e}")

    return None


def _get_next_quest(current_quest_id: str) -> str | None:
    """Return the next quest in the chain, or None."""
    chains = [
        ["talk_to_sage", "map_dungeon", "forge_key", "find_crystal"],  # Shadow Kael
        ["explore_crypt", "map_catacombs", "scout_treasury"],          # Sage Mira
        ["study_runes", "decipher_scroll", "unlock_vault"],            # High Priest Orin
        ["collect_ore", "forge_weapons", "arm_guard"],                 # King Aldric
        ["gather_herbs", "brew_potion", "heal_npcs"],                  # Dame Elara
    ]
    for chain in chains:
        try:
            idx = chain.index(current_quest_id)
            if idx + 1 < len(chain):
                return chain[idx + 1]
        except ValueError:
            continue
    return None


async def get_active_quest_for_npc(db, npc_id: str) -> dict | None:
    """Get the active quest for an NPC, if any."""
    try:
        cursor = await db.execute(
            """SELECT qp.*, dq.title, dq.description, dq.quest_type, dq.starting_npc
               FROM dungeon_quest_progress qp
               JOIN dungeon_quests dq ON qp.quest_id = dq.quest_id
               WHERE qp.npc_id=? AND qp.status='active'
               LIMIT 1""",
            (npc_id,),
        )
        row = await cursor.fetchone()
        if row:
            return {
                "quest_id": row["quest_id"],
                "title": row["title"],
                "description": row["description"],
                "starting_npc": row["starting_npc"],
            }
    except Exception:
        pass
    return None
