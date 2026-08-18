"""Every number in the EDRN correction comment, re-derived and checked against the draft's text.

This message corrects a claim we already posted, so it has to be right in a way the first one was
not. Each figure is recomputed here and matched both to the computation and to the string present in
the draft. Exits non-zero on any mismatch.

Run: python probes/edrn_correction_numbers.py
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import pathlib
import sys

import networkx as nx
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "probes"
TOOL = ROOT / "agora_output" / "hotrg_edrn"
DRAFT = ROOT / "agora_output" / "drafts" / "edrn_correction_2026-08-18b.md"

spec = importlib.util.spec_from_file_location("edrn", HERE / "edrn_valley_is_the_uniform_point.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
sgspec = importlib.util.spec_from_file_location("sg", TOOL / "scan_guard.py")
SG = importlib.util.module_from_spec(sgspec)
sgspec.loader.exec_module(SG)

TEXT = DRAFT.read_text(encoding="utf-8")
SWEEP = json.loads((HERE / "edrn_smallworld_seed_sweep.result.json").read_text())
TREND = json.loads((HERE / "edrn_smallworld_size_trend.result.json").read_text())
EXACT = json.loads((HERE / "edrn_smallworld_exact.result.json").read_text())

Z = P._z_table(15)
IDX = np.nonzero(Z.sum(axis=0) == 1)[0]
ZI = Z[:, IDX].astype(np.float64)
checks: list[tuple[str, bool, str]] = []


def ck(name, ok, detail):
    checks.append((name, bool(ok), detail))


def says(*bits):
    miss = [b for b in bits if b not in TEXT]
    return (not miss), miss


# ---------------------------------------------------------------- tree
nT, eT = P.binary_tree(15)
allpairs = list(itertools.combinations(range(15), 2))
S2 = 0.5 * P.hamiltonian(15, allpairs, [1.0] * len(allpairs), Z) + (3 * 15 / 4) * sp.eye(1 << 15, format="csr")


def tree_point(s, k=10):
    c = [1.0] * len(eT)
    c[0] = float(s)
    h = P.hamiltonian(15, eT, c, Z).tocsr()[IDX][:, IDX]
    w, V = eigsh(h, k=k, which="SA", tol=0, maxiter=300000,
                 v0=np.random.default_rng(2).standard_normal(IDX.size))
    o = np.argsort(w)
    w, V = w[o], V[:, o]
    d = int(np.sum(w - w[0] < 1e-8))
    p = V[:, 0] ** 2
    return float(np.array([p @ (ZI[i] * ZI[j]) for i, j in eT]).std()), d


hf = P.hamiltonian(15, eT, [1.0] * len(eT), Z).tocsr()
wf, Vf = eigsh(hf, k=10, which="SA", tol=0, maxiter=300000,
               v0=np.random.default_rng(2).standard_normal(1 << 15))
of = np.argsort(wf)
wf, Vf = wf[of], Vf[:, of]
df = int(np.sum(wf - wf[0] < 1e-8))
s2 = [float(Vf[:, a] @ (S2.tocsr() @ Vf[:, a])) for a in range(df)]
nA, nB = 1 + 4, 2 + 8
ok, miss = says("⟨S²⟩ = 8.7500", "S = 5/2", "5 against 10")
ck("the tree's total spin is 5/2 on every ground state, as Lieb-Mattis requires",
   ok and all(abs(x - 8.75) < 1e-6 for x in s2) and abs(nA - nB) / 2 == 2.5,
   "<S^2> = %s ; bipartition %d vs %d -> S=%.1f%s"
   % (["%.4f" % x for x in s2], nA, nB, abs(nA - nB) / 2, "" if ok else " MISSING %s" % miss))

grid = np.arange(0.0, 3.0001, 0.02)
tv = [tree_point(float(s)) for s in grid]
E = np.array([x[0] for x in tv])
D = [x[1] for x in tv]
i = int(np.argmin(E))
prom = float(min(E[:i].max(), E[i + 1:].max()) - E[i])
degs_off0 = {d for s, d in zip(grid, D) if s > 0}
ok, miss = says("s = 0.92, E = 0.115598", "0.096864", "0.215628", "0.100030")
ck("the tree scan: unique sector state off s=0, and its minimum, prominence and depth",
   ok and degs_off0 == {1} and abs(grid[i] - 0.92) < 1e-9 and abs(E[i] - 0.115598) < 5e-6
   and abs(prom - 0.096864) < 5e-6 and abs(E[0] - 0.215628) < 5e-6
   and abs(E.max() - E[i] - 0.100030) < 5e-6,
   "degeneracy off s=0: %s (at s=0 it is %d) ; min %.6f at s=%.2f ; prominence %.6f ; E(0)=%.6f ; "
   "depth %.6f%s" % (sorted(degs_off0), D[0], E[i], grid[i], prom, E[0], E.max() - E[i],
                     "" if ok else " MISSING %s" % miss))

flat = [float(s) for s, v in zip(grid, E) if v - E[i] < 1e-3]
var = float(max(v for s, v in zip(grid, E) if min(flat) <= s <= max(flat)) - E[i])
ok, miss = says("s ∈ [0.84, 0.98]", "7.5e-4")
ck("the tree minimum is flat over [0.84, 0.98], varying by 7.5e-4",
   ok and abs(min(flat) - 0.84) < 1e-9 and abs(max(flat) - 0.98) < 1e-9 and abs(var - 7.5e-4) < 5e-6,
   "within 1e-3 of the minimum over %.2f..%.2f, varying by %.2e%s"
   % (min(flat), max(flat), var, "" if ok else " MISSING %s" % miss))

ok, miss = says("0.1926", "0.1481 ± 0.0461", "[0.1020, 0.1942]")
ck("the manuscript's tree figures are transcribed correctly",
   ok and abs((0.1481 - 0.0461) - 0.1020) < 5e-5 and abs((0.1481 + 0.0461) - 0.1942) < 5e-5,
   "interval from 0.1481 +/- 0.0461 is [%.4f, %.4f]%s"
   % (0.1481 - 0.0461, 0.1481 + 0.0461, "" if ok else " MISSING %s" % miss))

# ---------------------------------------------------------------- size trend
seed42 = {}
for n in ("10", "12", "14"):
    pr = [p["prominence"] for p in TREND[n]["per_edge"] if p["prominence"] is not None]
    seed42[n] = float(np.median(pr))
ok, miss = says("0.047736 / 0.045620 /\n0.007216")
ck("the seed-42 medians that first looked like a collapse",
   all(abs(seed42[n] - v) < 5e-6 for n, v in
       (("10", 0.047736), ("12", 0.045620), ("14", 0.007216))),
   "%.6f / %.6f / %.6f" % (seed42["10"], seed42["12"], seed42["14"]))

per_n = {}
for r in SWEEP.values():
    per_n.setdefault(r["n"], []).append(r)
means = {n: float(np.mean([r["median_prominence"] for r in rs])) for n, rs in per_n.items()}
rng = {n: (min(r["median_prominence"] for r in rs), max(r["median_prominence"] for r in rs))
       for n, rs in per_n.items()}
scaled = {n: float(np.mean([r["median_scaled"] for r in rs])) for n, rs in per_n.items()}
ok, miss = says("0.034234", "0.026250", "0.018427",
                "[0.011364, 0.047724]", "[0.004505, 0.052421]", "[0.007216, 0.035564]",
                "0.153 / 0.129 / 0.098")
ck("the five-seed means, ranges, and the edge-count-scaled trend",
   ok and all(abs(means[n] - v) < 5e-6 for n, v in ((10, 0.034234), (12, 0.026250), (14, 0.018427)))
   and all(abs(rng[n][0] - a) < 5e-6 and abs(rng[n][1] - b) < 5e-6 for n, (a, b) in
           ((10, (0.011364, 0.047724)), (12, (0.004505, 0.052421)), (14, (0.007216, 0.035564))))
   and all(abs(round(scaled[n], 3) - v) < 5e-4 for n, v in ((10, 0.153), (12, 0.129), (14, 0.098))),
   "means %s ; scaled %s%s"
   % ({n: round(v, 6) for n, v in sorted(means.items())},
      {n: round(v, 3) for n, v in sorted(scaled.items())}, "" if ok else " MISSING %s" % miss))

# the ranges must actually overlap, or the caveat is wrong
overlap = min(rng[10][1], rng[12][1], rng[14][1]) > max(rng[10][0], rng[12][0], rng[14][0])
ck("the ranges genuinely overlap, which is what makes the caveat true",
   overlap and says("ranges overlap heavily")[0],
   "N=10 %s, N=12 %s, N=14 %s -- common region [%.6f, %.6f]"
   % (rng[10], rng[12], rng[14], max(r[0] for r in rng.values()), min(r[1] for r in rng.values())))

unsafe_graphs = sum(1 for r in SWEEP.values() if r["unsafe_gap"] > 0)
unsafe_edges = sum(r["unsafe_gap"] for r in SWEEP.values())
gaps14 = [p["gap_at_min"] for p in TREND["14"]["per_edge"]]
worst = min(gaps14)
worst_edge = TREND["14"]["per_edge"][int(np.argmin(gaps14))]["edge"]
ok, miss = says("5 edges in 4 of them", "3.0e-04", "(6,8)")
ck("the vanishing-gap edges: 5 edges across 4 of the 15 graphs",
   ok and unsafe_edges == 5 and unsafe_graphs == 4 and len(SWEEP) == 15
   and abs(worst - 3.0e-4) < 5e-6 and worst_edge == [6, 8],
   "%d edges across %d of %d graphs; smallest %.1e on N=14 edge %s%s"
   % (unsafe_edges, unsafe_graphs, len(SWEEP), worst, tuple(worst_edge),
      "" if ok else " MISSING %s" % miss))

# positive control: the sector routine vs the independent full-space run at N=10
oldmin = {}
for ei, e in enumerate([tuple(x) for x in EXACT["edges"]]):
    cur = EXACT["curves"][str(ei)]
    oldmin[e] = cur[int(np.argmin([c[1] for c in cur]))][0]
agree = sum(1 for p in TREND["10"]["per_edge"] if abs(p["s_star"] - oldmin[tuple(p["edge"])]) <= 0.011)
ck("positive control: the sector routine reproduces the full-space run at N=10",
   agree == 20 and says("20 of\n20 edges")[0], "%d/20 edges agree" % agree)

# ---------------------------------------------------------------- isotropic vs XX+ZZ
src = (TOOL / "dmrg_valley.py").read_text(encoding="utf-8")
ns: dict = {}
a = src.index("def sierpinski_graph")
exec("import networkx as nx\n" + src[a:src.index("\ndef ", a + 5)], ns)
G = ns["sierpinski_graph"](2)
edges = sorted(tuple(sorted(x)) for x in G.edges())
CE = (0, 6)
near = {v for v in G if min(nx.shortest_path_length(G, v, CE[0]),
                            nx.shortest_path_length(G, v, CE[1])) <= 2}
local = [k for k, (u, v) in enumerate(edges) if u in near and v in near]
tgt = edges.index(CE)


def depths(iso):
    g, l = [], []
    for s in np.arange(0.0, 3.0001, 0.02):
        c = [1.0] * 27
        c[tgt] = float(s)
        h = SG._H(15, edges, c, Z, iso).tocsr()[IDX][:, IDX]
        w, V = eigsh(h, k=6, which="SA", tol=0, maxiter=300000,
                     v0=np.random.default_rng(3).standard_normal(IDX.size))
        o = np.argsort(w)
        V = V[:, o]
        p = V[:, 0] ** 2
        corr = np.array([p @ (ZI[i] * ZI[j]) for i, j in edges])
        g.append(float(corr.std()))
        l.append(float(corr[local].std()))
    g, l = np.array(g), np.array(l)
    return float(g.max() - g.min()), float(l.max() - l.min())


gi, li = depths(True)
gx, lx = depths(False)
ok, miss = says("0.143538", "0.144542", "0.263346", "0.276416", "12 of 27 edges")
ck("isotropic vs XX+ZZ, global and local (radius-2, 12 of 27 edges)",
   ok and len(local) == 12 and abs(gi - 0.143538) < 5e-6 and abs(gx - 0.144542) < 5e-6
   and abs(li - 0.263346) < 5e-6 and abs(lx - 0.276416) < 5e-6
   and abs(round(100 * abs(gx - gi) / gi, 1) - 0.7) < 0.05,
   "global iso %.6f vs xz %.6f (%.1f%%) ; local %.6f vs %.6f (%.0f%%) over %d edges%s"
   % (gi, gx, 100 * abs(gx - gi) / gi, li, lx, 100 * abs(lx - li) / li, len(local),
      "" if ok else " MISSING %s" % miss))

# ---------------------------------------------------------------- our own 0.1902
Gg = nx.Graph()
groups: list = []


def rec(v1, v2, v3, d, tag=None):
    if d == 0:
        for x, y in [(v1, v2), (v2, v3), (v3, v1)]:
            Gg.add_edge(x, y)
            groups.append((tuple(sorted((x, y))), tag))
        return
    m12 = max(Gg.nodes) + 1
    m23, m31 = m12 + 1, m12 + 2
    Gg.add_nodes_from([m12, m23, m31])
    rec(v1, m12, m31, d - 1, 0 if tag is None else tag)
    rec(v2, m23, m12, d - 1, 1 if tag is None else tag)
    rec(v3, m31, m23, d - 1, 2 if tag is None else tag)


Gg.add_nodes_from([0, 1, 2])
rec(0, 1, 2, 2)
sub: dict = {}
for e_, t in groups:
    sub.setdefault(t, set()).add(e_)
base = sorted(tuple(sorted(x)) for x in Gg.edges())
own = {t: [k for k, v in sub.items() if any(t in ed for ed in v)][0] for t in (0, 2)}
local18 = sorted(sub[own[0]] | sub[own[2]])
li18 = [base.index(x) for x in local18]
edges28 = base + [(0, 2)]


def depth18(iso):
    L = []
    for s in np.arange(0.0, 3.0001, 0.02):
        c = [1.0] * len(base) + [float(s)]
        h = SG._H(15, edges28, c, Z, iso).tocsr()[IDX][:, IDX]
        w, V = eigsh(h, k=6, which="SA", tol=0, maxiter=300000,
                     v0=np.random.default_rng(3).standard_normal(IDX.size))
        o = np.argsort(w)
        p = V[:, o][:, 0] ** 2
        corr = np.array([p @ (ZI[i] * ZI[j]) for i, j in base])
        L.append(float(corr[li18].std()))
    L = np.array(L)
    return float(L.max() - L.min())


d18x, d18i = depth18(False), depth18(True)
ok, miss = says("0.200462", "0.181144", "0.1902", "18 of the 27 edges")
ck("our own published 0.1902 is bracketed, not matched",
   ok and len(local18) == 18 and abs(d18x - 0.200462) < 5e-6 and abs(d18i - 0.181144) < 5e-6
   and d18i < 0.1902 < d18x,
   "18-edge local depth: XX+ZZ %.6f, isotropic %.6f ; published 0.1902 lies between%s"
   % (d18x, d18i, "" if ok else " MISSING %s" % miss))

# ---------------------------------------------------------------- the fixes we claim to have made
dv = (TOOL / "dmrg_valley.py").read_text(encoding="utf-8")
rm = (TOOL / "README.md").read_text(encoding="utf-8")
sg = (TOOL / "scan_guard.py").read_text(encoding="utf-8")
dv_code = dv.split('"""', 2)[-1]          # drop the module docstring, which QUOTES the old line
ck("the changes the message claims we made are actually in the files",
   "def assert_real_edge" in dv and "defect=(0, 6)" in dv
   and "(0,2,s)" not in dv_code.replace(" ", "") and "defect" in
   [l for l in dv_code.splitlines() if "edge_w=" in l.replace(" ", "")][0]
   and "CORRECTIONS, 2026-08-18" in rm and "treat 0.1902 as unverified" in rm
   and "def check_edge" in sg and "isolated_dim_spikes_at" in sg
   and says("assert_real_edge")[0],
   "dmrg_valley guarded and defaulting to (0,6); README carries the corrections; scan_guard has both")

wd = max(len(c[0]) for c in checks)
print("EDRN correction -- %d claim groups\n" % len(checks))
for name, okv, detail in checks:
    print("  [%s] %-*s\n        %s" % ("PASS" if okv else "FAIL", wd, name, detail))
bad = [c for c in checks if not c[1]]
print("\n%d/%d verified" % (len(checks) - len(bad), len(checks)))
sys.exit(1 if bad else 0)
