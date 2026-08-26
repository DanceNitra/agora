"""Re-run the drift/forgetting result from scratch, because its three lab receipts have rotated out.

WHY. `insight-optimal-forgetting-mis-read-as-miscalibration` claims that in a drifting world the
accuracy-maximising belief updater FORGETS, and that a stationary calibration audit then reads that
forgetting as conservatism. It cites three lab ids for a drift-rate sweep. None of the three
(`8cc533`, `56e5de`, `6d8e4f`) is in `.lab.json` any more, so by our own rule the numbers are
unbacked: a claim ships with a Lab baseline measured in the same cycle, or it does not ship.

Unlike the firewall note checked the same night, this one is re-derivable in seconds. It is a
simulation, not a measurement of anything in the world, so re-running IS the receipt. No model, no
network, stdlib only.

THE MODEL, exactly as the note describes it:
  a binary hidden state that flips with probability `flip_p` each step; an observation that matches
  the state with probability `obs_acc`; a scalar leaky log-odds updater `b <- lambda*b + evidence`,
  where evidence is +/- log(a/(1-a)). lambda = 1 is the leak-free Bayesian.

TWO MEASUREMENTS, which are different questions and the whole point:
  DRIFT ACCURACY  - does sign(b) match the CURRENT state, live, as the world flips.
  AUDIT GAP       - mean(confidence) - mean(correct) over blocks where the state is HELD FIXED.
                    This is the stationary audit. A negative gap reads as "underconfident".

WHAT THE NOTE PREDICTS, pre-registered here before the run so the comparison is honest:
  * leak-free accuracy sits near chance (0.50-0.52) at every drift rate
  * the optimal lambda is below 1, and falls as drift gets faster
  * the audit gap at the optimal lambda is MORE NEGATIVE than at leak-free
  * the accuracy gain from forgetting is large (the note reports +0.23 to +0.44)

The note's own falsifier, kept: the claim dies if the audit gap at lambda* is about equal to
leak-free, or if the drift gain is under 0.05.

SEEDED, and the seed is reported, because a spread across seeds is the thing a single run hides.
"""
from __future__ import annotations

import io
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OBS_ACC = 0.75
STEPS = 60_000
BLOCK = 200                     # the stationary audit holds the state fixed for a block
LAMBDAS = [round(1.0 - 0.02 * i, 2) for i in range(0, 16)]   # 1.00 down to 0.70
DRIFTS = [0.005, 0.02, 0.08]
SEEDS = [11, 12, 13]


def drift_run(flip_p: float, lam: float, seed: int) -> float:
    """Accuracy against the CURRENT state in a world that keeps moving."""
    rng = random.Random(seed)
    ev = math.log(OBS_ACC / (1 - OBS_ACC))
    state, b, correct = 1, 0.0, 0
    for _ in range(STEPS):
        if rng.random() < flip_p:
            state = 1 - state
        obs = state if rng.random() < OBS_ACC else 1 - state
        b = lam * b + (ev if obs == 1 else -ev)
        correct += ((1 if b > 0 else 0) == state)
    return correct / STEPS


