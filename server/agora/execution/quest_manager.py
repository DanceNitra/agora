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
    "talk_to_sage": {
        "agent": "Kael",
        "target_npc": "Mordecai",
        "target_x": 20 * 32,  # Mordecai's position
        "target_y": 16 * 32,
        "required_action": "talk",
        "progress_step": "Consulted the Sage",
    },
    "map_dungeon": {
        "agent": "Kael",
        "target_npc": "Lyra",
        "target_x": 3 * 32,
        "target_y": 17 * 32,
        "required_action": "talk",
        "progress_step": "Got the Dungeon Map",
    },
    "forge_key": {
        "agent": "Kael",
        "target_npc": "Grom",
        "target_x": 5 * 32,
        "target_y": 10 * 32,
        "required_action": "talk",
        "progress_step": "Forged the Ancient Key",
    },
    "find_crystal": {
        "agent": "Kael",
        "target_npc": None,
        "target_x": 22 * 32,  # Deepest chamber
        "target_y": 18 * 32,
        "required_action": "explore",
        "progress_step": "Found the Crystal of Eternity",
    },
}

# What the target NPC should say when asked about a quest
QUEST_RESPONSES = {
    "Mordecai": {
        "talk_to_sage": (
            "Ah, you seek the Crystal of Eternity! I have studied the ancient texts. "
            "To find it, you must first map the dungeon. Speak with Lyra the scout — "
            "she has explored the eastern chambers and can give you a map."
        ),
    },
    "Lyra": {
        "map_dungeon": (
            "I've mapped most of the dungeon! But there's a sealed door in the "
            "northern corridor that requires an ancient key. Grom the blacksmith "
            "knows how to forge one, but he needs materials."
        ),
    },
    "Grom": {
        "forge_key": (
            "An ancient key, eh? I can forge one, but I need iron ingots from the "
            "mine and a scroll fragment with the key pattern. Once you have those, "
            "bring them to me and I'll make the key."
        ),
    },
}

# What the quest-doer learns (stored as memory/inventory)
QUEST_OUTCOMES = {
    "talk_to_sage": {
        "memory": "Mordecai told me I need to map the dungeon first. Lyra can help.",
        "inventory_add": [],
    },
    "map_dungeon": {
        "memory": "Lyra gave me the Dungeon Map. The sealed door needs an ancient key from Grom.",
        "inventory_add": ["Dungeon Map"],
    },
    "forge_key": {
        "memory": "Grom forged the Ancient Key! Now I can open the sealed door.",
        "inventory_add": ["Ancient Key"],
    },
    "find_crystal": {
        "memory": "I found the legendary Crystal of Eternity in the deepest chamber!",
        "inventory_add": ["Crystal of Eternity"],
    },
}

# ── Public API ──

_quests_assigned = False


async def auto_assign_quests(db) -> None:
    """Assign the first quest in the chain to Kael at startup."""
    global _quests_assigned
    if _quests_assigned:
        return

    try:
        # Check if Kael already has an active quest
        cursor = await db.execute(
            "SELECT 1 FROM dungeon_quest_progress WHERE npc_id=? AND status='active'",
            ("kael",),
        )
        if await cursor.fetchone():
            _quests_assigned = True
            return

        # Start the first quest for Kael
        cursor = await db.execute(
            "SELECT quest_id FROM dungeon_quests WHERE quest_id='talk_to_sage'",
        )
        if not await cursor.fetchone():
            # Quests not seeded yet — don't fail
            return

        await db.execute(
            """INSERT INTO dungeon_quest_progress (npc_id, quest_id, status, progress, started_at)
               VALUES ('kael', 'talk_to_sage', 'active', '{}', datetime('now'))
               ON CONFLICT(npc_id, quest_id) DO UPDATE SET status='active'""",
        )
        await db.commit()
        _quests_assigned = True
        print("[QuestManager] Assigned talk_to_sage to Kael")
    except Exception as e:
        print(f"[QuestManager] auto_assign error: {e}")


async def inject_quest_context(db, agent_name: str, context: str) -> tuple[str, dict | None]:
    """Inject quest info into LLM context.
    Returns (updated_context, active_quest_info_or_None).
    """
    if agent_name not in ("Kael", "Lyra", "Mordecai"):
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
                        "Mordecai": "(20*32, 16*32) — southeast area",
                        "Lyra": "(3*32, 17*32) — near the chest",
                        "Grom": "(5*32, 10*32) — near the anvil",
                        "Kael": "(10*32, 16*32) — center area",
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
    if agent_name not in ("Kael",):
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
    if agent_name not in ("Kael", "Lyra", "Mordecai"):
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
    chain = ["talk_to_sage", "map_dungeon", "forge_key", "find_crystal"]
    try:
        idx = chain.index(current_quest_id)
        if idx + 1 < len(chain):
            return chain[idx + 1]
    except ValueError:
        pass
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
