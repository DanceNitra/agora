"""Verify the three s=0 numbers in the letter that have NO artifact behind them:
  (1) the same star under two node labellings gives I(0) = 0.219396 and 0.208193, agreeing to
      1.1e-16 at s = 1;
  (2) the gap inside four of the six ground sectors collapses to about 1e-15 at s = 0;
  (3) of ten of his trees, seven also take their I_min at s = 0.
"""
import sys, os, json, importlib.util, itertools
sys.stdout.reconfigure(line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "the_s0_projector_is_basis_arbitrary_and_two_streams_read_it.result.json")
spec = importlib.util.spec_from_file_location(
    "hp", os.path.join(HERE, "his_heaviest_feature_is_read_at_the_one_point_where_it_is_undefined.py"))
hp = importlib.util.module_from_spec(spec); spec.loader.exec_module(hp)
import numpy as np, networkx as nx
from scipy.linalg import eigh
N = 7
out = {}

# (2) sector gaps at s=0 and s=1 for the star
star = [(0, j) for j in range(1, N)]
for s in (0.0, 1.0):
    gaps = {}
    for n_up in range(1, N):
        Hd, _ = hp._sector(star, (0, 1), s, n_up, [s if e == (0, 1) else 1.0 for e in star])
        v = eigh(Hd)[0]
        gaps[n_up] = float(v[1] - v[0])
    out["star_sector_gaps_s%g" % s] = gaps
    print("star sector gaps at s=%g: %s" % (s, {k: "%.3e" % v for k, v in gaps.items()}))
n_below = sum(1 for v in out["star_sector_gaps_s0"].values() if v < 1e-12)
print("  -> %d of 6 sectors have gap < 1e-12 at s=0" % n_below)
out["sectors_with_collapsed_gap_at_s0"] = n_below

# (1) two node labellings of the SAME star
def I_at(edges, contra, s):
    P, E, act = hp.full_projector_and_energy(edges, contra, [s], 6, 0.0)
    return hp.avg_mutual_information(P[0], act)

perm = {0: 3, 3: 0}          # relabel: swap the centre with leaf 3
star2 = [(perm.get(a, a), perm.get(b, b)) for (a, b) in star]
c1, c2 = (0, 1), (perm.get(0, 0), perm.get(1, 1))
for s in (0.0, 1.0):
    a, b = I_at(star, c1, s), I_at(star2, c2, s)
    print("I(s=%g): labelling A %.6f  labelling B %.6f   |diff| %.3e" % (s, a, b, abs(a - b)))
    out["I_two_labellings_s%g" % s] = [a, b, abs(a - b)]

# also: does the ARBITRARY eigenvector choice show up under a pure basis rotation of the solver?
# re-solve the SAME star with the edge list in a different ORDER (changes nothing physically)
star3 = list(reversed(star))
for s in (0.0, 1.0):
    a, b = I_at(star, c1, s), I_at(star3, c1, s)
    print("I(s=%g): edge order A %.6f  reversed %.6f   |diff| %.3e" % (s, a, b, abs(a - b)))
    out["I_edge_order_s%g" % s] = [a, b, abs(a - b)]

# (3) where does I_min sit for his trees?
sv = np.linspace(0, 3, 101)
argmins = []
for seed in range(1000, 1010):
    T = nx.random_labeled_tree(n=N, seed=seed)
    e = list(T.edges()); r = hp.bipartite_rank(N, e)
    P, E, act = hp.full_projector_and_energy(e, e[0], sv, r, 0.0)
    Iv = np.array([hp.avg_mutual_information(p, act) for p in P])
    k = int(np.argmin(Iv))
    argmins.append(k)
    print("  tree seed %d rank %d: I_min at index %d (s=%.2f)" % (seed, r, k, sv[k]))
out["tree_I_argmin_index_seeds_1000_1009"] = argmins
out["trees_with_I_min_at_s0"] = sum(1 for k in argmins if k == 0)
print("  -> %d of 10 trees take I_min at s=0" % out["trees_with_I_min_at_s0"])

# and the star itself
P, E, act = hp.full_projector_and_energy(star, (0, 1), sv, 6, 0.0)
Iv = np.array([hp.avg_mutual_information(p, act) for p in P])
print("  star: I_min at index %d (s=%.2f)" % (int(np.argmin(Iv)), sv[int(np.argmin(Iv))]))
out["star_I_argmin_index"] = int(np.argmin(Iv))
json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1)
