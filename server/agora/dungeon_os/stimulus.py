"""Stimulus Engine — bridges real-world events into Dungeon OS quests.

Transforms external stimuli (files, webhooks, Telegram, cron) into quests
assigned to the correct NPC based on subsystem mapping.

Stimulus → Orchestrator analysis → Quest creation → Agent work → Warden verify
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

# Map stimulus type → subsystem → default NPC
STIMULUS_ROUTING = {
    "file": {
        "knowledge": "scribe",
        "tooling": "forge",
        "comms": "hermes",
    },
    "alert": {
        "safety": "warden",
        "economy": "ledger",
        "comms": "hermes",
    },
    "schedule": {
        "knowledge": "scribe",
        "economy": "ledger",
        "tooling": "openclaw",
    },
    "webhook": {
        "tooling": "openclaw",
        "safety": "warden",
        "knowledge": "scribe",
    },
}


class StimulusEngine:
    """Listens for external events and converts them to Dungeon OS quests."""

    def __init__(self, quest_engine, os_state=None, db=None):
        self.qe = quest_engine
        self.os_state = os_state
        self.db = db
        self._watch_dir: Optional[Path] = None
        self._known_files: set = set()
        self._last_check: float = 0

    # ── Public API ─────────────────────────────────────

    async def inject_stimulus(
        self,
        stimulus_type: str,
        source: str,
        title: str,
        description: str,
        subsystem: str = "knowledge",
        priority: int = 5,
    ) -> dict:
        """Inject an external stimulus — creates a quest automatically.

        Args:
            stimulus_type: 'file', 'alert', 'schedule', 'webhook'
            source: Where it came from (e.g. 'telegram:user123', 'github:PR#42')
            title: Human-readable quest title
            description: What needs to be done
            subsystem: Which osState subsystem this affects
            priority: 1-10 (higher = more urgent)

        Returns:
            Created quest dict or error dict.
        """
        quest_id = f"{stimulus_type}-{source.replace(':', '-').replace('/', '-')}-{int(time.time())}"
        # Truncate ID to reasonable length and remove special URL chars
        quest_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in quest_id)[:60]

        # Determine best NPC for this stimulus
        route = STIMULUS_ROUTING.get(stimulus_type, {})
        suggested_agent = route.get(subsystem, "scribe")

        success_criteria = [
            f"Analyze and respond to: {description[:100]}",
            f"Log outcome with source: {source}",
            "Warden can verify the result is correct",
        ]

        result = await self.qe.create_quest(
            quest_id=quest_id,
            title=title[:80],
            goal=description[:200],
            subsystem=subsystem,
            success_criteria=success_criteria,
            reward=max(10, priority * 5),
        )

        if "error" not in result:
            result["suggested_agent"] = suggested_agent
            result["stimulus_source"] = source
            print(f"[Stimulus] {stimulus_type} from {source} → quest '{quest_id}'")

        return result

    async def inject_file_stimulus(self, filepath: str) -> dict:
        """React to a new file appearing in the watch directory."""
        path = Path(filepath)
        if not path.exists():
            return {"error": f"File not found: {filepath}"}

        ext = path.suffix.lower()
        name = path.stem

        # Route by file extension
        if ext in (".md", ".txt", ".csv"):
            subsystem = "knowledge"
            npc = "scribe"
        elif ext in (".py", ".js", ".ts", ".sh", ".yaml", ".json"):
            subsystem = "tooling"
            npc = "forge"
        elif ext in (".log", ".err"):
            subsystem = "safety"
            npc = "warden"
        else:
            subsystem = "knowledge"
            npc = "scribe"

        # Read first 200 chars for context
        try:
            preview = path.read_text()[:200]
        except Exception:
            preview = f"[Binary file: {ext}]"

        return await self.inject_stimulus(
            stimulus_type="file",
            source=f"fs:{name}",
            title=f"Process new file: {name}",
            description=f"New file detected: {filepath}\nPreview: {preview}",
            subsystem=subsystem,
            priority=5,
        )

    async def inject_health_stimulus(self) -> dict:
        """Scheduled health check — creates maintenance quests if needed."""
        if not self.os_state or not self.db:
            return {"status": "skipped", "reason": "os_state or db not available"}

        state = self.os_state.get_all()
        low_subsystems = [s for s, v in state.items() if v < 10]

        results = []
        if low_subsystems:
            for sub in low_subsystems:
                r = await self.inject_stimulus(
                    stimulus_type="schedule",
                    source="health-check",
                    title=f"Boost {sub} subsystem",
                    description=f"Subsystem '{sub}' is at {state[sub]}/70. "
                                f"Needs attention to reach boot threshold.",
                    subsystem=sub,
                    priority=8,
                )
                results.append(r)

        return {
            "status": "checked",
            "low_subsystems": low_subsystems,
            "quests_created": len(results),
        }

    # ── File watcher ───────────────────────────────────

    async def set_watch_dir(self, directory: str):
        """Set a directory to watch for new files."""
        self._watch_dir = Path(directory)
        self._watch_dir.mkdir(parents=True, exist_ok=True)
        # Snapshot current files
        if self._watch_dir.exists():
            self._known_files = set(
                str(p) for p in self._watch_dir.iterdir() if p.is_file()
            )
        print(f"[Stimulus] Watching: {directory} ({len(self._known_files)} existing files)")

    async def poll_watch_dir(self) -> list[dict]:
        """Check watch directory for new files. Returns created quests."""
        if not self._watch_dir:
            return []

        new_quests = []
        current_files = set(
            str(p) for p in self._watch_dir.iterdir() if p.is_file()
        )

        new_arrivals = current_files - self._known_files
        for fpath in sorted(new_arrivals):
            result = await self.inject_file_stimulus(fpath)
            if "error" not in result:
                new_quests.append(result)

        self._known_files = current_files
        return new_quests


# ── API endpoint helper ──────────────────────────

async def get_stimulus_engine(request) -> Optional[StimulusEngine]:
    """Get or create the stimulus engine from app state."""
    engine = getattr(request.app.state, "stimulus_engine", None)
    if engine is None:
        qe = getattr(request.app.state, "quest_engine", None)
        os_state = getattr(request.app.state, "os_state", None)
        db = getattr(request.app.state, "db", None)
        if qe:
            engine = StimulusEngine(qe, os_state, db)
            request.app.state.stimulus_engine = engine
    return engine
