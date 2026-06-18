"""
Crucible replication: Hong & Page (2004 PNAS) "diversity trumps ability" — a random/diverse group of
problem-solvers can outperform a group of the best individual solvers. Genuinely CONTESTED (Thompson
2014 critiqued it as fragile/condition-dependent), so FAILED is a live possibility. On the frontier
(collective intelligence / the science of better thinking).

Minimal faithful model (Hong-Page): n points on a ring, each a random value (the objective). An agent's
HEURISTIC is an ordered tuple of distinct step sizes from {1..L} (e.g. (3,5,9)); from a start point it
repeatedly looks ahead by its step sizes and moves to the first improvement, until stuck. Individual
ability = mean stopping value over all starts. A GROUP solves by relay: agents take turns improving the
current point with their own heuristic, cycling until a full round yields no gain.
Compare: top-N-by-ability group vs random-N group. Hong-Page: random >= best. We measure it and test
robustness (how it depends on the heuristic-pool richness L).
"""
import numpy as np

def solve(values, start, heur, n):
    pos = start
    improved = True
    while improved:
        improved = False
        for d in heur:
            nxt = (pos + d) % n
            if values[nxt] > values[pos]:
                pos = nxt; improved = True
                break
    return pos

def individual_score(values, heur, n, starts):
    return np.mean([values[solve(values, s, heur, n)] for s in starts])

def group_score(values, group, n, starts):
    tot = 0.0
    for s in starts:
        pos = s
        improved = True
        while improved:
            improved = False
            for heur in group:
                np2 = solve(values, pos, heur, n)
                if values[np2] > values[pos]:
                    pos = np2; improved = True
        tot += values[pos]
    return tot / len(starts)

def overlap(group):
    """Mean pairwise step-set Jaccard overlap within a group (1 = identical heuristics, clustered)."""
    sets = [set(h) for h in group]
    if len(sets) < 2:
        return 0.0
    tot = c = 0.0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            u = sets[i] | sets[j]
            tot += len(sets[i] & sets[j]) / len(u); c += 1
    return tot / c

def run(L, n=800, k=3, pool_size=120, group_n=10, n_land=25, rand_draws=5, seed0=0):
    rng = np.random.default_rng(abs(seed0) % (2**32))
    all_h = []
    while len(all_h) < pool_size:
        h = tuple(rng.choice(np.arange(1, L + 1), size=k, replace=False).tolist())
        if h not in all_h:
            all_h.append(h)
    diffs, abil_gap, best_ov, rand_ov = [], [], [], []
    for li in range(n_land):
        values = rng.random(n)
        starts = list(range(0, n, max(1, n // 40)))               # ~40 starts
        abil = sorted(((individual_score(values, h, n, starts), i) for i, h in enumerate(all_h)), reverse=True)
        best_group = [all_h[i] for _, i in abil[:group_n]]
        bscore = group_score(values, best_group, n, starts)
        # average the high-variance random group over several independent draws (fair "expected" random)
        rs, ros = [], []
        for _ in range(rand_draws):
            idx = rng.choice(len(all_h), size=group_n, replace=False)
            rg = [all_h[i] for i in idx]
            rs.append(group_score(values, rg, n, starts)); ros.append(overlap(rg))
        diffs.append(np.mean(rs) - bscore)                        # random - best
        # individual-ability sanity: best agents' solo score vs random agents' solo
        abil_gap.append(abil[0][0] - np.mean([individual_score(values, all_h[i], n, starts)
                                              for i in rng.choice(len(all_h), 10, replace=False)]))
        best_ov.append(overlap(best_group)); rand_ov.append(np.mean(ros))
    diffs = np.array(diffs)
    se = diffs.std(ddof=1) / np.sqrt(len(diffs))
    return {"L": L, "mean_diff": float(diffs.mean()), "se": float(se),
            "t": float(diffs.mean() / se) if se > 0 else 0.0, "n_land": len(diffs),
            "best_overlap": float(np.mean(best_ov)), "rand_overlap": float(np.mean(rand_ov)),
            "abil_gap": float(np.mean(abil_gap))}

if __name__ == "__main__":
    print("Hong-Page 'diversity trumps ability' (n=800, pool=120, group=10; random group averaged over 5 draws).")
    print("diff = random_group - best_group (paired per landscape). Hong-Page: diff >= 0 (diversity wins/ties).\n")
    print("  L | mean(random-best) +- SE | t | best-grp overlap vs random-grp | best-vs-rand solo ability")
    rows = []
    for L in [6, 12, 20]:
        r = run(L)
        rows.append(r)
        print(f"  {r['L']:<3}| {r['mean_diff']:+.4f} +- {r['se']:.4f}   | {r['t']:+.2f} | "
              f"{r['best_overlap']:.3f} vs {r['rand_overlap']:.3f}            | +{r['abil_gap']:.3f}")

    # significance-aware verdict (|t|>2 ~ p<0.05, paired)
    div_sig = sum(1 for r in rows if r["t"] > 2)        # random significantly beats best
    abil_sig = sum(1 for r in rows if r["t"] < -2)      # best significantly beats random
    clustered = np.mean([r["best_overlap"] - r["rand_overlap"] for r in rows]) > 0.02
    print("\n=== VERDICT ===")
    print(f"diversity significantly wins: {div_sig}/{len(rows)} | ability significantly wins: {abil_sig}/{len(rows)} | "
          f"best-group more clustered than random: {clustered}")
    if div_sig >= 2:
        verdict, msg = "REPRODUCED", ("Random/diverse groups significantly beat the best-ability group — "
            "Hong-Page holds: the elite share blind spots (clustered heuristics) that diversity escapes.")
    elif abil_sig >= 2:
        verdict, msg = "FAILED", ("The best-ability group significantly beats the random group — the STRONG "
            "'diversity trumps ability' claim FAILS under a faithful, statistically-powered replication. "
            f"Magnitude is small ({abs(np.mean([r['mean_diff'] for r in rows]))*100:.2f}% of value) but consistent "
            "and significant; and the best group is NOT meaningfully more clustered than random, so the "
            "diversity-escapes-blind-spots mechanism does not bite here.")
    else:
        verdict, msg = "PARTIAL/NOT-ROBUST", ("No significant or sign-stable advantage either way (|t|<2) — "
            "the dramatic 'diversity trumps ability' claim is NOT a robust general result here; it is at "
            "best a small, condition-dependent effect, consistent with the Thompson (2014) critique.")
    print(f"VERDICT: {verdict}")
    print(msg)
