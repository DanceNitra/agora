#!/usr/bin/env python3
"""
ensemble_calibrator.py — should you AGGREGATE your reasoners, or trust the single best?

WHY
    Adding more reasoners (LLM samples, models, voters, experts) does NOT always help. There is a
    boundary in the (individual competence x error-correlation) plane: above it, majority vote beats the
    best single reasoner (Condorcet / wisdom of crowds); BELOW it, the reasoners share a misleading cue
    (a common bias, a popular wrong anchor, herding) and the majority LOCKS ONTO that correlated error —
    so the crowd votes WORSE than its average member, and adding reasoners does not close the gap (the
    'redundancy trap'). Measured: that amplification region is ~53% of the plane when the shared cue is
    misleading; the safe-aggregation threshold RISES with error-correlation; confidence-weighting does
    not rescue it. (Agora capstone: the Collective Intelligence Phase Diagram.)

WHAT THIS DOES
    PRIMARY (model-free): give it your reasoners' answers on a set of items with KNOWN answers; it
    measures each reasoner's accuracy (competence), the inter-reasoner error correlation, and whether
    majority vote actually beats the average / best single reasoner on YOUR data — then recommends
    AGGREGATE or DON'T, with the reason. This decision is read straight from your data; no model assumed.
    FALLBACK (summary-only): if you only have (avg competence, error-correlation), it estimates which
    side of the measured boundary you are on. Clearly an estimate — prefer the data-driven path.

ZERO dependencies (stdlib only). The --demo phase-diagram uses numpy if available, else is skipped.

USAGE
    # data-driven (the real decision): a JSON file {"votes": [[a,b,c],...], "truth": [t,...]}
    #   votes[i] = the answers of your N reasoners on item i; truth[i] = the correct answer. Any labels.
    python ensemble_calibrator.py --data my_ensemble.json
    # summary-only estimate:
    python ensemble_calibrator.py --competence 0.62 --correlation 0.4
    # reproduce the phase diagram (needs numpy):
    python ensemble_calibrator.py --demo

Part of Agora (https://github.com/DanceNitra/agora). License: MIT.
"""
import argparse, json, sys
from collections import Counter

# Measured boundary c*(rho): minimum AVERAGE single-accuracy at which majority aggregation starts to help,
# as a function of inter-reasoner error-correlation rho (binary task, misleading shared cue g~0.35, N=21;
# from agora_output/lab/20260619-172843_collective-intelligence-phase-diagram). Above rho~0.70 aggregation
# is unsafe at any feasible competence. This is an ESTIMATE for the summary-only path; the data path is exact.
_BOUNDARY = [(0.02, 0.51), (0.07, 0.59), (0.13, 0.64), (0.21, 0.66), (0.30, 0.67),
             (0.38, 0.67), (0.47, 0.68), (0.55, 0.68), (0.63, 0.68)]
_RHO_CEILING = 0.70


def _interp_cstar(rho):
    """Estimated competence threshold c*(rho) from the measured boundary (linear interp)."""
    if rho >= _RHO_CEILING:
        return None  # no feasible competence rescues aggregation
    pts = _BOUNDARY
    if rho <= pts[0][0]:
        return pts[0][1]
    for (r0, c0), (r1, c1) in zip(pts, pts[1:]):
        if r0 <= rho <= r1:
            t = (rho - r0) / (r1 - r0) if r1 > r0 else 0.0
            return c0 + t * (c1 - c0)
    return pts[-1][1]


def _majority(row):
    """Most common answer in a row; ties broken deterministically by sorted label."""
    c = Counter(row)
    top = max(c.values())
    return sorted([k for k, n in c.items() if n == top], key=lambda z: str(z))[0]


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def _pearson(a, b):
    n = len(a)
    if n < 2:
        return float("nan")
    ma, mb = _mean(a), _mean(b)
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return 0.0  # a constant correctness vector -> no linear correlation signal
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return cov / (va ** 0.5 * vb ** 0.5)


