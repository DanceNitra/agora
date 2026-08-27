"""Does a model actually ANSWER? A healthy :8000 does not say so, and today it did not.

MEASURED 2026-08-01. The brain returned `{"status":"ok","agents":8}`, the dungeon returned 200, and
every process-hygiene check passed -- while EVERY LLM call in the deployment failed with

    503 server busy, please try again.  maximum pending requests exceeded

Ollama had been up 7.9 days and its internal pending-request queue had wedged. Killing every client
did not clear it (zero established connections, still 503); only restarting the server process did.
So the entire swarm had no LLM, for an unknown length of time, behind two green health checks.

CLAUDE.md already says this in words -- "a healthy :8000 says nothing about whether a model answers"
-- and nothing enforced it. This is the enforcement.

TWO THINGS THIS DELIBERATELY DOES.

  * A UNIQUE PROMPT PER TIER, PER RUN. A repeated prompt can be served from cache, and a 0.0-second
    "the tier is alive" is a cache hit, not a call. The arithmetic differs every run and the ANSWER
    is checked, not merely the presence of a string.
  * IT REPORTS LATENCY. A tier that answers in 40 s is alive and starving the swarm just the same;
    the number is the difference between "working" and "working well enough to run on".

Exit code 1 if any tier fails to answer correctly, so it can be wired into a watchdog. It writes
nothing and changes nothing.
"""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "server"))

# LOAD THE BRAIN'S ENVIRONMENT, EXPLICITLY. Without it `call_llm` falls back to the code's built-in
# default model and reports "Missing credentials" -- and this probe then declares every tier dead
# while the tiers are fine. Measured on its own first run: it printed "3 of 3 tiers did not answer"
# against a local Ollama that had just answered three unique arithmetic prompts correctly.
# A liveness check that tests its own launch directory rather than the system is worse than none.
_ENV = REPO / "server" / ".env"
if _ENV.exists():
    import os as _os
    for _line in _ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        _os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
else:                                    # refuse rather than measure the defaults
    print("REFUSED: %s not found -- without it this probe measures the code defaults, not the "
          "deployment, and would report healthy tiers as dead" % _ENV)
    raise SystemExit(2)

TIERS = ("cheap", "main", "reasoning")
#: The reasoning tier is FLOORED, never capped: qwen3:30b-a3b burns its budget on thinking and emits
#: EMPTY content under a small cap. See CLAUDE.md -- a tight cap is the recurring "0 notes" bug.
MAX_TOKENS = 16000
SLOW_S = 25.0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        from agora.execution.llm_client import call_llm
    except Exception as e:
        print("cannot import the llm client (%s: %s)" % (type(e).__name__, e))
        return 1

    # A different sum every run. A tier that answers instantly with the previous run's number is a
    # cache, and a cache cannot tell you the model is reachable.
    a, b = random.randint(11, 89), random.randint(11, 89)
    want = str(a + b)
    print("LLM TIER LIVENESS -- %s   (unique prompt: %d + %d)" % (time.strftime("%H:%M:%S"), a, b))
    print("a green /health says nothing about this; on 2026-08-01 both were green and every tier was 503\n")

    bad = 0
    print("  %-11s %9s  %s" % ("tier", "seconds", "answer"))
    for tier in TIERS:
        t0 = time.time()
        try:
            out = (call_llm("Reply with only the digits, nothing else.",
                            "What is %d + %d?" % (a, b), tier, 0.0, MAX_TOKENS) or "").strip()
        except Exception as e:
            out, dt = "EXC %s: %s" % (type(e).__name__, str(e)[:60]), time.time() - t0
            print("  %-11s %9.1f  %s" % (tier, dt, out))
            bad += 1
            continue
        dt = time.time() - t0
        ok = want in out
        note = "" if ok else "   <-- WRONG or EMPTY (expected %s)" % want
        if ok and dt > SLOW_S:
            note = "   <-- alive but slow enough to starve the swarm"
        print("  %-11s %9.1f  %r%s" % (tier, dt, out[:40], note))
        if not ok:
            bad += 1

    print()
    if bad:
        print("RESULT: %d of %d tiers did not answer. The swarm cannot do research without them, and"
              % (bad, len(TIERS)))
        print("        no other health check in this repo will tell you. If the error mentions")
        print("        'maximum pending requests', the Ollama server has wedged: killing clients does")
        print("        NOT clear it (measured -- zero connections, still 503); restart the server.")
        return 1
    print("RESULT: all %d tiers answered correctly." % len(TIERS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