def audit_run(lam: float, seed: int) -> float:
    """The stationary audit: the world does NOT move. Confidence minus accuracy.

    TWO IMPLEMENTATION ERRORS LIVE HERE, both mine, both from trying to do this in the same pass as
    the drift measurement. The first pinned only a LABEL while the world kept flipping underneath
    it, which scores predictions against a stale target and turned every gap positive. The second
    suppressed flips using a window that was always open, so the world never moved at all and every
    cell went to a triumphant 1.000. Drift and audit are different worlds and need different runs.

    Belief is reset per block, so the audit measures calibration within a stationary stretch rather
    than the residue of a drift the audit claims not to have.
    """
    rng = random.Random(seed + 7919)
    ev = math.log(OBS_ACC / (1 - OBS_ACC))
    conf_sum, corr, n = 0.0, 0, 0
    for _ in range(STEPS // BLOCK):
        state = rng.randint(0, 1)
        b = 0.0
        for _ in range(BLOCK):
            obs = state if rng.random() < OBS_ACC else 1 - state
            b = lam * b + (ev if obs == 1 else -ev)
            pred = 1 if b > 0 else 0
            conf_sum += 1.0 / (1.0 + math.exp(-abs(b)))
            corr += (pred == state)
            n += 1
    return (conf_sum / n) - (corr / n)


def main() -> int:
    print(f"  {STEPS:,} steps, obs accuracy {OBS_ACC}, audit block {BLOCK}, seeds {SEEDS}")
    print(f"  lambda swept {LAMBDAS[0]} down to {LAMBDAS[-1]}\n")
    rows, v = [], {}
    for flip_p in DRIFTS:
        best = None
        table = {}
        for lam in LAMBDAS:
            accs = [drift_run(flip_p, lam, sd) for sd in SEEDS]
            gaps = [audit_run(lam, sd) for sd in SEEDS]
            acc, gap = sum(accs) / len(accs), sum(gaps) / len(gaps)
            spread = max(accs) - min(accs)
            table[lam] = (acc, gap, spread)
            if best is None or acc > table[best][0]:
                best = lam
        leak_acc, leak_gap, _ = table[1.0]
        b_acc, b_gap, b_spread = table[best]
        rows.append({"flip_p": flip_p, "lambda_star": best,
                     "acc_leakfree": round(leak_acc, 3), "acc_lambda_star": round(b_acc, 3),
                     "acc_gain": round(b_acc - leak_acc, 3),
                     "audit_gap_leakfree": round(leak_gap, 3),
                     "audit_gap_lambda_star": round(b_gap, 3),
                     "acc_spread_across_seeds": round(b_spread, 4)})
        print(f"  flip_p {flip_p:<6} lambda* {best:<5} "
              f"acc {leak_acc:.3f} -> {b_acc:.3f} (+{b_acc - leak_acc:.3f})   "
              f"audit gap {b_gap:+.3f} vs leak-free {leak_gap:+.3f}")

    # --- the note's own pre-committed falsifier, applied to THIS run --------------------------
    v["leak_free_sits_near_chance_everywhere"] = all(
        0.48 <= r["acc_leakfree"] <= 0.54 for r in rows)
    v["the_optimal_lambda_is_below_one_everywhere"] = all(r["lambda_star"] < 1.0 for r in rows)
    v["forgetting_buys_real_accuracy_gain_over_0.05"] = all(r["acc_gain"] > 0.05 for r in rows)
    v["the_audit_reads_the_forgetter_as_MORE_conservative"] = all(
        r["audit_gap_lambda_star"] < r["audit_gap_leakfree"] for r in rows)
    v["faster_drift_means_more_forgetting"] = (
        rows[-1]["lambda_star"] <= rows[0]["lambda_star"])
    # --- controls ------------------------------------------------------------------------------
    # The sweep must be able to return lambda = 1. If 1.0 is not a candidate the "below one" result
    # is a property of the grid rather than of the world.
    v["CONTROL_leak_free_was_a_candidate"] = 1.0 in LAMBDAS
    # And the accuracy differences must exceed the seed spread, or the sweep is picking noise.
    v["CONTROL_the_gain_exceeds_the_seed_spread"] = all(
        r["acc_gain"] > 10 * max(r["acc_spread_across_seeds"], 1e-4) for r in rows)

    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")

    json.dump({"probe": os.path.basename(__file__), "verdicts": v, "rows": rows,
               "params": {"steps": STEPS, "obs_acc": OBS_ACC, "audit_block": BLOCK,
                          "seeds": SEEDS, "lambdas": LAMBDAS},
               "why": "the note's three lab ids (8cc533, 56e5de, 6d8e4f) have rotated out of "
                      ".lab.json, so this re-derives the result in the current cycle",
               "scope": "a toy 2-state drift world. It isolates a mechanism and is not a "
                        "calibrated number for any real system."},
              io.open(os.path.join(HERE, "optimal_forgetting_reads_as_miscalibration.result.json"),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
