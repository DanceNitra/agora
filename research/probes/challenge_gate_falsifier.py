"""Does walking the candidate list actually unwedge the challenge sweep?

I shipped the walk and said plainly that I had NOT verified end to end that the gate passes any
candidate. Building a cursor that advances through eight items the gate refuses one after another
would look exactly like a fix and change nothing. So: run the REAL gate, imported from the dungeon,
against the REAL candidates the brain now serves.

Two questions, and the second is the one that matters:
  1. Does the fix unwedge it -- does ANY candidate pass where the head did not?
  2. Is the gate over-rejecting -- what fraction of the on-mission belief pool does it refuse?

If (1) passes and (2) shows the gate refusing nearly everything, then Bounty/Court will fire once and
starve again, and the real defect is the gate's tokenizer, not the cursor.

Read-only. Imports the shipped gate; does not reimplement it.
"""
import asyncio
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\agora\agora-game-server")

BRAIN = "http://127.0.0.1:8000/api/v1/agent-os/brain/"


def get(path):
    with urllib.request.urlopen(BRAIN + path, timeout=40) as r:
        return json.load(r)


async def main():
    #: the SHIPPED gate, not a copy of it -- a reimplementation would test my understanding of the
    #: gate rather than the gate, which is the mistake the arXiv probe already made once today.
    from mcp_server import _gate_filter, _gate_refresh, _gate_cache, _theme_words

    d = get("belief-challenge-target")
    targets = d.get("targets") or []
    print(f"candidates served by the brain: {len(targets)}\n")

    await _gate_refresh()
    prio = _gate_cache.get("prio") or set()
    print(f"board priority tokens in the gate: {len(prio)}")
    print(f"   sample: {sorted(prio)[:12]}\n")

    passed = await _gate_filter([t["title"] for t in targets])
    passing = set(passed)

    print("PER-CANDIDATE VERDICT (the head is what the old code judged, alone):")
    for i, t in enumerate(targets):
        title = t["title"]
        ok = title in passing
        overlap = sorted(_theme_words(title) & prio)[:4]
        tag = "PASS" if ok else "drop"
        head = "  <- HEAD (all the old code ever saw)" if i == 0 else ""
        print(f"  [{tag}] {title[:58]}{head}")
        if ok:
            print(f"         matched on: {overlap}")

    print(f"\n1) UNWEDGED? {len(passing)}/{len(targets)} candidates pass the gate.")
    if targets and targets[0]["title"] not in passing and passing:
        print("   YES - the head is refused and a later candidate passes. Exactly the case that")
        print("   wedged the sweep for 42 days; the old code stopped at the head and queued nothing.")
    elif not passing:
        print("   NO - every candidate is refused. The cursor is not the defect; the gate is.")
    else:
        print("   INCONCLUSIVE - the head itself passes, so this run does not exercise the walk.")

    # 2) Is the gate over-rejecting the whole pool? Ask the brain for every challengeable belief.
    sys.path.insert(0, r"C:\Users\Danculus\agora\server")
    from agora.execution.belief_revision import list_beliefs
    alive = [b for b in list_beliefs("C:/Users/Danculus/my-second-brain")
             if b["belief_status"] in ("active", "survived")]
    ok_all = await _gate_filter([b["title"] for b in alive])
    n = len(alive)
    print(f"\n2) GATE ACCEPTANCE over the WHOLE live belief pool: {len(ok_all)}/{n} "
          f"({100 * len(ok_all) / max(n, 1):.0f}%)")
    if n and len(ok_all) / n < 0.15:
        print("   The gate refuses >85% of the canon. One fire, then starvation again.")
    else:
        print("   The gate leaves a real working set; the cursor was the binding constraint.")


asyncio.run(main())
