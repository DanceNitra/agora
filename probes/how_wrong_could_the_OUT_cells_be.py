"""What is the chance an OUT 3/3 is three false negatives? Computed from our own measured flap rate.

WHY THIS EXISTS. The CR finding rests on ONE cell: the CRLF arm's line 125, OUT 3/3. And the same
run contains a demonstrated false negative -- the LF arm's line 124 came back IN, OUT, IN on a
needle that is certainly inside the cap, because line 125 above it read 3/3. @pjt222 saw the same
mode and named it as the one thing in this design that can make a boundary look tighter than it is.

So "OUT 3/3" is not free, and the honest question is how often three trials can all miss. That is
answerable from the run itself rather than assumed: every trial on a needle KNOWN to be inside the
cap is a Bernoulli draw on the instrument's false-negative rate.

The estimate is 1 in 15, which sounds decisive and is not, because 15 trials with one event carry a
very wide interval. Reporting p^3 from the point estimate would be the same error as reporting a
spread from a mean. Both are printed, and the WILSON UPPER BOUND is the one a claim rests on.

WHAT THIS DOES NOT DO. It bounds flakiness, not systematic error. If the instrument were wrong in a
way that fires on every trial of a particular cell, no number of trials would see it, and this
computes nothing about that. It also treats trials as independent, which three sequential sessions
against an identical fixture approximately are and not exactly.

stdlib only. Reads the two committed artifacts; runs no session.
"""
from __future__ import annotations

import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = {
    "LF": os.path.join(HERE, "the_cap_on_windows_and_what_a_crlf_line_costs.lf.result.json"),
    "CRLF": os.path.join(HERE, "the_cap_on_windows_and_what_a_crlf_line_costs.crlf.result.json"),
}
# The one cell the CR claim rests on, named here so the number below is about it and not about
# "the run" in general.
LOAD_BEARING = ("CRLF", "125")


def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def load(path: str) -> dict:
    if not os.path.exists(path):
        raise SystemExit(f"REFUSED: {path} is absent; there is nothing to bound")
    return json.load(io.open(path, encoding="utf-8"))


def main() -> int:
    trials_in = fn = 0
    out_cells = []
    detail = []
    for lab, path in ARMS.items():
        d = load(path)
        pos = {k: v["digits_end"] for k, v in d["needles"].items()}
        sc = {k: tuple(v) for k, v in d["scores"].items()}
        # A needle is KNOWN to be inside the cap if some needle at a HIGHER position read in every
        # trial. That is the only inference absence-is-not-evidence permits, and it is why the
        # highest IN cell itself contributes to the denominator but nothing above it does.
        top = max((pos[k] for k, (n, t) in sc.items() if k in pos and n == t), default=None)
        for k, p_ in sorted(pos.items(), key=lambda x: x[1]):
            n, t = sc[k]
            if top is not None and p_ <= top:
                trials_in += t
                fn += t - n
                detail.append((lab, k, p_, n, t, "known IN"))
            elif n == 0:
                out_cells.append((lab, k, p_))
                detail.append((lab, k, p_, n, t, "OUT"))

    for lab, k, p_, n, t, role in detail:
        flag = "   <- FLAP" if role == "known IN" and n < t else ""
        print(f"  {lab:<4} line {k:>3}  ends {p_:>6}  {n}/{t}  {role}{flag}")

    lo, hi = wilson(fn, trials_in)
    p_hat = fn / trials_in if trials_in else 0.0
    print(f"\n  false negatives on needles KNOWN to be inside the cap: {fn} of {trials_in}")
    print(f"  per-trial rate {p_hat:.4f}, Wilson 95% [{lo:.4f}, {hi:.4f}]")

    rows = []
    for label, p in (("point estimate", p_hat), ("Wilson 95% UPPER", hi)):
        one = p ** 3
        fam = 1 - (1 - one) ** len(out_cells) if out_cells else 0.0
        rows.append({"basis": label, "p": p, "p_cubed": one, "family_wise": fam})
        print(f"\n  at p = {p:.4f} ({label})")
        print(f"    one OUT 3/3 is three false negatives : {one:.4f}"
              + (f"   ({1 / one:.0f}-to-1 against)" if one else ""))
        print(f"    ANY of the {len(out_cells)} OUT cells is        : {fam:.4f}")

    v = {}
    v["there_is_at_least_one_known_IN_needle_per_arm"] = trials_in >= 6
    v["the_flap_is_real_and_counted"] = fn >= 1
    v["the_load_bearing_cell_is_an_OUT_cell"] = LOAD_BEARING in [(a, k) for a, k, _ in out_cells]
    # CONTROL: if every trial had succeeded, this file would print a zero and mean nothing. Assert
    # the estimator can move -- a bound derived from fn=0 is not a bound, it is an absence.
    v["CONTROL_the_estimate_is_not_vacuous"] = 0 < p_hat < 1
    v["CONTROL_the_upper_bound_is_looser_than_the_point"] = hi > p_hat
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")

    print(f"\n  THE NUMBER A CLAIM ABOUT {LOAD_BEARING[0]} LINE {LOAD_BEARING[1]} RESTS ON:")
    print(f"    worst case consistent with our own data, {hi ** 3:.4f}"
          f"  ({1 / hi ** 3:.0f}-to-1 against) -- and that cell is PAIRED with the LF arm's line")
    print("    125 reading IN 3/3 at the position it would occupy if the CR were stripped, so the")
    print("    finding does not rest on an absence alone.")

    out = os.path.join(HERE, "how_wrong_could_the_OUT_cells_be.result.json")
    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "trials_on_known_IN_needles": trials_in, "false_negatives": fn,
               "p_hat": p_hat, "wilson95": [lo, hi], "out_cells": out_cells,
               "risk": rows, "load_bearing_cell": list(LOAD_BEARING),
               "load_bearing_worst_case": hi ** 3},
              io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nwrote {out}")
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
