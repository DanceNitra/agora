#!/usr/bin/env python3
"""Does GIL RELEASE decide concurrent entry, or does DURATION vs the scheduler quantum? REFUTED.

History, because the refutation is the finding. The draft for langchain-ai/docs#4018 asserted that
GIL release rather than call duration decides whether a sequential graph enters a custom saver
concurrently. The first version of this probe "supported" that at a single operating point,
WORK_S = 2.5 ms, and its controls could not catch why:

  * the equal-cost control was a TAUTOLOGY. Both arms self-terminate on wall clock (`time.sleep(w)`
    and `while perf_counter() < end`), so the ratio is ~1.0 by construction and the control could
    never fire.
  * the calibration was described as anchored on another probe. It read cells computed in the same
    run, and its zero-work floor merely restated the duration hypothesis it was meant to rule out.

CPython's default switch interval is 5 ms (`sys.getswitchinterval()`). A GIL-holding busy loop of
2.5 ms is shorter than the interval at which the interpreter even considers preempting it, so
"releases the GIL" and "is shorter than the quantum" were perfectly aliased at the only point run.

This version sweeps the duration across the quantum, which separates them. Measured 2026-08-29:
the GIL-HOLDING arm overlaps 40/40 once it outlasts the switch interval, and 40/40 at 2.5 ms if the
interval is lowered. The variable is duration relative to the quantum. The GIL framing is dead.

CONTROLS (each able to FAIL, each printed):
  C1  the spy recorded saver calls at all; an empty record can never be reported as a clean 0.
  C2  the SWEEP itself is the control that the first version lacked: if GIL release were the
      variable, the busy arm would stay at 0 across every duration. A single non-zero busy cell
      refutes it. This cannot be satisfied by construction, which is the point.
  C3  the quantum is varied directly via sys.setswitchinterval, so the proposed mechanism is
      manipulated rather than assumed.
"""
import sys, threading, time
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

TRIALS = 40
SWEEP_MS = (0.0, 0.5, 2.5, 10.0, 20.0)     # straddles the 5 ms default quantum


class Rec:
    def __init__(self):
        self.lock = threading.Lock(); self.calls = []
    def add(self, t0, t1, th):
        with self.lock: self.calls.append((t0, t1, th))
    def durs_ms(self): return [(b - a) * 1000.0 for a, b, _ in self.calls]
    def overlapped(self):
        cs = sorted(self.calls)
        for i, (a0, a1, ath) in enumerate(cs):
            for b0, b1, bth in cs[i + 1:]:
                if b0 >= a1: break
                if ath != bth: return True
        return False


def make(kind, work_s, holder):
    def work():
        if work_s <= 0: return
        if kind == "sleep":
            time.sleep(work_s)                      # releases the GIL
        else:
            end = time.perf_counter() + work_s
            while time.perf_counter() < end: pass   # pure Python: holds the GIL

    class S(InMemorySaver):
        def put(self, *a, **k):
            t0 = time.perf_counter(); work()
            try: return super().put(*a, **k)
            finally: holder[0].add(t0, time.perf_counter(), threading.get_ident())
        def put_writes(self, *a, **k):
            t0 = time.perf_counter(); work()
            try: return super().put_writes(*a, **k)
            finally: holder[0].add(t0, time.perf_counter(), threading.get_ident())
    return S


class State(TypedDict):
    steps: list


def build(saver):
    g = StateGraph(State)
    g.add_node("A", lambda s: {"steps": s["steps"] + ["A"]})
    g.add_node("B", lambda s: {"steps": s["steps"] + ["B"]})
    g.add_edge(START, "A"); g.add_edge("A", "B"); g.add_edge("B", END)
    return g.compile(checkpointer=saver)


def run(kind, work_s, durability="sync"):
    holder = [None]; cls = make(kind, work_s, holder)
    n = 0; d = []; total = 0
    for t in range(TRIALS):
        holder[0] = Rec()
        build(cls()).invoke({"steps": []},
                            {"configurable": {"thread_id": "%s%.4f%d" % (kind, work_s, t)}},
                            durability=durability)
        d.extend(holder[0].durs_ms()); total += len(holder[0].calls)
        if holder[0].overlapped(): n += 1
    assert total, "C1 FAILED: no saver calls recorded, the probe never reached its target"
    return sum(d) / len(d), n


def main():
    import importlib.metadata as md
    q = sys.getswitchinterval()
    print("GIL release, or duration vs the scheduler quantum? langgraph %s, %d trials/cell"
          % (md.version("langgraph"), TRIALS))
    print("  sys.getswitchinterval() = %.4f s (%.1f ms)   graph: START -> A -> B -> END\n"
          % (q, q * 1000))
    print("  %-9s | %-22s | %s" % ("work_ms", "sleep (releases GIL)", "busy (holds GIL)"))
    print("  " + "-" * 62)
    busy_hits = {}
    for w in SWEEP_MS:
        ms, ns = run("sleep", w / 1000.0)
        mb, nb = run("busy", w / 1000.0)
        busy_hits[w] = nb
        print("  %-9.1f | %6.2f ms  %6s      | %6.2f ms  %s"
              % (w, ms, "%d/%d" % (ns, TRIALS), mb, "%d/%d" % (nb, TRIALS)))
        sys.stdout.flush()

    print("\n  -- C3: manipulate the proposed mechanism, sys.setswitchinterval(0.0005) --")
    sys.setswitchinterval(0.0005)
    mb2, nb2 = run("busy", 0.0025)
    print("  busy 2.5 ms at a 0.5 ms quantum: %6.2f ms  %d/%d" % (mb2, nb2, TRIALS))
    sys.setswitchinterval(q)

    print("\n=== VERDICT ===")
    above = [w for w in SWEEP_MS if w > q * 1000 and busy_hits[w] > 0]
    if above or nb2 > 0:
        print("  REFUTED. A GIL-HOLDING call overlaps too, once it outlasts the quantum")
        print("  (busy non-zero at %s ms) or once the quantum is shortened under it (%d/%d)."
              % (above, nb2, TRIALS))
        print("  The variable is call duration RELATIVE TO THE SWITCH INTERVAL, not GIL release.")
        return 0
    print("  NOT REFUTED: the busy arm stayed at 0 across the whole sweep and under a short quantum.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
