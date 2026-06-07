"""Context Manager — agent memory salience filtering and compaction (C v ETCSLV).

Zodpovednosti:
  - build_context(agent) → structured summary pre LLM think cyklus
  - salience_filter(memories, state) → odstráni irelevantné spomienky
  - compact(memory) → zlúči podobné spomienky, skráti staré
  - working_memory → aktuálne dôležité veci (goal, pending task, nearby)
"""

import json
from datetime import datetime
from typing import Any, Optional


# Maximum memories before compaction triggers
MAX_MEMORIES = 50
# Keep at most this many after compaction
COMPACT_TARGET = 20
# Age threshold in ticks — memories older than this are "stale"
STALE_AGE_TICKS = 100


class ContextManager:
    """Manages agent context — salience, compaction, and LLM context building."""

    def __init__(self, state_store, db):
        self.state_store = state_store
        self.db = db
        self._working_memory: dict[str, dict] = {}  # npc_id -> {key: value}

    # ═══════════════════════════════════════════
    # CONTEXT BUILDING (pre-LLM)
    # ═══════════════════════════════════════════

    async def build_context(self, npc_id: str) -> str:
        """Build a compact, structured context string for an agent's LLM prompt.

        Output is a ~400-800 char string with the most salient information.
        """
        if not self.state_store:
            return f"Agent {npc_id[:8]}"

        parts = []

        # ── Identity ──
        npc = await self.state_store.get_npc(npc_id)
        brain = await self.state_store.get_brain(npc_id)
        body = await self.state_store.get_body(npc_id)
        soul = await self.state_store.get_soul(npc_id)

        if npc:
            name = npc.get("npc_name", npc_id[:8])
            role = npc.get("role", "unknown")
            parts.append(f"You are {name}, a {role}.")

        # ── Physical state (salient only) ──
        salient_body = []
        if body:
            s = body.get("stamina", 100)
            f = body.get("fatigue", 0)
            h = body.get("hunger", 0)
            if f > 60:
                salient_body.append(f"exhausted (fatigue={f:.0f})")
            if h > 60:
                salient_body.append(f"hungry ({h:.0f})")
            if s < 30:
                salient_body.append(f"low stamina ({s:.0f})")
            else:
                salient_body.append("feeling fine")
        if npc:
            salient_body.append(f"HP={npc.get('health', 100):.0f}")
        parts.append(" | ".join(salient_body))

        # ── State of mind ──
        if brain:
            som = brain.get("state_of_mind", "focused")
            goal = brain.get("current_goal", "")
            parts.append(f"Mind: {som}")
            if goal:
                parts.append(f"Goal: {goal[:60]}")

        # ── Working memory (high-priority items) ──
        wm = self._working_memory.get(npc_id, {})
        if wm.get("priority_item"):
            parts.append(f"Priority: {wm['priority_item'][:80]}")
        if wm.get("blocked_on"):
            parts.append(f"Blocked: {wm['blocked_on'][:60]}")

        # ─️ Salient memories (last 3 actions) ──
        if brain:
            memories = json.loads(brain.get("memory", "[]"))
            if memories:
                last3 = memories[-3:]
                action_summary = []
                for m in last3:
                    action = m.get("action", "?")
                    reason = m.get("reasoning", "")
                    result = m.get("result", "?")
                    action_summary.append(f"{action}({result})")
                parts.append(f"Recent: {' → '.join(action_summary)}")

        # ── Salient nearby events ──
        try:
            all_npcs = await self.state_store.get_all_active_npcs()
            if npc:
                from agora.agent_os.dungeon_map import get_room_at, distance
                my_room = get_room_at(npc["pos_x"], npc["pos_y"])
                nearby = [
                    o["npc_name"] for o in all_npcs
                    if o["npc_id"] != npc_id
                    and get_room_at(o["pos_x"], o["pos_y"]) == my_room
                ]
                if nearby:
                    parts.append(f"Nearby: {', '.join(nearby)}")
        except Exception:
            pass

        # ── Pending help requests (salient) ──
        try:
            pending = await self.state_store.get_pending_help_requests()
            for hr in pending:
                if hr.get("requester_name") == npc.get("npc_name", ""):
                    parts.append(f"Waiting for {hr.get('helper_name')} ({hr.get('problem_type')})")
                elif hr.get("helper_name") == npc.get("npc_name", ""):
                    parts.append(f"Needed by {hr.get('requester_name')} ({hr.get('problem_type')})")
        except Exception:
            pass

        return " | ".join(parts)

    # ═══════════════════════════════════════════
    # SALIENCE FILTER — remove irrelevant memories
    # ═══════════════════════════════════════════

    def salience_filter(self, memories: list[dict], current_state: dict) -> list[dict]:
        """Remove low-salience memories.

        Retention rules:
          - Keep memories with explicit results ("success" or "failure")
          - Keep help-related memories (seek_help, help_request)
          - Keep combat/injury memories
          - Keep goal-related memories (match current_goal)
          - Discard routine "scout_area" / "nothing unusual" memories
          - Discard memories older than STALE_AGE_TICKS if they're routine
        """
        if not memories:
            return []

        current_goal = current_state.get("self", {}).get("current_goal", "").lower() if current_state else ""
        filtered = []

        for mem in memories:
            action = mem.get("action", "")
            result = mem.get("result", "")
            reasoning = mem.get("reasoning", "")
            tick = mem.get("tick", 0)
            content = f"{action} {result} {reasoning}".lower()

            # Always keep: help interactions
            if action in ("seek_help", "help_request", "complete_help"):
                filtered.append(mem)
                continue

            # Always keep: combat/injury
            if any(w in content for w in ["combat", "attack", "injury", "heal", "damage", "health"]):
                filtered.append(mem)
                continue

            # Always keep: explicit results (success/failure)
            if result in ("success", "error", "failure"):
                filtered.append(mem)
                continue

            # Always keep: goal-relevant
            if current_goal and any(w in content for w in current_goal.split()):
                filtered.append(mem)
                continue

            # Discard: routine exploration with no findings
            if "scout_area" in content and ("nothing" in content or "unusual" in content):
                continue

            # Discard: stale and generic
            if tick > 0 and mem.get("tick", 0) < (current_state.get("tick", 0) - STALE_AGE_TICKS):
                if "routine" in content or "nothing" in content:
                    continue

            # Keep everything else
            filtered.append(mem)

        return filtered

    # ═══════════════════════════════════════════
    # COMPACTION — merge and shorten
    # ═══════════════════════════════════════════

    def compact(self, memories: list[dict]) -> list[dict]:
        """Compress memories when they exceed MAX_MEMORIES.

        Strategy:
          1. Group consecutive same-action memories
          2. Merge them into one summary entry
          3. Drop duplicates (same action + same params)
          4. If still too many, summarize oldest ones
        """
        if len(memories) <= MAX_MEMORIES:
            return memories

        # Step 1: Remove exact duplicates (same action + same params)
        seen = set()
        deduped = []
        for mem in memories:
            key = f"{mem.get('action', '')}:{json.dumps(mem.get('params', {}), sort_keys=True)}"
            if key not in seen:
                seen.add(key)
                deduped.append(mem)

        # Step 2: Group consecutive same actions
        if len(deduped) > COMPACT_TARGET:
            grouped = []
            i = 0
            while i < len(deduped):
                current_action = deduped[i].get("action", "")
                batch = [deduped[i]]
                j = i + 1
                while j < len(deduped) and deduped[j].get("action", "") == current_action:
                    batch.append(deduped[j])
                    j += 1

                if len(batch) >= 3:
                    # Merge batch into summary
                    grouped.append({
                        "action": current_action,
                        "tick": batch[0].get("tick", 0),
                        "count": len(batch),
                        "result": batch[-1].get("result", "unknown"),
                        "reasoning": f"Repeated {current_action} {len(batch)} times",
                        "timestamp": datetime.utcnow().isoformat(),
                        "compacted": True,
                    })
                else:
                    grouped.extend(batch)
                i = j

            deduped = grouped

        # Step 3: If still too many, keep only last COMPACT_TARGET
        if len(deduped) > COMPACT_TARGET:
            deduped = deduped[-COMPACT_TARGET:]

        return deduped

    async def check_and_compact(self, npc_id: str) -> bool:
        """Check if an NPC's memory needs compaction and compact if needed.

        Returns True if compaction happened.
        """
        if not self.state_store:
            return False

        try:
            brain = await self.state_store.get_brain(npc_id)
            if not brain:
                return False

            memories = json.loads(brain.get("memory", "[]"))
            if len(memories) <= MAX_MEMORIES:
                return False

            # Compact
            compacted = self.compact(memories)
            await self.state_store.update_brain(npc_id, {
                "memory": json.dumps(compacted),
            })
            print(f"[ContextManager] Compacted {npc_id[:8]} memory: {len(memories)} → {len(compacted)}")
            return True

        except Exception as e:
            print(f"[ContextManager] Compaction error for {npc_id[:8]}: {e}")
            return False

    # ═══════════════════════════════════════════
    # WORKING MEMORY
    # ═══════════════════════════════════════════

    async def set_working_memory(self, npc_id: str, key: str, value: Any):
        """Set a high-priority working memory item.

        Working memory persists across ticks and overrides regular memory.
        Used for: current goal progress, blocked status, priority tasks.
        """
        if npc_id not in self._working_memory:
            self._working_memory[npc_id] = {}
        self._working_memory[npc_id][key] = str(value)[:200]

    def get_working_memory(self, npc_id: str, key: str = None) -> Any:
        """Get working memory item(s)."""
        wm = self._working_memory.get(npc_id, {})
        if key:
            return wm.get(key)
        return wm

    async def clear_working_memory(self, npc_id: str):
        """Clear all working memory for an agent."""
        self._working_memory.pop(npc_id, None)

    async def apply_salience_filter(self, npc_id: str, current_state: dict = None):
        """Apply salience filter to an NPC's brain memory in DB."""
        if not self.state_store:
            return

        try:
            brain = await self.state_store.get_brain(npc_id)
            if not brain:
                return

            memories = json.loads(brain.get("memory", "[]"))
            if not memories:
                return

            filtered = self.salience_filter(memories, current_state or {})
            if len(filtered) < len(memories):
                await self.state_store.update_brain(npc_id, {
                    "memory": json.dumps(filtered),
                })
                print(f"[ContextManager] Filtered {npc_id[:8]}: {len(memories)} → {len(filtered)} memories")
        except Exception as e:
            print(f"[ContextManager] Salience error for {npc_id[:8]}: {e}")
