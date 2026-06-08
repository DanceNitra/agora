"""State Store — transactional persistence layer pre Agent OS a dungeon NPCs (S v ETCSLV).

Design:
  - begin_tick(): otvorí transakčný buffer
  - get_*(): číta z DB (direct reads) alebo z bufferu ak existuje pending write
  - update_*(): zapíše do bufferu, nie priamo do DB
  - commit_tick(): atomický flush bufferu do DB + snapshot checkpoint
  - rollback_tick(): zahodí buffer (pri chybe)

SNAPSHOT systém:
  - Auto-snapshot každých SNAPSHOT_INTERVAL tickov
  - Umožňuje rollback pri crashi
  - Store v samostatnej tabuľke ako JSON blob
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

SNAPSHOT_INTERVAL = 60  # every 60 ticks (~1 epoch)


class StateStore:
    """Transactional state layer — binding constraint (S) v ETCSLV harnesse."""

    def __init__(self, db):
        self.db = db
        self._buffer: dict[str, dict[str, Any]] = {}  # {"table:pk": {column: value, ...}}
        self._tick_count = 0
        self._in_transaction = False

    # ═══════════════════════════════════════════
    # TRANSACTION CONTROL
    # ═══════════════════════════════════════════

    async def begin_tick(self, tick_count: int):
        """Start a new transaction buffer for this tick."""
        if self._in_transaction:
            await self.rollback_tick()
        self._tick_count = tick_count
        self._buffer = {}
        self._in_transaction = True

    async def commit_tick(self):
        """Flush all buffered writes to DB atomically."""
        if not self._in_transaction or not self._buffer:
            self._in_transaction = False
            return

        try:
            for key, changes in self._buffer.items():
                table, pk = key.split(":", 1)
                if not changes:
                    continue
                set_clause = ", ".join(f"{col}=?" for col in changes)
                values = list(changes.values())

                # Determine primary key column
                if table == "dungeon_npcs":
                    pk_col = "npc_id"
                elif table == "agent_identities":
                    pk_col = "agent_id"
                elif table == "agent_body":
                    pk_col = "npc_id"
                elif table == "agent_brain":
                    pk_col = "npc_id"
                elif table == "agent_soul":
                    pk_col = "npc_id"
                elif table in ("agent_skills", "agent_abilities", "agent_help_requests"):
                    pk_col = "id"
                else:
                    # Try to find primary key
                    cursor = await self.db.execute(
                        f"SELECT name FROM pragma_table_info('{table}') WHERE pk=1"
                    )
                    row = await cursor.fetchone()
                    pk_col = row[0] if row else "id"

                sql = f"UPDATE {table} SET {set_clause} WHERE {pk_col}=?"
                values.append(pk)
                await self.db.execute(sql, values)

            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e
        finally:
            self._buffer = {}
            self._in_transaction = False

        # Auto-snapshot
        if self._tick_count > 0 and self._tick_count % SNAPSHOT_INTERVAL == 0:
            await self._snapshot()

    async def rollback_tick(self):
        """Discard the transaction buffer (no changes written)."""
        self._buffer = {}
        self._in_transaction = False

    # ═══════════════════════════════════════════
    # INTERNAL: buffer helpers
    # ═══════════════════════════════════════════

    def _key(self, table: str, pk: str) -> str:
        return f"{table}:{pk}"

    def _buffer_write(self, table: str, pk: str, changes: dict):
        """Add changes to the transaction buffer."""
        key = self._key(table, pk)
        if key not in self._buffer:
            self._buffer[key] = {}
        self._buffer[key].update(changes)

    def _validate_float(self, value: Any, min_v: float, max_v: float, name: str) -> float:
        """Validate and clamp a float value."""
        try:
            v = float(value)
            if v < min_v or v > max_v:
                print(f"[StateStore] ⚠ Clamping {name}: {v} to [{min_v}, {max_v}]")
                return max(min_v, min(v, max_v))
            return v
        except (TypeError, ValueError):
            print(f"[StateStore] ⚠ Invalid {name}: {value}, using default {min_v}")
            return min_v

    # ═══════════════════════════════════════════
    # ENTITY: DUNGEON NPC
    # ═══════════════════════════════════════════

    async def get_npc(self, npc_id: str) -> Optional[dict]:
        """Get full NPC state from DB (reads bypass buffer)."""
        cursor = await self.db.execute(
            "SELECT * FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

    async def get_npc_by_name(self, name: str) -> Optional[dict]:
        """Lookup NPC by name."""
        cursor = await self.db.execute(
            "SELECT * FROM dungeon_npcs WHERE npc_name=?", (name,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

    async def get_all_active_npcs(self) -> list[dict]:
        """Get all active NPCs."""
        cursor = await self.db.execute(
            "SELECT * FROM dungeon_npcs WHERE status='active'"
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def update_npc(self, npc_id: str, changes: dict):
        """Buffer position/health/status update for NPC."""
        validated = {}
        if "pos_x" in changes:
            validated["pos_x"] = self._validate_float(changes["pos_x"], 0, 1280, f"{npc_id}.pos_x")
        if "pos_y" in changes:
            validated["pos_y"] = self._validate_float(changes["pos_y"], 0, 608, f"{npc_id}.pos_y")
        if "health" in changes:
            validated["health"] = self._validate_float(changes["health"], 0, 100, f"{npc_id}.health")
        if "status" in changes:
            validated["status"] = str(changes["status"])
        if "inventory" in changes:
            validated["inventory"] = json.dumps(changes["inventory"])
        if "objective" in changes:
            validated["objective"] = str(changes["objective"])
        validated["updated_at"] = datetime.utcnow().isoformat()
        self._buffer_write("dungeon_npcs", npc_id, validated)

    # ═══════════════════════════════════════════
    # ENTITY: AGENT BODY
    # ═══════════════════════════════════════════

    async def get_body(self, npc_id: str) -> Optional[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM agent_body WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def update_body(self, npc_id: str, changes: dict):
        """Buffer stamina/hunger/fatigue/awareness update."""
        validated = {}
        for field in ("stamina", "hunger", "fatigue", "awareness"):
            if field in changes:
                validated[field] = self._validate_float(changes[field], 0, 100, f"body.{npc_id}.{field}")
        if "status_effects" in changes:
            validated["status_effects"] = json.dumps(changes["status_effects"])
        if validated:
            self._buffer_write("agent_body", npc_id, validated)

    # ═══════════════════════════════════════════
    # ENTITY: AGENT BRAIN
    # ═══════════════════════════════════════════

    async def get_brain(self, npc_id: str) -> Optional[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM agent_brain WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def update_brain(self, npc_id: str, changes: dict):
        """Buffer state_of_mind/goal/plan_stack update."""
        validated = {}
        valid_states = {"focused", "confused", "panicked", "resting", "planning", "blocked"}
        if "state_of_mind" in changes:
            new_state = str(changes["state_of_mind"])
            if new_state not in valid_states:
                print(f"[StateStore] ⚠ Invalid state_of_mind: {new_state}, defaulting to 'confused'")
                new_state = "confused"
            validated["state_of_mind"] = new_state
        if "current_goal" in changes:
            validated["current_goal"] = str(changes["current_goal"])
        if "plan_stack" in changes:
            validated["plan_stack"] = json.dumps(changes["plan_stack"])
        if "memory" in changes:
            validated["memory"] = json.dumps(changes["memory"])
        if "last_decision" in changes:
            validated["last_decision"] = str(changes["last_decision"])
        validated["updated_at"] = datetime.utcnow().isoformat()
        if validated:
            self._buffer_write("agent_brain", npc_id, validated)

    # ═══════════════════════════════════════════
    # ENTITY: AGENT SOUL
    # ═══════════════════════════════════════════

    async def get_soul(self, npc_id: str) -> Optional[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM agent_soul WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def update_soul(self, npc_id: str, changes: dict):
        validated = {}
        if "emotional_state" in changes:
            validated["emotional_state"] = str(changes["emotional_state"])
        if "moral_alignment" in changes:
            validated["moral_alignment"] = str(changes["moral_alignment"])
        validated["updated_at"] = datetime.utcnow().isoformat()
        if validated:
            self._buffer_write("agent_soul", npc_id, validated)

    # ═══════════════════════════════════════════
    # ENTITY: SKILLS
    # ═══════════════════════════════════════════

    async def get_skill(self, npc_id: str, skill_name: str) -> Optional[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM agent_skills WHERE npc_id=? AND skill_name=?",
            (npc_id, skill_name),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_all_skills(self, npc_id: str) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM agent_skills WHERE npc_id=? ORDER BY level DESC",
            (npc_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def update_skill(self, skill_id: int, changes: dict):
        """Buffer skill XP/level update."""
        validated = {}
        if "level" in changes:
            validated["level"] = int(self._validate_float(changes["level"], 0, 100, f"skill.{skill_id}.level"))
        if "xp" in changes:
            validated["xp"] = self._validate_float(changes["xp"], 0, 9999, f"skill.{skill_id}.xp")
        if "xp_to_next" in changes:
            validated["xp_to_next"] = self._validate_float(changes["xp_to_next"], 1, 9999, f"skill.{skill_id}.xp_to_next")
        validated["last_used_at"] = datetime.utcnow().isoformat()
        if validated:
            self._buffer_write("agent_skills", str(skill_id), validated)

    # ═══════════════════════════════════════════
    # ENTITY: HELP REQUESTS
    # ═══════════════════════════════════════════

    async def create_help_request(self, requester_id: str, helper_id: str,
                                   problem_type: str, description: str,
                                   requester_task: str = "") -> int:
        """Insert a new help request directly (must be in buffer? Or direct since it's INSERT)."""
        cursor = await self.db.execute(
            "INSERT INTO agent_help_requests (requester_id, helper_id, problem_type, description, status, requester_task) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (requester_id, helper_id, problem_type, description, requester_task),
        )
        await self.db.commit()
        return cursor.lastrowid

    async def get_pending_help_requests(self) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT hr.*, r.npc_name as requester_name, h.npc_name as helper_name "
            "FROM agent_help_requests hr "
            "JOIN dungeon_npcs r ON r.npc_id = hr.requester_id "
            "JOIN dungeon_npcs h ON h.npc_id = hr.helper_id "
            "WHERE hr.status IN ('pending', 'in_progress')"
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def update_help_request(self, req_id: int, changes: dict):
        """Buffer help request status update."""
        validated = {}
        valid_statuses = {"pending", "in_progress", "completed", "rejected", "resolved"}
        if "status" in changes:
            s = str(changes["status"])
            if s not in valid_statuses:
                print(f"[StateStore] ⚠ Invalid help status: {s}, defaulting to 'pending'")
                s = "pending"
            validated["status"] = s
        if "accepted_at" in changes:
            validated["accepted_at"] = str(changes["accepted_at"])
        if "resolved_at" in changes:
            validated["resolved_at"] = str(changes["resolved_at"])
        if "helper_reply" in changes:
            validated["helper_reply"] = str(changes["helper_reply"])
        if validated:
            self._buffer_write("agent_help_requests", str(req_id), validated)

    async def get_pending_request_for_npc(self, npc_id: str) -> Optional[dict]:
        """Check if NPC already has a pending/in_progress help request."""
        cursor = await self.db.execute(
            "SELECT * FROM agent_help_requests "
            "WHERE requester_id=? AND status IN ('pending', 'in_progress') "
            "LIMIT 1",
            (npc_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    # ═══════════════════════════════════════════
    # ENTITY: AGENT IDENTITIES (thinking agents)
    # ═══════════════════════════════════════════

    async def get_agent(self, agent_id: str) -> Optional[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM agent_identities WHERE agent_id=?", (agent_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_all_active_agents(self) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM agent_identities WHERE status='active'"
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def update_agent(self, agent_id: str, changes: dict):
        """Buffer trust/energy/status update for agent_identities."""
        validated = {}
        if "trust_score" in changes:
            validated["trust_score"] = self._validate_float(changes["trust_score"], 0, 1, f"agent.{agent_id}.trust")
        if "energy_balance" in changes:
            validated["energy_balance"] = self._validate_float(changes["energy_balance"], 0, 100, f"agent.{agent_id}.energy")
        if "status" in changes:
            validated["status"] = str(changes["status"])
        validated["updated_at"] = datetime.utcnow().isoformat()
        if validated:
            self._buffer_write("agent_identities", agent_id, validated)

    # ═══════════════════════════════════════════
    # SNAPSHOT / RESTORE
    # ═══════════════════════════════════════════

    async def _snapshot(self):
        """Save full state snapshot for crash recovery."""
        try:
            snapshot_data = {
                "tick": self._tick_count,
                "npc_ids": [],
                "agent_ids": [],
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Collect NPC data
            for npc in await self.get_all_active_npcs():
                npc_id = npc["npc_id"]
                snapshot_data["npc_ids"].append(npc_id)
                snapshot_data[f"npc:{npc_id}"] = {
                    "pos": (npc["pos_x"], npc["pos_y"]),
                    "health": npc["health"],
                    "status": npc["status"],
                }
                # OS data
                brain = await self.get_brain(npc_id)
                if brain:
                    snapshot_data[f"brain:{npc_id}"] = {
                        "state": brain["state_of_mind"],
                        "goal": brain["current_goal"],
                    }
                body = await self.get_body(npc_id)
                if body:
                    snapshot_data[f"body:{npc_id}"] = {
                        "stamina": body["stamina"],
                        "fatigue": body["fatigue"],
                        "hunger": body["hunger"],
                    }

            # Store as JSON in a dedicated table
            await self.db.execute(
                "CREATE TABLE IF NOT EXISTS state_snapshots ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "tick INTEGER NOT NULL, "
                "snapshot TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT (datetime('now')))"
            )
            await self.db.execute(
                "INSERT INTO state_snapshots (tick, snapshot) VALUES (?, ?)",
                (self._tick_count, json.dumps(snapshot_data)),
            )
            await self.db.commit()
            print(f"[StateStore] 📸 Snapshot saved at tick {self._tick_count} ({len(snapshot_data['npc_ids'])} NPCs)")
        except Exception as e:
            print(f"[StateStore] ⚠ Snapshot error: {e}")

    async def get_latest_snapshot(self) -> Optional[dict]:
        """Get the most recent snapshot."""
        try:
            cursor = await self.db.execute(
                "SELECT * FROM state_snapshots ORDER BY tick DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                result["snapshot"] = json.loads(result["snapshot"])
                return result
        except Exception:
            pass
        return None

    async def restore_latest_snapshot(self) -> bool:
        """Restore state from latest snapshot (for crash recovery)."""
        snap = await self.get_latest_snapshot()
        if not snap:
            print("[StateStore] No snapshot to restore")
            return False

        data = snap["snapshot"]
        print(f"[StateStore] 🔄 Restoring from snapshot tick {data['tick']}...")
        # Restoration is per-tick — for now, just log what would be restored
        print(f"[StateStore]   NPCs: {len(data.get('npc_ids', []))}")
        for npc_id in data.get("npc_ids", []):
            npc = data.get(f"npc:{npc_id}", {})
            brain = data.get(f"brain:{npc_id}", {})
            body = data.get(f"body:{npc_id}", {})
            print(f"[StateStore]   {npc_id[:8]}.. pos={npc.get('pos')} state={brain.get('state')} stamina={body.get('stamina')}")
        return True
