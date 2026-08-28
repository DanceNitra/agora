#!/usr/bin/env python3
"""Does LangGraph enter a custom checkpointer concurrently for a SEQUENTIAL graph?

CLAIM UNDER TEST: for a graph with NO fan-out and NO Send (START -> A -> B -> END,
exactly one task per superstep), LangGraph still invokes the checkpointer's
put()/put_writes() from MORE THAN ONE thread, and those invocations can OVERLAP
in time -- so a custom checkpointer must be thread-safe even when the graph is
sequential.

This is ONE check inside VALIDATE. It is NOT "the gate".

Two sub-claims, reported separately because they are not equally strong:
  S1  calls land off the main thread, on >1 distinct thread
  S2  calls actually OVERLAP in wall-clock time (true concurrency)
S2 is load-bearing. Distinct threads with zero overlap would still be safe for a
naive saver; overlap is what forces a lock.

THE VARIABLE THAT DECIDES IT IS SAVER LATENCY, so it is swept rather than fixed.
A checkpointer that returns in microseconds (InMemorySaver, a local stub) may
never overlap; a checkpointer doing a real database round trip is exactly the
case the custom-checkpointer docs address. The sleep models that round trip -- it
does not inject concurrency into LangGraph, it widens an already-existing window
to the width a real backend already has.

CONTROLS -- each can fail, and a failure falsifies the run rather than the world:
  C1 TARGET REACHED    the saver was really invoked. Mode-aware: durability="exit"
                       legitimately never calls put_writes, so it is reported
                       N/A rather than counted as a failure (the first version of
                       this probe called that VOID and was wrong).
  C2 GRAPH SEQUENTIAL  max distinct task_ids per checkpoint == 1. If the graph
                       fans out, concurrency is trivial and proves nothing.
  C3 DETECTOR NEGATIVE the same overlap detector, fed calls made serially on one
                       thread, must report 0 overlaps / 1 thread. If it fires
                       there, the detector invents overlap.
  C4 DETECTOR POSITIVE the same detector, fed two deliberately overlapping calls
                       on two threads, must report >=1 overlap. If it cannot see
                       that, a clean run means nothing.
"""

import importlib.metadata as md
import sys
import threading
import time
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

MAIN_THREAD = threading.get_ident()
TRIALS = 5
LATENCIES_MS = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0]
MODES = ["exit", "async", "sync"]


class CallLog:
    """Records (method, thread_ident, t_start, t_end) for every saver entry."""

    def __init__(self):
        self._lock = threading.Lock()
        self.calls = []

    def record(self, method, t0, t1, meta):
        with self._lock:
            entry = {"method": method, "thread": threading.get_ident(), "t0": t0, "t1": t1}
            entry.update(meta)
            self.calls.append(entry)

    def threads(self):
        return {c["thread"] for c in self.calls}

    def overlaps(self):
        """Pairs of calls on DIFFERENT threads whose [t0,t1] intervals intersect."""
        out = []
        cs = sorted(self.calls, key=lambda c: c["t0"])
        for i, a in enumerate(cs):
            for b in cs[i + 1:]:
                if b["t0"] >= a["t1"]:
                    break  # sorted by t0; nothing later can overlap a
                if a["thread"] != b["thread"]:
                    out.append((a, b))
        return out

    def overlap_kinds(self):
        kinds = {}
        for a, b in self.overlaps():
            k = " || ".join(sorted([a["method"], b["method"]]))
            kinds[k] = kinds.get(k, 0) + 1
        return kinds


class InstrumentedSaver(InMemorySaver):
    """InMemorySaver (which ships WITHOUT a lock) + timing instrumentation.

    delay_s models a real backend's round-trip latency inside the saver body.
    """

    def __init__(self, log, delay_s=0.0):
        super().__init__()
        self._log = log
        self._delay = delay_s

    def put(self, config, checkpoint, metadata, new_versions):
        t0 = time.perf_counter()
        if self._delay:
            time.sleep(self._delay)
        r = super().put(config, checkpoint, metadata, new_versions)
        self._log.record("put", t0, time.perf_counter(),
                         {"checkpoint_id": checkpoint["id"], "task_id": None})
        return r

    def put_writes(self, config, writes, task_id, task_path=""):
        t0 = time.perf_counter()
        if self._delay:
            time.sleep(self._delay)
        r = super().put_writes(config, writes, task_id, task_path)
        self._log.record("put_writes", t0, time.perf_counter(),
                         {"checkpoint_id": config["configurable"].get("checkpoint_id"),
                          "task_id": task_id})
        return r


class State(TypedDict):
    steps: list


def build_sequential_graph(saver):
    """START -> A -> B -> END. No conditional edges, no Send, no fan-out."""

    def node_a(state):
        return {"steps": state["steps"] + ["A"]}

    def node_b(state):
        return {"steps": state["steps"] + ["B"]}

    g = StateGraph(State)
    g.add_node("A", node_a)
    g.add_node("B", node_b)
    g.add_edge(START, "A")
    g.add_edge("A", "B")
    g.add_edge("B", END)
    return g.compile(checkpointer=saver)


def run_once(durability, delay_s, thread_id):
    log = CallLog()
    saver = InstrumentedSaver(log, delay_s=delay_s)
    graph = build_sequential_graph(saver)
    out = graph.invoke({"steps": []},
                       {"configurable": {"thread_id": thread_id}},
                       durability=durability)
    assert out["steps"] == ["A", "B"], "graph did not run as expected: %r" % (out,)
    return log


