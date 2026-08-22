"""The valley position is where the graph's automorphism group is, not where a contradiction is.

THE CLAIM UNDER TEST (@luoxuejian000, 22 Aug revision, MAIN RESULT + control graphs):
"a contradiction edge at (0,6) produces a sharp valley at s=1.000"; controls: "Ring | 1.0 | 0.0891 |
0.0993+/-0.0286"; tree valley at 1.70; random no stable valley. And section "Mechanism": "asymmetric
contradiction injection into inequivalent subgraphs may trigger localized correlation reorganization
... but the control-graph results (ring and tree also show valleys) suggest the phenomenon may be
more general than the asymmetric-injection hypothesis."

THE ALTERNATIVE HYPOTHESIS: E(s) is the SPATIAL DISPERSION of <sz sz> across edges. At s=1 the
contradiction edge equals every other bond, so the graph is the UNIFORM graph and its full
automorphism group Aut(G) acts. For any ground state that carries the symmetry, edges in the same
Aut-orbit have EQUAL correlations, so the within-orbit part of the dispersion is exactly zero and E
falls to the between-orbit floor. Then:
  - ring (edge-transitive, ONE orbit) => E(1) = 0 EXACTLY on a symmetric state; the "depth" is just E(0).
  - gasket (D3, 27 edges in few orbits) => E(1) = between-orbit floor only, a symmetry number.
  - tree / random (little or no symmetry) => nothing special at s=1, minimum elsewhere or unstable.
That single mechanism would predict all four of the paper's graph results, and the paper says the
mechanism is open.

CONTROLS (each must hold or the reading is void)
  * ORBIT INSTRUMENT: on the symmetric state the WITHIN-orbit dispersion must be ~0 while the
    BETWEEN-orbit part is not -- if within-orbit is nonzero, the orbit computation is wrong.
  * NEGATIVE CONTROL: at a NON-degenerate s the manifold width must be exactly 0.0.
  * VACUITY CONTROL: on a graph with trivial Aut (all orbits size 1) the within-orbit dispersion is
    identically 0 for EVERY s -- so it cannot be used as evidence there, and must be reported so.
  * E(0) reproduced against his published 0.246731 for the gasket.
"""
from __future__ import annotations
import itertools, json, os, time
import numpy as np
import networkx as nx
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import eigsh

HERE = os.path.dirname(os.path.abspath(__file__))
T0 = time.time()

L2_EDGES = [(0, 6), (0, 8), (1, 9), (1, 11), (2, 12), (2, 14), (3, 6), (3, 7), (3, 9), (3, 10),
            (4, 10), (4, 11), (4, 12), (4, 13), (5, 7), (5, 8), (5, 13), (5, 14),
            (6, 7), (7, 8), (9, 10), (10, 11), (12, 13), (13, 14), (6, 8), (9, 11), (12, 14)]


def build_H(n, edges, j, n_up):
    basis = list(itertools.combinations(range(n), n_up))
    idx = {s: i for i, s in enumerate(basis)}
    H = lil_matrix((len(basis), len(basis)))
    for (a, b), J in zip(edges, j):
        for k, s in enumerate(basis):
            H[k, k] += J * (1 if a in s else -1) * (1 if b in s else -1)
            ua, ub = a in s, b in s
            if ua and not ub:
                H[k, idx[tuple(sorted(set(s) - {a} | {b}))]] += 2 * J
            elif ub and not ua:
                H[k, idx[tuple(sorted(set(s) - {b} | {a}))]] += 2 * J
    return csr_matrix(H), basis


def sp_table(basis, edges):
    return np.array([[(1 if a in s else -1) * (1 if b in s else -1) for s in basis]
                     for (a, b) in edges], float)


def corr(vec, sp):
    d = np.abs(vec) ** 2 if np.iscomplexobj(vec) else vec ** 2
    return sp @ d


def E_of(vec, sp):
    c = corr(vec, sp)
    return float(np.sqrt(np.mean((c - c.mean()) ** 2)))


def ground_manifold(H, k=10, tol=1e-9):
    rng = np.random.default_rng(20260822)
    w, v = eigsh(H, k=min(k, H.shape[0] - 1), which="SA", tol=0,
                 v0=rng.standard_normal(H.shape[0]), maxiter=400000)
    o = np.argsort(w)
    w, v = w[o], v[:, o]
    d = int(np.nonzero(np.diff(w) > tol)[0][0] + 1)
    return w[0], v[:, :d], d


