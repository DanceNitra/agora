#!/usr/bin/env python3
"""Refine the concurrency threshold, reporting MEASURED saver-call duration.

The sweep reported a nominal sleep of 0.5 ms as the point where concurrent entry
appears. A nominal sleep is not a measured duration -- time.sleep() granularity
on Windows is coarse, so the real boundary must be stated in terms of what the
saver call ACTUALLY took, not what was requested.

Reports, per cell: requested sleep, MEASURED mean/min/max call duration, distinct
threads, and the fraction of trials showing cross-thread overlap.
"""

import sys
import threading
import time
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

MAIN_THREAD = threading.get_ident()
TRIALS = 10
REQUESTED_MS = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0]


class CallLog:
    def __init__(self):
        self._lock = threading.Lock()
        self.calls = []

    def record(self, method, t0, t1):
        with self._lock:
            self.calls.append({"method": method, "thread": threading.get_ident(),
                               "t0": t0, "t1": t1})

    def threads(self):
        return {c["thread"] for c in self.calls}

    def durations_ms(self):
        return [(c["t1"] - c["t0"]) * 1000.0 for c in self.calls]

    def overlaps(self):
        out = []
        cs = sorted(self.calls, key=lambda c: c["t0"])
        for i, a in enumerate(cs):
            for b in cs[i + 1:]:
                if b["t0"] >= a["t1"]:
                    break
                if a["thread"] != b["thread"]:
                    out.append((a, b))
        return out


class InstrumentedSaver(InMemorySaver):
    def __init__(self, log, delay_s=0.0):
        super().__init__()
        self._log = log
        self._delay = delay_s

    def put(self, config, checkpoint, metadata, new_versions):
        t0 = time.perf_counter()
        if self._delay:
            time.sleep(self._delay)
        r = super().put(config, checkpoint, metadata, new_versions)
        self._log.record("put", t0, time.perf_counter())
        return r

    def put_writes(self, config, writes, task_id, task_path=""):
        t0 = time.perf_counter()
        if self._delay:
            time.sleep(self._delay)
        r = super().put_writes(config, writes, task_id, task_path)
        self._log.record("put_writes", t0, time.perf_counter())
        return r


class State(TypedDict):
    steps: list


def run_once(durability, delay_s, tid):
    log = CallLog()
    saver = InstrumentedSaver(log, delay_s=delay_s)

    def a(state):
        return {"steps": state["steps"] + ["A"]}

    def b(state):
        return {"steps": state["steps"] + ["B"]}

    g = StateGraph(State)
    g.add_node("A", a)
    g.add_node("B", b)
    g.add_edge(START, "A")
    g.add_edge("A", "B")
    g.add_edge("B", END)
    graph = g.compile(checkpointer=saver)
    out = graph.invoke({"steps": []}, {"configurable": {"thread_id": tid}},
                       durability=durability)
    assert out["steps"] == ["A", "B"]
    return log


def main():
    print("threshold refinement -- MEASURED call duration vs concurrent entry")
    print("  trials per cell: %d   graph: START -> A -> B -> END (sequential)" % TRIALS)
    print("  clock: time.perf_counter, platform: %s" % sys.platform)
    print()
    print("  %-6s %-9s | %-10s %-10s %-10s | %-8s %s"
          % ("durab.", "sleep_ms", "dur_mean", "dur_min", "dur_max", "threads", "trials_ovl"))
    print("  " + "-" * 82)

    for dur in ("async", "sync"):
        for req_ms in REQUESTED_MS:
            delay = req_ms / 1000.0
            all_d = []
            n_ovl = 0
            tot_thr = 0
            for t in range(TRIALS):
                log = run_once(dur, delay, "%s-%s-%d" % (dur, req_ms, t))
                all_d.extend(log.durations_ms())
                tot_thr += len(log.threads())
                if log.overlaps():
                    n_ovl += 1
            assert MAIN_THREAD not in set(), ""
            print("  %-6s %-9.2f | %-10.4f %-10.4f %-10.4f | %-8.1f %d/%d"
                  % (dur, req_ms, sum(all_d) / len(all_d), min(all_d), max(all_d),
                     tot_thr / TRIALS, n_ovl, TRIALS))
            sys.stdout.flush()
        print()


if __name__ == "__main__":
    main()
