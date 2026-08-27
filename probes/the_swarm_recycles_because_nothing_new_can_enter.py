"""Why 96% of the swarm's contributions are refused as duplicates -- and it is NOT the gate.

Measured 2026-08-08. Replaces `stream_dedup_rejects_the_work_it_already_accepted.py`, whose verdict
was WRONG and is retracted below.

THE RETRACTED ATTEMPT. That probe replayed the live dedup gate against discoveries the system had
already accepted and found it would now refuse 80.7% of them -- read as "the gate over-fires". The
control was contaminated: the accepted corpus is dominated by 2026-06-19..27 rows written BEFORE the
gate existed, where single titles repeat 70x and 69x. Refusing 80% of a corpus that is itself ~20x
duplicated is the gate being RIGHT. A control drawn from the era the fix was built to end cannot
test the fix.

WHAT IS ACTUALLY HAPPENING, from the producer side instead of the gate side:

  1. the eight agents share ~7 distinct intents, five of them held by ALL EIGHT
  2. `_recent_intents` (cap 50/agent) is supposed to stop self-repetition, but `_seen.append()`
     never dedups -- so 50 slots hold 5-7 distinct values, ~8 copies each. THE ANTI-REPETITION
     MEMORY IS CONSUMED BY THE REPETITION IT EXISTS TO PREVENT.
  3. saturated, `fresh` is empty, and `chosen = (fresh or interleaved)` re-serves the same picks
  4. the brain correctly refuses them as near-duplicates
  5. nothing new enters `collective_knowledge`, so the `findings` bucket keeps re-seeding from the
     same top-8 -- and the pool cannot change

That is a closed loop, and the dedup gate is what seals it, not what causes it. The 2026-07-20 note
in `mcp_server.py` already named this echo loop; routing the pool through the board gate filtered
OFF-MISSION items but never made the on-mission pool refresh.

Read-only. Prints MEASURED:/VERDICT:.
"""
from __future__ import annotations

import collections
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REJECTED = REPO / ".rejected_writes.json"
INTENTS = REPO / "agora-game-server" / ".recent_intents.json"
DB = REPO / "server" / "agora.db"


def main() -> int:
    if not REJECTED.exists() or not INTENTS.exists():
        print("MEASURED: ledger or intents file absent")
        print("VERDICT: NOT_COMPUTABLE")
        return 0

    rej = json.loads(REJECTED.read_text(encoding="utf-8"))
    dedup = [r for r in rej if "dedup" in (r.get("reason") or "")]
    titles = collections.Counter((r.get("title") or "")[:70] for r in dedup)
    factor = len(dedup) / max(1, len(titles))
    ts = sorted(r.get("ts", 0) for r in dedup)
    hours = max(0.1, (ts[-1] - ts[0]) / 3600.0)
    print("MEASURED: %d dedup refusals over %.1f h = %.1f/h, but only %d DISTINCT titles "
          "(resubmission factor %.1fx)" % (len(dedup), hours, len(dedup) / hours,
                                           len(titles), factor))
    worst, n = titles.most_common(1)[0]
    agents = {r.get("npc") for r in dedup if (r.get("title") or "")[:70] == worst}
    print("MEASURED: worst title submitted %dx by %d DISTINCT agents -- it is not one agent looping, "
          "it is all of them holding the same card" % (n, len(agents)))

    intents = json.loads(INTENTS.read_text(encoding="utf-8"))
    shared = collections.Counter()
    print("MEASURED: _recent_intents (cap 50 per agent):")
    for eid, seen in sorted(intents.items()):
        shared.update(set(seen))
        print("            %-13s %2d entries / %d DISTINCT" % (eid, len(seen), len(set(seen))))
    all8 = sum(1 for _, c in shared.items() if c == len(intents))
    print("MEASURED: %d distinct intents across the whole swarm; %d of them held by ALL %d agents"
          % (len(shared), all8, len(intents)))

    con = sqlite3.connect("file:%s?mode=ro" % DB.as_posix(), uri=True)
    rows = con.execute("SELECT substr(created_at,1,7) m, COUNT(*) FROM collective_knowledge "
                       "WHERE knowledge_type='discovery' GROUP BY m ORDER BY m DESC LIMIT 4"
                       ).fetchall()
    con.close()
    print("MEASURED: discoveries accepted per month (the pool that re-seeds the findings bucket): %s"
          % ", ".join("%s=%d" % (m, c) for m, c in rows[::-1]))

    saturated = sum(1 for s in intents.values() if len(s) >= 50 and len(set(s)) < 12)
    if saturated == len(intents) and factor > 5:
        print("VERDICT: REPRODUCED -- every agent's anti-repetition memory is saturated with "
              "duplicates of a handful of intents, and the refusals are %.1fx resubmissions of the "
              "same work. The dedup gate is correct; the SUPPLY is the defect." % factor)
    else:
        print("VERDICT: FAILED -- the closed-loop signature did not reproduce "
              "(saturated=%d/%d, factor=%.1fx)" % (saturated, len(intents), factor))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