def manifold_E_range(V, sp, ngrid=181):
    """min/max of E over all normalised complex combinations of the columns of V."""
    d = V.shape[1]
    if d == 1:
        e = E_of(V[:, 0], sp)
        return e, e, V[:, 0]
    best = (np.inf, None)
    worst = (-np.inf, None)
    if d == 2:
        for th in np.linspace(0, np.pi / 2, ngrid):
            for ph in np.linspace(0, 2 * np.pi, ngrid):
                psi = np.cos(th) * V[:, 0] + np.exp(1j * ph) * np.sin(th) * V[:, 1]
                e = E_of(psi, sp)
                if e < best[0]:
                    best = (e, psi)
                if e > worst[0]:
                    worst = (e, psi)
    else:
        rng = np.random.default_rng(7)
        for _ in range(20000):
            c = rng.standard_normal(d) + 1j * rng.standard_normal(d)
            c /= np.linalg.norm(c)
            psi = V @ c
            e = E_of(psi, sp)
            if e < best[0]:
                best = (e, psi)
            if e > worst[0]:
                worst = (e, psi)
    return best[0], worst[0], best[1]


def real_seed_E(H, sp, nseeds=12):
    vals = []
    for s in range(nseeds):
        rng = np.random.default_rng(1000 + s)
        w, v = eigsh(H, k=2, which="SA", tol=0, v0=rng.standard_normal(H.shape[0]), maxiter=400000)
        vals.append(E_of(v[:, int(np.argmin(w))], sp))
    return float(min(vals)), float(max(vals))


def edge_orbits(G):
    """Aut(G) order and the partition of edges into Aut-orbits."""
    gm = nx.algorithms.isomorphism.GraphMatcher(G, G)
    autos = list(gm.isomorphisms_iter())
    E = [tuple(sorted(e)) for e in G.edges()]
    lab = {e: e for e in E}
    changed = True
    while changed:
        changed = False
        for a in autos:
            for e in E:
                m = tuple(sorted((a[e[0]], a[e[1]])))
                if lab[m] < lab[e]:
                    lab[e] = lab[m]
                    changed = True
                elif lab[e] < lab[m]:
                    lab[m] = lab[e]
                    changed = True
    orb = {}
    for e in E:
        orb.setdefault(lab[e], []).append(e)
    return len(autos), list(orb.values()), E


def decompose(c, E_order, orbits):
    """within-orbit and between-orbit contributions to Var(c)."""
    pos = {e: i for i, e in enumerate(E_order)}
    tot = float(np.var(c))
    n = len(E_order)
    within = 0.0
    means = []
    for ob in orbits:
        ix = [pos[e] for e in ob]
        sub = c[ix]
        within += len(ix) * np.var(sub)
        means.append((len(ix), sub.mean()))
    within /= n
    gm = c.mean()
    between = sum(k * (m - gm) ** 2 for k, m in means) / n
    return tot, float(within), float(between)


OUT = {"probe": os.path.basename(__file__), "graphs": {}, "controls": {}}

try:
    TREE = nx.random_labeled_tree(15, seed=42)
except AttributeError:
    TREE = nx.random_tree(15, seed=42)

GRAPHS = {
    "ring15": nx.cycle_graph(15),
    "gasketL2": nx.Graph(L2_EDGES),
    "tree15": TREE,
    "random15": nx.gnm_random_graph(15, 27, seed=42),
}
DEFECT = {"ring15": (0, 1), "gasketL2": (0, 6), "tree15": None, "random15": None}

