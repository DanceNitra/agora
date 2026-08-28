#!/usr/bin/env python3
"""Do REAL checkpointers overlap on a sequential graph? No simulated latency.

The sleep-based probe established that overlap appears once a saver call costs
~0.5 ms, but it never measured a real saver, so "below every real DB round trip"
was an unearned claim. This replaces the simulation: it wraps ACTUAL savers,
adds no sleep, and reports the latency they really have.

Savers under test:
  InMemorySaver   -- control. In-process dict. Expected: fast, no overlap.
  SqliteSaver     -- LangGraph's own file-backed saver. Holds a threading.Lock.
  InspeximusSaver -- OURS. No lock. put() and put_writes() each call store._save(),
                     a full JSON serialization of the store to disk.

Graph is strictly sequential: START -> A -> B -> END, no fan-out, no Send.

Also counts EXCEPTIONS raised inside the saver, because the failure mode we are
chasing for our own store is an intermittent refusal, not a wrong answer.
"""

import os
import sys
import tempfile
import threading
import time
import traceback
from typing import TypedDict

sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

TRIALS = 40


class Rec:
    def __init__(self):
        self.lock = threading.Lock()
        self.calls = []
        self.errors = []

    def add(self, method, t0, t1):
        with self.lock:
            self.calls.append({"m": method, "th": threading.get_ident(), "t0": t0, "t1": t1})

    def err(self, method, e):
        with self.lock:
            self.errors.append("%s: %s: %s" % (method, type(e).__name__, e))

    def threads(self):
        return {c["th"] for c in self.calls}

    def durs_ms(self):
        return [(c["t1"] - c["t0"]) * 1000.0 for c in self.calls]

    def overlaps(self):
        out = []
        cs = sorted(self.calls, key=lambda c: c["t0"])
        for i, a in enumerate(cs):
            for b in cs[i + 1:]:
                if b["t0"] >= a["t1"]:
                    break
                if a["th"] != b["th"]:
                    out.append((a, b))
        return out


def spy(base_cls):
    """Wrap a saver class with timing only. No sleep, no behaviour change."""

    class Spy(base_cls):
        _rec = None

        def put(self, *a, **k):
            t0 = time.perf_counter()
            try:
                return super().put(*a, **k)
            except Exception as e:
                self._rec.err("put", e)
                raise
            finally:
                self._rec.add("put", t0, time.perf_counter())

        def put_writes(self, *a, **k):
            t0 = time.perf_counter()
            try:
                return super().put_writes(*a, **k)
            except Exception as e:
                self._rec.err("put_writes", e)
                raise
            finally:
                self._rec.add("put_writes", t0, time.perf_counter())

    Spy.__name__ = "Spy" + base_cls.__name__
    return Spy


class State(TypedDict):
    steps: list


def build(saver):
    def a(s):
        return {"steps": s["steps"] + ["A"]}

    def b(s):
        return {"steps": s["steps"] + ["B"]}

    g = StateGraph(State)
    g.add_node("A", a)
    g.add_node("B", b)
    g.add_edge(START, "A")
    g.add_edge("A", "B")
    g.add_edge("B", END)
    return g.compile(checkpointer=saver)


def run_case(name, make_saver, durability):
    rec = Rec()
    n_overlap_trials = 0
    n_failed_runs = 0
    all_d = []
    tot_thr = 0
    for t in range(TRIALS):
        trial_rec = Rec()
        try:
            saver = make_saver()
            saver._rec = trial_rec
            g = build(saver)
            out = g.invoke({"steps": []}, {"configurable": {"thread_id": "t%d" % t}},
                           durability=durability)
            if out["steps"] != ["A", "B"]:
                n_failed_runs += 1
        except Exception as e:
            n_failed_runs += 1
            trial_rec.err("invoke", e)
        all_d.extend(trial_rec.durs_ms())
        tot_thr += len(trial_rec.threads())
        if trial_rec.overlaps():
            n_overlap_trials += 1
        rec.errors.extend(trial_rec.errors)
    mean = sum(all_d) / len(all_d) if all_d else 0.0
    print("  %-16s %-6s | %-9.4f %-9.4f | %-7.1f %-8s %-8s %s"
          % (name, durability, mean, max(all_d) if all_d else 0.0,
             tot_thr / TRIALS, "%d/%d" % (n_overlap_trials, TRIALS),
             n_failed_runs, len(rec.errors)))
    sys.stdout.flush()
    return rec, n_overlap_trials, n_failed_runs


def main():
    import importlib.metadata as md
    print("REAL savers on a SEQUENTIAL graph -- no simulated latency")
    print("  langgraph %s | trials per cell %d" % (md.version("langgraph"), TRIALS))
    print("  graph: START -> A -> B -> END (no fan-out, no Send)")
    print()
    print("  %-16s %-6s | %-9s %-9s | %-7s %-8s %-8s %s"
          % ("saver", "durab", "dur_mean", "dur_max", "threads", "ovl_trls", "failed", "errors"))
    print("  " + "-" * 92)

    tmp = tempfile.mkdtemp(prefix="lgreal_")
    cases = []

    cases.append(("InMemorySaver", lambda: spy(InMemorySaver)()))

    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        import sqlite3

        def mk_sqlite():
            p = os.path.join(tmp, "s%d.db" % len(os.listdir(tmp)))
            conn = sqlite3.connect(p, check_same_thread=False)
            return spy(SqliteSaver)(conn)

        cases.append(("SqliteSaver", mk_sqlite))
    except Exception as e:
        print("  SqliteSaver unavailable: %s" % e)

    try:
        from inspeximus.integrations.langgraph import InspeximusSaver

        def mk_insp():
            p = os.path.join(tmp, "i%d.json" % len(os.listdir(tmp)))
            return spy(InspeximusSaver)(path=p)

        cases.append(("InspeximusSaver", mk_insp))
    except Exception as e:
        print("  InspeximusSaver unavailable: %s" % type(e).__name__)
        traceback.print_exc()

    results = {}
    for dur in ("async", "sync"):
        for name, mk in cases:
            results[(name, dur)] = run_case(name, mk, dur)
        print()

    print("=== ERRORS SEEN (first 5 per cell) ===")
    any_err = False
    for (name, dur), (rec, _, _) in results.items():
        if rec.errors:
            any_err = True
            print("  %s / durability=%s : %d errors" % (name, dur, len(rec.errors)))
            for e in rec.errors[:5]:
                print("      %s" % e)
    if not any_err:
        print("  none")


if __name__ == "__main__":
    main()
