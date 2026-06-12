"""
Replication: Hong & Page (2004) "Groups of diverse problem solvers can outperform groups
of high-ability problem solvers" (PNAS 101(46)).

Claim under test: in the canonical heuristic-search setup, a group of N agents picked at
RANDOM from the heuristic pool ("diverse") achieves a higher expected final value than the
group of the N individually BEST-performing agents ("best"), under relay group search.

Setup (faithful to the paper's computational experiment):
- Landscape: circular ring of n points, each with an i.i.d. Uniform[0,100] value.
- Heuristic: an ordered tuple of k DISTINCT step sizes from {1..l}. Agent at point x checks
  x+s1, x+s2, ... (mod n) in order; moves to the first strictly-better point; repeats; stops
  at a local optimum for its heuristic.
- Individual ability: expected stopping value over all starting points on fresh landscapes.
- Group (relay) search: from a starting point, agents take turns improving the current point
  with their heuristic; the group stops when no agent can improve it.
- Comparison: group of the 10 best individual agents vs 10 agents sampled uniformly at random
  from the pool, averaged over landscapes and starting points.
Paper's parameters: n=2000, k=3, l=12, group sizes 10-20.

Severity: we ALSO probe robustness at smaller l (a narrower heuristic pool) and a smoother
landscape, where critics (Thompson 2014, AMS Notices) argue the result is fragile/parameter-
dependent. Verdict rule:
  REPRODUCED  -- random > best at the paper's stated parameters (clear margin).
  FAILED      -- random <= best at the paper's stated parameters.
  (robustness probes annotate the note either way; they do not flip the headline verdict)
"""
import numpy as np

rng = np.random.default_rng(20260612)


def make_heuristics(l, k):
    """All ordered tuples of k distinct step sizes from {1..l}."""
    pool = []
    def rec(prefix):
        if len(prefix) == k:
            pool.append(tuple(prefix)); return
        for s in range(1, l + 1):
            if s not in prefix:
                rec(prefix + [s])
    rec([])
    return pool


def climb(landscape, start, heur):
    """Agent's stopping point from start (first-improvement, cyclic checks in heuristic order)."""
    n = len(landscape)
    x = start
    improved = True
    while improved:
        improved = False
        for s in heur:
            y = (x + s) % n
            if landscape[y] > landscape[x]:
                x = y
                improved = True
                break
    return x


def relay(landscape, start, heuristics):
    """Group relay search: agents in turn improve the point until none can."""
    n = len(landscape)
    x = start
    improved = True
    while improved:
        improved = False
        for h in heuristics:
            x2 = climb(landscape, x, h)
            if landscape[x2] > landscape[x]:
                x = x2
                improved = True
    return landscape[x]


def experiment(n, l, k, group=10, n_land=12, n_starts=40, n_ability_starts=60, smooth=0):
    pool = make_heuristics(l, k)
    # --- ability ranking on independent landscapes (no selection bias into the test set)
    abil = np.zeros(len(pool))
    for _ in range(3):
        L = rng.uniform(0, 100, n)
        if smooth:
            ker = np.ones(smooth) / smooth
            L = np.convolve(np.r_[L, L[:smooth]], ker, mode="same")[:n]
        starts = rng.integers(0, n, n_ability_starts)
        for i, h in enumerate(pool):
            abil[i] += np.mean([L[climb(L, s, h)] for s in starts])
    best_idx = np.argsort(abil)[::-1][:group]
    best_team = [pool[i] for i in best_idx]
    # --- head-to-head on fresh landscapes
    diffs, b_scores, r_scores = [], [], []
    for _ in range(n_land):
        L = rng.uniform(0, 100, n)
        if smooth:
            ker = np.ones(smooth) / smooth
            L = np.convolve(np.r_[L, L[:smooth]], ker, mode="same")[:n]
        rand_team = [pool[i] for i in rng.choice(len(pool), group, replace=False)]
        starts = rng.integers(0, n, n_starts)
        b = np.mean([relay(L, s, best_team) for s in starts])
        r = np.mean([relay(L, s, rand_team) for s in starts])
        b_scores.append(b); r_scores.append(r); diffs.append(r - b)
    diffs = np.array(diffs)
    se = diffs.std(ddof=1) / np.sqrt(len(diffs))
    return float(np.mean(b_scores)), float(np.mean(r_scores)), float(diffs.mean()), float(se), len(pool)


print("=== Hong-Page (2004) replication: diversity vs ability, relay search ===")
b, r, d, se, ps = experiment(n=2000, l=12, k=3)
print(f"[paper params n=2000 l=12 k=3 group=10] pool={ps}")
print(f"  best-team  mean final value = {b:.2f}")
print(f"  random-team mean final value = {r:.2f}")
print(f"  diff (random - best) = {d:+.2f}  (SE {se:.2f}, t={d/se:.1f})")
verdict_main = "random>best" if d > 2 * se else ("best>=random" if d < -2 * se else "tie")
print(f"  -> {verdict_main}")

print("\n=== Robustness probe 1: narrower pool l=6 (fewer heuristics to differ with) ===")
b2, r2, d2, se2, ps2 = experiment(n=2000, l=6, k=3)
print(f"  pool={ps2}  best={b2:.2f} random={r2:.2f} diff={d2:+.2f} (SE {se2:.2f})")

print("\n=== Robustness probe 2: smoothed landscape (window 5; fewer local optima) ===")
b3, r3, d3, se3, _ = experiment(n=2000, l=12, k=3, smooth=5)
print(f"  best={b3:.2f} random={r3:.2f} diff={d3:+.2f} (SE {se3:.2f})")

print("\n=== Verdict ===")
if d > 2 * se:
    print("REPRODUCED at the paper's parameters: the random (diverse) team beats the best team.")
elif d < -2 * se:
    print("FAILED at the paper's parameters: the best team beats the random team.")
else:
    print("TIE at the paper's parameters (no significant difference).")
print(f"robustness: l=6 diff {d2:+.2f}; smooth diff {d3:+.2f} "
      f"(negative = ability wins when the problem gets easier/pool narrows)")