for name, G in GRAPHS.items():
    n = G.number_of_nodes()
    n_up = n // 2
    naut, orbits, E_order = edge_orbits(G)
    d = DEFECT[name] or tuple(sorted(list(G.edges())[0]))
    d = tuple(sorted(d))
    edges = [tuple(sorted(e)) for e in G.edges()]
    print(f"[{name}] |V|={n} |E|={len(edges)} |Aut|={naut} "
          f"orbit_sizes={sorted(len(o) for o in orbits)} defect={d}", flush=True)
    rec = {"n": n, "n_edges": len(edges), "aut_order": naut,
           "edge_orbit_sizes": sorted(len(o) for o in orbits), "defect": list(d)}

    H1, basis = build_H(n, edges, [1.0] * len(edges), n_up)
    sp = sp_table(basis, edges)
    e0, V, deg = ground_manifold(H1)
    emin, emax, psimin = manifold_E_range(V, sp)
    rec["s1"] = {"degeneracy": deg, "E_ground": float(e0), "E_manifold_min": emin,
                 "E_manifold_max": emax, "manifold_width": emax - emin}
    c = corr(psimin, sp)
    tot, wi, be = decompose(c, E_order, orbits)
    rec["s1"]["at_min_state"] = {"var_total": tot, "var_within_orbit": wi,
                                 "var_between_orbit": be,
                                 "within_frac": (wi / tot if tot > 0 else 0.0)}
    rmin, rmax = real_seed_E(H1, sp)
    rec["s1"]["real_seed_E"] = [rmin, rmax]

    j0 = [0.0 if e == d else 1.0 for e in edges]
    H0, b0 = build_H(n, edges, j0, n_up)
    sp0 = sp_table(b0, edges)
    z0, V0, deg0 = ground_manifold(H0)
    e0min, e0max, _ = manifold_E_range(V0, sp0)
    rec["s0"] = {"degeneracy": deg0, "E": e0min, "E_max": e0max, "width": e0max - e0min}

    scan = {}
    for s in [round(float(x), 2) for x in np.arange(0.0, 3.01, 0.10)]:
        js = [s if e == d else 1.0 for e in edges]
        Hs, bs = build_H(n, edges, js, n_up)
        sps = sp_table(bs, edges)
        _, Vs, dgs = ground_manifold(Hs)
        a, _, _ = manifold_E_range(Vs, sps, ngrid=61)
        scan[f"{s:.2f}"] = {"E": a, "deg": dgs}
    rec["scan_symmetric_state"] = scan
    smin = min(scan, key=lambda k: scan[k]["E"])
    rec["argmin_s_symmetric"] = float(smin)
    rec["E_at_argmin"] = scan[smin]["E"]
    rec["depth_symmetric"] = rec["s0"]["E"] - scan[smin]["E"]
    print(f"   s=1 deg={deg} E_min={emin:.12f} E_max={emax:.12f} "
          f"within_frac={rec['s1']['at_min_state']['within_frac']:.3e} | "
          f"real seeds [{rmin:.6f},{rmax:.6f}] | E(0)={rec['s0']['E']:.6f} | argmin s={smin}",
          flush=True)
    OUT["graphs"][name] = rec

edges = [tuple(sorted(e)) for e in nx.Graph(L2_EDGES).edges()]
js = [0.5 if e == (0, 6) else 1.0 for e in edges]
Hc, bc = build_H(15, edges, js, 7)
spc = sp_table(bc, edges)
_, Vc, dc = ground_manifold(Hc)
a, b, _ = manifold_E_range(Vc, spc)
OUT["controls"]["nondegenerate_point_width"] = {"s": 0.5, "deg": dc, "width": b - a}
# The line above is COMPUTED, not a literal -- but at deg=1 the manifold is one vector, so the width
# is zero by construction and the check cannot fail. The sibling probe shipped the same weakness as
# an actual hardcoded 0.0 and an adversarial pass caught it there; fixing the class, not the instance.
# The control that CAN fail: at a non-degenerate point independent real start vectors must agree.
_sv = []
for _s in range(8):
    _r = np.random.default_rng(2000 + _s)
    _, _ev = eigsh(Hc, k=1, which="SA", v0=_r.standard_normal(Hc.shape[0]))
    _sv.append(E_of(_ev[:, 0], spc))
_spread = float(max(_sv) - min(_sv))
OUT["controls"]["nondegenerate_seed_spread"] = _spread
print("  CONTROL s=0.5 (deg %d): 8 independent seeds spread = %.2e" % (dc, _spread), flush=True)
assert _spread < 1e-12, ("a NON-degenerate point is state-dependent (%.2e): every state-selection "
                         "reading in this file is void" % _spread)
OUT["controls"]["gasket_E0_measured_vs_published_0.246731"] = OUT["graphs"]["gasketL2"]["s0"]["E"]
OUT["controls"]["random15_all_orbits_size_1"] = all(
    k == 1 for k in OUT["graphs"]["random15"]["edge_orbit_sizes"])
OUT["elapsed_s"] = time.time() - T0
p = os.path.join(HERE, "edrn_the_valley_sits_where_the_automorphism_group_is.result.json")
json.dump(OUT, open(p, "w"), indent=1)
print("WROTE", p, f"{OUT['elapsed_s']:.1f}s")
print(json.dumps(OUT["controls"], indent=1))
