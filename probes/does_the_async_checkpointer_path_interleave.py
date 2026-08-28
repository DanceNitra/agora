#!/usr/bin/env python3
"""The ASYNC path: does a custom checkpointer's aput/aput_writes INTERLEAVE?

The sync finding (real savers overlap on OS threads for a sequential graph) says
nothing about ainvoke. On the async path LangGraph drives aput/aput_writes as
asyncio tasks on ONE event-loop thread, so a threading.Lock is a no-op there.
The hazard is different in kind: coroutine bodies interleave at each await point.

That predicts a split which is what this probe tests:

  ATOMIC saver   -- async methods contain NO await (ours: `async def aput` just
                    calls the sync body). The coroutine runs to completion without
                    yielding, so it CANNOT interleave. Accidentally safe -- but it
                    blocks the event loop for the whole call.
  AWAITING saver -- async methods await anything at all (any real async driver:
                    asyncpg, motor, redis.asyncio). It yields mid-body, so a
                    second call can enter before the first leaves.

CONTROLS:
  C1 the saver was really invoked on the async path (>0 aput AND >0 aput_writes)
  C2 the graph is genuinely sequential (max 1 distinct task_id per checkpoint)
  C3 the interleave detector must report 0 for a deliberately atomic body and
     >=1 for a deliberately yielding one -- otherwise a clean run means nothing
"""

import asyncio
import sys
import threading
import time
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

TRIALS = 20


class Rec:
    def __init__(self):
        self.events = []          # (kind, method, seq, thread)
        self.depth = 0
        self.max_depth = 0
        self.interleavings = 0
        self._seq = 0
        self.threads = set()
        self.tasks_per_ckpt = {}

    def note_write(self, ckpt_id, task_id):
        self.tasks_per_ckpt.setdefault(ckpt_id, set()).add(task_id)

    def max_tasks_per_ckpt(self):
        """C2: 1 means every superstep had a single task, i.e. genuinely sequential.
        Returns None when there is nothing to judge, so an EMPTY set can never be
        reported as PASS -- the defect this control had in its first revision."""
        if not self.tasks_per_ckpt:
            return None
        return max(len(v) for v in self.tasks_per_ckpt.values())

    def enter(self, method):
        self._seq += 1
        s = self._seq
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        if self.depth > 1:
            self.interleavings += 1
        self.threads.add(threading.get_ident())
        self.events.append(("enter", method, s))
        return s

    def leave(self, method, s):
        self.depth -= 1
        self.events.append(("leave", method, s))


class AtomicSaver(InMemorySaver):
    """Ours in shape: async delegates straight to the sync body, no await."""

    def __init__(self, rec, work_s=0.010):
        super().__init__()
        self._rec = rec
        self._work = work_s

    async def aput(self, config, checkpoint, metadata, new_versions):
        s = self._rec.enter("aput")
        try:
            time.sleep(self._work)          # blocking work, no yield
            return super().put(config, checkpoint, metadata, new_versions)
        finally:
            self._rec.leave("aput", s)

    async def aput_writes(self, config, writes, task_id, task_path=""):
        s = self._rec.enter("aput_writes")
        self._rec.note_write(config["configurable"].get("checkpoint_id"), task_id)
        try:
            time.sleep(self._work)
            return super().put_writes(config, writes, task_id, task_path)
        finally:
            self._rec.leave("aput_writes", s)


class AwaitingSaver(InMemorySaver):
    """Any real async driver: the body yields at an await."""

    def __init__(self, rec, work_s=0.010):
        super().__init__()
        self._rec = rec
        self._work = work_s

    async def aput(self, config, checkpoint, metadata, new_versions):
        s = self._rec.enter("aput")
        try:
            await asyncio.sleep(self._work)   # the yield point
            return super().put(config, checkpoint, metadata, new_versions)
        finally:
            self._rec.leave("aput", s)

    async def aput_writes(self, config, writes, task_id, task_path=""):
        s = self._rec.enter("aput_writes")
        self._rec.note_write(config["configurable"].get("checkpoint_id"), task_id)
        try:
            await asyncio.sleep(self._work)
            return super().put_writes(config, writes, task_id, task_path)
        finally:
            self._rec.leave("aput_writes", s)


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


async def run_case(name, cls, durability):
    n_inter_trials = 0
    tot_depth = tot_calls = 0
    threads = set()
    c1_fail = c2_fail = 0
    for t in range(TRIALS):
        rec = Rec()
        saver = cls(rec)
        g = build(saver)
        out = await g.ainvoke({"steps": []},
                              {"configurable": {"thread_id": "%s-%d" % (name, t)}},
                              durability=durability)
        assert out["steps"] == ["A", "B"]
        methods = {m for (_, m, _) in rec.events}
        if not ({"aput", "aput_writes"} <= methods) and durability != "exit":
            c1_fail += 1
        worst = rec.max_tasks_per_ckpt()
        if worst is not None and worst > 1:
            c2_fail += 1
        if rec.interleavings:
            n_inter_trials += 1
        tot_depth += rec.max_depth
        tot_calls += sum(1 for e in rec.events if e[0] == "enter")
        threads |= rec.threads
    print("  %-14s %-6s | %-6.1f %-10.2f %-9d %-9s %s"
          % (name, durability, tot_calls / TRIALS, tot_depth / TRIALS,
             len(threads), "%d/%d" % (n_inter_trials, TRIALS),
             ("C1 fails=%d " % c1_fail if c1_fail else "C1 ok ") +
             ("C2 fails=%d" % c2_fail if c2_fail else "C2 ok")))
    sys.stdout.flush()
    return n_inter_trials


async def control_c3():
    """Detector must see 0 for atomic and >=1 for yielding, on hand-driven tasks."""
    rec = Rec()

    async def atomic():
        s = rec.enter("x")
        time.sleep(0.005)
        rec.leave("x", s)

    await asyncio.gather(*[atomic() for _ in range(4)])
    atomic_inter = rec.interleavings

    rec2 = Rec()

    async def yielding():
        s = rec2.enter("y")
        await asyncio.sleep(0.005)
        rec2.leave("y", s)

    await asyncio.gather(*[yielding() for _ in range(4)])
    return atomic_inter, rec2.interleavings


async def main():
    import importlib.metadata as md
    print("ASYNC path -- does a custom checkpointer INTERLEAVE on ainvoke?")
    print("  langgraph %s | trials %d | graph START -> A -> B -> END (sequential)"
          % (md.version("langgraph"), TRIALS))

    a_i, y_i = await control_c3()
    print("\n=== C3 DETECTOR CONTROL ===")
    print("  atomic bodies (no await)   : interleavings=%d -> %s"
          % (a_i, "PASS" if a_i == 0 else "FAIL"))
    print("  yielding bodies (await)    : interleavings=%d -> %s"
          % (y_i, "PASS" if y_i >= 1 else "FAIL"))
    if a_i != 0 or y_i < 1:
        print("  VOID -- detector failed its own control")
        return

    print("\n  %-14s %-6s | %-6s %-10s %-9s %-9s %s"
          % ("saver", "durab", "calls", "max_depth", "threads", "interlv", "note"))
    print("  " + "-" * 82)
    for dur in ("async", "sync"):
        for name, cls in (("Atomic(ours)", AtomicSaver), ("Awaiting(real)", AwaitingSaver)):
            await run_case(name, cls, dur)
        print()


if __name__ == "__main__":
    asyncio.run(main())
