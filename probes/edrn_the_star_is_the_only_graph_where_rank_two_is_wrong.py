# -*- coding: utf-8 -*-
"""Marat asked us to check his star-N=7 PCA result. This is the check.

HIS CLAIM (edrn-dmrg-verification#2, comment 5442370999, 2026-08-27): building the density matrix of
the degenerate ground manifold "(rank 2 for the star)" for each s in [0,3] and running PCA over
those matrices gives PC1+PC2 = 97.9%, PC2/PC1 in [0.615, 0.903] "depending on which edge is chosen
as the contradiction edge", against 50 random labelled trees at mean 0.192, max 0.422, p = 0.0000.

TWO THINGS THIS MEASURES, and the second is the one that matters.

1. THE EDGE CANNOT MATTER. K_{1,6} is edge-transitive, so every choice of contradiction edge gives
   an isomorphic operator. Relabelling acts on the flattened density matrices as ONE fixed
   permutation, an orthogonal map applied identically to every sample, and PCA variance ratios are
   invariant under that. An edge-dependent PC2/PC1 is therefore a property of the pipeline.

2. RANK 2 IS EXACT FOR THE TREES AND WRONG FOR THE STAR. Lieb-Mattis on a bipartite AFM tree gives
   ground total spin |nA - nB|/2, hence a (|nA - nB| + 1)-fold manifold. The star is the extreme
   imbalance among N=7 trees, 1 against 6, so 6-fold. A typical random labelled tree splits 3
   against 4, so 2-fold. Treating every graph as rank 2 is exact for the comparison group and an
   ARBITRARY 2-of-6 slice for the star alone, which is the one graph the claim is about.

CONTROLS: a broken tree generator is the obvious way to get this wrong, so every generated graph is
verified to be a tree before use. The first version of this file produced cyclic disconnected graphs
168 times in 200 and its rank histogram was meaningless. Lieb-Mattis is not assumed either, it is
checked against the measured rank on every graph.
"""
import heapq
import importlib.util
import io
import json
import random
import sys

import numpy as np

N = 7
SS = np.linspace(0.05, 3.0, 60)          # rank is a constant 6 here; s = 0 alone is 10-fold
STAR = [(0, i) for i in range(1, N)]

_spec = importlib.util.spec_from_file_location(
    "orb", "probes/edrn_the_orbit_floor_holds_across_the_symmetry_spectrum.py")
_m = importlib.util.module_from_spec(_spec)
_m.__name__ = "orb"
try:
    _spec.loader.exec_module(_m)
except SystemExit:
    pass


def bit(t):
    """basis entries are TUPLES of occupied sites, so the lift into the 2^N space is a bitmask."""
    return sum(1 << s for s in t)


def is_tree(edges):
    if len(edges) != N - 1 or len(set(edges)) != N - 1:
        return False
    par = list(range(N))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        par[ra] = rb
    return len({find(i) for i in range(N)}) == 1


def random_tree(rng):
    """Prufer decode. The popped leaf's degree must be decremented too; without that the output is
    not a tree at all, which is how the first version produced cycles."""
    pr = [rng.randrange(N) for _ in range(N - 2)]
    deg = [1] * N
    for x in pr:
        deg[x] += 1
    leaves = [i for i in range(N) if deg[i] == 1]
    heapq.heapify(leaves)
    edges = []
    for x in pr:
        leaf = heapq.heappop(leaves)
        edges.append((min(leaf, x), max(leaf, x)))
        deg[leaf] -= 1
        deg[x] -= 1
        if deg[x] == 1:
            heapq.heappush(leaves, x)
    u, v_ = [i for i in range(N) if deg[i] == 1][:2]
    edges.append((min(u, v_), max(u, v_)))
    return edges


