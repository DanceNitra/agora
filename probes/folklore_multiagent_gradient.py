"""Folklore assay #4: "multi-agent beats single-agent at fixed cost" -- across a capability gradient.

THE CLAIM. The field's folklore is that running several agents and combining them beats one agent.
The contrarian version, and the only one worth measuring, holds COST FIXED: three chains of budget B
against one chain of budget 3B. Anything that does not hold cost fixed is measuring the budget.

PRIOR ART, STATED UP FRONT BECAUSE THE BAR HERE FORBIDS RE-DERIVATION. Self-consistency (Wang et al.,
ICLR 2023) established that sampling several chains and majority-voting beats one chain. "More agents
is all you need" (Li et al., 2024) scaled that. Sequential-versus-parallel test-time compute at a
fixed budget is studied too (Snell et al., 2024). So the parallel-vs-sequential question is NOT ours
and we do not claim it.

WHAT IS OURS is the axis the positioning document names: does the advantage SHRINK AS THE MODEL GETS
MORE CAPABLE? A mechanism that helps a 7B and stops helping a 30B is a weak-model crutch, and the
field keeps citing the 7B result. That gradient is the measurement; the within-tier comparison is
just the instrument.

DESIGN
  task        multi-step arithmetic word problems generated with known integer answers. Judge-free:
              scoring is exact match on an integer, so no LLM sits in the loop and no rubric drifts.
  conditions  SINGLE  -- one call, max_tokens = 3B
              VOTE    -- three independent calls at max_tokens = B, majority vote on the parsed answer
              Both spend the same generation budget. That is the whole point.
  unit        per-item advantage = correct(VOTE) - correct(SINGLE), in {-1, 0, +1}. Items are the
              sample, so the CI is over items and the two conditions see identical problems.
  tiers       cheap (qwen2.5:7b) -> main (llama3.1:8b) -> reasoning (qwen3:30b-a3b)

BUDGETS ARE PER-TIER ON PURPOSE. qwen3:30b spends its allowance on thinking and emits no content at
all under a tight cap -- a documented failure here, not a guess -- so it gets a far larger B. This is
sound because the advantage is computed WITHIN a tier: we compare advantages across tiers, never raw
accuracies, so a per-tier budget difference cannot leak into the gradient.

THE HONEST LIMIT, WHICH MUST TRAVEL WITH ANY VERDICT. There is no frontier anchor on this box. Three
local rungs measure the SLOPE of the advantage across 7B-30B; they cannot license a claim about a
frontier model. If the advantage is already gone by 30B that is suggestive and no more, and the
verdict must say so rather than borrow the word "frontier".

CONTROLS. Two, both able to fail:
  * a PARSE-RATE report per tier and condition -- if SINGLE's long generations fail to parse more
    often than VOTE's short ones, any advantage is a formatting artifact and not reasoning, and the
    run says so instead of scoring it.
  * a DEGENERATE-VOTE counter -- if the three voters agree unanimously on nearly every item, the vote
    is not combining anything and the comparison is one chain against one chain with extra steps.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from collections import Counter

_SERVER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server")
sys.path.insert(0, _SERVER)

# LOAD server/.env BEFORE importing the client. `agora.main` does this at import time, so anything
# started from server/ inherits it -- and anything started from the repo root does NOT. Skipping it
# silently swaps every tier for the code's built-in cloud default, which then fails on missing
# credentials while the run still prints a full table of zeros. That is the documented failure that
# produced "all three LLM tiers are dead" here once, and it produced it again on the first launch of
# this very file. The loader is four lines; the mistake costs a whole run and looks like data.
def _load_env(path=os.path.join(_SERVER, ".env")):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except OSError:
        print("WARNING: could not read %s -- tiers will use built-in defaults" % path)


_load_env()
from agora.execution.llm_client import call_llm  # noqa: E402

N_ITEMS = int(os.environ.get("FOLKLORE_N", "15"))
SEED = 20260801
TIERS = [("cheap", 250), ("main", 250), ("reasoning", 2500)]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agora_output",
                   "lab", "folklore_multiagent_gradient.json")

SYSTEM = ("You solve arithmetic word problems. Work briefly, then end your reply with the final "
          "answer on its own last line in exactly this form: ANSWER: <integer>")


def make_items(n, seed=SEED, level=None):
    """Deterministic multi-step problems with computed ground truth. No dataset, no contamination.

    `level` sets difficulty, and it must be CALIBRATED rather than guessed. Level 1 was the original
    and it put the 7B rung at 1.000 against 1.000 -- both conditions at the ceiling, where no
    difference can appear no matter how well or badly the mechanism works. An assay whose task has no
    headroom cannot answer its own question, so `calibrate` below measures accuracy per level and
    picks one with room on both sides before any gradient is spent.

    Every answer is COMPUTED from the drawn numbers, never written into the prompt, and the
    arithmetic stays exact -- no percentages, no rounding, so there is exactly one defensible answer.
    """
    level = level if level is not None else int(os.environ.get("FOLKLORE_LEVEL", "3"))
    rng = random.Random(seed + 1000 * level)
    items = []
    while len(items) < n:
        if level == 1:
            a, b = rng.randint(12, 40), rng.randint(3, 9)
            c, d, e = rng.randint(5, 25), rng.randint(2, 6), rng.randint(7, 30)
            ans = (a * b) - (d * b) + c - e
            q = (f"A warehouse receives {a} crates holding {b} widgets each. {d} of those crates are "
                 f"damaged and discarded with all their widgets. Later {c} loose widgets arrive, and "
                 f"{e} widgets are sold. How many widgets remain?")
        elif level == 2:
            a, b = rng.randint(140, 460), rng.randint(7, 19)
            c, d, e = rng.randint(200, 900), rng.randint(3, 11), rng.randint(60, 380)
            ans = (a * b) - (d * b) + c - e
            q = (f"A depot receives {a} crates holding {b} widgets each. {d} of those crates are "
                 f"damaged and discarded with all their widgets. Later {c} loose widgets arrive, and "
                 f"{e} widgets are sold. How many widgets remain?")
        else:
            a, b = rng.randint(140, 460), rng.randint(7, 19)
            c, d, e = rng.randint(200, 900), rng.randint(3, 11), rng.randint(60, 380)
            g, h = rng.randint(4, 9), rng.randint(11, 29)
            # one more chained stage: the remainder is split into g equal shipments, h of which are
            # returned intact. Exact integer division is forced by construction, not by rounding.
            base = (a * b) - (d * b) + c - e
            per = base // g
            ans = base - (per * g) + (per * 1) + h
            q = (f"A depot receives {a} crates holding {b} widgets each. {d} of those crates are "
                 f"damaged and discarded with all their widgets. Later {c} loose widgets arrive, and "
                 f"{e} widgets are sold. The remaining widgets are divided as evenly as possible into "
                 f"{g} shipments, and any widgets that do not fit evenly are kept at the depot. One "
                 f"whole shipment is then returned to the depot, and {h} more widgets arrive. How many "
                 f"widgets are at the depot?")
        if ans <= 0:
            continue
        items.append({"q": q, "answer": ans, "level": level})
    return items


def calibrate(levels=(1, 2, 3), n=8, tier="cheap"):
    """Measure accuracy per difficulty level so the gradient is spent on a task with headroom.

    Prints accuracy and picks the level closest to 0.55 among those inside [0.15, 0.85]. A level
    outside that band is rejected: at the ceiling or the floor the two conditions cannot differ, so
    the assay would return a confident null that is really a statement about the task.
    """
    print("CALIBRATION -- accuracy by difficulty on the %s rung (%d items each)" % (tier, n))
    scored = []
    for lv in levels:
        items = make_items(n, level=lv)
        ok = 0
        for it in items:
            ans = parse(ask(tier, it["q"], 750, 0.0))
            ok += 1 if ans == it["answer"] else 0
        acc = ok / n
        usable = 0.15 <= acc <= 0.85
        scored.append((lv, acc, usable))
        print("  level %d: accuracy %.3f  %s" % (lv, acc, "usable" if usable else "NO HEADROOM"))
    usable = [(lv, acc) for lv, acc, u in scored if u]
    if not usable:
        print("\nNo level has headroom on this rung. Widen the generator before spending a gradient.")
        return None
    best = min(usable, key=lambda t: abs(t[1] - 0.55))
    print("\nchosen level %d (accuracy %.3f)" % best)
    return best[0]


ANS_RE = re.compile(r"ANSWER:\s*(-?\d[\d,]*)", re.I)


def parse(text):
    """Return the integer answer, or None. None is a PARSE FAILURE and is counted, never scored as wrong."""
    if not text:
        return None
    m = ANS_RE.findall(text)
    if not m:
        m = re.findall(r"(-?\d[\d,]*)", text)
        if not m:
            return None
    try:
        return int(m[-1].replace(",", ""))
    except ValueError:
        return None


def ask(tier, q, max_tokens, temperature):
    try:
        return call_llm(SYSTEM, q, tier, temperature, max_tokens)
    except Exception as exc:  # a dead tier must not be scored as a wrong answer
        return "__ERROR__ %s" % exc


def run_tier(tier, budget, items):
    single_ok, vote_ok, adv = [], [], []
    parse_fail = {"single": 0, "vote": 0}
    unanimous = 0
    t0 = time.time()
    for i, it in enumerate(items):
        # SINGLE: one chain, triple budget, greedy.
        s_raw = ask(tier, it["q"], budget * 3, 0.0)
        s_ans = parse(s_raw)
        if s_ans is None:
            parse_fail["single"] += 1
        s_correct = 1 if s_ans == it["answer"] else 0

        # VOTE: three chains at budget B. Temperature > 0 or the three chains are one chain.
        votes = []
        for k in range(3):
            v_raw = ask(tier, it["q"], budget, 0.7)
            v_ans = parse(v_raw)
            if v_ans is None:
                parse_fail["vote"] += 1
            else:
                votes.append(v_ans)
        if votes:
            top, count = Counter(votes).most_common(1)[0]
            if count == 3:
                unanimous += 1
            v_correct = 1 if top == it["answer"] else 0
        else:
            v_correct = 0

        single_ok.append(s_correct)
        vote_ok.append(v_correct)
        adv.append(v_correct - s_correct)
        print("  [%s] item %2d/%d  single=%d vote=%d  adv=%+d  (%.0fs)"
              % (tier, i + 1, len(items), s_correct, v_correct, adv[-1], time.time() - t0), flush=True)

    n = len(items)
    # ABSOLUTE failure control, not a relative one. The two original controls compared parse failures
    # between SINGLE and VOTE, so a run where EVERYTHING failed cancelled to zero difference and was
    # reported as a clean null. This one looks at the failure rate itself, which a total failure
    # cannot hide from.
    total_calls = n * 4
    total_fail = parse_fail["single"] + parse_fail["vote"]
    s_acc, v_acc = sum(single_ok) / n, sum(vote_ok) / n

    # CEILING / FLOOR CONTROL. If both conditions sit at the top or the bottom of the scale there is
    # no headroom for a difference to appear in, so a +0.000 advantage says the TASK could not
    # discriminate -- it says nothing about the mechanism. The first run of this file hit exactly
    # that: single 1.000, vote 1.000 on the 7B rung, which reads like a clean null and is not one.
    # Without this the harness would hand classify() a saturated column and get back a confident
    # INCONCLUSIVE for the wrong reason.
    saturated = (s_acc >= 0.95 and v_acc >= 0.95) or (s_acc <= 0.05 and v_acc <= 0.05)
    valid = total_fail < 0.5 * total_calls and not saturated
    return {
        "tier": tier, "budget_per_chain": budget, "n_items": n,
        "valid": valid,
        "saturated": saturated,
        "parse_fail_rate": round(total_fail / total_calls, 4),
        "single_acc": round(sum(single_ok) / n, 4),
        "vote_acc": round(sum(vote_ok) / n, 4),
        "advantage_mean": round(sum(adv) / n, 4),
        "advantage_samples": adv,
        "parse_failures": parse_fail,
        "unanimous_votes": unanimous,
        "degenerate_vote": unanimous >= 0.9 * n,
        "seconds": round(time.time() - t0, 1),
    }


def preflight():
    """Refuse to run unless every tier ANSWERS CORRECTLY. Aborts; it does not warn.

    The first launch of this file produced a complete, well-formatted results table of zeros because
    every call had failed on missing credentials, and not one of the in-run controls fired -- both of
    them compared parse failures BETWEEN conditions, so a total failure cancelled out and read as
    agreement. A harness that cannot tell "the mechanism does nothing" from "nothing ran" has measured
    nothing, and it is worse than a crash because it writes a plausible file.

    Each tier gets a DIFFERENT arithmetic question, because a 0.0-second reply to a repeated prompt is
    a cache hit and proves only that the cache is alive. The ANSWER is checked, not the liveness.
    """
    print("PRE-FLIGHT -- every tier must answer a unique question correctly, or nothing runs")
    ok = True
    for idx, (tier, _budget) in enumerate(TIERS):
        a, b = 37 + idx * 11, 8 + idx * 3
        t0 = time.time()
        raw = ask(tier, "A bin holds %d bolts. %d more are added. How many bolts are in the bin?" % (a, b),
                  4000 if tier == "reasoning" else 400, 0.0)
        got, want, dt = parse(raw), a + b, time.time() - t0
        good = got == want
        ok = ok and good
        print("  %-10s %5.1fs  expected %4d  got %-6s  %s"
              % (tier, dt, want, got, "ok" if good else "FAIL: " + str(raw)[:110].replace("\n", " ")))
    if not ok:
        print("\nABORTED: a tier did not answer correctly. Fix the tier before spending a run; a table "
              "of zeros from a dead tier is indistinguishable from a real null.")
        sys.exit(1)
    print("  all tiers answer correctly\n")


def main():
    items = make_items(N_ITEMS)
    print("folklore assay #4 -- multi-agent vs single at FIXED COST, across a capability gradient")
    print("%d generated items, exact-match on an integer, judge-free\n" % len(items))
    preflight()
    results = []
    for tier, budget in TIERS:
        print("tier %s (B=%d per chain; SINGLE gets %d)" % (tier, budget, budget * 3), flush=True)
        results.append(run_tier(tier, budget, items))
        r = results[-1]
        print("  -> single %.3f  vote %.3f  advantage %+.3f  parse_fail %s  unanimous %d/%d  %.0fs\n"
              % (r["single_acc"], r["vote_acc"], r["advantage_mean"], r["parse_failures"],
                 r["unanimous_votes"], r["n_items"], r["seconds"]), flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(os.path.normpath(OUT), "w", encoding="utf-8") as fh:
        json.dump({"items": items, "results": results, "seed": SEED,
                   "note": "No frontier anchor: three local rungs measure the SLOPE only."}, fh, indent=1)

    print("=" * 78)
    print("%-12s %10s %8s %10s %12s %10s" % ("tier", "single", "vote", "advantage", "parse_fail", "unanim"))
    for r in results:
        print("%-12s %10.3f %8.3f %+10.3f %12s %8d/%d"
              % (r["tier"], r["single_acc"], r["vote_acc"], r["advantage_mean"],
                 r["parse_failures"], r["unanimous_votes"], r["n_items"]))
    invalid = [r for r in results if not r["valid"]]
    if invalid:
        print("\nCONTROL TRIPPED -- NO MEASUREMENT.")
        for r in invalid:
            if r.get("saturated"):
                print("  %s: single %.3f / vote %.3f -- both conditions are at the ceiling or the "
                      "floor, so the task has no headroom for a difference. This is a statement about "
                      "the TASK, not about the mechanism." % (r["tier"], r["single_acc"], r["vote_acc"]))
            else:
                print("  %s: %.0f%% of calls failed to parse -- a dead-tier run, not a null."
                      % (r["tier"], 100 * r["parse_fail_rate"]))
        print("\nNothing here may be fed to classify(), and the pre-registration must NOT be resolved "
              "against it: scoring a forecast on an experiment that could not discriminate scores the "
              "forecaster on our task design.")
        sys.exit(2)

    print("\nMEASURED: advantage by tier = %s"
          % ", ".join("%s %+0.3f" % (r["tier"], r["advantage_mean"]) for r in results))
    for r in results:
        if r["degenerate_vote"]:
            print("CONTROL TRIPPED: %s vote was unanimous on %d/%d items -- it is not combining anything"
                  % (r["tier"], r["unanimous_votes"], r["n_items"]))
        if r["parse_failures"]["single"] > r["parse_failures"]["vote"] + 2:
            print("CONTROL TRIPPED: %s SINGLE failed to parse %d times vs VOTE %d -- any advantage here "
                  "is a formatting artifact" % (r["tier"], r["parse_failures"]["single"],
                                                r["parse_failures"]["vote"]))
    print("\nVerdict is NOT written here. Feed advantage_samples to folklore.classify().")
    print("written -> %s" % os.path.normpath(OUT))


if __name__ == "__main__":
    main()
