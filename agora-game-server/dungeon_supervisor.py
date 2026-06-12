"""
DUNGEON SUPERVISOR — keeps the dungeon life-loop alive.

Run THIS instead of `python mcp_server.py` directly:
    python dungeon_supervisor.py

Why it exists: the dungeon's async life-loop (agent movement, quest completion, discoveries) can
wedge — a blocked await or a half-dead process leaves the QuestBoard frozen while the process still
answers HTTP. An in-process asyncio watchdog can't catch that (a blocked event loop starves it too).
So the supervisor is a SEPARATE, loop-free process that owns the child's lifecycle:

  • launches mcp_server.py (redirecting its logs, so logs are always captured),
  • reads the heartbeat file the life-loop stamps every ~4s,
  • if the heartbeat goes STALE (loop wedged) or the child EXITS, it cleanly kills the child + any
    stray mcp_server processes, waits for the port to free, and relaunches,
  • backs off if it has to restart repeatedly (so a hard-crashing build doesn't spin).

The supervisor has no event loop and does nothing but sleep + check a file, so it cannot itself stall.
Point the Windows Startup-folder autostart at this script to make the dungeon self-healing.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEARTBEAT = HERE / ".dungeon_heartbeat"
LOG_OUT = HERE / "_dungeon.log"
LOG_ERR = HERE / "_dungeon.err"
SUP_LOG = HERE / "_supervisor.log"

PORT = 5174
STALE_SECONDS = 60          # no heartbeat advance for this long ⇒ wedged loop
STARTUP_GRACE = 150         # allow this long after a (re)launch before judging the heartbeat
CHECK_EVERY = 10            # poll cadence
RESTART_WINDOW = 600        # if > MAX_RESTARTS happen within this window, widen the backoff
MAX_RESTARTS = 4
BACKOFF_MAX = 120


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} [supervisor] {msg}"
    print(line, flush=True)
    try:
        with SUP_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def kill_stray_dungeons(except_pid: int | None = None) -> int:
    """Kill any python process running mcp_server.py (other than except_pid)."""
    killed = 0
    try:
        import psutil
    except Exception:
        return 0
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cl = p.info["cmdline"] or []
            if (any("mcp_server.py" in c for c in cl)
                    and any("python" in (c or "").lower() for c in cl)
                    and "-c" not in cl and p.info["pid"] != except_pid):
                p.kill()
                killed += 1
        except Exception:
            pass
    return killed


def wait_port_free(timeout: float = 20.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not port_in_use(PORT):
            return True
        time.sleep(0.5)
    return False


def read_heartbeat() -> tuple[int, int] | None:
    """(wall_ts, loop_n) or None if missing/unreadable."""
    try:
        ts, n = HEARTBEAT.read_text(encoding="utf-8").split()
        return int(ts), int(n)
    except Exception:
        return None


def launch() -> subprocess.Popen:
    kill_stray_dungeons()
    wait_port_free(10)
    try:
        HEARTBEAT.unlink()           # clear so a stale file can't look fresh
    except Exception:
        pass
    out = open(LOG_OUT, "w", encoding="utf-8")
    err = open(LOG_ERR, "w", encoding="utf-8")
    env = dict(os.environ)
    env.pop("DUNGEON_AUTOPUSH", None)
    creat = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    child = subprocess.Popen([sys.executable, "-u", "mcp_server.py"],
                             cwd=str(HERE), stdout=out, stderr=err, env=env, creationflags=creat)
    log(f"launched mcp_server.py pid={child.pid}")
    return child


def main() -> None:
    log(f"supervisor up (stale>{STALE_SECONDS}s, grace {STARTUP_GRACE}s)")
    restarts: list[float] = []
    child = launch()
    launched_at = time.time()

    while True:
        time.sleep(CHECK_EVERY)
        reason = ""

        if child.poll() is not None:
            reason = f"child exited (code {child.returncode})"
        elif time.time() - launched_at > STARTUP_GRACE:
            hb = read_heartbeat()
            if hb is None:
                reason = "no heartbeat file after grace period"
            elif time.time() - hb[0] > STALE_SECONDS:
                reason = f"heartbeat stale {int(time.time() - hb[0])}s (loop wedged at n={hb[1]})"

        if not reason:
            continue

        # backoff if restarting too often
        now = time.time()
        restarts = [t for t in restarts if now - t < RESTART_WINDOW]
        restarts.append(now)
        backoff = 0
        if len(restarts) > MAX_RESTARTS:
            backoff = min(BACKOFF_MAX, 15 * (len(restarts) - MAX_RESTARTS))
            log(f"RESTART ({reason}) — {len(restarts)} restarts/{RESTART_WINDOW}s, backing off {backoff}s")
        else:
            log(f"RESTART ({reason})")

        try:
            child.terminate()
            try:
                child.wait(timeout=8)
            except Exception:
                child.kill()
        except Exception:
            pass
        kill_stray_dungeons()
        if backoff:
            time.sleep(backoff)
        child = launch()
        launched_at = time.time()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("supervisor stopped (KeyboardInterrupt)")
