"""Every number in the EDRN ensemble letter, re-derived and matched against the draft's own text.

Each of the three previous messages in this thread carried a figure I had not re-derived, and the
gate caught two of them. This one recomputes from the result files (and, where the claim is about the
model itself, from scratch), then asserts the exact string is present in the draft. Exits non-zero on
any mismatch and prints what it expected.

Sources, deliberately separated so no number can drift to a file that did not produce it:
  * the ensemble table, trends, criterion and gap counts  -> edrn_smallworld_ensemble.result.json
    (100 graphs, 25 per size, the run of 18 August)
  * the variance decomposition and the re-run control     -> edrn_the_size_question_...result.json
  * the enrichment and solver controls                    -> edrn_is_the_vanishing_gap_...result.json
  * his Table I / Table II                                -> edrn_smallworld_size_trend.result.json
                                                             plus a fresh step-0.001 scan here

Run: python probes/edrn_ensemble_letter_numbers.py
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys

import networkx as nx
import numpy as np
from scipy.sparse.linalg import eigsh

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "probes"
DRAFT = ROOT / "agora_output" / "drafts" / "edrn_ensemble_2026-08-19.md"

ENS = json.loads((HERE / "edrn_smallworld_ensemble.result.json").read_text(encoding="utf-8"))
DENS = json.loads((HERE / "edrn_is_the_vanishing_gap_a_density_artifact.result.json")
                  .read_text(encoding="utf-8"))
V2 = json.loads((HERE / "edrn_the_size_question_needs_a_trend_test_not_a_pairwise_one.result.json")
                .read_text(encoding="utf-8"))
SEED42 = json.loads((HERE / "edrn_smallworld_size_trend.result.json").read_text(encoding="utf-8"))
TEXT = DRAFT.read_text(encoding="utf-8")

_g = importlib.util.spec_from_file_location("gk", HERE / "edrn_valley_is_the_uniform_point.py")
P = importlib.util.module_from_spec(_g)
_g.loader.exec_module(P)
_t = importlib.util.spec_from_file_location("trendmod", HERE / "edrn_smallworld_size_trend.py")
T = importlib.util.module_from_spec(_t)
_t.loader.exec_module(T)

SIZES = (10, 12, 14, 16)
ROWS = list(ENS.values())
checks: list[tuple[str, bool, str]] = []
expected: list[str] = []


def ck(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


def _norm(s):
    """Compare on content, not on typography: line wrapping and the minus glyph must not decide.

    Numbers, digits and separators survive this untouched, so a wrong figure still fails.
    """
    return re.sub(r"\s+", " ", s.replace("−", "-").replace(" ", " ")).strip()


NORM = None       # set after TEXT is read


def says(*bits):
    missing = [b for b in bits if _norm(b) not in NORM]
    for b in bits:
        expected.append(b)
    return (not missing), ("missing: " + " | ".join(missing) if missing else "")


NORM = _norm(TEXT)


def boot_mean_ci(vals, n=20000, seed=20260819):
    rng = np.random.default_rng(seed)
    a = np.asarray(vals, dtype=float)
    m = a[rng.integers(0, a.size, size=(n, a.size))].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def slope_ci(x, y, n=20000, seed=5):
    rng = np.random.default_rng(seed)
    b0 = float(np.polyfit(x, y, 1)[0])
    bs = np.empty(n)
    for t in range(n):
        i = rng.integers(0, x.size, size=x.size)
        while np.unique(x[i]).size < 2:
            i = rng.integers(0, x.size, size=x.size)
        bs[t] = np.polyfit(x[i], y[i], 1)[0]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return b0, float(lo), float(hi), bool(hi < 0 or lo > 0)


# ------------------------------------------------------- 1. the run as described
ck("ensemble size", *says("100 graphs, 25 per size", "k = 0..24", "2,600 edge"))
ck("100 graphs are what the file holds", len(ROWS) == 100, "%d rows" % len(ROWS))
ck("all graphs connected",
   all(nx.is_connected(nx.watts_strogatz_graph(n, 4, 0.1, seed=sd)) for n in SIZES for sd in range(25)))
ck("scan count matches", sum(r["edges"] for r in ROWS) == 2600, "%d" % sum(r["edges"] for r in ROWS))

# ------------------------------------------------------- 2. the model IS his Eq. (1)
sx = np.array([[0, 1], [1, 0]], float)
sy = np.array([[0, -1j], [1j, 0]])
sz = np.diag([1.0, -1.0])


def kron_site(n, ops):
    M = np.array([[1]], complex)
    for k in range(n - 1, -1, -1):
        M = np.kron(M, ops.get(k, np.eye(2)))
    return M


worst = 0.0
for n, edges, coup in ((2, [(0, 1)], [1.0]),
                       (3, [(0, 1), (1, 2), (0, 2)], [1.0, 0.7, 1.3]),
                       (4, [(0, 1), (1, 2), (2, 3), (0, 3)], [1.0, 1.0, 1.0, 0.4])):
    z = T.z_table(n)
    ours = T.hamiltonian(n, edges, coup, z, np.arange(1 << n)).toarray()
    ref = np.zeros((1 << n, 1 << n), complex)
    for (i, j), w in zip(edges, coup):
        for s_ in (sx, sy, sz):
            ref += w * kron_site(n, {i: s_, j: s_})
    worst = max(worst, float(np.abs(ours - ref).max()))
ck("H equals sigma.sigma to machine zero at N=2,3,4", worst == 0.0, "max dev %.1e" % worst)
ck("the draft says so", *says("machine zero at N = 2, 3, 4"))

# ------------------------------------------------------- 3. Sz=0 holds the ground state
viol = []
for n in (10, 12):
    for sd in (0, 1, 3, 7):
        g = nx.watts_strogatz_graph(n, 4, 0.1, seed=sd)
        edges = sorted(tuple(sorted(e)) for e in g.edges())
        for s in (0.5, 1.5):
            coup = [1.0] * len(edges)
            coup[0] = s
            z = T.z_table(n)
            best = None
            for m in range(0, n + 1, 2):
                idx = np.nonzero(z.sum(axis=0) == m)[0]
                if idx.size < 3:
                    continue
                h = T.hamiltonian(n, edges, coup, z, idx)
                e = (np.sort(np.linalg.eigvalsh(h.toarray()))[0] if idx.size <= 64 else
                     np.sort(eigsh(h, k=1, which="SA", tol=0, maxiter=300000,
                                   return_eigenvectors=False))[0])
                if best is None or e < best - 1e-10:
                    best = float(e)
            idx = np.nonzero(z.sum(axis=0) == 0)[0]
            h = T.hamiltonian(n, edges, coup, z, idx)
            e0 = float(np.sort(eigsh(h, k=1, which="SA", tol=0, maxiter=300000,
                                     return_eigenvectors=False))[0])
            if abs(e0 - best) > 1e-8:
                viol.append((n, sd, s))
ck("Sz=0 holds the global ground state, 16 configurations", not viol, str(viol[:3]))
ck("draft states it", *says("Sz = 0 sector holds the global ground state", "16 configurations"))

# ------------------------------------------------------- 4. the per-size table
for n in SIZES:
    rs = [r for r in ROWS if r["n"] == n]
    m = [r["median_prominence"] for r in rs]
    sc = [r["median_scaled"] for r in rs]
    lo, hi = boot_mean_ci(m)
    slo, shi = boot_mean_ci(sc)
    ck("table row N=%d" % n,
       *says("%.6f [%.6f, %.6f]" % (np.mean(m), lo, hi),
             "%.4f [%.4f, %.4f]" % (np.mean(sc), slo, shi),
             "%.1f of %d" % (np.mean([r["interior"] for r in rs]), 2 * n)))

# ------------------------------------------------------- 5. the trend test
N = np.array([r["n"] for r in ROWS], float)
Pm = np.array([r["median_prominence"] for r in ROWS], float)
Sc = np.array([r["median_scaled"] for r in ROWS], float)
Ai = np.array([r["n_ge_001"] / r["interior"] for r in ROWS], float)
Ii = np.array([r["interior"] / r["edges"] for r in ROWS], float)
Gi = np.array([1.0 if r["unsafe_gap"] else 0.0 for r in ROWS], float)

b, lo, hi, excl = slope_ci(N, np.log(Pm))
ck("raw trend excludes zero", excl, "[%+.5f, %+.5f]" % (lo, hi))
ck("raw trend numbers", *says("%+.5f" % b, "[%+.5f, %+.5f]" % (lo, hi), "x%.3f" % np.exp(6 * b)))
b, lo, hi, excl = slope_ci(N, np.log(Sc))
ck("scaled trend includes zero", not excl, "[%+.5f, %+.5f]" % (lo, hi))
ck("scaled trend numbers", *says("%+.5f" % b, "[%+.5f, %+.5f]" % (lo, hi), "x%.3f" % np.exp(6 * b)))

b, lo, hi, excl = slope_ci(N, Ai)
ck("criterion-share trend", excl, "[%+.5f, %+.5f]" % (lo, hi))
ck("criterion-share numbers", *says("%+.5f" % b, "[%+.5f, %+.5f]" % (lo, hi),
                                    "%.1f points" % abs(100 * 6 * b)))
b, lo, hi, excl = slope_ci(N, Ii)
ck("interior-share trend", excl, "[%+.5f, %+.5f]" % (lo, hi))
ck("interior-share numbers", *says("%+.5f" % b, "[%+.5f, %+.5f]" % (lo, hi),
                                   "%.1f points" % abs(100 * 6 * b)))
b, lo, hi, excl = slope_ci(N, Gi)
ck("gap-incidence trend", excl, "[%+.5f, %+.5f]" % (lo, hi))
ck("gap-incidence numbers", *says("%+.5f" % b, "[%+.5f, %+.5f]" % (lo, hi), "%d points" % round(100 * 6 * b)))

# ------------------------------------------------------- 6. criterion and gap tables
for n in SIZES:
    rs = [r for r in ROWS if r["n"] == n]
    it, ed = sum(r["interior"] for r in rs), sum(r["edges"] for r in rs)
    ge = sum(r["n_ge_001"] for r in rs)
    ue = sum(r["unsafe_gap"] for r in rs)
    inc = sum(1 for r in rs if r["unsafe_gap"])
    ck("criterion row N=%d" % n, *says("%d/%d  (%.1f%%)" % (it, ed, 100 * it / ed),
                                       "%d/%d  (%.1f%%)" % (ge, it, 100 * ge / it)))
    ck("gap row N=%d" % n, *says("%d/%d" % (ue, ed), "(%.1f%%)" % (100 * ue / ed), "%d/%d" % (inc, len(rs))))

r16 = [r for r in ROWS if r["n"] == 16]
w_all = sum(r["unsafe_gap"] for r in r16) / sum(r["edges"] for r in r16)
n16_0 = [r for r in r16 if r["seed"] != 0]
w_no0 = sum(r["unsafe_gap"] for r in n16_0) / sum(r["edges"] for r in n16_0)
seed0 = ENS["16_0"]["unsafe_gap"]
ck("seed-0 split", *says("7.8% to", "3.9%", "%d of the %d flagged edges"
                         % (seed0, sum(r["unsafe_gap"] for r in r16))))
ck("split arithmetic", abs(w_all - 0.0775) < 1e-3 and abs(w_no0 - 0.0391) < 1e-3,
   "%.4f / %.4f" % (w_all, w_no0))

# ------------------------------------------------------- 7. seed 0 is the ring lattice
def ring_lattice(n, k=4):
    g = nx.Graph()
    g.add_nodes_from(range(n))
    for i in range(n):
        for j in range(1, k // 2 + 1):
            g.add_edge(i, (i + j) % n)
    return g


ck("seed 0 is the unrewired ring lattice at every size",
   all(nx.is_isomorphic(nx.watts_strogatz_graph(n, 4, 0.1, seed=0), ring_lattice(n)) for n in SIZES))
g16 = nx.watts_strogatz_graph(16, 4, 0.1, seed=0)
aut = sum(1 for _ in nx.algorithms.isomorphism.GraphMatcher(g16, g16).isomorphisms_iter())
ck("|Aut| = 2N at N=16", aut == 32, "|Aut|=%d" % aut)
ck("all 32 of its edges flagged", seed0 == ENS["16_0"]["edges"], "%d of %d" % (seed0, ENS["16_0"]["edges"]))
ck("draft states it", *says("|Aut| = 2N", "all 32 of its edges are\nflagged"))

# ------------------------------------------------------- 8. the density / solver controls
dsum = DENS["summary"]
nsc = len(DENS["rows"])
npts = sum(r["n_points"] for r in DENS["rows"])
at = sum(dsum[str(n)]["0.05"]["at_min"] for n in SIZES)
bg = sum(dsum[str(n)]["0.05"]["background"] for n in SIZES)
enr = (at / nsc) / (bg / (npts - nsc))
ck("pooled enrichment", *says("%.1f×" % enr))

# the enrichment WITHOUT the unrewired ring lattice -- it inflates this number as well as the share
rw = [r for r in DENS["rows"] if r["seed"] != 0]
at_rw = sum(1 for r in rw if r["below_at_min"]["0.05"])
bg_rw = sum(r["below"]["0.05"] for r in rw) - at_rw
pts_rw = sum(r["n_points"] for r in rw) - len(rw)
enr_rw = (at_rw / len(rw)) / (bg_rw / pts_rw)
ck("enrichment over rewired graphs only",
   *says("%d flagged minima in %d edges" % (at_rw, len(rw)),
         "%d flagged points in %s" % (bg_rw, format(pts_rw, ",")),
         "%.1f×" % enr_rw))
ck("the ring lattice inflates it", enr > enr_rw, "all %.1f vs rewired %.1f" % (enr, enr_rw))
ck("background endpoints", *says("%.3f%%" % (100 * dsum["10"]["0.05"]["background_rate"]),
                                 "%.2f%%" % (100 * dsum["16"]["0.05"]["background_rate"])))
ark = DENS["arpack"]
ck("solver control clean", ark["moved"] == 0 and ark["survive"] == ark["flagged"],
   "flagged %d moved %d worst %.1e" % (ark["flagged"], ark["moved"], ark["worst"]))
gaps20 = [g20 for r in DENS["rows"] for _j, _g6, g20, _dd in r["recheck"]]
ndeg = sum(1 for r in DENS["rows"] for _j, _g6, _g20, dd in r["recheck"] if dd > 1)
ck("no exact degeneracy among flagged points", ndeg == 0, "%d degenerate" % ndeg)
ck("solver-control numbers", *says("%d flagged points" % ark["flagged"], "3.3e-13",
                                   "%.2e" % min(gaps20), "%.3f" % np.median(gaps20)))

# ------------------------------------------------------- 9. the re-run control + variance shares
ctrl = V2.get("control", {"reproduced": 0, "disagreed": -1})
ck("independent re-run reproduces", ctrl["disagreed"] == 0, "reproduced %d disagreed %d"
   % (ctrl["reproduced"], ctrl["disagreed"]))
ck("re-run control stated", *says("%d of them exactly" % ctrl["reproduced"]))
vs = V2.get("variance_share", {})
for n in SIZES:
    v = vs.get(str(n))
    if v is None:
        ck("variance share N=%d" % n, False, "absent from the v2 result file")
        continue
    ck("variance share N=%d" % n, *says("%.3f" % v["at_min_mean"], "%.3f" % v["flank_mean"],
                                        "%.3f" % v["uniform"]))

# ------------------------------------------------------- 10. his tables
per42 = {tuple(p["edge"]): p for p in SEED42["10"]["per_edge"]}
g42 = np.array([p["gap_at_min"] for p in SEED42["10"]["per_edge"]])
emin = SEED42["10"]["per_edge"][int(np.argmin(g42))]["edge"]
emax = SEED42["10"]["per_edge"][int(np.argmax(g42))]["edge"]
ck("seed-42 gap range", *says("%.4f to %.4f" % (g42.min(), g42.max()), "%.4f" % np.median(g42),
                              "(%d,%d)" % tuple(emin), "(%d,%d)" % tuple(emax)))

HIS = {(0, 1): 0.176842, (0, 9): 0.078783, (0, 2): 0.083366, (0, 8): 0.065437, (1, 9): 0.113332,
       (1, 4): 0.103002, (1, 8): 0.085229, (1, 6): 0.089372, (2, 3): 0.085424, (2, 4): 0.077994,
       (2, 5): 0.119505, (3, 4): 0.100840, (3, 5): 0.073179, (4, 5): 0.087107, (4, 6): 0.089948,
       (5, 6): 0.082213, (6, 7): 0.104364, (6, 8): 0.157596, (7, 8): 0.107895, (7, 9): 0.081416}
agree = sum(1 for e, r in HIS.items() if abs(per42[tuple(sorted(e))]["full_range"] - r) < 5e-6)
ck("Table I reproduces on all 20 rows", agree == 20, "%d/20 within 5e-6" % agree)
ck("draft claims 20 rows and 5e-07", *says("All 20\nrows of Table I reproduce", "5e-07"))

# the three Table-II edges, re-scanned here at step 0.001
g = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
edges = sorted(tuple(sorted(e)) for e in g.edges())
sv = np.arange(0.0, 3.0 + 1e-9, 0.001)
tab2 = {(0, 1): 0.184933, (1, 9): 0.220252, (1, 4): 0.241610}
for e, his_depth in tab2.items():
    _, out = T._scan((10, edges, edges.index(e), sv))
    E = np.array([c[1] for c in out])
    i = int(np.argmin(E))
    prom = float(min(E[:i].max(), E[i + 1:].max()) - E[i])
    rng_ = float(E.max() - E.min())
    ck("Table II edge %s: his depth exceeds the curve's range" % (e,), his_depth > rng_,
       "his %.6f vs range %.6f" % (his_depth, rng_))
    ck("Table II edge %s numbers" % (e,), *says("%.6f" % his_depth, "%.6f" % rng_, "%.6f" % prom,
                                                "%.3f" % sv[i]))
ck("(1,9) gap at its minimum", *says("%.4f" % per42[(1, 9)]["gap_at_min"]))

# where the prominence-defining maxima actually sit: if they are the scan ends, say so
tot_f = end_f = 0
for nn in ("10", "12", "14"):
    for _ei, curve in SEED42[nn]["curves"].items():
        Ec = np.array([c[1] for c in curve])
        i = int(np.argmin(Ec))
        if not (0 < i < len(Ec) - 1):
            continue
        li = int(np.argmax(Ec[:i]))
        ri = i + 1 + int(np.argmax(Ec[i + 1:]))
        for j in (li, ri):
            tot_f += 1
            end_f += (j == 0 or j == len(Ec) - 1)
ck("flanking maxima sit at the scan ends", end_f / tot_f > 0.9, "%d of %d" % (end_f, tot_f))
ck("draft says so", *says("%d%% of them" % round(100 * end_f / tot_f)))

# ------------------------------------------------------- 11. corners are not edges; exact energies
dists = {}
for L in (1, 2):
    n, E = P.sierpinski_sieve(L)
    gg = nx.Graph()
    gg.add_nodes_from(range(n))
    gg.add_edges_from(E)
    tips = [v for v in gg if gg.degree(v) == 2]
    dists[L] = {nx.shortest_path_length(gg, a, b) for i, a in enumerate(tips) for b in tips[i + 1:]}
ck("tips are at distance 2 (L1) and 4 (L2)", dists[1] == {2} and dists[2] == {4}, str(dists))
ck("draft says so", *says("distance 2 at L1 and 4 at L2"))

energies = {}
for L in (1, 2):
    n, E = P.sierpinski_sieve(L)
    H = P.hamiltonian(n, E, [1.0] * len(E), P._z_table(n))
    energies[L] = float(np.sort(np.linalg.eigvalsh(H.toarray()))[0]) if (1 << n) <= 64 else \
        float(np.sort(eigsh(H, k=6, which="SA", tol=0, maxiter=300000, return_eigenvectors=False))[0])
ratio = -16.921463 / energies[2]
ck("exact isotropic energies", *says("%.6f at L1 and %.6f at L2" % (energies[1], energies[2]),
                                     "-6.000000 and -16.921463", "%.1f%%" % (100 * ratio)))

# ------------------------------------------------------- report
bad = [c for c in checks if not c[1]]
w = max(len(c[0]) for c in checks)
for name, ok, detail in checks:
    print("%-4s %-*s %s" % ("OK" if ok else "FAIL", w, name, detail))
print("\n%d/%d checks pass" % (len(checks) - len(bad), len(checks)))
if bad:
    print("\nstrings the draft must contain (in order of check):")
    for s in expected:
        print("   %r" % s)
sys.exit(1 if bad else 0)
