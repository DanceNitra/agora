"""Every number in the outbound EDRN letter, re-derived and checked against the letter's text.

The letter goes to a co-author who is about to submit, and it corrects advice we gave him that was
wrong. So no figure in it may rest on a note: each one is recomputed here and compared both to the
computation and to the string actually present in the draft. Exits non-zero on any mismatch.

Run: python probes/edrn_letter_numbers.py
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

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "probes"
TOOL = ROOT / "agora_output" / "hotrg_edrn"
LETTER = ROOT / "agora_output" / "drafts" / "edrn_reverification_2026-08-18.md"

spec = importlib.util.spec_from_file_location("edrn", HERE / "edrn_valley_is_the_uniform_point.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

TEXT = LETTER.read_text(encoding="utf-8")
SW = json.loads((HERE / "edrn_smallworld_exact.result.json").read_text())
RUN = json.loads((HERE / "edrn_valley_is_the_uniform_point.result.json").read_text())

Z = P._z_table(15)
IDX = np.nonzero(Z.sum(axis=0) == 1)[0]
ZI = Z[:, IDX].astype(np.float64)
RNG = np.random.default_rng(20260818)
checks: list[tuple[str, bool, str]] = []


def ck(name, ok, detail):
    checks.append((name, bool(ok), detail))


def says(*bits):
    missing = [b for b in bits if b not in TEXT]
    return (not missing), missing


def sector(edges, coup, k=6, tol=1e-8):
    h = P.hamiltonian(15, edges, coup, Z).tocsr()[IDX][:, IDX]
    w, v = eigsh(h, k=k, which="SA", tol=0, maxiter=300000,
                 v0=np.random.default_rng(1).standard_normal(IDX.size))
    o = np.argsort(w)
    w, v = w[o], v[:, o]
    d = int(np.sum(w - w[0] < tol))
    return v[:, :d], d


def mats(B, edges):
    M = np.empty((len(edges), B.shape[1], B.shape[1]))
    for k, (i, j) in enumerate(edges):
        wg = ZI[i] * ZI[j]
        M[k] = B.T @ (wg[:, None] * B)
    return M


def Eof(c, M):
    return float(np.real(np.einsum("a,kab,b->k", np.conj(c), M, c)).std())


def span(M, d, cplx):
    """Extrema over the ground space. For d=2 every state is c = (cos t, e^{if} sin t), so this is a
    two-parameter optimisation with a determined answer -- NOT a minimum over random draws. Sampling
    gave 0.110269 and 0.110284 on two runs of the same quantity, and 0.001251 vs 0.000373 for the
    ring whose true infimum is exactly zero; a quoted six-decimal sampling artefact is not a number."""
    if d != 2:
        raise ValueError("this exact form assumes a 2-dimensional ground space, got %d" % d)
    ts = np.linspace(0, np.pi / 2, 721)
    fs = np.linspace(0, 2 * np.pi, 1441) if cplx else np.array([0.0, np.pi])
    V = np.array([[Eof(np.array([np.cos(t), np.exp(1j * f) * np.sin(t)]), M) for t in ts] for f in fs])
    return float(V.min()), float(V.max())


nF, eF = P.sierpinski_sieve(2)
TIP = next(i for i, (u, v) in enumerate(eF) if u == 0)
nR, eR = P.ring(15)


def curve_at(s, edges=eF, tgt=None):
    tgt = TIP if tgt is None else tgt
    c = [1.0] * len(edges)
    c[tgt] = float(s)
    B, d = sector(edges, c)
    return Eof(np.eye(d)[0].astype(complex), mats(B, edges)), d


# 1 -- the real/complex table the letter prints
Bf, df = sector(eF, [1.0] * 27)
Mf = mats(Bf, eF)
fr = span(Mf, df, False)
fc = span(Mf, df, True)
Br, dr = sector(eR, [1.0] * 15)
Mr = mats(Br, eR)
rr = span(Mr, dr, False)
rc = span(Mr, dr, True)
ok, miss = says("0.159658 .. 0.159658", "0.110269 .. 0.159658",
                "0.130979 .. 0.130979", "0.000000 .. 0.130979")
ck("the real-vs-complex table", ok and df == 2 and dr == 2
   and abs(fr[1] - 0.159658) < 5e-6 and abs(fc[0] - 0.110269) < 5e-7
   and abs(rr[1] - 0.130979) < 5e-6 and rc[0] < 1e-9,
   "fractal real %.6f..%.6f complex %.6f..%.6f | ring real %.6f..%.6f complex %.6f..%.6f%s"
   % (fr[0], fr[1], fc[0], fc[1], rr[0], rr[1], rc[0], rc[1], "" if ok else " MISSING %s" % miss))

# 2 -- the ring's momentum eigenstates give exactly zero
rot = ((IDX << 1) | (IDX >> 14)) & ((1 << 15) - 1)
pos = -np.ones(1 << 15, dtype=np.int64)
pos[IDX] = np.arange(IDX.size)
Tg = Br[pos[rot], :].T @ Br
ev, evec = np.linalg.eig(Tg)
mom = [Eof(evec[:, a] / np.linalg.norm(evec[:, a]), Mr) for a in range(dr)]
ck("ring momentum eigenstates give exactly zero dispersion",
   max(mom) < 1e-9 and all(abs(abs(x) - 1) < 1e-8 for x in ev) and says("exactly zero")[0],
   "E on the two translation eigenstates = %s ; |eigenvalues of T| = %s"
   % (["%.1e" % x for x in mom], ["%.6f" % abs(x) for x in ev]))

# 3 -- the three curve points and the prominence
c098, _ = curve_at(0.98)
c100, d100 = curve_at(1.00)
c102, _ = curve_at(1.02)
grid = np.arange(0.0, 3.0001, 0.05)
cv = np.array([curve_at(float(s))[0] for s in grid])
i = int(np.argmin(cv))
prom = float(min(cv[:i].max(), cv[i + 1:].max()) - cv[i])
ok, miss = says("0.171192", "0.159658 at s = 1.00", "0.161712", "0.0888")
ck("the fixed-sector curve has a smooth interior minimum at s=1.000",
   ok and abs(c098 - 0.171192) < 5e-6 and abs(c100 - 0.159658) < 5e-6
   and abs(c102 - 0.161712) < 5e-6 and abs(grid[i] - 1.0) < 1e-9 and abs(prom - 0.0888) < 5e-4,
   "0.98/1.00/1.02 = %.6f/%.6f/%.6f ; min at s=%.2f ; prominence %.6f%s"
   % (c098, c100, c102, grid[i], prom, "" if ok else " MISSING %s" % miss))

# 4 -- the depth interval
e0 = cv[0]
lo_d, hi_d = e0 - fc[1], e0 - fc[0]
ok, miss = says("0.246731", "0.087073", "0.136462", "0.099826")
ck("the depth is an interval, and E(0) matches the manuscript's own baseline",
   ok and abs(e0 - 0.246731) < 5e-6 and abs(lo_d - 0.087073) < 5e-5 and abs(hi_d - 0.136462) < 5e-6,
   "E(0)=%.6f -> depth %.6f .. %.6f%s" % (e0, lo_d, hi_d, "" if ok else " MISSING %s" % miss))

# 5 -- exact degeneracy, the gap, and the reconstruction
h = P.hamiltonian(15, eF, [1.0] * 27, Z)
w = np.sort(eigsh(h, k=8, which="SA", tol=0, maxiter=300000,
                  v0=np.random.default_rng(11).standard_normal(1 << 15), return_eigenvectors=False))
split, gap = float(w[3] - w[0]), float(w[4] - w[0])
rec = np.array([gap] * 4 + [0.0])
ok, miss = says("1.8e-13", "0.185709", "0.1486", "0.0743")
ck("four-fold and exactly degenerate; the gap statistic reconstructs",
   ok and int(np.sum(w - w[0] < 1e-8)) == 4 and split < 3e-13 and abs(gap - 0.185709) < 5e-7
   and abs(rec.mean() - 0.1486) < 5e-5 and abs(rec.std() - 0.0743) < 5e-5,
   "degeneracy 4, splitting %.1e, gap %.6f -> %.4f +/- %.4f%s"
   % (split, gap, rec.mean(), rec.std(), "" if ok else " MISSING %s" % miss))

# 6 -- E(0.99) agreement with the manuscript
e099, _ = curve_at(0.99)
ok, miss = says("0.16403207", "0.164032")
ck("E(0.99) agrees with the manuscript to six figures",
   ok and abs(e099 - 0.16403207) < 5e-8, "%.8f%s" % (e099, "" if ok else " MISSING %s" % miss))

# 7 -- structure
src = TOOL.joinpath("dmrg_valley.py").read_text(encoding="utf-8")
ns: dict = {}
a = src.index("def sierpinski_graph")
exec("import networkx as nx\n" + src[a:src.index("\ndef ", a + 5)], ns)
G = ns["sierpinski_graph"](2)
tips = sorted(v for v in G if G.degree(v) == 2)
d_tips = {nx.shortest_path_length(G, u, v) for u, v in itertools.combinations(tips, 2)}
ok, miss = says("vertex 0 -> neighbours [6, 8]", "vertex 1 -> neighbours [9, 11]",
                "vertex 2 -> neighbours [12, 14]")
ck("tips 0,1,2 at distance 4; (0,6) is an edge, (0,1) and (0,2) are not",
   ok and tips == [0, 1, 2] and sorted(G[0]) == [6, 8] and sorted(G[1]) == [9, 11]
   and sorted(G[2]) == [12, 14] and d_tips == {4} and G.has_edge(0, 6)
   and not G.has_edge(0, 1) and not G.has_edge(0, 2),
   "tips %s, distances %s, (0,6)=%s (0,1)=%s (0,2)=%s%s"
   % (tips, sorted(d_tips), G.has_edge(0, 6), G.has_edge(0, 1), G.has_edge(0, 2),
      "" if ok else " MISSING %s" % miss))

# 8 -- our own toolchain lines
h40 = TOOL.joinpath("hotrg.py").read_text(encoding="utf-8").splitlines()[39]
dv = src.splitlines()
ok, miss = says("SX_i SX_j + SZ_i SZ_j", "(0,2,s)")
ck("the two source lines we quote from our own toolchain",
   ok and "SX" in h40 and "SZ" in h40 and "SY" not in h40
   and not any("Sigmay" in l for l in dv) and "(0,2,s)" in dv[78].replace(" ", ""),
   "hotrg.py:40 %s%s" % (h40.strip(), "" if ok else " MISSING %s" % miss))

# 9 -- the ratio identity numbers
byj: dict = {}
for r in RUN["rows"]:
    if r["kind"] == "ratio":
        byj.setdefault(r["j0"], {})[r["ratio"]] = r["E"]
dev = max(abs(byj[j][k] - byj[1.0][k]) for j in byj for k in set(byj[j]) & set(byj[1.0]))
mins = {j: min(v, key=v.get) for j, v in byj.items()}
ok, miss = says("H(s,J₀) = J₀·H(s/J₀,1)", "3e-14")
ck("the ratio identity: the minimum sits at s = J0 for every background",
   ok and all(abs(m - 1.0) < 1e-9 for m in mins.values()) and dev < 3e-14,
   "minima at ratio %s for J0 %s ; curves coincide to %.1e%s"
   % (sorted({round(m, 3) for m in mins.values()}), sorted(byj), dev,
      "" if ok else " MISSING %s" % miss))

# 10 -- small world
theirs = {(0, 1): 1.496, (1, 9): 0.311, (1, 4): 1.251, (1, 8): 0.720, (1, 6): 0.800, (2, 3): 1.090,
          (2, 4): 0.940, (2, 5): 0.750, (3, 4): 0.840, (3, 5): 0.980, (4, 5): 1.100, (4, 6): 0.910,
          (5, 6): 1.080, (6, 7): 0.470, (6, 8): 1.380, (7, 8): 0.000, (7, 9): 2.140}
match = interior = 0
degs, gaps, proms = set(), [], []
for ei, eg in enumerate([tuple(x) for x in SW["edges"]]):
    cur = SW["curves"][str(ei)]
    ss = np.array([r[0] for r in cur])
    Ev = np.array([r[1] for r in cur])
    degs |= {r[2] for r in cur}
    k = int(np.argmin(Ev))
    gaps.append(cur[k][3])
    if eg in theirs and abs(ss[k] - theirs[eg]) <= 0.011:
        match += 1
    if 0 < k < len(Ev) - 1:
        interior += 1
        proms.append(min(Ev[:k].max(), Ev[k + 1:].max()) - Ev[k])
ok, miss = says("17 of your 17 quoted valley positions", "19 of 20 edges have an interior minimum",
                "0.34–1.02", "0.000484", "0.124434", "17 of 20 survive a threshold")
ck("small-world: reproduces, non-degenerate throughout, prominence counts",
   ok and degs == {1} and match == 17 and interior == 19
   and abs(min(gaps) - 0.34) < 0.01 and abs(max(gaps) - 1.02) < 0.01
   and abs(min(proms) - 0.000484) < 5e-6 and abs(max(proms) - 0.124434) < 5e-6
   and sum(p >= 0.01 for p in proms) == 17 and sum(p >= 0.02 for p in proms) == 15,
   "%d/17 positions, %d/20 interior, degeneracies %s, gaps %.2f-%.2f, prominence %.6f-%.6f, "
   "17@0.01=%s 15@0.02=%s%s"
   % (match, interior, sorted(degs), min(gaps), max(gaps), min(proms), max(proms),
      sum(p >= 0.01 for p in proms), sum(p >= 0.02 for p in proms),
      "" if ok else " MISSING %s" % miss))

# 11 -- the guard tool really exists and really refuses
ck("scan_guard.py is in the shared repository", (TOOL / "scan_guard.py").exists(),
   str((TOOL / "scan_guard.py").relative_to(ROOT)))

wd = max(len(c[0]) for c in checks)
print("EDRN letter -- %d claim groups\n" % len(checks))
for name, okv, detail in checks:
    print("  [%s] %-*s\n        %s" % ("PASS" if okv else "FAIL", wd, name, detail))
bad = [c for c in checks if not c[1]]
print("\n%d/%d verified" % (len(checks) - len(bad), len(checks)))
sys.exit(1 if bad else 0)
