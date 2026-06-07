"""Dungeon OS — osState engine.

The dungeon has a global osState with 5 subsystems. Completing quests raises
subsystem levels. When all pass a threshold, the dungeon "boots" into the
Agentic Operating System.

Subsystems:
  - comms:     communication infrastructure (Hermes)
  - knowledge: knowledge base & records (Scribe)
  - tooling:   workstations & capabilities (Forge + OpenClaw)
  - economy:   resource & value tracking (Ledger)
  - safety:    verification & guardrails (Warden)
"""

import json
import time
from typing import Optional

OS_BOOT_THRESHOLD = 70  # each subsystem must reach 70+ to boot


class OsState:
    """Global OS state with 5 subsystems.

    Persisted to DB and kept in-memory for fast access.
    """

    def __init__(self, db=None):
        self.db = db
        self._state = {
            "comms": 0,
            "knowledge": 0,
            "tooling": 0,
            "economy": 0,
            "safety": 0,
        }
        self._changed_at = time.time()
        self._boot_triggered = False

    async def load(self):
        """Load osState from DB, or initialize if not present."""
        if not self.db:
            return

        try:
            cursor = await self.db.execute(
                "SELECT subsystem, value FROM os_state"
            )
            rows = await cursor.fetchall()
            for row in rows:
                subsystem = row["subsystem"]
                if subsystem in self._state:
                    self._state[subsystem] = row["value"]

            # Check if boot was previously triggered
            cursor_boot = await self.db.execute(
                "SELECT value FROM os_meta WHERE key='boot_triggered'"
            )
            row_boot = await cursor_boot.fetchone()
            if row_boot:
                self._boot_triggered = bool(int(row_boot["value"]))

            print(f"[OsState] Loaded: {self._state}")
        except Exception:
            print("[OsState] Table not found, will initialize on first save")

    async def save(self):
        """Persist current osState to DB."""
        if not self.db:
            return

        try:
            for subsystem, value in self._state.items():
                await self.db.execute(
                    "INSERT OR REPLACE INTO os_state (subsystem, value, updated_at) "
                    "VALUES (?, ?, datetime('now'))",
                    (subsystem, value),
                )

            # Track boot trigger
            await self.db.execute(
                "INSERT OR REPLACE INTO os_meta (key, value, updated_at) "
                "VALUES ('boot_triggered', ?, datetime('now'))",
                (str(int(self._boot_triggered)),),
            )

            await self.db.commit()
        except Exception as e:
            print(f"[OsState] Save error: {e}")

    def get(self, subsystem: str) -> int:
        """Get current value for a subsystem."""
        return self._state.get(subsystem, 0)

    def get_all(self) -> dict:
        """Get full osState dict."""
        return dict(self._state)

    def get_boot_progress(self) -> dict:
        """Get boot progress: each subsystem as fraction of threshold."""
        progress = {}
        for subsystem, value in self._state.items():
            progress[subsystem] = min(100, int(value / OS_BOOT_THRESHOLD * 100))
        return progress

    def is_boot_ready(self) -> bool:
        """Check if all subsystems meet the boot threshold."""
        return all(v >= OS_BOOT_THRESHOLD for v in self._state.values())

    async def raise_subsystem(self, subsystem: str, amount: int = 5) -> int:
        """Raise a subsystem level. Returns new value.

        Args:
            subsystem: One of comms, knowledge, tooling, economy, safety.
            amount: Points to add (typically 5-40 per quest completion).

        Returns:
            New subsystem value (capped at 100).
        """
        if subsystem not in self._state:
            return 0

        old = self._state[subsystem]
        new = min(100, old + amount)
        self._state[subsystem] = new
        self._changed_at = time.time()

        if old == new and new == 100:
            return new  # already maxed

        print(f"[OsState] {subsystem}: {old} → {new} (+{amount})")
        await self.save()

        # Check boot condition
        if self.is_boot_ready() and not self._boot_triggered:
            self._boot_triggered = True
            print(f"[OsState] ⚡ ALL SUBSYSTEMS ONLINE — BOOT TRIGGERED!")
            await self.save()

        return new

    async def set_subsystem(self, subsystem: str, value: int):
        """Explicitly set a subsystem value (for admin/seed)."""
        self._state[subsystem] = max(0, min(100, value))
        self._changed_at = time.time()
        await self.save()

    def is_booted(self) -> bool:
        return self._boot_triggered

    def get_stats(self) -> dict:
        """Get full osState statistics."""
        return {
            "state": dict(self._state),
            "boot_progress": self.get_boot_progress(),
            "threshold": OS_BOOT_THRESHOLD,
            "boot_ready": self.is_boot_ready(),
            "boot_triggered": self._boot_triggered,
            "last_changed": self._changed_at,
        }


async def ensure_os_state_tables(db):
    """Create os_state and os_meta tables if they don't exist."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS os_state (
            subsystem   TEXT PRIMARY KEY,
            value       INTEGER NOT NULL DEFAULT 0,
            updated_at  TEXT
        )
    """)
    await db.execute("""
        INSERT OR IGNORE INTO os_state (subsystem, value) VALUES
            ('comms', 0),
            ('knowledge', 0),
            ('tooling', 0),
            ('economy', 0),
            ('safety', 0)
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS os_meta (
            key     TEXT PRIMARY KEY,
            value   TEXT NOT NULL DEFAULT '',
            updated_at TEXT
        )
    """)
    await db.commit()