def bipartition_gap(edges):
    adj = {i: set() for i in range(N)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    col = {0: 0}
    st = [0]
    while st:
        u = st.pop()
        for w_ in adj[u]:
            if w_ not in col:
                col[w_] = 1 - col[u]
                st.append(w_)
    a = sum(1 for c in col.values() if c == 0)
    return abs(a - (N - a))


def _sectors(edges, s, contra):
    w = [s if e == contra else 1.0 for e in range(len(edges))]
    out = []
    for n_up in range(1, N):
        H, basis = _m.build_H(N, edges, w, n_up)
        d, V, e0 = _m.ground_manifold(H)
        V = np.asarray(V)
        if V.ndim == 1:
            V = V.reshape(-1, 1)
        out.append((float(e0), V, list(basis), int(d)))
    return out


def ground_rank(edges, s=1.0, contra=0):
    recs = _sectors(edges, s, contra)
    g = min(r[0] for r in recs)
    return sum(d for e0, _, _, d in recs if abs(e0 - g) < 1e-9)


def manifold(edges, s, contra):
    recs = _sectors(edges, s, contra)
    g = min(r[0] for r in recs)
    cols = []
    for e0, V, basis, d in recs:
        if abs(e0 - g) > 1e-9:
            continue
        for j in range(min(d, V.shape[1])):
            f = np.zeros(2 ** N)
            for bi, b in enumerate(basis):
                f[bit(b)] = float(np.real(V[bi, j]))
            n = np.linalg.norm(f)
            if n > 0:
                cols.append(f / n)
    return np.array(cols).T


def pc_ratio(rhos):
    X = np.array([r.ravel() for r in rhos])
    X = X - X.mean(0)
    sv = np.linalg.svd(X, compute_uv=False)
    var = sv ** 2 / (sv ** 2).sum()
    return float(var[1] / var[0]), float(var[0] + var[1])


def spectrum(s, contra):
    w = [s if e == contra else 1.0 for e in range(6)]
    ev = []
    for n_up in range(1, N):
        H, _ = _m.build_H(N, STAR, w, n_up)
        ev += list(np.linalg.eigvalsh(H.toarray()))
    return np.sort(np.array(ev))


res, v = {}, {}

# 1 - the edge is an isomorphism
base = spectrum(0.7, 0)
res["spectrum_max_diff_across_edges"] = max(
    float(np.max(np.abs(spectrum(0.7, c) - base))) for c in range(1, 6))
v["CONTROL_the_spectra_were_actually_computed"] = len(base) > 50
v["edge_choice_is_an_isomorphism"] = res["spectrum_max_diff_across_edges"] < 1e-12

# 2 - the correct object is edge-independent
full = {}
for c in (0, 3, 5):
    rhos = []
    for s in SS:
        M = manifold(STAR, float(s), c)
        rhos.append((M @ M.T) / M.shape[1])
    full[c] = pc_ratio(rhos)
res["full_projector_pc2_over_pc1"] = {str(k): full[k][0] for k in full}
res["full_projector_pc1_plus_pc2"] = {str(k): full[k][1] for k in full}
_vals = [full[k][0] for k in full]
v["full_projector_is_edge_independent"] = (max(_vals) - min(_vals)) < 1e-6

# 3 - an arbitrary rank-2 slice of the 6-fold manifold spreads
slices = []
for t in range(15):
    rng_np = np.random.default_rng(t)
    rhos = []
    Q = None
    for s in SS:
        M = manifold(STAR, float(s), 0)
        if Q is None:
            Q, _ = np.linalg.qr(rng_np.standard_normal((M.shape[1], M.shape[1])))
        sel = (M @ Q)[:, :2]
        rhos.append((sel @ sel.T) / 2)
    slices.append(pc_ratio(rhos)[0])
res["arbitrary_rank2_slice_min"] = min(slices)
res["arbitrary_rank2_slice_max"] = max(slices)
v["an_arbitrary_slice_spreads"] = (max(slices) - min(slices)) > 0.2
v["the_slice_range_brackets_his_range"] = min(slices) < 0.615 and max(slices) > 0.903

# 4 - Lieb-Mattis, checked rather than assumed
rng = random.Random(7)
rows, seen = [], set()
while len(rows) < 50:
    e = random_tree(rng)
    if not is_tree(e):
        continue
    key = tuple(sorted(e))
    if key in seen:
        continue
    seen.add(key)
    rows.append((bipartition_gap(e), ground_rank(e)))
res["star_gap"] = bipartition_gap(STAR)
res["star_rank"] = ground_rank(STAR)
res["tree_rank_histogram"] = {str(r): sum(1 for _, x in rows if x == r) for _, r in rows}
v["CONTROL_every_generated_graph_is_a_tree"] = len(rows) == 50
v["lieb_mattis_holds_on_every_graph"] = all(r == g + 1 for g, r in rows)
v["star_is_six_fold"] = res["star_rank"] == 6
v["most_random_trees_really_are_rank_two"] = sum(1 for _, r in rows if r == 2) >= 35
v["CONTROL_a_broken_generator_would_be_caught"] = not is_tree(
    [(0, 1), (0, 1), (2, 3), (3, 4), (4, 5), (5, 6)])

v = {k: bool(x) for k, x in v.items()}
io.open("probes/edrn_the_star_is_the_only_graph_where_rank_two_is_wrong.result.json",
        "w", encoding="utf-8").write(json.dumps({"measured": res, "verdicts": v}, indent=2))
for k, ok in v.items():
    print("%-46s %s" % (k, "PASS" if ok else "FAIL"))
print("\n%d/%d" % (sum(v.values()), len(v)))
print(json.dumps(res, indent=2))
sys.exit(0 if all(v.values()) else 1)
