"""Every number in the Table III reply, re-derived, and every quote checked against his own files.

This message tells a collaborator that his fix did not fix it, twelve days before he submits. That
raises the bar rather than lowering it: each figure is recomputed here, and each line quoted from his
evidence package is matched against the bytes in the archive rather than retyped from a reading of
it. Exits non-zero on any mismatch.

Run: python probes/edrn_table3_numbers.py
"""
from __future__ import annotations

import importlib.util
import io
import pathlib
import re
import sys
import zipfile

import networkx as nx
import numpy as np
from scipy.sparse.linalg import eigsh

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "probes"
DRAFT = ROOT / "agora_output" / "drafts" / "edrn_table3_is_the_floor_not_the_depth.md"
ZIP = pathlib.Path(r"C:\Users\Danculus\AppData\Local\Temp\claude\C--Users-Danculus-agora"
                   r"\7dccb956-7590-4d6e-9f54-b1f278456c96\scratchpad\guanghao_evidence.zip")

TEXT = re.sub(r"\s+", " ", DRAFT.read_text(encoding="utf-8").replace("\u2212", "-"))
checks: list[tuple[str, bool, str]] = []


def ck(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


def says(*bits):
    missing = [b for b in bits if re.sub(r"\s+", " ", b) not in TEXT]
    return (not missing), ("missing: " + " | ".join(missing) if missing else "")


_t = importlib.util.spec_from_file_location("T", HERE / "edrn_smallworld_size_trend.py")
T = importlib.util.module_from_spec(_t)
_t.loader.exec_module(T)
_p = importlib.util.spec_from_file_location("P", HERE / "edrn_valley_is_the_uniform_point.py")
P = importlib.util.module_from_spec(_p)
_p.loader.exec_module(P)

# ---------------------------------------------------------------- his own files, read as bytes
z = zipfile.ZipFile(ZIP)


def member(fragment):
    hits = [n for n in z.namelist() if fragment in n and not n.endswith("/")]
    assert len(hits) == 1, "%r matched %d members" % (fragment, len(hits))
    raw = z.read(hits[0])
    for enc in ("utf-8", "gb18030", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise AssertionError("undecodable: %s" % hits[0])


table3_src = member("多种子审计5种子实验数据.txt")
audit01 = member("(0,1)边高分辨率多种子审计实验数据.txt")
frac06 = member("多种子审计：边 (0, 6).实验数据.txt")

ck("his Table III source says 谷深 0.184933", "谷深: 0.184933" in table3_src)
ck("and 0.220252 and 0.241610", "谷深: 0.220252" in table3_src and "谷深: 0.241610" in table3_src)
ck("his 7-seed audit separates the two", "valley_fine=0.184935" in audit01 and "depth=0.063126" in audit01)
ck("the draft quotes both of his lines",
   *says("谷深: 0.184933", "valley_fine=0.184935", "depth=0.063126", "valley_s=1.495"))
ck("his windows are as the draft states", "s ∈ [1.3, 1.7]" in table3_src)
ck("the fractal audit really is 13 points", "13点" in frac06 and "s ∈ [0.0, 3.0]" in frac06)
ck("draft says 13 points and the step it implies", *says("13 points across s ∈ [0, 3]", "0.25"))

seeds = [float(x) for x in re.findall(r"极小值=([0-9.]+)", frac06)]
ck("five seed minima recovered from his file", len(seeds) == 5, str(seeds))
ck("draft quotes them", *says(*["%.6f" % s for s in seeds]))
ck("his own mean and sd", "均值=0.099826" in frac06 and "标准差=0.006397" in frac06)
ck("draft quotes the sd", *says("0.006397"))

# ---------------------------------------------------------------- our re-derivation
g = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
edges = sorted(tuple(sorted(e)) for e in g.edges())
sv = np.arange(0.0, 3.0 + 1e-9, 0.001)
HIS = {(0, 1): 0.184933, (1, 9): 0.220252, (1, 4): 0.241610}
spans, proms, floors = {}, {}, {}
for e, dep in HIS.items():
    _, out = T._scan((10, edges, edges.index(e), sv))
    E = np.array([c[1] for c in out])
    i = int(np.argmin(E))
    spans[e] = float(E.max() - E.min())
    proms[e] = float(min(E[:i].max(), E[i + 1:].max()) - E[i])
    floors[e] = float(E[i])
    ck("(%d,%d): his 'depth' IS the floor" % e, abs(dep - floors[e]) < 5e-6,
       "his %.6f vs floor %.6f (%.1e)" % (dep, floors[e], abs(dep - floors[e])))
ck("the floor-match table", *says(*["%.6f" % floors[e] for e in HIS]))
ck("the differences quoted", *says("2.9e-07", "2.8e-07", "2.5e-07"))
ck("full-range spans at step 0.001", *says("%.6f / %.6f / %.6f" % (spans[(0, 1)], spans[(1, 9)], spans[(1, 4)])))
HIS_TABLE2 = {(0, 1): 0.176842, (1, 9): 0.113332, (1, 4): 0.103002}
ck("spans really are within 2e-05 of his Table II",
   all(abs(spans[e] - v) < 2e-5 for e, v in HIS_TABLE2.items()),
   " ".join("%s %.6f vs %.6f" % (e, spans[e], v) for e, v in HIS_TABLE2.items()))
ck("the corrected prominences", *says("%.6f / %.6f / %.6f" % (proms[(0, 1)], proms[(1, 9)], proms[(1, 4)])))
ck("the (1,9) collapse is stated", *says("0.220252 to **0.008856**"))

# ---------------------------------------------------------------- the ground-space interval
n, EE = P.sierpinski_sieve(2)
Z = P._z_table(n)
idx = np.nonzero(Z.sum(axis=0) == 1)[0]
zi = Z[:, idx].astype(float)
fe = [tuple(sorted(x)) for x in EE]
H = P.hamiltonian(n, fe, [1.0] * len(fe), Z)[idx][:, idx]
w, V = eigsh(H, k=8, which="SA", tol=0, maxiter=300000)
o = np.argsort(w)
w, V = w[o], V[:, o]
deg = int(np.sum(w - w[0] < 1e-8))
ck("the Sz sector ground space really is 2-dimensional at s=1.000", deg == 2, "dim=%d" % deg)


def obs(vec):
    p = np.abs(vec) ** 2
    return float(np.array([p @ (zi[a] * zi[b]) for a, b in fe]).std())


vals = [obs(np.cos(t) * V[:, 0] + np.exp(1j * ph) * np.sin(t) * V[:, 1])
        for t in np.linspace(0, np.pi, 181) for ph in np.linspace(0, 2 * np.pi, 181)]
lo, hi = min(vals), max(vals)
ck("the interval we published before seeing his data", abs(lo - 0.110269) < 1e-5 and abs(hi - 0.159658) < 1e-5,
   "[%.6f, %.6f]" % (lo, hi))
ck("draft quotes it", *says("[0.110269, 0.159658]"))
ck("all five of his minima land inside it", all(lo - 1e-9 <= s <= hi + 1e-9 for s in seeds),
   str([s for s in seeds if not (lo - 1e-9 <= s <= hi + 1e-9)]))
top_gap = hi - max(seeds)
ck("the largest sits just under the top", *says("3.6e-04"))
ck("that distance is right", abs(top_gap - 3.6e-4) < 5e-5, "%.2e" % top_gap)
spread = max(seeds) - min(seeds)
ck("their spread", *says("0.0171"))
ck("spread is right", abs(spread - 0.0171) < 5e-4, "%.4f" % spread)

# ---------------------------------------------------------------- the ensemble sentence
ens = __import__("json").loads((HERE / "edrn_smallworld_ensemble.result.json").read_text(encoding="utf-8"))
rows = list(ens.values())
N = np.array([r["n"] for r in rows], float)
Pm = np.array([r["median_prominence"] for r in rows], float)
Sc = np.array([r["median_scaled"] for r in rows], float)
Ed = np.array([r["edges"] for r in rows], float)
def slope(x, y, n=20000, seed=5):
    """A FRESH generator per statistic, seeded. Sharing one across three calls makes each interval
    depend on how many were computed before it, so the same number comes out differently depending on
    the order of the file -- which is how a bootstrap interval quoted in prose stops being
    reproducible. This is the third time today that shape has cost a correction."""
    rng = np.random.default_rng(seed)
    b = float(np.polyfit(x, y, 1)[0])
    bs = np.empty(n)
    for t in range(n):
        i = rng.integers(0, x.size, size=x.size)
        while np.unique(x[i]).size < 2:
            i = rng.integers(0, x.size, size=x.size)
        bs[t] = np.polyfit(x[i], y[i], 1)[0]
    return b, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


b1, l1, h1 = slope(N, np.log(Pm))
b2, l2, h2 = slope(N, np.log(Sc))
b3, l3, h3 = slope(np.log(Ed), np.log(Pm))
ck("raw trend", *says("%+.5f" % b1, "[%+.5f, %+.5f]" % (l1, h1), "%.3f" % np.exp(6 * b1)))
ck("scaled trend", *says("%+.5f" % b2, "[%+.5f, %+.5f]" % (l2, h2)))
ck("the exponent", *says("%.3f" % b3, "[%.3f, %.3f]" % (l3, h3)))
ck("the exponent's interval really excludes 0 and contains -1/2",
   h3 < 0 and l3 <= -0.5 <= h3, "a=%.3f [%.3f, %.3f]" % (b3, l3, h3))

bad = [c for c in checks if not c[1]]
w_ = max(len(c[0]) for c in checks)
for name, ok, detail in checks:
    print("%-4s %-*s %s" % ("OK" if ok else "FAIL", w_, name, detail))
print("\n%d/%d checks pass" % (len(checks) - len(bad), len(checks)))
if bad:
    print("\nmeasured: floors %s | spans %s | proms %s | interval [%.6f, %.6f] | spread %.4f | top gap %.2e"
          % (floors, spans, proms, lo, hi, spread, top_gap))
sys.exit(1 if bad else 0)
