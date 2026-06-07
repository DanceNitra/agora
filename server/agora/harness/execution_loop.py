"""Execution Loop — formal observe-think-act harness (E v ETCSLV).

Každý tick:
  1. OBSERVE:  perceive state (body, position, pending helps, memories)
  2. THINK:    LLM or rule-based decision → which tool + params
  3. ACT:      execute via ToolRegistry, log result, update memory

ExecutionLoop nahrádza starý _think() + _seek_help_auto() pattern
formálnym decision-making cyklom.
"""

import json
import random
from datetime import datetime
from typing import Any, Callable, Optional

from agora.harness.tool_registry import ToolRegistry, ToolCall


class ExecutionEngine:
    """Formal observe-think-act cycle for dungeon NPCs."""

    def __init__(self, state_store, tool_registry: ToolRegistry, db,
                 llm_client: Optional[Callable] = None):
        self.state_store = state_store
        self.tool_registry = tool_registry
        self.db = db
        self.llm_client = llm_client
        self._action_history: dict[str, list[dict]] = {}  # npc_id -> [{tick, action, result}]
        self._tick_count: int = 0

    # ═══════════════════════════════════════════
    # OBSERVE — perceive the world
    # ═══════════════════════════════════════════

    async def observe(self, npc_id: str) -> dict:
        """Collect full perceptual state for an agent.

        Returns structured dict with:
          - self: body, brain, soul, skills
          - position: room, coordinates
          - nearby: other NPCs in same room
          - pending: pending help requests
          - memories: recent memories from brain
        """
        state = {
            "npc_id": npc_id,
            "tick": 0,
            "self": {},
            "position": {},
            "nearby": [],
            "pending_helps": [],
            "memories": [],
        }

        if not self.state_store:
            return state

        # ── Self state ──
        npc = await self.state_store.get_npc(npc_id)
        body = await self.state_store.get_body(npc_id)
        brain = await self.state_store.get_brain(npc_id)
        soul = await self.state_store.get_soul(npc_id)
        skills = await self.state_store.get_all_skills(npc_id)

        if npc:
            state["self"] = {
                "name": npc.get("npc_name", "unknown"),
                "role": npc.get("role", ""),
                "health": npc.get("health", 100),
                "status": npc.get("status", "active"),
                "pos_x": npc.get("pos_x", 0),
                "pos_y": npc.get("pos_y", 0),
            }

        if body:
            state["self"].update({
                "stamina": body.get("stamina", 100),
                "fatigue": body.get("fatigue", 0),
                "hunger": body.get("hunger", 0),
                "awareness": body.get("awareness", 1.0),
            })

        if brain:
            state["self"]["state_of_mind"] = brain.get("state_of_mind", "focused")
            state["self"]["current_goal"] = brain.get("current_goal", "")
            state["self"]["plan_stack"] = json.loads(brain.get("plan_stack", "[]"))
            memories_raw = brain.get("memory", "[]")
            state["memories"] = json.loads(memories_raw) if memories_raw else []

        if soul:
            state["self"]["emotional_state"] = soul.get("emotional_state", "neutral")
            state["self"]["moral_alignment"] = soul.get("moral_alignment", "neutral")

        if skills:
            state["self"]["skills"] = {
                s["skill_name"]: {"level": s["level"], "xp": s["xp"]}
                for s in skills
            }

        # ── Position / room ──
        if npc:
            try:
                from agora.agent_os.dungeon_map import get_room_at
                state["position"]["room"] = get_room_at(
                    npc.get("pos_x", 0), npc.get("pos_y", 0)
                )
                state["position"]["x"] = npc.get("pos_x", 0)
                state["position"]["y"] = npc.get("pos_y", 0)
            except Exception:
                state["position"]["room"] = "unknown"

        # ── Nearby NPCs ──
        try:
            all_npcs = await self.state_store.get_all_active_npcs()
            my_pos = (npc["pos_x"], npc["pos_y"]) if npc else (0, 0)
            my_room = state["position"].get("room", "")
            for other in all_npcs:
                if other["npc_id"] != npc_id:
                    from agora.agent_os.dungeon_map import get_room_at, distance
                    other_room = get_room_at(other["pos_x"], other["pos_y"])
                    if other_room == my_room:
                        d = distance(my_pos[0], my_pos[1],
                                      other["pos_x"], other["pos_y"])
                        state["nearby"].append({
                            "name": other["npc_name"],
                            "role": other.get("role", ""),
                            "distance_px": round(d, 1),
                            "health": other.get("health", 100),
                        })
        except Exception:
            pass

        # ── Pending help requests ──
        try:
            pending = await self.state_store.get_pending_help_requests()
            state["pending_helps"] = [
                {
                    "id": hr.get("id"),
                    "requester": hr.get("requester_name"),
                    "helper": hr.get("helper_name"),
                    "problem": hr.get("problem_type"),
                    "status": hr.get("status"),
                }
                for hr in pending
            ]
        except Exception:
            pass

        return state

    # ═══════════════════════════════════════════
    # THINK — decide next action
    # ═══════════════════════════════════════════

    async def think(self, npc_id: str, state: dict) -> Optional[dict]:
        """Decide what tool to call and with what parameters.

        Returns decision dict: {tool_id, parameters, reasoning}
        or None if no action needed.
        """
        s = state.get("self", {})
        name = s.get("name", "unknown")
        goal = s.get("current_goal", "")
        state_of_mind = s.get("state_of_mind", "focused")
        health = s.get("health", 100)
        fatigue = s.get("fatigue", 0)
        stamina = s.get("stamina", 100)

        # Emergency: low health → seek healing
        if health < 25 and stamina > 10:
            return {
                "tool_id": "seek_help",
                "parameters": {
                    "helper_name": "Zara",
                    "problem_type": "healing",
                    "description": f"{name} critically injured (HP={health:.0f})",
                },
                "reasoning": f"Low health ({health:.0f}), need healing",
            }

        # Fatigue: rest if exhausted
        if fatigue > 75 or stamina < 15:
            return {
                "tool_id": "move",
                "parameters": {"target_x": s.get("pos_x", 400), "target_y": s.get("pos_y", 300)},
                "reasoning": f"Too tired (fatigue={fatigue:.0f}, stamina={stamina:.0f}), staying put",
            }

        # Confused/panicked → seek help for current goal
        if state_of_mind in ("confused", "panicked"):
            problem_type = self._classify_problem(goal)
            if problem_type:
                # Find the best helper from help matrix
                helper_name = self._find_best_helper_for(name, problem_type)
                if helper_name:
                    return {
                        "tool_id": "seek_help",
                        "parameters": {
                            "helper_name": helper_name,
                            "problem_type": problem_type,
                            "description": f"{name} needs help with '{goal[:60]}'",
                        },
                        "reasoning": f"Confused about {goal}, asking {helper_name}",
                    }

        # Goal-based: execute plan step
        plan_stack = state.get("memories", [])
        if plan_stack:
            return None  # still following existing plan (handled elsewhere)

        # LLM think (if enabled)
        if self.llm_client:
            try:
                decision = await self._llm_think(state)
                if decision:
                    return decision
            except Exception:
                pass  # fall through to random action

        # Default: random role-appropriate action
        return await self._random_action(name, state)

    def _classify_problem(self, goal: str) -> Optional[str]:
        """Map a goal to a problem type from help matrix."""
        if not goal:
            return None
        g = goal.lower()
        if any(w in g for w in ["fight", "combat", "attack", "defend", "battle"]):
            return "combat"
        if any(w in g for w in ["craft", "forge", "smith", "build", "repair"]):
            return "crafting"
        if any(w in g for w in ["research", "study", "read", "learn", "knowledge", "scroll"]):
            return "knowledge"
        if any(w in g for w in ["navigate", "explore", "find", "search", "map", "scout"]):
            return "navigation"
        if any(w in g for w in ["brew", "potion", "alchemy", "herb", "elixir"]):
            return "alchemy"
        if any(w in g for w in ["trade", "sell", "buy", "bargain", "deal"]):
            return "trading"
        if any(w in g for w in ["heal", "cure", "medicine"]):
            return "healing"
        return None

    def _find_best_helper_for(self, requester_name: str, problem_type: str) -> Optional[str]:
        """Find the best NPC to help with a problem type (from help matrix)."""
        try:
            from agora.agent_os.agent_os import HELP_MATRIX
            helpers = HELP_MATRIX.get(problem_type, [])
            if not helpers:
                return None
            # Skip self
            qualified = [(h, s, d) for h, s, d in helpers if h != requester_name]
            return qualified[0][0] if qualified else None
        except Exception:
            return None

    async def _llm_think(self, state: dict) -> Optional[dict]:
        """Use LLM to decide next action."""
        s = state.get("self", {})
        nearby = state.get("nearby", [])
        pending = state.get("pending_helps", [])
        name = s.get("name", "agent")

        prompt = (
            f"You are {name}, a {s.get('role', 'dungeon')} agent in a dungeon."
            f"\nState: health={s.get('health')}, stamina={s.get('stamina')}, "
            f"fatigue={s.get('fatigue')}, goal='{s.get('current_goal', 'none')}'"
            f"\nLocation: {state.get('position', {}).get('room', 'unknown')}"
            f"\nNearby NPCs: {[n['name'] for n in nearby]}"
            f"\nPending helps: {[(p['requester'], p['problem']) for p in pending]}"
            f"\nSkills: {list(s.get('skills', {}).keys())}"
            f"\n\nAvailable tools: move, query_library, create_artifact, seek_help"
            f"\nChoose ONE tool and parameters. Return valid JSON: {{\"tool\": \"tool_id\", \"params\": {{...}}}}"
        )

        response = await self.llm_client(prompt)
        try:
            decision = json.loads(str(response))
            tool_id = decision.get("tool")
            params = decision.get("params", {})
            if tool_id:
                return {
                    "tool_id": tool_id,
                    "parameters": params,
                    "reasoning": f"LLM chose {tool_id}",
                }
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    async def _random_action(self, name: str, state: dict) -> Optional[dict]:
        """Default random action when no clear decision."""
        import random

        s = state.get("self", {})
        state_of_mind = s.get("state_of_mind", "focused")

        # Only act if not resting
        if state_of_mind == "resting":
            return {
                "tool_id": "move",
                "parameters": {
                    "target_x": s.get("pos_x", 400),
                    "target_y": s.get("pos_y", 300),
                },
                "reasoning": f"Resting in place ({name})",
            }

        options = ["scout_area", "create_artifact", "query_library"]
        picks = random.choices(options, weights=[0.5, 0.3, 0.2], k=1)
        tool_id = picks[0]

        params = {}
        if tool_id == "create_artifact":
            params = {"title": f"{name}'s observation", "content": f"Observed nothing unusual at tick {state.get('tick', 0)}."}
        elif tool_id == "query_library":
            params = {"question": f"What should I do, ancient oracle?"}

        return {
            "tool_id": tool_id,
            "parameters": params,
            "reasoning": f"Random {tool_id} action",
        }

    # ═══════════════════════════════════════════
    # ACT — execute decision
    # ═══════════════════════════════════════════

    async def act(self, npc_id: str, decision: dict, broadcast_fn=None) -> dict:
        """Execute the chosen tool and return result."""
        if not decision:
            return {"status": "noop", "reason": "no decision"}

        tool_id = decision["tool_id"]
        params = decision.get("parameters", {})

        # Execute via ToolRegistry
        result = await self.tool_registry.call_tool(
            agent_id=npc_id,
            tool_id=tool_id,
            params=params,
            broadcast_fn=broadcast_fn,
        )

        # Log to action history
        if npc_id not in self._action_history:
            self._action_history[npc_id] = []
        self._action_history[npc_id].append({
            "tick": 0,
            "tool": tool_id,
            "params": params,
            "result": result,
            "reasoning": decision.get("reasoning", ""),
            "timestamp": datetime.utcnow().isoformat(),
        })

        return result

    # ═══════════════════════════════════════════
    # FULL CYCLE
    # ═══════════════════════════════════════════

    async def tick(self, npc_id: str, broadcast_fn=None) -> dict:
        """Run one full observe-think-act cycle for an agent.

        Returns dict with {observe, think, act} results.
        """
        # 1. OBSERVE
        state = await self.observe(npc_id)
        state["tick"] = self._tick_count if hasattr(self, '_tick_count') else 0

        # 2. THINK
        decision = await self.think(npc_id, state)
        if not decision:
            return {
                "npc_id": npc_id[:8],
                "observe": {
                    "position": state.get("position", {}),
                    "state_of_mind": state.get("self", {}).get("state_of_mind", ""),
                    "nearby": len(state.get("nearby", [])),
                },
                "think": None,
                "act": {"status": "noop", "reason": "no decision"},
            }

        # 3. ACT
        result = await self.act(npc_id, decision, broadcast_fn)

        # Record in brain memory
        if self.state_store and decision and result.get("status") != "error":
            try:
                brain = await self.state_store.get_brain(npc_id)
                if brain:
                    memories = json.loads(brain.get("memory", "[]"))
                    memories.append({
                        "tick": self._tick_count if hasattr(self, '_tick_count') else 0,
                        "action": decision["tool_id"],
                        "params": decision.get("parameters", {}),
                        "reasoning": decision.get("reasoning", ""),
                        "result": result.get("status", "unknown"),
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    # Keep only last 20 memories
                    if len(memories) > 20:
                        memories = memories[-20:]
                    await self.state_store.update_brain(npc_id, {
                        "memory": json.dumps(memories),
                        "last_decision": f"{decision['tool_id']}({json.dumps(decision.get('parameters', {}))})",
                    })
            except Exception as e:
                print(f"[ExecutionLoop] Memory update error: {e}")

        return {
            "npc_id": npc_id[:8],
            "observe": {
                "position": state.get("position", {}),
                "state_of_mind": state.get("self", {}).get("state_of_mind", ""),
                "nearby": len(state.get("nearby", [])),
            },
            "think": decision,
            "act": result,
        }

    # ═══════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════

    def get_action_history(self, npc_id: str, limit: int = 10) -> list[dict]:
        """Get recent actions for an NPC."""
        history = self._action_history.get(npc_id, [])
        return history[-limit:]
