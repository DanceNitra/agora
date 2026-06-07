"""Action Registry — maps Dungeon OS NPC skills to real executable functions.

Each NPC role has a set of skills (defined in roles.py). This registry
attaches real Python functions to those skills so agents can actually
DO things in the real world when they work on a quest.

Architecture:
  skill_name → ActionFunction(config, quest) → {"status": "ok", "output": "..."}
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

# Type for an action function
# Takes: config dict, quest dict, optional params
# Returns: dict with status and output
ActionFunc = Callable[
    [dict, dict, dict],
    Coroutine[Any, Any, dict],
]


class ActionRegistry:
    """Global registry of real actions that NPCs can execute."""

    def __init__(self):
        self._actions: dict[str, ActionFunc] = {}
        self._npc_actions: dict[str, list[str]] = {}  # npc_name → [skill_names]

    def register(self, npc_name: str, skill_name: str, func: ActionFunc):
        """Register an action function for a NPC's skill."""
        self._actions[f"{npc_name}:{skill_name}"] = func
        if npc_name not in self._npc_actions:
            self._npc_actions[npc_name] = []
        self._npc_actions[npc_name].append(skill_name)

    async def execute(
        self,
        npc_name: str,
        skill_name: str,
        config: dict,
        quest: dict,
        params: Optional[dict] = None,
    ) -> dict:
        """Execute a registered action. Returns result dict."""
        key = f"{npc_name}:{skill_name}"
        func = self._actions.get(key)
        if not func:
            # Try generic fallback
            func = self._actions.get(f"*:{skill_name}")
        if not func:
            return {
                "status": "skipped",
                "output": f"No action registered for {npc_name}:{skill_name}",
                "simulated": True,
            }
        try:
            result = await func(config, quest, params or {})
            return result
        except Exception as e:
            return {
                "status": "error",
                "output": f"Action failed: {e}",
                "error": str(e),
            }

    def get_skills(self, npc_name: str) -> list[str]:
        """Get all registered skill names for an NPC."""
        return self._npc_actions.get(npc_name, [])

    def has_action(self, npc_name: str, skill_name: str) -> bool:
        return f"{npc_name}:{skill_name}" in self._actions


# Global singleton
_registry: Optional[ActionRegistry] = None


def get_registry() -> ActionRegistry:
    global _registry
    if _registry is None:
        _registry = ActionRegistry()
        # Import and register built-in actions
        _register_builtins(_registry)
    return _registry


def _register_builtins(registry: ActionRegistry):
    """Register all built-in actions."""
    # Lazy imports to avoid circular deps
    from agora.dungeon_os.actions.hermes import (
        action_send_message,
        action_broadcast,
        action_deliver,
    )
    from agora.dungeon_os.actions.scribe import (
        action_write_note,
        action_query,
        action_summarize,
    )
    from agora.dungeon_os.actions.forge import (
        action_run_script,
        action_build,
        action_request_resources,
    )
    from agora.dungeon_os.actions.warden import (
        action_verify_quest,
        action_sandbox,
    )
    from agora.dungeon_os.actions.corporation import (
        action_scan_horizon,
        action_deep_research,
        action_store_knowledge,
        action_evaluate_proposal,
        action_compound,
    )

    # Hermes
    for skill in ("send_message", "relay", "broadcast", "deliver"):
        registry.register("hermes", skill, action_send_message)

    # Scribe
    registry.register("scribe", "record", action_write_note)
    registry.register("scribe", "write_note", action_write_note)
    registry.register("scribe", "summarize", action_summarize)
    registry.register("scribe", "query", action_query)

    # Forge
    registry.register("forge", "build_station", action_build)
    registry.register("forge", "run_script", action_run_script)
    registry.register("forge", "request_resources", action_request_resources)
    registry.register("forge", "store_blueprint", action_run_script)

    # Warden
    registry.register("warden", "verify", action_verify_quest)
    registry.register("warden", "sandbox", action_sandbox)

    # Corporation roles
    registry.register("scout", "scan_horizon", action_scan_horizon)
    registry.register("scout", "research", action_deep_research)
    registry.register("researcher", "deep_research", action_deep_research)
    registry.register("researcher", "repo_analysis", action_deep_research)
    registry.register("researcher", "docs_analysis", action_deep_research)
    registry.register("researcher", "best_practices", action_deep_research)
    registry.register("brainmaster", "store_knowledge", action_store_knowledge)
    registry.register("brainmaster", "synthesize", action_store_knowledge)
    registry.register("ceo", "evaluate_proposal", action_evaluate_proposal)
    registry.register("cto", "evaluate_proposal", action_evaluate_proposal)
    registry.register("warden", "compound", action_compound)

    # Generic fallbacks
    registry.register("*", "wait", _action_wait)
    registry.register("*", "move", _action_wait)


async def _action_wait(config: dict, quest: dict, params: dict) -> dict:
    """Generic wait/skip action."""
    reason = params.get("reason", "No action needed")
    return {"status": "skipped", "output": f"Wait: {reason}", "simulated": True}
