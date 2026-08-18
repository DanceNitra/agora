"""Every number we would state to a co-author, re-derived here and checked against the manuscript.

The rule this file exists to satisfy: a number in a note is not verified data. Each CLAIM below is
recomputed from scratch (or from the run receipt written by edrn_valley_is_the_uniform_point.py) and
compared with what the manuscript prints. A claim that cannot be re-derived is not sent.

Run:  python probes/edrn_claims_receipt.py
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import pathlib
import sys

import networkx as nx
import numpy as np
from scipy.sparse.linalg import eigsh

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("edrn", HERE / "edrn_valley_is_the_uniform_point.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
RUN = json.loads((HERE / "edrn_valley_is_the_uniform_point.result.json").read_text())

rows = RUN["rows"]
EDGES = [tuple(x) for x in RUN["fractal_L2_edges"]]
Z = P._z_table(15)
checks: list[tuple[str, bool, str]] = []


def check(name, ok, detail):
    checks.append((name, bool(ok), detail))


def scan(graph):
    d = {r["s"]: (r["E"], r["degeneracy"]) for r in rows if r["kind"] == "scan" and r["graph"] == graph}
    return d


# 1 -- POSITIVE CONTROL. Without this every other line is void.
ring_uniform = RUN["control_ring_uniform_E"]
check("CONTROL uniform ring dispersion is exactly zero", ring_uniform < 1e-10,
      "measured %.3e (edge-transitivity forces 0)" % ring_uniform)

# 2 -- our Hamiltonian is HIS Hamiltonian: reproduce a manuscript number away from the degenerate point
n, e = P.sierpinski_sieve(2)
tip = next(i for i, (u, v) in enumerate(e) if u == 0)
c = [1.0] * 27; c[tip] = 0.99
_, _, V = P.solve(n, e, c, Z)
e099, _ = P.enhanced_projected(V, e, Z)
check("cross-validation: E(s=0.99) reproduces the manuscript to 6 s.f.", abs(e099 - 0.164032) < 5e-7,
      "ours %.8f vs manuscript 0.164032 (Table 'default control')" % e099)

# 3 -- the exact gap, and the manuscript's reported gap statistic
h = P.hamiltonian(15, e, [1.0] * 27, Z)
w = np.sort(eigsh(h, k=10, which="SA", tol=0, maxiter=200000,
                  v0=np.random.default_rng(7).standard_normal(1 << 15), return_eigenvectors=False))
gap = float(w[np.abs(w - w[0]) > 1e-8][0] - w[0])
recon = np.array([gap] * 4 + [0.0])
check("manuscript gap 0.1486+/-0.0743 == mean/std of {g,g,g,g,0}, g = exact gap",
      abs(recon.mean() - 0.1486) < 5e-4 and abs(recon.std() - 0.0743) < 5e-4,
      "exact gap %.5f -> mean %.4f std %.4f ; inverting the reported mean gives %.5f"
      % (gap, recon.mean(), recon.std(), 0.1486 * 5 / 4))

# 4 -- the ratio identity: the valley position IS the background coupling
byj: dict = {}
for r in rows:
    if r["kind"] == "ratio":
        byj.setdefault(r["j0"], {})[r["ratio"]] = r["E"]
mins = {j0: min(v, key=v.get) for j0, v in byj.items()}
dev = max(abs(byj[j0][k] - byj[1.0][k]) for j0 in byj for k in set(byj[j0]) & set(byj[1.0]))
check("E depends only on s/J0, so the valley sits at s = J0", all(abs(m - 1.0) < 1e-9 for m in mins.values()),
      "minima at ratio %s for J0 %s ; curves agree to %.1e"
      % (sorted(set(round(m, 3) for m in mins.values())), sorted(byj), dev))

# 5 -- the valley has no width
width = {}
for s in (0.9999, 1.0, 1.0001):
    cc = [1.0] * 27; cc[tip] = s
    _, dg, VV = P.solve(n, e, cc, Z)
    width[s] = (P.enhanced_projected(VV, e, Z)[0], dg)
check("the feature is one point wide and co-located with a degeneracy jump",
      width[0.9999][1] == 2 and width[1.0][1] == 4 and width[1.0001][1] == 2
      and width[1.0][0] < width[0.9999][0] - 0.04,
      "E/deg: %.6f/%d -> %.6f/%d -> %.6f/%d"
      % (width[0.9999][0], width[0.9999][1], width[1.0][0], width[1.0][1],
         width[1.0001][0], width[1.0001][1]))

# 6 -- the tree is the internal control: no degeneracy jump, and no valley either
SU2 = json.loads((HERE / "edrn_su2_invariant_scan.result.json").read_text())
tr = SU2["tree15"]
tE = dict(zip(tr["s"], tr["E"]))
check("tree: ground state non-degenerate throughout, and NO valley at s=1",
      set(tr["sector_degeneracy"]) == {1} and abs(tr["argmin_s"] - 1.0) > 0.05,
      "Sz-sector degeneracy %s at every s; minimum at s=%.2f not 1.0; E(0.95)=%.6f E(1.00)=%.6f E(1.05)=%.6f "
      "-- manuscript reports a tree valley at s=1.0 of depth 0.1926"
      % (sorted(set(tr["sector_degeneracy"])), tr["argmin_s"], tE[0.95], tE[1.0], tE[1.05]))

# 6b -- and the graphs that DO show the feature are exactly those with a degeneracy jump
fr, rg = SU2["fractal_L2"], SU2["ring15"]
frE, rgE = dict(zip(fr["s"], fr["E"])), dict(zip(rg["s"], rg["E"]))
check("valley present exactly where the degeneracy jumps (SU(2)-invariant observable)",
      set(fr["sector_degeneracy"]) == {1, 2} and set(rg["sector_degeneracy"]) == {1, 2}
      and abs(fr["argmin_s"] - 1.0) < 1e-9 and abs(rg["argmin_s"] - 1.0) < 1e-9 and rgE[1.0] < 1e-12,
      "fractal %.6f->%.6f->%.6f ; ring %.6f->%.6f->%.6f (exact zero at the uniform point)"
      % (frE[0.95], frE[1.0], frE[1.05], rgE[0.95], rgE[1.0], rgE[1.05]))

# 6c -- the two implementations are bound by isotropy: averaging <sz sz> over a full spin multiplet
# must equal (1/3)<sigma.sigma>. One is computed in the full 32768 space, the other in the 6435-state
# Sz sector by a different routine. If they agree to 6 s.f. at many points, neither is improvising.
worst, npts = 0.0, 0
for gname in ("fractal_L2", "ring15"):
    proj = {r_["s"]: r_["E"] for r_ in rows if r_["kind"] == "scan" and r_["graph"] == gname}
    inv = dict(zip(SU2[gname]["s"], SU2[gname]["E"]))
    for sv in sorted(set(proj) & set(inv)):
        if abs(sv - 1.0) < 1e-9:
            continue                      # at the degenerate point the ground space spans two multiplets
        worst = max(worst, abs(proj[sv] - inv[sv] / 3.0)); npts += 1
check("isotropy binds the two independent implementations: <sz sz>_multiplet == (1/3)<sigma.sigma>",
      worst < 1e-6 and npts > 80,
      "max deviation %.2e over %d shared scan points, two different state spaces and routines" % (worst, npts))

# 6d -- the feature does not survive a CONTINUOUS observable. The ground space at s=1 contains the
# state that continues from either side; the value it carries equals both one-sided limits, so the
# continuous continuation of E through s=1 has no feature at all.
DISC = json.loads((HERE / "edrn_the_observable_is_discontinuous_at_s1.result.json").read_text())
check("the continuous continuation of E through s=1 shows NO feature",
      DISC["continuous_continuation_has_no_feature"] and DISC["gap_max_vs_limits"] < 5e-4,
      "one-sided limits ~0.159660 vs attainable max at s=1 %.8f (differ by %.1e); the symmetric "
      "mixture over the enlarged space gives %.8f, and the manuscript's own default-control table "
      "reports 0.159658 -- i.e. its other calculation already lands on the continuous value"
      % (DISC["attainable_max"], DISC["gap_max_vs_limits"], DISC["at_s1_symmetric"]))

# 7 -- structure: no two tips adjacent, verified by two isomorphic constructions
g = nx.Graph(e)
tips = [v for v in g if g.degree(v) == 2]
n1, e1 = P.sierpinski_sieve(1); g1 = nx.Graph(e1); t1 = [v for v in g1 if g1.degree(v) == 2]
G = nx.Graph()
for cpy in range(3):
    G.add_edges_from(((cpy, u), (cpy, v)) for u, v in e1)
for a, b in [((0, t1[1]), (1, t1[0])), ((1, t1[2]), (2, t1[1])), ((2, t1[0]), (0, t1[2]))]:
    G = nx.contracted_nodes(G, a, b, self_loops=False)
check("no edge joins two tip vertices (two independent constructions, isomorphic)",
      nx.is_isomorphic(G, g) and not any(g.has_edge(u, v) for u, v in itertools.combinations(tips, 2)),
      "tips %s, pairwise distance %s, isomorphic=%s"
      % (tips, [nx.shortest_path_length(g, u, v) for u, v in itertools.combinations(tips, 2)],
         nx.is_isomorphic(G, g)))

# 8 -- no REAL edge can produce range 0.000000
ed: dict = {}
for r in rows:
    if r["kind"] == "edges":
        ed.setdefault(r["edge_index"], {})[r["s"]] = r["E"]
rng = {i: max(x for s, x in v.items() if s != 1.0) - min(x for s, x in v.items() if s != 1.0)
       for i, v in ed.items()}
lo = min(rng, key=rng.get)
check("every one of the 27 real edges moves the observable", rng[lo] > 1e-3,
      "least sensitive edge %s gives range %.6f over s in [0,0.9]; manuscript's control edge reports "
      "0.000000 with scatter 1.4e-11" % (EDGES[lo], rng[lo]))

w_ = max(len(c[0]) for c in checks)
print("EDRN claim receipt -- %d checks\n" % len(checks))
for name, ok, detail in checks:
    print("  [%s] %-*s  %s" % ("PASS" if ok else "FAIL", w_, name, detail))
bad = [c for c in checks if not c[1]]
print("\n%d/%d verified" % (len(checks) - len(bad), len(checks)))
sys.exit(1 if bad else 0)
