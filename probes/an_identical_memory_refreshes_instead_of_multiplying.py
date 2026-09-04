"""Does storing the same memory twice create two rows, and is MAX_EPISODIC a real limit?

WHY. `agent_memories` held 40,205 rows of which 37,755 were one string: the vault gate's rejection
notice. 27,100 belonged to a single agent. The call site's comment claimed a strong episodic memory
would teach the agent to stop resubmitting the same ungrounded note; nobody measured whether it
did, and the agent resubmitted for 63 days. The writing has since tapered off on its own (27,841 in
July, 9,912 in August, 2 in September), so this guard is about the shape of the write path rather
than a live fire, but 94% of the swarm's memory was one sentence and nothing could have stopped it.

RUN ON A COPY. The live database is never written by this probe.

CHECKS, each able to fail:
  1. A repeat does not add a row, and returns the id of the row already held.
  2. A repeat still counts as an experience: importance rises and decay resets, so "this keeps
     happening to me" is recorded as salience rather than as volume.
  3. THE CONTROL: a DIFFERENT memory still creates a row. A guard that collapses everything would
     pass check 1 while destroying the memory system, and that failure is worse than the bloat.
  4. THE CONTROL IS SCOPED PER AGENT: the same text from a different agent is a new row, because
     memories belong to whoever had them.
  5. THE CAP IS ENFORCED. MAX_EPISODIC is 100. The old prune deleted only rows BELOW
     IMPORTANCE_THRESHOLD (0.8), so a memory written AT 0.8 was immortal and one agent accumulated
     27,456 episodic rows against a cap of 100. After a write, the agent's episodic count must be at
     or under the cap even when every row sits at or above the threshold.
  6. THE CAP KEEPS THE RIGHT ONES. A high-importance memory must survive the trim while a
     low-importance one does not, otherwise the cap is enforced by throwing away the best rows.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERVER = os.path.join(ROOT, "server")
LIVE = os.path.join(SERVER, "agora.db")
OUT = os.path.join(HERE, "an_identical_memory_refreshes_instead_of_multiplying.result.json")
sys.path.insert(0, SERVER)

A = "00000000-0000-0000-0000-000000000005"
FRESH = "probe-fresh-agent-0001"
FRESH_B = "probe-fresh-agent-0002"
TEXT = "a probe memory that is written twice on purpose"


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


from agora.agent_os.memory_agent import MemoryAgent


async def run(db_path):
    import aiosqlite
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        async def rows(npc, text):
            cur = await db.execute("select count(*) from agent_memories where npc_id=? and content=?",
                                   (npc, text))
            return (await cur.fetchone())[0]

        async def one(mid):
            cur = await db.execute("select importance, decay_factor from agent_memories where id=?",
                                   (mid,))
            return await cur.fetchone()

        # The dedupe checks run on a FRESH agent. They cannot run on a loaded one: the cap fix below
        # trims that agent to its 100 most important rows, and a probe memory at importance 0.5 is
        # evicted the instant it is written. The first version of this probe did exactly that and
        # read the eviction as a missing row.
        mem = MemoryAgent(db, FRESH)
        id1 = await mem.store_memory(TEXT, "episodic", 0.5, "reflective", "probe")
        n1 = await rows(FRESH, TEXT)
        id2 = await mem.store_memory(TEXT, "episodic", 0.5, "reflective", "probe")
        n2 = await rows(FRESH, TEXT)
        r = await one(id2)

        other = await mem.store_memory(TEXT + " but different", "episodic", 0.5, "reflective", "probe")
        n_other = await rows(FRESH, TEXT + " but different")

        memb = MemoryAgent(db, FRESH_B)
        idb = await memb.store_memory(TEXT, "episodic", 0.5, "reflective", "probe")
        n_b = await rows(FRESH_B, TEXT)

        # The cap, on the REAL agent that held 27,456 episodic rows against a limit of 100.
        cur = await db.execute("select count(*) from agent_memories where npc_id=? and "
                               "memory_type='episodic'", (A,))
        episodic_before = (await cur.fetchone())[0]
        loaded = MemoryAgent(db, A)
        keep_id = await loaded.store_memory("a probe memory that must survive the cap", "episodic",
                                            1.0, "excited", "probe")
        drop_id = await loaded.store_memory("a probe memory that must be evicted", "episodic",
                                            0.10, "neutral", "probe")
        cur = await db.execute("select count(*) from agent_memories where npc_id=? and "
                               "memory_type='episodic'", (A,))
        episodic = (await cur.fetchone())[0]
        cur = await db.execute("select count(*) from agent_memories where id=?", (keep_id,))
        kept = (await cur.fetchone())[0]
        cur = await db.execute("select count(*) from agent_memories where id=?", (drop_id,))
        dropped = (await cur.fetchone())[0]

        return dict(id1=id1, id2=id2, n1=n1, n2=n2,
                    importance=r["importance"], decay=r["decay_factor"],
                    other=other, n_other=n_other, idb=idb, n_b=n_b,
                    episodic_before=episodic_before, episodic=episodic,
                    cap=MemoryAgent.MAX_EPISODIC, kept=kept, dropped=dropped)


def main():
    if not os.path.isfile(LIVE):
        refuse("no agora.db, so this check has nothing to write into")
    d = tempfile.mkdtemp(prefix="memdedupe_")
    tmp = os.path.join(d, "agora.db")
    shutil.copy2(LIVE, tmp)

    res = asyncio.run(run(tmp))
    print("  first write  -> id %s, rows with that text: %d" % (res["id1"], res["n1"]))
    print("  second write -> id %s, rows with that text: %d" % (res["id2"], res["n2"]))
    if res["n1"] != 1:
        refuse("the first write did not create exactly one row (%d); the fixture is wrong" % res["n1"])
    if res["n2"] != 1:
        refuse("the repeat created a second row (%d total); the guard did not fire" % res["n2"])
    if res["id1"] != res["id2"]:
        refuse("the repeat returned a different id (%s vs %s), so callers holding the id would "
               "diverge" % (res["id1"], res["id2"]))
    print("  the repeat returned the SAME id and added no row")

    print()
    print("  importance after the repeat: %.2f (from 0.50), decay reset to %.1f"
          % (res["importance"], res["decay"]))
    if res["importance"] <= 0.5:
        refuse("importance did not rise, so a recurring experience leaves no trace at all, which "
               "trades one failure for another")
    if res["decay"] != 1.0:
        refuse("decay was not refreshed, so a repeated memory still fades on the old schedule")

    print()
    print("  CONTROL: a DIFFERENT memory -> id %s, rows: %d" % (res["other"], res["n_other"]))
    if res["n_other"] != 1 or res["other"] == res["id1"]:
        refuse("a different memory did not create its own row; the guard collapses everything and "
               "has destroyed the memory system rather than deduplicated it")
    print("  CONTROL: the same text from another agent -> id %s, rows: %d" % (res["idb"], res["n_b"]))
    if res["n_b"] != 1 or res["idb"] == res["id1"]:
        refuse("the guard reached across agents; a memory belongs to whoever had it")

    print()
    print("  CAP: MAX_EPISODIC is %d; the loaded agent held %d episodic memories and now holds %d"
          % (res["cap"], res["episodic_before"], res["episodic"]))
    if res["episodic"] > res["cap"]:
        refuse("the agent holds %d episodic memories against a cap of %d, so the cap is still not "
               "enforced once every row sits at or above IMPORTANCE_THRESHOLD"
               % (res["episodic"], res["cap"]))
    print("  CONTROL: the importance-1.00 memory survived (%d), the importance-0.10 one did not (%d)"
          % (res["kept"], res["dropped"]))
    if res["kept"] != 1:
        refuse("the cap evicted a high-importance memory, so it is enforced by discarding the best "
               "rows rather than the worst")
    if res["dropped"] != 0:
        refuse("the low-importance memory survived the trim, so this fixture never exercised the "
               "cap and check 5 proved nothing")

    print()
    print("  VERDICT: a repeat refreshes, a new memory is still a new memory, the cap is a cap.")
    json.dump({"script": os.path.basename(__file__), **res,
               "controls": {"distinct_memory_still_stored": True,
                            "scoped_per_agent": True,
                            "salience_recorded": True}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
