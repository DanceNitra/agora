"""Did widening the swarm's supply actually change what it works on?

The leading indicators are measurable immediately; the OUTCOME (accept rate) is not, because
contributions arrive far slower than plans. This probe reports both and refuses to call the outcome
either way until enough contributions exist to mean anything -- a rate over n=1 is not a rate.

Baseline, measured 2026-08-08 before the fix (probes/the_swarm_recycles_because_nothing_new_can_enter.py):

    distinct intents swarm-wide        7      (5 held by all 8 agents)
    per agent                          50 entries / 5-7 distinct
    board-gate pass rate by source     findings 8/8, directions 4/10, papers 1/6, flywheel 0/3
    dedup refusals                     400 over 17.9 h, 28 distinct titles, 14.3x resubmission

Run it again after a few hours of traffic. VERDICT reports on the OUTCOME only.
"""
from __future__ import annotations

import collections
import io
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INTENTS = REPO / "agora-game-server" / ".recent_intents.json"
DUNGEON_LOG = REPO / "agora-game-server" / "_dungeon.err"
REJECTED = REPO / ".rejected_writes.json"

BASE_DISTINCT = 7
MIN_N = 30          # below this the accept rate is noise, and saying so is the point


def _last_restart() -> str:
    """Timestamp of the newest dungeon boot, found by the `+N ticks this process` counter RESETTING.

    Self-locating on purpose: hard-coding a time would silently measure the wrong window the next
    time this probe is run, which is exactly the mistake it exists to correct.
    """
    if not DUNGEON_LOG.exists():
        return ""
    boot, prev = "", None
    for line in io.open(DUNGEON_LOG, encoding="utf-8", errors="replace"):
        m = re.search(r"\+(\d+) ticks this process", line)
        if not m:
            continue
        cur = int(m.group(1))
        if prev is not None and cur < prev:
            boot = line[:19]
        prev = cur
    return boot


def main() -> int:
    if not INTENTS.exists():
        print("MEASURED: no intents file")
        print("VERDICT: NOT_COMPUTABLE")
        return 0

    d = json.loads(INTENTS.read_text(encoding="utf-8"))
    seen = collections.Counter()
    for v in d.values():
        seen.update(set(v))
    shared = sum(1 for _, n in seen.items() if n == len(d))
    sat = [k for k, v in d.items() if len(v) >= 50 and len(set(v)) < 12]
    print("MEASURED: distinct intents swarm-wide %d (baseline %d)" % (len(seen), BASE_DISTINCT))
    print("MEASURED: held by all %d agents: %d | agents still saturated: %d"
          % (len(d), shared, len(sat)))

    kinds = collections.Counter(t.split(":")[0] for t in seen)
    external = kinds.get("Ground a finding from", 0) + kinds.get("Test Agora's claim", 0)
    print("MEASURED: intent sources %s" % dict(kinds))
    print("MEASURED: EXTERNAL anchors (papers + flywheel) reaching agents: %d of %d "
          "(baseline 0 of 7 -- the swarm was reading only its own canon)"
          % (external, len(seen)))

    # OUTCOME: contributions since the fix WENT LIVE, which is the last dungeon restart -- not
    # "today". The first version of this counted all of 2026-08-08 and reported n=358 at 11.9x
    # resubmission, but the fix landed at 09:31 and almost all of those 358 predate it. Comparing
    # pre-fix and post-fix traffic in one bucket measures nothing; the window has to be time-matched
    # to the intervention. The restart locates itself: `+N ticks this process` RESETS on a fresh
    # process, so the last decrease in that counter is the boot.
    cutoff = _last_restart()
    print("MEASURED: window starts at the last dungeon restart: %s" % (cutoff or "unknown"))
    n = acc = 0
    reasons: collections.Counter = collections.Counter()
    titles: collections.Counter = collections.Counter()
    if DUNGEON_LOG.exists():
        for line in io.open(DUNGEON_LOG, encoding="utf-8", errors="replace"):
            if "[contribute]" not in line or (cutoff and line[:19] < cutoff):
                continue
            n += 1
            titles[re.sub(r".*: ", "", line).strip()[:60]] += 1
            if "REJECTED" not in line:
                acc += 1
            else:
                m = re.search(r"REJECTED by the brain \(([^)]*)", line)
                reasons[m.group(1) if m else "?"] += 1
    factor = n / max(1, len(titles))
    print("MEASURED: contributions today n=%d, accepted=%d, distinct titles=%d "
          "(resubmission %.1fx; baseline 14.3x)" % (n, acc, len(titles), factor))
    if reasons:
        print("MEASURED: refusal reasons %s" % dict(reasons.most_common(4)))

    if len(seen) <= BASE_DISTINCT or external == 0:
        print("VERDICT: FAILED -- supply did not widen, or no external anchor is reaching agents")
        return 0
    if n < MIN_N:
        print("VERDICT: NOT_COMPUTABLE -- supply widened (%d intents, %d external) but only %d "
              "contributions since the fix; an accept rate over n=%d is not a rate. Re-run later."
              % (len(seen), external, n, n))
        return 0
    if acc > 0 or factor < 3.0:
        print("VERDICT: REPRODUCED -- supply widened AND the loop opened (accepted=%d, "
              "resubmission %.1fx against a 14.3x baseline)" % (acc, factor))
    else:
        print("VERDICT: FAILED -- supply widened but nothing lands and work is still resubmitted "
              "%.1fx; the remaining block is downstream of supply" % factor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
