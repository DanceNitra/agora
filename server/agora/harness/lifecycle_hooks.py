"""Lifecycle Hooks — byzantine validation layer (L v ETCSLV harnesse).

Pre-tick:
  - Save snapshot of NPC state (positions, health, stamina, fatigue, energy)
  - Validate invariants: all values in [0, 100]

Post-tick:
  - Teleportation detection: NPC moved more than v_max * 1.5
  - Energy cheat: unexpected energy gain
  - Skill limit: skill level > 100
  - Health anomaly: health increased without healing
  - Stuck detection: confused/panicked NPC not moving for N ticks
  - Status invariant: dead NPC with position
  - Duplicate help request check
"""

import json
from datetime import datetime
from typing import Any, Optional

# ── Byzantine detection thresholds ──
V_MAX_PX = 4          # max pixels per tick (from physical_world step_px)
V_MAX_TOLERANCE = 1.5 # multiplier for teleport detection
TELEPORT_THRESHOLD = V_MAX_PX * V_MAX_TOLERANCE  # 6px
MAX_HEALTH = 100.0
MAX_STAT = 100.0
MAX_SKILL_LEVEL = 100
STUCK_TICKS = 10  # if an NPC in confused/panicked hasn't moved in 10 ticks, flag it


class LifecycleHooks:
    """Byzantine validation and lifecycle hooks for the tick loop.

    Usage:
        hooks = LifecycleHooks(state_store, db)
        await hooks.pre_tick(npc_ids=[...])    # snapshot + validate
        # ... run tick ...
        violations = await hooks.post_tick()    # diff + detect anomalies
        for v in violations:
            print(f"[Byzantine] {v}")
    """

    def __init__(self, state_store, db):
        self.state_store = state_store
        self.db = db
        self._pre_snapshot: dict[str, dict] = {}   # npc_id -> {pos, health, stamina, ...}
        self._stuck_counter: dict[str, int] = {}    # npc_id -> ticks without movement
        self._violations_log: list[dict] = []
        self._tick_count: int = 0
        # (npc_id, type) -> tick when last persisted. A standing condition (e.g. an NPC stuck
        # in 'panicked') breaches the same invariant EVERY tick; without this guard it wrote one
        # DB row per tick and flooded `events` to 50k+ rows of identical 'stuck' violations
        # (96% of the table). We keep the in-memory log every tick (full fidelity) but persist a
        # given (npc, type) at most once per cooldown — periodic evidence, not a flood.
        self._persist_cooldown: dict[tuple, int] = {}
        self._PERSIST_EVERY_TICKS: int = 300

    # ═══════════════════════════════════════════
    # PRE-TICK — snapshot and invariant check
    # ═══════════════════════════════════════════

    async def pre_tick(self, npc_ids: list[str]) -> list[dict]:
        """Run pre-tick validation. Returns pre-tick violations (invariant breaks)."""
        self._tick_count += 1
        self._pre_snapshot = {}
        violations = []

        if not self.state_store:
            return violations

        for npc_id in npc_ids:
            snapshot = await self._capture_npc_state(npc_id)
            if not snapshot:
                continue

            self._pre_snapshot[npc_id] = snapshot

            # ── Invariant check: all bounds ──
            inv = self._check_invariants(npc_id, snapshot)
            violations.extend(inv)

        if violations:
            for v in violations:
                print(f"[Byzantine:pre]  {v}")

        return violations

    async def _capture_npc_state(self, npc_id: str) -> Optional[dict]:
        """Capture all relevant state for one NPC."""
        try:
            npc = await self.state_store.get_npc(npc_id)
            body = await self.state_store.get_body(npc_id)
            brain = await self.state_store.get_brain(npc_id)

            if not npc:
                return None

            return {
                "pos_x": npc.get("pos_x", 0),
                "pos_y": npc.get("pos_y", 0),
                "health": npc.get("health", 100),
                "status": npc.get("status", "active"),
                "stamina": body.get("stamina", 100) if body else 100,
                "fatigue": body.get("fatigue", 0) if body else 0,
                "hunger": body.get("hunger", 0) if body else 0,
                "state_of_mind": brain.get("state_of_mind", "focused") if brain else "focused",
                "current_goal": brain.get("current_goal", "") if brain else "",
                "energy": npc.get("energy_balance", 100),
            }
        except Exception as e:
            print(f"[Byzantine] Failed to capture state for {npc_id[:8]}: {e}")
            return None

    def _check_invariants(self, npc_id: str, state: dict) -> list[str]:
        """Check basic invariants that must always hold."""
        issues = []
        label = npc_id[:8]

        if state["health"] < 0 or state["health"] > MAX_HEALTH:
            issues.append(f"[{label}] Health invariant: {state['health']} ∉ [0, {MAX_HEALTH}]")

        for field in ("stamina", "fatigue", "hunger"):
            val = state.get(field, 0)
            if val < 0 or val > MAX_STAT:
                issues.append(f"[{label}] {field} invariant: {val} ∉ [0, {MAX_STAT}]")

        if state["status"] == "dead" and state["health"] > 0:
            issues.append(f"[{label}] Status invariant: dead but health={state['health']}")

        return issues

    # ═══════════════════════════════════════════
    # POST-TICK — diff + anomaly detection
    # ═══════════════════════════════════════════

    async def post_tick(self, npc_ids: list[str]) -> list[dict]:
        """Run post-tick validation. Returns detected violations with context.

        Each violation dict: {
            'type': str,          # e.g. 'teleport', 'energy_cheat', 'stuck'
            'npc_id': str,
            'detail': str,
            'old_state': dict,
            'new_state': dict,
        }
        """
        violations = []

        if not self.state_store or not self._pre_snapshot:
            return violations

        for npc_id in npc_ids:
            old_state = self._pre_snapshot.get(npc_id)
            if not old_state:
                continue

            new_state = await self._capture_npc_state(npc_id)
            if not new_state:
                continue

            # ── 1. Teleportation detection ──
            teleport_v = self._detect_teleport(npc_id, old_state, new_state)
            if teleport_v:
                violations.append(teleport_v)

            # ── 2. Health anomaly ──
            health_v = self._detect_health_anomaly(npc_id, old_state, new_state)
            if health_v:
                violations.append(health_v)

            # ── 3. Energy anomaly (for thinking agents) ──
            energy_v = self._detect_energy_anomaly(npc_id, old_state, new_state)
            if energy_v:
                violations.append(energy_v)

            # ── 4. Stuck detection ──
            stuck_v = self._detect_stuck(npc_id, old_state, new_state)
            if stuck_v:
                violations.append(stuck_v)

            # ── 5. Status invariant ──
            status_v = self._detect_status_violation(npc_id, old_state, new_state)
            if status_v:
                violations.append(status_v)

        # Log all violations
        for v in violations:
            print(f"[Byzantine:post] [{v['type']}] {v['detail']}")
            self._violations_log.append({
                **v,
                "tick": self._tick_count,
                "timestamp": datetime.utcnow().isoformat(),
            })

        # Persist to DB if there are violations
        if violations:
            await self._persist_violations(violations)

        return violations

    def _detect_teleport(self, npc_id: str, old: dict, new: dict) -> Optional[dict]:
        """Detect if an NPC moved more than allowed per tick."""
        ox, oy = old["pos_x"], old["pos_y"]
        nx, ny = new["pos_x"], new["pos_y"]

        dx = nx - ox
        dy = ny - oy
        dist = (dx * dx + dy * dy) ** 0.5

        if dist > TELEPORT_THRESHOLD:
            return {
                "type": "teleport",
                "npc_id": npc_id,
                "severity": "warning" if dist < TELEPORT_THRESHOLD * 3 else "critical",
                "detail": (
                    f"{npc_id[:8]} moved {dist:.1f}px (max {TELEPORT_THRESHOLD}px) "
                    f"— ({ox:.0f},{oy:.0f}) → ({nx:.0f},{ny:.0f})"
                ),
                "old_state": old,
                "new_state": new,
            }
        return None

    def _detect_health_anomaly(self, npc_id: str, old: dict, new: dict) -> Optional[dict]:
        """Detect if health increased without cause (no healing action)."""
        oh = old["health"]
        nh = new["health"]

        if nh > oh + 2.0:  # > 2 health gain in one tick is suspicious
            return {
                "type": "health_anomaly",
                "npc_id": npc_id,
                "severity": "warning",
                "detail": (
                    f"{npc_id[:8]} health increased {oh:.1f} → {nh:.1f} "
                    f"(+{nh - oh:.1f} in one tick, no healing detected)"
                ),
                "old_state": old,
                "new_state": new,
            }
        return None

    def _detect_energy_anomaly(self, npc_id: str, old: dict, new: dict) -> Optional[dict]:
        """Detect if energy increased more than allowed (max replenish is 4/tick)."""
        old_energy = old.get("energy", 100)
        new_energy = new.get("energy", 100)
        MAX_ENERGY_GAIN = 4.0  # max replenish in RoomClusterScheduler

        if new_energy > old_energy + MAX_ENERGY_GAIN + 0.5:  # small buffer
            return {
                "type": "energy_cheat",
                "npc_id": npc_id,
                "severity": "critical",
                "detail": (
                    f"{npc_id[:8]} energy gained {new_energy - old_energy:.1f} "
                    f"(max allowed {MAX_ENERGY_GAIN}) — {old_energy:.1f} → {new_energy:.1f}"
                ),
                "old_state": old,
                "new_state": new,
            }
        return None

    def _detect_stuck(self, npc_id: str, old: dict, new: dict) -> Optional[dict]:
        """Detect NPCs stuck in confused/panicked without moving."""
        old_pos = (old["pos_x"], old["pos_y"])
        new_pos = (new["pos_x"], new["pos_y"])
        state_of_mind = old.get("state_of_mind", "")

        if state_of_mind in ("confused", "panicked"):
            if old_pos == new_pos:
                self._stuck_counter[npc_id] = self._stuck_counter.get(npc_id, 0) + 1
            else:
                self._stuck_counter[npc_id] = 0  # reset if they moved

            if self._stuck_counter.get(npc_id, 0) >= STUCK_TICKS:
                return {
                    "type": "stuck",
                    "npc_id": npc_id,
                    "severity": "warning",
                    "detail": (
                        f"{npc_id[:8]} stuck for {self._stuck_counter[npc_id]} ticks "
                        f"in '{state_of_mind}' without moving — "
                        f"goal: '{old.get('current_goal', 'none')[:50]}'"
                    ),
                    "old_state": old,
                    "new_state": new,
                }
        else:
            self._stuck_counter[npc_id] = 0  # reset if not confused

        return None

    def _detect_status_violation(self, npc_id: str, old: dict, new: dict) -> Optional[dict]:
        """Detect dead NPC with position changes."""
        if old["status"] == "dead" and new["status"] == "dead":
            same_pos = (old["pos_x"] == new["pos_x"] and old["pos_y"] == new["pos_y"])
            if not same_pos:
                return {
                    "type": "status_violation",
                    "npc_id": npc_id,
                    "severity": "critical",
                    "detail": (
                        f"{npc_id[:8]} is DEAD but position changed "
                        f"({old['pos_x']:.0f},{old['pos_y']:.0f}) → "
                        f"({new['pos_x']:.0f},{new['pos_y']:.0f})"
                    ),
                    "old_state": old,
                    "new_state": new,
                }
        return None

    # ═══════════════════════════════════════════
    # SKILL LIMIT VALIDATION (separate, heavier check)
    # ═══════════════════════════════════════════

    async def validate_skill_limits(self, npc_id: str) -> Optional[dict]:
        """Check that no skill exceeds MAX_SKILL_LEVEL."""
        if not self.state_store:
            return None

        try:
            skills = await self.state_store.get_all_skills(npc_id)
            for skill in skills:
                if skill["level"] > MAX_SKILL_LEVEL:
                    return {
                        "type": "skill_limit",
                        "npc_id": npc_id,
                        "severity": "warning",
                        "detail": (
                            f"{npc_id[:8]} skill '{skill['skill_name']}' "
                            f"level={skill['level']} exceeds max {MAX_SKILL_LEVEL}"
                        ),
                        "skill_name": skill["skill_name"],
                        "level": skill["level"],
                    }
        except Exception as e:
            print(f"[Byzantine] Skill validation error for {npc_id[:8]}: {e}")

        return None

    # ═══════════════════════════════════════════
    # DUPLICATE HELP REQUEST DETECTION
    # ═══════════════════════════════════════════

    async def detect_duplicate_help_requests(self) -> list[dict]:
        """Check for NPCs with multiple pending help requests of same type."""
        violations = []

        try:
            cursor = await self.db.execute(
                "SELECT requester_id, problem_type, COUNT(*) as cnt "
                "FROM agent_help_requests "
                "WHERE status IN ('pending', 'in_progress') "
                "GROUP BY requester_id, problem_type "
                "HAVING cnt > 1"
            )
            dupes = await cursor.fetchall()

            for d in dupes:
                violations.append({
                    "type": "duplicate_help",
                    "npc_id": d["requester_id"],
                    "severity": "warning",
                    "detail": (
                        f"{d['requester_id'][:8]} has {d['cnt']} pending "
                        f"'{d['problem_type']}' help requests (max 1 expected)"
                    ),
                    "problem_type": d["problem_type"],
                    "count": d["cnt"],
                })
        except Exception as e:
            print(f"[Byzantine] Duplicate help check error: {e}")

        return violations

    # ═══════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════

    async def _persist_violations(self, violations: list[dict]):
        """Store violations in DB for dashboard and historical analysis.

        Persists each (npc_id, type) at most once per `_PERSIST_EVERY_TICKS` ticks so a standing
        breach can't flood the events table (see _persist_cooldown). The in-memory log keeps every
        tick; only the durable DB write is throttled.
        """
        try:
            persisted = 0
            for v in violations:
                key = (v.get("npc_id", "unknown"), v.get("type", "?"))
                last = self._persist_cooldown.get(key)
                if last is not None and (self._tick_count - last) < self._PERSIST_EVERY_TICKS:
                    continue                       # same standing breach — already logged recently
                self._persist_cooldown[key] = self._tick_count
                persisted += 1
                await self.db.execute(
                    "INSERT INTO events (id, event_type, source_id, aggregate_type, aggregate_id, payload) "
                    "VALUES (lower(hex(randomblob(16))), 'byzantine_violation', ?, 'npc', ?, ?)",
                    (
                        v.get("npc_id", "unknown"),
                        v.get("npc_id", "unknown"),
                        json.dumps({
                            "type": v["type"],
                            "severity": v.get("severity", "warning"),
                            "detail": v["detail"],
                            "tick": self._tick_count,
                        }),
                    ),
                )
            await self.db.commit()
        except Exception as e:
            print(f"[Byzantine] Persist error: {e}")

    # ═══════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════

    def get_violations_log(self, limit: int = 50) -> list[dict]:
        """Get recent violations (from in-memory log)."""
        return self._violations_log[-limit:]

    async def get_violations_from_db(self, limit: int = 50) -> list[dict]:
        """Get recent violations from DB events."""
        try:
            cursor = await self.db.execute(
                "SELECT * FROM events WHERE event_type='byzantine_violation' "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [dict(r) for r in await cursor.fetchall()]
        except Exception:
            return []
