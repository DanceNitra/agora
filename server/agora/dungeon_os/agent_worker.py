"""Agent Worker — quest-driven tick engine for Dungeon OS NPCs.

Each tick:
  1. Find all claimed quests
  2. For each, determine the owning NPC
  3. NPC decides an action based on quest + skills
  4. Action is executed (real shell/file/API)
  5. After action, quest is submitted for Warden review
  6. Warden verifies (or denies)

This transforms quests from abstract board items into real executed work.
"""

import json
import time
from datetime import datetime
from typing import Optional

from agora.dungeon_os.actions.registry import get_registry


# Map NPC names → typical action skills based on subsystem
NPC_WORKFLOW = {
    "hermes": {
        "comms": {"skill": "send_message", "params": {}},
        "knowledge": {"skill": "deliver", "params": {}},
    },
    "lyra": {
        "comms": {"skill": "send_message", "params": {}},
    },
    "scribe": {
        "knowledge": {"skill": "write_note", "params": {}},
        "safety": {"skill": "query", "params": {}},
    },
    "mordecai": {
        "knowledge": {"skill": "query", "params": {}},
    },
    "forge": {
        "tooling": {"skill": "run_script", "params": {}},
        "knowledge": {"skill": "store_blueprint", "params": {"command": "echo 'Blueprint stored'"}},
    },
    "grom": {
        "tooling": {"skill": "build_station", "params": {}},
    },
    "openclaw": {
        "tooling": {"skill": "run_script", "params": {}},
    },
    "ledger": {
        "economy": {"skill": "query", "params": {}},
    },
    "finn": {
        "economy": {"skill": "query", "params": {}},
    },
    "warden": {
        "safety": {"skill": "verify", "params": {}},
    },
    "guard": {
        "safety": {"skill": "sandbox", "params": {}},
    },
}


class AgentWorker:
    """Processes claimed quests: NPC works → submits → Warden verifies."""

    def __init__(self, quest_engine, db=None, config: Optional[dict] = None):
        self.qe = quest_engine
        self.db = db
        self.config = config or {}
        self.registry = get_registry()
        self._stats = {"ticks": 0, "actions_taken": 0, "quests_completed": 0}

    async def tick(self) -> dict:
        """Run one work tick. Returns summary of what happened."""
        self._stats["ticks"] += 1
        tick_start = time.time()

        # Get all claimed quests (agents working on them)
        claimed = await self.qe.list_quests("claimed")
        review = await self.qe.list_quests("review")

        results = []

        # Step 1: Process claimed quests (NPC does the work)
        for quest in claimed:
            work_result = await self._process_claimed(quest)
            results.append(work_result)

        # Step 2: Process review quests (Warden verifies)
        for quest in review:
            verify_result = await self._process_review(quest)
            results.append(verify_result)

        # Clean up empty results
        results = [r for r in results if r]

        tick_duration = time.time() - tick_start

        return {
            "tick": self._stats["ticks"],
            "claimed_processed": len([r for r in results if r.get("stage") == "work"]),
            "verified": len([r for r in results if r.get("stage") == "verify"]),
            "actions_taken": self._stats["actions_taken"],
            "duration_ms": round(tick_duration * 1000),
            "results": results,
        }

    async def _process_claimed(self, quest: dict) -> Optional[dict]:
        """An NPC works on a claimed quest: executes action, submits."""
        npc_name = quest.get("owner", "").lower()
        subsystem = quest.get("subsystem", "knowledge")
        quest_id = quest.get("id", "")

        if not npc_name:
            return None

        # Determine the action
        workflow = NPC_WORKFLOW.get(npc_name, {})
        action_info = workflow.get(subsystem, {})

        if not action_info:
            # Generic fallback: try to write a note about the quest
            action_info = {"skill": "write_note", "params": {}}
            skill = "write_note"
        else:
            skill = action_info.get("skill", "write_note")

        action_params = dict(action_info.get("params", {}))
        # Add quest context to params
        action_params["message"] = quest.get("goal", "")
        action_params["title"] = quest.get("title", "")
        action_params["body"] = quest.get("goal", "")
        action_params["details"] = json.dumps({
            "quest_id": quest_id,
            "criteria": quest.get("success_criteria", []),
        })

        # Execute the action via registry
        action_result = await self.registry.execute(
            npc_name=npc_name,
            skill_name=skill,
            config=self.config,
            quest=quest,
            params=action_params,
        )

        self._stats["actions_taken"] += 1

        print(
            f"[Worker] {npc_name.capitalize()} executed '{skill}' "
            f"on '{quest_id}': {action_result.get('status', '?')}"
        )

        # If action succeeded, submit for Warden review
        if action_result.get("status") == "ok":
            submit_result = await self.qe.submit_for_review(quest_id, quest.get("owner", ""))
            if "error" in submit_result:
                print(f"[Worker] Submit failed for {quest_id}: {submit_result['error']}")
                return {
                    "stage": "work",
                    "npc": npc_name,
                    "quest": quest_id,
                    "action": skill,
                    "action_status": "ok",
                    "submit_status": "error",
                    "error": submit_result["error"],
                    "output_preview": action_result.get("output", "")[:100],
                }

            return {
                "stage": "work",
                "npc": npc_name,
                "quest": quest_id,
                "action": skill,
                "action_status": "ok",
                "submit_status": "ok",
                "output_preview": action_result.get("output", "")[:100],
            }
        else:
            # Action failed — log but don't submit
            return {
                "stage": "work",
                "npc": npc_name,
                "quest": quest_id,
                "action": skill,
                "action_status": action_result.get("status", "error"),
                "output_preview": action_result.get("output", "")[:100],
                "simulated": action_result.get("simulated", False),
            }

    async def _process_review(self, quest: dict) -> Optional[dict]:
        """Warden verifies a quest in review status."""
        quest_id = quest.get("id", "")

        # Warden N-run verification
        verify_result = await self.qe.verify_quest(quest_id, runs=3)

        if "error" in verify_result:
            print(f"[Worker] Verify failed for {quest_id}: {verify_result['error']}")
            return None

        verification = verify_result.get("verification", {})
        outcome = verification.get("outcome", "fail")
        self._stats["quests_completed"] += 1 if outcome == "pass" else 0

        print(
            f"[Worker] Warden verified '{quest_id}': {outcome.upper()} "
            f"({verification.get('pass_count', 0)}/{verification.get('total_runs', 0)})"
        )

        return {
            "stage": "verify",
            "quest": quest_id,
            "outcome": outcome,
            "pass_count": verification.get("pass_count", 0),
            "total_runs": verification.get("total_runs", 3),
            "missing_criteria": verification.get("missing_criteria", []),
        }

    def get_stats(self) -> dict:
        return dict(self._stats)
