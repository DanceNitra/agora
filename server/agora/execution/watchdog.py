"""
The Watchdog (brain side) — the organism survives the night.

If a process dies at 3 a.m., today the system is dead until someone notices. The brain and
the dungeon now watch EACH OTHER: this side checks the dungeon every ~5 minutes; after two
consecutive misses it restarts it. A crash-loop guard (3 restarts/hour) stops the thrashing
and alerts the owner instead. The dungeon holds the mirror-image watchdog for the brain.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DUNGEON_URL = "http://localhost:5174/"
DUNGEON_DIR = Path(__file__).resolve().parents[3] / "agora-game-server"
CHECK_EVERY = int(os.environ.get("AGORA_WATCHDOG_INTERVAL", "300"))
_state = {"misses": 0, "restarts": [], "muted_until": 0.0}


def _dungeon_up(timeout: int = 10) -> bool:
    try:
        with urllib.request.urlopen(DUNGEON_URL, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def should_restart(state: dict, now: float, window: int = 3600, max_restarts: int = 3) -> bool:
    """Crash-loop guard: at most max_restarts per window, else back off (pure, testable)."""
    state["restarts"] = [t for t in state["restarts"] if now - t < window]
    return len(state["restarts"]) < max_restarts


def kill_dungeon() -> int:
    """Stop every mcp_server.py python (not us — we're uvicorn)."""
    killed = 0
    try:
        import psutil
        for p in psutil.process_iter(["cmdline", "name"]):
            try:
                cmd = " ".join(p.info.get("cmdline") or [])
                if "mcp_server.py" in cmd and "python" in (p.info.get("name") or "").lower() \
                        and " -c " not in cmd:
                    p.kill()
                    killed += 1
            except Exception:
                continue
    except Exception:
        pass
    return killed


def start_dungeon() -> bool:
    """Start one dungeon exactly the canonical way (hidden, logs appended)."""
    try:
        env = {k: v for k, v in os.environ.items() if k != "DUNGEON_AUTOPUSH"}
        env["PYTHONUNBUFFERED"] = "1"
        flags = 0x08000008          # DETACHED_PROCESS | CREATE_NO_WINDOW
        with open(DUNGEON_DIR / "_dungeon.log", "ab") as out, \
             open(DUNGEON_DIR / "_dungeon.err", "ab") as err:
            subprocess.Popen([sys.executable, "-u", "mcp_server.py"],
                             cwd=str(DUNGEON_DIR), env=env, creationflags=flags,
                             stdout=out, stderr=err)
        return True
    except Exception:
        return False


async def _alert(text: str) -> None:
    try:
        from agora.api.agent_os_api import _send_telegram
        await _send_telegram("🐶 Watchdog: " + text)
    except Exception:
        pass


async def watch_dungeon_forever() -> None:
    """The brain's vigil over the dungeon."""
    await asyncio.sleep(120)                      # grace period after our own boot
    while True:
        await asyncio.sleep(CHECK_EVERY)
        if await asyncio.to_thread(_dungeon_up):
            _state["misses"] = 0
            continue
        _state["misses"] += 1
        if _state["misses"] < 2:
            continue                              # one blip ≠ down (manual restarts happen)
        now = time.time()
        if not should_restart(_state, now):
            if now > _state["muted_until"]:
                await _alert("dungeon is DOWN and in a crash loop — backing off, needs a human.")
                _state["muted_until"] = now + 3600
            _state["misses"] = 0
            continue
        await asyncio.to_thread(kill_dungeon)
        ok = await asyncio.to_thread(start_dungeon)
        _state["restarts"].append(now)
        _state["misses"] = 0
        await _alert(f"dungeon was down — restarted it ({'ok' if ok else 'START FAILED'}).")
