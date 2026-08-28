#!/usr/bin/env python3
"""Does concurrent entry actually LOSE WRITES, or is overlap harmless?

Overlap is not a race. The sync probe showed real savers are entered
concurrently on a sequential graph; this asks whether that costs anything.

N threads each call put_writes with a DISTINCT task_id against ONE saver
instance and one checkpoint, then the writes are read back and counted.
Expected N. Anything less is lost data.

CONTROLS:
  SERIAL   the same N writes issued one after another on one thread. If serial
           also loses writes, the defect is not concurrency and the whole test
           is void.
  LOCKED   SqliteSaver, which holds a threading.Lock, under the identical
           concurrent harness. It should lose nothing -- if it does, the harness
           is wrong rather than the saver.
  DISJOINT InMemorySaver, no lock but disjoint dict keys. Expected intact.
"""
import os, sys, tempfile, threading, traceback
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from langgraph.checkpoint.memory import InMemorySaver

N = 12
ROUNDS = 8
CFG = {"configurable": {"thread_id": "t", "checkpoint_ns": "", "checkpoint_id": "c1"}}


def seed(saver):
    from langgraph.checkpoint.base import empty_checkpoint
    ck = empty_checkpoint(); ck["id"] = "c1"
    saver.put({"configurable": {"thread_id": "t", "checkpoint_ns": ""}}, ck,
              {"source": "input", "step": 0, "writes": {}}, {})


def count_writes(saver):
    t = saver.get_tuple(CFG)
    return len(t.pending_writes or []) if t else 0


def concurrent(saver, n=N):
    errs = []
    bar = threading.Barrier(n)
    def w(i):
        try:
            bar.wait()
            saver.put_writes(CFG, [("ch", "v%d" % i)], "task%d" % i)
        except Exception as e:
            errs.append("%s: %s" % (type(e).__name__, e))
    ts = [threading.Thread(target=w, args=(i,)) for i in range(n)]
    for t in ts: t.start()
    for t in ts: t.join()
    return errs


def serial(saver, n=N):
    errs = []
    for i in range(n):
        try:
            saver.put_writes(CFG, [("ch", "v%d" % i)], "task%d" % i)
        except Exception as e:
            errs.append("%s: %s" % (type(e).__name__, e))
    return errs


def arm(label, make, mode):
    lost_rounds = 0; tot_lost = 0; all_errs = []
    for r in range(ROUNDS):
        saver = make()
        seed(saver)
        errs = (concurrent if mode == "concurrent" else serial)(saver)
        got = count_writes(saver)
        if got < N:
            lost_rounds += 1; tot_lost += (N - got)
        all_errs.extend(errs)
    print("  %-16s %-11s | expected %d  lost_rounds %d/%d  writes_lost %-4d errors %d"
          % (label, mode, N, lost_rounds, ROUNDS, tot_lost, len(all_errs)))
    sys.stdout.flush()
    return all_errs


def main():
    tmp = tempfile.mkdtemp(prefix="harm_")
    print("Does concurrent entry LOSE WRITES?  N=%d threads, %d rounds\n" % (N, ROUNDS))
    seen = {}
    seen["mem"] = arm("InMemorySaver", lambda: InMemorySaver(), "concurrent")

    try:
        import sqlite3
        from langgraph.checkpoint.sqlite import SqliteSaver
        c = [0]
        def mk():
            c[0] += 1
            return SqliteSaver(sqlite3.connect(os.path.join(tmp, "s%d.db" % c[0]),
                                               check_same_thread=False))
        seen["sqlite"] = arm("SqliteSaver", mk, "concurrent")
    except Exception as e:
        print("  SqliteSaver unavailable: %s" % e)

    try:
        from inspeximus.integrations.langgraph import InspeximusSaver
        c = [0]
        def mki():
            c[0] += 1
            return InspeximusSaver(path=os.path.join(tmp, "i%d.json" % c[0]))
        seen["insp_serial"] = arm("InspeximusSaver", mki, "serial")
        seen["insp_conc"] = arm("InspeximusSaver", mki, "concurrent")
    except Exception:
        traceback.print_exc()

    print("\n=== ERRORS (first 6 per arm) ===")
    any_e = False
    for k, v in seen.items():
        if v:
            any_e = True
            print("  %s: %d" % (k, len(v)))
            for e in v[:6]: print("      %s" % e)
    if not any_e: print("  none")


if __name__ == "__main__":
    main()
