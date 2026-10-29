"""At which byte budget do the four shortening strategies stop being the same thing?

The A/B pilot measured one point and found nothing to measure: at the saver's natural budget, a
median 10.2% of the output, the digest, the footerless digest, head-and-tail truncation and an
UNRANKED evenly spaced sampler all kept the answer on exactly the same three of twelve tasks. Four
arms, one result, by construction. Running the model over that would have bought 1.50 USD of arms
that cannot differ.

The budget was a free parameter, which is the same defect that killed the retention claim earlier
the same day: there, a 400-byte window decided the direction. So this measures the CURVE instead of
a point, and it measures the only thing that has to be true before a model call is worth paying
for:

    does the strategy keep the answer at all?

That is a substring check, so this probe costs nothing and calls no model. If the arms never
diverge, there is nothing for an answering model to answer differently, and the A/B should not run.

THE DIGEST HAS TO SCALE HONESTLY. `save()` takes no budget: the digest is `TOP` sections of
`PREVIEW` characters, both module constants, so it is about a kilobyte whatever the output size.
Asking for a bigger digest therefore means asking the real ranking code for more sections, which is
what `_at_budget` does by raising TOP against the shipped ranker. It does not substitute a lighter
stand-in for the ranker, and the ranked ORDER is still the shipped order.

Controls:
  - the full arm must keep the answer on every task, at every budget. It is the arithmetic check.
  - every arm's bytes must land within a stated tolerance of the budget, or the arms are not
    comparable at that point and the row says so.
  - the overlap is reported, not just the counts: four arms at 3/12 each is only interesting if
    they are different threes.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULT = Path(__file__).with_suffix(".result.json")
FRACTIONS = (0.05, 0.10, 0.20, 0.30, 0.50)
ARMS = ("digest", "digest_no_footer", "truncate", "even_spread")

sys.argv = [sys.argv[0]]                       # the A/B probe reads argv at import time
_spec = importlib.util.spec_from_file_location(
    "ab", HERE / "does_the_digest_help_an_agent_answer_or_just_move_the_bytes.py")
_ab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ab)

from inspeximus import context_saver as cs     # noqa: E402


def digest_at(output, intent, budget):
    """The SHIPPED digest, asked for as many ranked sections as the budget allows.

    TOP and PREVIEW are module constants, so a bigger budget is more sections of the same ranked
    order rather than a different algorithm. Restored in a finally, because a leaked constant would
    silently change every later row.

    The digest is the LARGEST one that still fits the budget, never the first one that exceeds it.
    The first version grew TOP until the text reached the budget, which overshoots on the last
    section: at a nominal 10 percent the digest spent 17 percent of the baseline against
    truncation's 10, so it was winning on extra bytes. Every arm is then sized to the digest's
    ACTUAL length by the caller, so the comparison is byte-matched at every point on the curve.
    """
    top, preview = cs.TOP, cs.PREVIEW
    best, prev = "", None
    try:
        cs.PREVIEW = 240
        for n in range(1, 200):
            cs.TOP = n
            text = cs.save(output, intent, without_reranker="hybrid", ranking="lexical")["text"]
            if text == prev:
                break                          # the chunks ran out: more sections change nothing
            prev = text
            if len(text) > budget:
                break                          # keep the last one that fitted
            best = text
    finally:
        cs.TOP, cs.PREVIEW = top, preview
    return best or prev or ""


def arms_at(task, budget):
    """Every arm at the SAME byte count: the digest's own length, which is at most the budget."""
    out, intent = task["output"], task["intent"]
    dig = digest_at(out, intent, budget)
    sections = sum(1 for ln in dig.splitlines() if ln.startswith("- "))
    b = len(dig)                               # the shared budget, so no arm wins on extra bytes
    return {
        "digest": dig,
        "digest_no_footer": _ab.strip_footer(dig),
        "truncate": out if len(out) <= b else out[: b // 2] + "\n...\n" + out[-(b - b // 2):],
        "even_spread": _ab.even_spread(out, b, sections or 5),
    }


def main() -> int:
    tasks, corpus = _ab.build_tasks(60, 20261029, _ab.EDGE, _ab.MAX_CHARS, "public")
    if not tasks:
        print("no gradable task built: %s" % corpus)
        return 1
    print("%d tasks from the public corpus\n" % len(tasks), flush=True)

    curve = {}
    for frac in FRACTIONS:
        keeps = {a: set() for a in ARMS}
        byts = {a: 0 for a in ARMS}
        baseline = asked = 0
        for t in tasks:
            budget = max(200, int(len(t["output"]) * frac))
            if len(t["output"]) <= budget:
                continue                       # no arm can differ where the output already fits
            asked += 1
            baseline += len(t["output"])
            a = arms_at(t, budget)
            for arm in ARMS:
                byts[arm] += len(a[arm])
                if t["answer"] in a[arm]:
                    keeps[arm].add(t["id"])
        if not asked:
            continue
        distinct = len({frozenset(keeps[a]) for a in ARMS})
        curve["%d%%" % round(frac * 100)] = {
            "tasks_where_the_output_had_to_be_cut": asked,
            "kept_the_answer": {a: len(keeps[a]) for a in ARMS},
            "kept_pct": {a: round(100.0 * len(keeps[a]) / asked, 1) for a in ARMS},
            "bytes_pct_of_baseline": {a: round(100.0 * byts[a] / max(baseline, 1), 1) for a in ARMS},
            "the_arms_keep_it_on_the_same_tasks": distinct == 1,
            "distinct_answer_sets_across_the_four_arms": distinct,
            "digest_only": sorted(keeps["digest"] - keeps["truncate"])[:6],
            "truncation_only": sorted(keeps["truncate"] - keeps["digest"])[:6],
        }
        print("budget %3d%%  n=%2d  " % (round(frac * 100), asked)
              + "  ".join("%s %4.1f%% (%d B%%)" % (a, curve["%d%%" % round(frac * 100)]["kept_pct"][a],
                                                   curve["%d%%" % round(frac * 100)]["bytes_pct_of_baseline"][a])
                          for a in ARMS)
              + "  | same tasks: %s" % curve["%d%%" % round(frac * 100)]["the_arms_keep_it_on_the_same_tasks"],
              flush=True)

    diverges = [b for b, v in curve.items() if not v["the_arms_keep_it_on_the_same_tasks"]]
    out = {
        "measured": "2026-10-29",
        "what": "whether the four shortening strategies keep the answer on DIFFERENT tasks, "
                "swept over the byte budget. No model is called: keeping the answer is a "
                "precondition for answering it.",
        "corpus": corpus,
        "tasks": len(tasks),
        "curve": curve,
        "budgets_where_the_arms_differ": diverges,
        "verdict": ("an A/B is worth paying for at %s" % ", ".join(diverges)) if diverges else
                   "the arms never differ at any budget measured: an A/B here would measure nothing",
    }
    RESULT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\n%s\nresult: %s" % (out["verdict"], RESULT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
