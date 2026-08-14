"""Start the brain the canonical way: detached, and APPENDING to its logs.

WHY THIS FILE EXISTS. The dungeon has had a proper launcher for weeks --
`agora/execution/watchdog.py:start_dungeon()` opens `_dungeon.log`/`_dungeon.err` in `"ab"` and
hands the handles to Popen. The brain had none, so every restart went through an ad-hoc
`Start-Process -RedirectStandardOutput`, and PowerShell's redirection **truncates**. Measured
2026-08-06: the analogy forge produced its first forging in 5.7 days at 20:24, and by the time it
was looked for at 20:40 the access-log evidence was gone -- three restarts had each opened
`_brain.log` with the equivalent of `"wb"`. The ledger survived, so the event was still provable,
but the log that would have shown the request never had a chance.

A log you truncate on every restart is a log that is empty exactly when you need it: after a
restart, which is when you are debugging.

Usage (from the repo root or anywhere):
    python server/start_brain.py
Then verify, as always: one LISTEN on :8000, one mcp_server.py, zero supervisors.

TESTING THIS, and the two ways the obvious test lies. Both cost a run before the third worked:

  1. Do NOT append a sentinel while the OLD process still holds the log. Its handle is positional,
     so it keeps writing from its own offset and overwrites whatever you appended past it -- the
     sentinel vanishes and you conclude the launcher truncates, which it does not.
  2. Do NOT append a sentinel while the NEW process is running either, for the same reason.

  Stop the brain, THEN write the sentinel, THEN start it. That isolates "does open() truncate" from
  "does a concurrent writer overwrite", which are different questions with the same symptom.
  Measured this way: 197662 -> 202719 bytes with the sentinel still present. A test whose failure
  mode is indistinguishable from success is not a test.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG, ERR = HERE / "_brain.log", HERE / "_brain.err"

#: Append forever is a disk leak; rotating on every start is the truncation bug wearing a hat. Roll
#: only when a file is genuinely large, so an ordinary restart NEVER loses history.
_MAX_BYTES = 25 * 1024 * 1024


def _roll(p: Path) -> None:
    """Delegates to tools/logroll.py — the same implementation the dungeon's launcher now uses.

    It lived only here, so `_dungeon.err` grew to 1,021 MB while `_brain.log` stayed at 25. A
    rotation policy that exists in one of two launchers is a rotation policy for one of two logs.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
        from logroll import roll_if_big
        roll_if_big(p, _MAX_BYTES)
    except Exception:
        pass                                   # a rotation failure must never block the start


def start_brain() -> bool:
    """Launch one detached uvicorn with both streams APPENDED. True if the spawn succeeded."""
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = "."
        env["PYTHONUNBUFFERED"] = "1"
        flags = 0x08000008 if os.name == "nt" else 0   # DETACHED_PROCESS | CREATE_NO_WINDOW
        for p in (LOG, ERR):
            _roll(p)
        with open(LOG, "ab") as out, open(ERR, "ab") as err:
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "agora.main:app",
                 "--host", "127.0.0.1", "--port", "8000"],
                cwd=str(HERE), env=env, creationflags=flags, stdout=out, stderr=err)
        return True
    except Exception as exc:                   # noqa: BLE001 - the caller wants a bool, not a trace
        print(f"start_brain failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    raise SystemExit(0 if start_brain() else 1)
