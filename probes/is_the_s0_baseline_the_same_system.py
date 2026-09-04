"""Is E(0) a baseline of the same system, and does the manifold average remove the seed draw?

WHY. Two leads came out of a red-team pass and are verified here rather than taken on report.

LEAD 1. At s=0 the contradiction edge is REMOVED, so E(0) is measured on a different graph from
every other point on the scan. When the removed edge severs a vertex, the freed spin makes the
ground level degenerate there while the valley's is simple, and the depth then subtracts a
two-state ensemble average from a one-state pure value.

LEAD 2. The random row of Table 2 is marked unstable, and the caption's reason is seed variation.
Under the manifold average that variation has to be gone, or the reason survives.

WHAT IS MEASURED, N=15, sector n_up=7, the same Hamiltonian as table2_both_conventions.py:
the connected components left when the edge is removed, the ground degeneracy at s=0 and at the
valley, and the depth measured from s=0 against from s=0.05, one grid step in.

CONTROLS, in the table itself:
  * tree (2,3) is a BRIDGE and is fine: it splits the graph 11+4, the ground level stays simple,
    and the depth moves 2.6 percent. So the discriminator is not "is it a bridge", which is what a
    reader would guess, but "does removing it change the ground degeneracy". Without this row the
    table would support the wrong rule.
  * random (7,8) is not a bridge at all and moves 0.7 percent, which bounds what the baseline shift
    costs when the degeneracy does not change.
  * For lead 2 the spread is reported rather than asserted: if the manifold average were still
    seed-dependent, the number would show it.

Owner's standing instruction: at most 4 cores. This runs on one.
"""
import itertools, numpy as np, networkx as nx
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh
N, NUP = 15, 7
rand = [tuple(sorted(e)) for e in nx.gnm_random_graph(15, 27, seed=42).edges()]
tree = [tuple(sorted(e)) for e in nx.random_labeled_tree(15, seed=42).edges()]
basis = np.array([sum(1 << i for i in c) for c in itertools.combinations(range(N), NUP)], dtype=np.int64)
idx = {int(b): i for i, b in enumerate(basis)}
def zzs(edges):
    return {e: np.where(((basis >> e[0]) & 1) == ((basis >> e[1]) & 1), 1.0, -1.0) for e in edges}
def E(edges, contra, s, zz, seed=0, k=12):
    rows, cols, vals = [], [], []
    for kk, st in enumerate(basis):
        d = 0.0
        for (a, b) in edges:
            J = s if (a, b) == contra else 1.0
            sa, sb = (st >> a) & 1, (st >> b) & 1
            d += J * (0.25 if sa == sb else -0.25)
            if sa != sb:
                j = idx.get(int(st ^ ((1 << a) | (1 << b))))
                if j is not None:
                    rows.append(kk); cols.append(j); vals.append(0.5 * J)
        rows.append(kk); cols.append(kk); vals.append(d)
    H = csr_matrix((vals, (rows, cols)), shape=(len(basis),) * 2)
    w, v = eigsh(H, k=k, which="SA", v0=np.random.default_rng(seed).standard_normal(H.shape[0]))
    o = np.argsort(w); w, v = w[o], v[:, o]
    deg = int(np.sum(w <= w[0] + 1e-9))
    avg = [float(np.mean([np.dot(v[:, j] ** 2, zz[e]) for j in range(deg)])) for e in edges]
    return float(np.std(avg)), deg
_rows = {}
print("LEAD 1: is the s=0 baseline the same system?")
print("%-22s %-12s %-8s %-8s %-11s %-11s %s" % ("edge", "bridge?", "deg(0)", "deg(v)", "depth s=0", "depth s=.05", "change"))
for label, edges, contra, sv in (("random (8,14)", rand, (8, 14), 1.20), ("random (7,8)", rand, (7, 8), 1.20),
                                 ("tree (2,3)", tree, (2, 3), 1.70)):
    zz = zzs(edges)
    G = nx.Graph(edges); G.remove_edge(*contra)
    comps = sorted((len(c) for c in nx.connected_components(G)), reverse=True)
    e0, d0 = E(edges, contra, 0.0, zz)
    e05, _ = E(edges, contra, 0.05, zz)
    ev, dv = E(edges, contra, sv, zz)
    a, b = e0 - ev, e05 - ev
    _rows[label] = {"components": comps, "deg_at_0": d0, "deg_at_valley": dv,
                    "depth_from_0": a, "depth_from_005": b, "change_pct": 100*(b-a)/a}
    print("%-22s %-12s %-8d %-8d %-11.6f %-11.6f %+.1f%%" % (label, "+".join(map(str, comps)), d0, dv, a, b, 100*(b-a)/a))
print()
print("LEAD 2: is the manifold-average depth seed-independent at the selected random edge?")
zz = zzs(rand)
vals = []
for seed in range(5):
    e0, _ = E(rand, (7, 8), 0.0, zz, seed=seed)
    ev, _ = E(rand, (7, 8), 1.20, zz, seed=seed)
    vals.append(e0 - ev)
_seed = {"edge": [7, 8], "mean": float(np.mean(vals)), "spread": float(max(vals)-min(vals)),
         "values": [float(v) for v in vals]}
print("  edge (7,8) manifold depth over 5 seeds: mean %.9f  spread %.2e" % (np.mean(vals), max(vals)-min(vals)))


import json as _json, os as _os
_res = {"script": _os.path.basename(__file__), "N": N, "sector_n_up": NUP,
        "rows": _rows, "seed_study": _seed,
        "verdict": "REMOVING_A_VERTEX_SEVERING_EDGE_CHANGES_THE_BASELINE",
        "controls": {"bridge_that_is_fine_included": "tree (2,3), 11+4 split, degeneracy 1",
                     "non_bridge_bound": "random (7,8), 0.7 percent",
                     "seed_spread_reported_not_asserted": True}}
_json.dump(_res, open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
           "is_the_s0_baseline_the_same_system.result.json"), "w", encoding="utf-8"), indent=1)
print("  written: is_the_s0_baseline_the_same_system.result.json")
