"""Count every call that leaves this machine for a model, because nothing did.

WHY THIS EXISTS. On 2026-09-04 Ollama refused every tier with "you (rastislavdrahos) have reached
your weekly usage limit". Asked how many calls we had made, and by which part of the system, no
artifact we own could answer. `[LLM]` is printed only on FAILURE (llm_client.py 272-326), the
dungeon logs no conversation at all (`grep` for one returns 0), and a successful call leaves no
trace anywhere. The spend was invisible until the provider stopped us.

WHAT IT COUNTS. One line per model call, at the two places a request actually leaves:

    brain    server/agora/execution/llm_client.py   the OpenAI client and the urlopen path
    dungeon  agora-game-server/mcp_server.py        _llm_content_sync and _llm_prose_sync

Embeddings, brain HTTP and Telegram are different endpoints and are deliberately NOT counted; the
question is cloud model spend.

WHAT IT DOES NOT DO. It does not price anything. Ollama's limit is not published per call, so a
count is a count. It also cannot see a call made by a path that does not exist yet, which is why
`probes/every_model_call_goes_through_the_meter.py` asserts coverage rather than trusting this
docstring.

DESIGN NOTES, both of them lessons rather than preferences:
  * IT NEVER RAISES INTO THE CALLER. A meter that breaks a request is worse than no meter. But a
    meter that fails silently is how you get here in the first place, so its own failures are
    counted in `_meter_errors` and reported by `report()`.
  * ONE FILE PER PROCESS PER DAY, opened in append mode for a single short write. Two processes
    write concurrently and a shared file would need a lock on the hot path.
"""
from __future__ import annotations

import datetime
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIR = os.path.join(ROOT, "agora_output", "llm_meter")
_errors = os.path.join(DIR, "_meter_errors")


def _caller(skip: int = 2) -> str:
    """The function that asked for the model, found rather than passed in.

    Passing a label at every call site is a label that goes stale the first time somebody adds a
    site and forgets. The frame is always right.
    """
    try:
        f = sys._getframe(skip)
        return "%s.%s" % (os.path.basename(f.f_code.co_filename)[:-3], f.f_code.co_name)
    except Exception:
        return "?"


def record(process: str, model: str, ok: bool, prompt_chars: int = 0,
           completion_chars: int = 0, seconds: float = 0.0, caller: str | None = None,
           note: str = "") -> None:
    """Append one line for one model call. Never raises."""
    try:
        os.makedirs(DIR, exist_ok=True)
        row = {"t": time.time(), "iso": datetime.datetime.now().isoformat(timespec="seconds"),
               "process": process, "model": model, "ok": bool(ok),
               "caller": caller or _caller(3),
               "prompt_chars": int(prompt_chars), "completion_chars": int(completion_chars),
               "seconds": round(float(seconds), 3), "note": note[:120]}
        day = datetime.date.today().isoformat()
        path = os.path.join(DIR, "%s-%s.jsonl" % (process, day))
        with io.open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:                       # never break the caller
        try:
            os.makedirs(DIR, exist_ok=True)
            with io.open(_errors, "a", encoding="utf-8") as fh:
                fh.write("%s %s: %s\n" % (time.time(), type(e).__name__, str(e)[:160]))
        except Exception:
            pass


def rows(since_days: int | None = None):
    out = []
    if not os.path.isdir(DIR):
        return out
    cutoff = time.time() - since_days * 86400 if since_days else None
    for f in sorted(os.listdir(DIR)):
        if not f.endswith(".jsonl"):
            continue
        for ln in io.open(os.path.join(DIR, f), encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if cutoff and r.get("t", 0) < cutoff:
                continue
            out.append(r)
    return out


def report(since_days: int | None = None) -> str:
    import collections
    rs = rows(since_days)
    if not rs:
        return ("no calls recorded%s.\n  This is only good news if the meter is wired in: run\n"
                "  probes/every_model_call_goes_through_the_meter.py to check that it is."
                % (" in the last %d days" % since_days if since_days else ""))
    by_day = collections.Counter()
    by_proc = collections.Counter()
    by_caller = collections.Counter()
    fails = 0
    chars = 0
    for r in rs:
        by_day[r.get("iso", "?")[:10]] += 1
        by_proc[r.get("process", "?")] += 1
        by_caller["%s / %s" % (r.get("process", "?"), r.get("caller", "?"))] += 1
        fails += 0 if r.get("ok") else 1
        chars += int(r.get("prompt_chars", 0)) + int(r.get("completion_chars", 0))
    lines = ["model calls recorded: %d, of which %d failed" % (len(rs), fails),
             "characters in + out: %d" % chars, "", "by day:"]
    for d in sorted(by_day)[-14:]:
        lines.append("   %s  %6d" % (d, by_day[d]))
    lines += ["", "by process:"]
    for p, c in by_proc.most_common():
        lines.append("   %-10s %6d" % (p, c))
    lines += ["", "by caller:"]
    for c, n in by_caller.most_common(15):
        lines.append("   %-46s %6d" % (c[:46], n))
    if os.path.exists(_errors):
        n = sum(1 for _ in io.open(_errors, encoding="utf-8", errors="replace"))
        lines += ["", "METER ERRORS: %d (see %s) -- the count above is a floor" % (n, _errors)]
    return "\n".join(lines)


if __name__ == "__main__":
    days = int(sys.argv[2]) if len(sys.argv) > 2 else None
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        # The meter has to be shown able to count before anything is concluded from its silence.
        import tempfile
        original = DIR
        DIR = tempfile.mkdtemp(prefix="llm_meter_selftest_")
        _errors = os.path.join(DIR, "_meter_errors")
        for i in range(7):
            record("selftest", "model-x", ok=(i % 3 != 0), prompt_chars=10, completion_chars=5)
        got = len(rows())
        print("selftest: wrote 7, read back %d -> %s" % (got, "OK" if got == 7 else "BROKEN"))
        print("selftest: failures counted %d, expected 3"
              % sum(1 for r in rows() if not r.get("ok")))
        raise SystemExit(0 if got == 7 else 1)
    print(report(days))