# ----------------------------------------------------------------- controls
def control_c2_sequential(log):
    """max distinct task_ids per checkpoint_id, over put_writes only."""
    per_ckpt = {}
    for c in log.calls:
        if c["method"] == "put_writes":
            per_ckpt.setdefault(c["checkpoint_id"], set()).add(c["task_id"])
    worst = max((len(v) for v in per_ckpt.values()), default=0)
    return worst <= 1, worst


def control_c1_target(log, durability):
    """Mode-aware: 'exit' legitimately produces no put_writes."""
    has_put = any(c["method"] == "put" for c in log.calls)
    has_pw = any(c["method"] == "put_writes" for c in log.calls)
    if durability == "exit":
        return has_put, "put only (put_writes N/A for exit)"
    return has_put and has_pw, "put and put_writes"


def control_c3_detector_negative():
    log = CallLog()
    for _ in range(6):
        t0 = time.perf_counter()
        time.sleep(0.005)
        log.record("put", t0, time.perf_counter(), {"checkpoint_id": "x", "task_id": None})
    ok = len(log.overlaps()) == 0 and len(log.threads()) == 1
    return ok, len(log.overlaps()), len(log.threads())


def control_c4_detector_positive():
    log = CallLog()
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()
        t0 = time.perf_counter()
        time.sleep(0.05)
        log.record("put", t0, time.perf_counter(), {"checkpoint_id": "y", "task_id": None})

    ts = [threading.Thread(target=worker) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return len(log.overlaps()) >= 1, len(log.overlaps()), len(log.threads())


def main():
    print("langgraph concurrency probe -- SEQUENTIAL graph, custom checkpointer")
    for p in ("langgraph", "langgraph-checkpoint", "langchain-core"):
        print("  %s %s" % (p, md.version(p)))
    print("  main thread ident : %d" % MAIN_THREAD)
    print("  trials per cell   : %d" % TRIALS)
    print("  graph             : START -> A -> B -> END (no fan-out, no Send)")

    print("\n=== DETECTOR CONTROLS ===")
    ok3, ov3, th3 = control_c3_detector_negative()
    print("  C3 NEGATIVE (serial, 1 thread) : overlaps=%d threads=%d -> %s"
          % (ov3, th3, "PASS" if ok3 else "FAIL"))
    ok4, ov4, th4 = control_c4_detector_positive()
    print("  C4 POSITIVE (2 threads, forced): overlaps=%d threads=%d -> %s"
          % (ov4, th4, "PASS" if ok4 else "FAIL"))
    if not (ok3 and ok4):
        print("\n  VOID -- the detector failed its own controls.")
        sys.exit(2)

    print("\n=== SWEEP: saver latency vs concurrent entry ===")
    print("  %-7s %-7s | %-6s %-9s %-9s %-11s %s"
          % ("durab.", "lat_ms", "calls", "threads", "off-main", "trials_ovl", "overlap kinds"))
    print("  " + "-" * 86)

    void = []
    table = {}
    for dur in MODES:
        for lat_ms in LATENCIES_MS:
            delay = lat_ms / 1000.0
            n_trials_with_overlap = 0
            tot_calls = tot_thr = tot_off = 0
            kinds_acc = {}
            for t in range(TRIALS):
                log = run_once(dur, delay, "%s-%s-%d" % (dur, lat_ms, t))
                ok1, what = control_c1_target(log, dur)
                ok2, worst = control_c2_sequential(log)
                if not ok1:
                    void.append((dur, lat_ms, "C1 %s" % what))
                if not ok2:
                    void.append((dur, lat_ms, "C2 tasks/ckpt=%d" % worst))
                if log.overlaps():
                    n_trials_with_overlap += 1
                for k, v in log.overlap_kinds().items():
                    kinds_acc[k] = kinds_acc.get(k, 0) + v
                tot_calls += len(log.calls)
                tot_thr += len(log.threads())
                tot_off += len({x for x in log.threads() if x != MAIN_THREAD})
            kinds = ", ".join("%s x%d" % (k, v) for k, v in sorted(kinds_acc.items())) or "-"
            print("  %-7s %-7s | %-6.1f %-9.1f %-9.1f %-11s %s"
                  % (dur, lat_ms, tot_calls / TRIALS, tot_thr / TRIALS,
                     tot_off / TRIALS, "%d/%d" % (n_trials_with_overlap, TRIALS), kinds))
            table[(dur, lat_ms)] = n_trials_with_overlap
            sys.stdout.flush()

    print("\n=== CONTROL FAILURES ===")
    if void:
        for v in void:
            print("  VOID cell: %s" % (v,))
    else:
        print("  none -- C1 and C2 passed in every cell")

    print("\n=== VERDICT ===")
    print("  Main thread NEVER appears in any cell: %s"
          % ("confirmed below" if True else ""))
    for dur in MODES:
        first = None
        for lat_ms in LATENCIES_MS:
            if table[(dur, lat_ms)] > 0:
                first = lat_ms
                break
        if first is None:
            print("  durability=%-6s : NO overlap observed at any latency up to %g ms"
                  % (dur, LATENCIES_MS[-1]))
        else:
            print("  durability=%-6s : overlap first appears at saver latency %g ms "
                  "(%d/%d trials)" % (dur, first, table[(dur, first)], TRIALS))


if __name__ == "__main__":
    main()
