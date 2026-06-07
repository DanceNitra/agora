"""Warden actions — verification, sandbox, gatekeeping.

Real actions that Warden can execute:
  - verify: Run N-run LLM verification on a quest
  - sandbox: Run a flagged action in isolation for testing
"""

import json
from datetime import datetime


async def action_verify_quest(config: dict, quest: dict, params: dict) -> dict:
    """Run Warden N-run verification on a quest.

    This delegates to the QuestEngine's verify_quest method.
    The quest should already be in 'review' status.
    """
    qe = config.get("quest_engine")
    if not qe:
        return {"status": "error", "output": "No quest engine available", "simulated": True}

    runs = params.get("runs", 3)
    quest_id = quest.get("id", "")

    if not quest_id:
        return {"status": "error", "output": "No quest ID"}

    result = await qe.verify_quest(quest_id, runs=runs)

    if "error" in result:
        return {
            "status": "error",
            "output": f"Verification failed: {result['error']}",
            "simulated": True,
        }

    verification = result.get("verification", {})
    outcome = verification.get("outcome", "fail")

    return {
        "status": "ok" if outcome == "pass" else "fail",
        "output": (
            f"Warden N-run: {outcome.upper()} "
            f"({verification.get('pass_count', 0)}/{verification.get('total_runs', 0)} pass)"
        ),
        "verification": verification,
    }


async def action_sandbox(config: dict, quest: dict, params: dict) -> dict:
    """Run a flagged action in sandbox (simulated isolation)."""
    action_to_test = params.get("action", "unknown")
    agent = params.get("agent", "unknown")

    sandbox_log = {
        "quest_id": quest.get("id"),
        "agent": agent,
        "action": action_to_test,
        "sandboxed_at": datetime.now().isoformat(),
        "status": "isolated",
    }

    print(f"[Warden Sandbox] Isolated action '{action_to_test}' from {agent}")

    return {
        "status": "ok",
        "output": f"Action '{action_to_test}' sandboxed successfully. "
                  f"Run in sandbox: {params.get('command', 'N/A')}",
        "sandbox_log": sandbox_log,
        "simulated": True,
    }
