"""Roll a log when it is genuinely large — the one implementation, used by both launchers.

WHY IT IS SHARED. `server/start_brain.py` has had this since 2026-08-06, and its comment states the
balance exactly: "Append forever is a disk leak; rotating on every start is the truncation bug
wearing a hat. Roll only when a file is genuinely large, so an ordinary restart NEVER loses
history."

The dungeon's launcher (`watchdog.start_dungeon`) opened its streams with "ab" and never rolled. The
result, measured 2026-08-14: `_brain.log` sat at 25 MB while `_dungeon.err` had reached **1,021 MB**
— and `_dungeon.err` is the dungeon's real log, since its INFO lines go to stderr (`_dungeon.log`
held 4.7 kB). One process had the fix; the identical need in the other did not.

TIMING IS THE WHOLE CONSTRAINT. Rolling means renaming, and on Windows a rename fails while a
process holds the file open — and worse, truncating in place is unsafe here because the writers hold
POSITIONAL handles (start_brain.py's own docstring records this: the old process "keeps writing from
its own offset and overwrites whatever you appended past it"). So a log is only ever rolled by the
LAUNCHER, before the new process opens it and while the old one is gone. Never roll a live log.
"""
from __future__ import annotations

from pathlib import Path

DEFAULT_MAX_BYTES = 25 * 1024 * 1024


def roll_if_big(p: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> bool:
    """Rename `p` to `p.1` when it exceeds max_bytes. True if it rolled.

    Any failure is swallowed: a rotation problem must never block a service from starting. The
    previous `.1` is replaced, so at most one generation is kept here — `tools/log_archive.py` is
    what preserves older ones by compressing them out of the way.
    """
    try:
        p = Path(p)
        if p.exists() and p.stat().st_size > max_bytes:
            prev = p.with_suffix(p.suffix + ".1")
            prev.unlink(missing_ok=True)
            p.rename(prev)
            return True
    except Exception:
        pass
    return False