def assess(votes, truth):
    """Model-free verdict from labeled reasoner answers.
    votes: list of T rows, each a list of N reasoner answers. truth: list of T correct answers."""
    T = len(votes)
    if T == 0 or not votes[0]:
        return {"error": "no data"}
    N = len(votes[0])
    # correctness matrix (T x N)
    corr = [[1.0 if votes[i][j] == truth[i] else 0.0 for j in range(N)] for i in range(T)]
    cols = [[corr[i][j] for i in range(T)] for j in range(N)]
    competence = [_mean(c) for c in cols]
    avg_comp = _mean(competence)
    best_comp = max(competence)
    # inter-reasoner error correlation: mean pairwise Pearson of correctness columns
    pairs = [_pearson(cols[a], cols[b]) for a in range(N) for b in range(a + 1, N)]
    pairs = [p for p in pairs if p == p]  # drop nan
    rho = _mean(pairs) if pairs else float("nan")
    # majority-vote accuracy on the data
    maj_acc = _mean(1.0 if _majority(votes[i]) == truth[i] else 0.0 for i in range(T))
    # verdict, read straight from the data
    helps_vs_best = maj_acc >= best_comp - 1e-9
    helps_vs_avg = maj_acc >= avg_comp - 1e-9
    if maj_acc < avg_comp - 0.01:
        decision = "DO_NOT_AGGREGATE"
        why = ("majority vote is WORSE than the average single reasoner — you are in the amplification / "
               "redundancy trap (a shared misleading cue or herding). Adding reasoners will not help; "
               "diversify their evidence or use a single strong reasoner.")
    elif helps_vs_best:
        decision = "AGGREGATE"
        why = "majority vote beats even the best single reasoner — classic wisdom-of-crowds; aggregate."
    elif helps_vs_avg:
        decision = "AGGREGATE_WEAKLY"
        why = ("majority beats the average reasoner but not the best — aggregation helps if you cannot "
               "identify the best reasoner a priori; otherwise route to the best.")
    else:
        decision = "DO_NOT_AGGREGATE"
        why = "majority does not beat the average reasoner — no aggregation benefit on this data."
    return {"n_items": T, "n_reasoners": N,
            "avg_competence": round(avg_comp, 4), "best_competence": round(best_comp, 4),
            "error_correlation": round(rho, 4) if rho == rho else None,
            "majority_accuracy": round(maj_acc, 4),
            "beats_avg_single": helps_vs_avg, "beats_best_single": helps_vs_best,
            "decision": decision, "why": why}


def recommend(competence, rho):
    """Summary-only estimate from (avg competence, error-correlation) using the measured boundary."""
    cstar = _interp_cstar(rho)
    if cstar is None:
        return {"decision": "DO_NOT_AGGREGATE", "estimated_threshold": None,
                "why": (f"error-correlation rho={rho:.2f} is above the ceiling (~{_RHO_CEILING}); the measured "
                        "law says naive aggregation cannot beat a single reasoner at any feasible competence. "
                        "Reduce correlation (independent evidence) or use one strong reasoner.")}
    ok = competence >= cstar
    return {"decision": "AGGREGATE" if ok else "DO_NOT_AGGREGATE",
            "estimated_threshold": round(cstar, 3),
            "why": (f"estimated safe-aggregation threshold at rho={rho:.2f} is c*~{cstar:.2f}; your competence "
                    f"{competence:.2f} is {'above' if ok else 'below'} it. "
                    + ("Aggregate." if ok else "Below threshold — majority likely amplifies a correlated error.")
                    + " (Estimate from the measured boundary; the --data path is exact.)")}


def demo():
    try:
        import numpy as np
    except Exception:
        print("--demo needs numpy. Install numpy or use --data / --competence.")
        return
    rng = np.random.default_rng(0)
    print("Phase diagram (N=21, misleading shared cue g=0.35): '+' aggregate helps, '-' it HURTS\n")
    print("       corr->", "".join(f"{b:5.1f}" for b in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)))
    for mu in (0.2, 0.6, 1.0, 1.4, 1.8, 2.2):
        row = ""
        for beta in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
            T = 40000
            y = rng.choice([-1.0, 1.0], T)
            u = np.where(rng.random(T) < 0.35, y, -y)
            x = mu * y[:, None] + beta * u[:, None] + rng.normal(0, 1, (T, 21))
            v = np.where(x >= 0, 1.0, -1.0)
            single = (v == y[:, None]).mean()
            ens = np.where(v.sum(1) >= 0, 1.0, -1.0)
            d = (ens == y).mean() - single
            row += "    -" if d < -0.005 else ("    +" if d > 0.005 else "    .")
        print(f"  comp mu={mu:.1f}" + row)
    print("\nThe '-' region (~half the plane) is where MORE reasoners = WORSE. Measure YOUR ensemble with --data.")


def main():
    ap = argparse.ArgumentParser(description="Should you aggregate your reasoners, or trust the single best?")
    ap.add_argument("--data", help="JSON file: {'votes': [[a,b,...],...], 'truth': [t,...]}")
    ap.add_argument("--competence", type=float, help="summary-only: average single-reasoner accuracy")
    ap.add_argument("--correlation", type=float, help="summary-only: inter-reasoner error correlation rho")
    ap.add_argument("--demo", action="store_true")
    x = ap.parse_args()
    if x.demo:
        demo()
    elif x.data:
        d = json.load(open(x.data, encoding="utf-8"))
        print(json.dumps(assess(d["votes"], d["truth"]), indent=1))
    elif x.competence is not None and x.correlation is not None:
        print(json.dumps(recommend(x.competence, x.correlation), indent=1))
    else:
        ap.error("use --data FILE, or --competence C --correlation R, or --demo")


if __name__ == "__main__":
    main()
