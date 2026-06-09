"""
The Night Shift — sleep that consolidates memory.

A silent defect motivated this organ: the semantic index only ever rebuilt by hand, so every
note written since the last build was INVISIBLE to search, the Desk, gaps, bridges and the
contradiction sweep — eyes wide open, memory not recording. Nightly, while nothing else needs
the GPU, the Night Shift re-embeds the vault (fresh memory by morning), trims the retrieval
log, and applies a couple of waiting bridge links. The owner's own insight — consolidation as
critical-window load balancing — running on the system itself.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

_LOG = Path(__file__).resolve().parents[2] / ".night_shift.json"


def _record(entry: dict) -> None:
    try:
        log = json.loads(_LOG.read_text(encoding="utf-8"))
    except Exception:
        log = []
    log.append(entry)
    try:
        _LOG.write_text(json.dumps(log[-60:], ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def last_run_date() -> str:
    try:
        log = json.loads(_LOG.read_text(encoding="utf-8"))
        return log[-1].get("date", "") if log else ""
    except Exception:
        return ""


def _trim_retrieval_log(days: int = 90) -> int:
    from agora.execution.semantic_index import RETRIEVAL_LOG
    try:
        log = json.loads(RETRIEVAL_LOG.read_text(encoding="utf-8"))
    except Exception:
        return 0
    cutoff = time.time() - days * 86400
    kept = {p: e for p, e in log.items() if e.get("last", 0) >= cutoff}
    dropped = len(log) - len(kept)
    if dropped:
        RETRIEVAL_LOG.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")
    return dropped


async def run_night_shift(vault_path: str, apply_bridges: int = 2) -> dict:
    """The full consolidation pass. Heavy (GPU re-embed) — run while the owner sleeps."""
    t0 = time.time()
    from agora.execution.semantic_index import build_index, SemanticIndex

    stats = await asyncio.to_thread(build_index, vault_path)
    trimmed = await asyncio.to_thread(_trim_retrieval_log)

    bridges_applied = 0
    if apply_bridges:
        try:
            from agora.api.agent_os_api import _add_link
            si = SemanticIndex()
            pairs = await asyncio.to_thread(si.find_bridges, vault_path, apply_bridges + 2)
            for b in (pairs or [])[:apply_bridges]:
                bridges_applied += await asyncio.to_thread(
                    _add_link, vault_path, b.get("a_path", ""), b.get("b", ""), b.get("why", ""))
                bridges_applied += await asyncio.to_thread(
                    _add_link, vault_path, b.get("b_path", ""), b.get("a", ""), b.get("why", ""))
        except Exception:
            pass

    entry = {"date": time.strftime("%Y-%m-%d"), "ts": time.time(),
             "indexed": stats.get("notes", 0) if isinstance(stats, dict) else 0,
             "log_trimmed": trimmed, "bridges_applied": bridges_applied,
             "minutes": round((time.time() - t0) / 60, 1)}
    _record(entry)
    return entry
