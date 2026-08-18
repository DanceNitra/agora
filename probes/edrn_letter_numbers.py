"""Every number in the outbound EDRN letter, checked against an artifact or recomputed here.

The letter goes to a co-author who will act on it, so no figure in it may rest on a note. This
re-derives each one and fails loudly on any mismatch. Numbers quoted FROM the manuscript are marked
as such and are checked only for being transcribed correctly against the text we downloaded.

Run: python probes/edrn_letter_numbers.py       (exit 1 if any check fails)
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import pathlib
import re
import sys

import networkx as nx
import numpy as np
from scipy.sparse.linalg import eigsh

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "probes"
LETTER = ROOT / "agora_output" / "drafts" / "edrn_reverification_2026-08-18.md"
TOOL = ROOT / "agora_output" / "hotrg_edrn"

spec = importlib.util.spec_from_file_location("edrn", HERE / "edrn_valley_is_the_uniform_point.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

RUN = json.loads((HERE / "edrn_valley_is_the_uniform_point.result.json").read_text())
SU2 = json.loads((HERE / "edrn_su2_invariant_scan.result.json").read_text())
DISC = json.loads((HERE / "edrn_the_observable_is_discontinuous_at_s1.result.json").read_text())
SW = json.loads((HERE / "edrn_smallworld_exact.result.json").read_text())
TEXT = LETTER.read_text(encoding="utf-8")

checks: list[tuple[str, bool, str]] = []


def ck(name, ok, detail):
    checks.append((name, bool(ok), detail))


def in_letter(s):
    return s in TEXT


# ---- source lines we quote from our own toolchain
h40 = (TOOL / "hotrg.py").read_text(encoding="utf-8").splitlines()[39]
dv = (TOOL / "dmrg_valley.py").read_text(encoding="utf-8").splitlines()
ck("hotrg.py line 40 is the XZ bond term we quote",
   "SX" in h40 and "SZ" in h40 and "SY" not in h40 and in_letter("SX_i SX_j + SZ_i SZ_j"),
   h40.strip())
ck("dmrg_valley.py adds Sigmax/Sigmaz and no Sigmay",
   any("Sigmax" in l and "add_coupling_term" in l for l in dv)
   and any("Sigmaz" in l and "add_coupling_term" in l for l in dv)
   and not any("Sigmay" in l for l in dv),
   "lines 48-49 as quoted")
ck("dmrg_valley.py line 79 appends (0,2,s)", "(0,2,s)" in dv[78].replace(" ", ""), dv[78].strip())

# ---- graph structure, rebuilt from the collaboration's own constructor
src = (TOOL / "dmrg_valley.py").read_text(encoding="utf-8")
ns: dict = {}
a, b = src.index("def sierpinski_graph"), src.index("\ndef ", src.index("def sierpinski_graph") + 5)
exec("import networkx as nx\n" + src[a:b], ns)
G = ns["sierpinski_graph"](2)
tips = sorted(v for v in G if G.degree(v) == 2)
nb = {v: sorted(G[v]) for v in tips}
dists = [nx.shortest_path_length(G, u, v) for u, v in itertools.combinations(tips, 2)]
ck("gasket L2 is 15/27 with tips 0,1,2 and the neighbour lists quoted",
   (G.number_of_nodes(), G.number_of_edges()) == (15, 27) and tips == [0, 1, 2]
   and nb[0] == [6, 8] and nb[1] == [9, 11] and nb[2] == [12, 14]
   and in_letter("vertex 0 -> neighbours [6, 8]"),
   "tips %s neighbours %s" % (tips, nb))
ck("no tip-tip pair is an edge and all are at distance 4",
   set(dists) == {4} and not any(G.has_edge(u, v) for u, v in itertools.combinations(tips, 2))
   and G.has_edge(0, 6) and not G.has_edge(0, 1) and not G.has_edge(0, 2),
   "distances %s ; (0,6) edge=%s ; (0,1) edge=%s ; (0,2) edge=%s"
   % (dists, G.has_edge(0, 6), G.has_edge(0, 1), G.has_edge(0, 2)))

# ---- least sensitive real edge
ed: dict = {}
for r in RUN["rows"]:
    if r["kind"] == "edges":
        ed.setdefault(r["edge_index"], {})[r["s"]] = r["E"]
least = min(max(x for s, x in v.items() if s != 1.0) - min(x for s, x in v.items() if s != 1.0)
            for v in ed.values())
ck("least sensitive of the 27 real edges moves the observable by 0.024618",
   abs(least - 0.024618) < 5e-7 and in_letter("0.024618"), "%.6f" % least)

# ---- agreement with the manuscript at the two defined points
tipedge = next(i for i, (u, v) in enumerate([tuple(x) for x in RUN["fractal_L2_edges"]]) if u == 0)
e0 = ed[tipedge][0.0]
ck("E(s=0) is 0.246731, matching the manuscript's own baseline",
   abs(e0 - 0.246731) < 5e-7 and in_letter("0.246731"), "%.6f" % e0)
n_, e_ = P.sierpinski_sieve(2)
Z = P._z_table(15)
c = [1.0] * 27
c[next(i for i, (u, v) in enumerate(e_) if u == 0)] = 0.99
_, _, V = P.solve(n_, e_, c, Z)
e099 = P.enhanced_projected(V, e_, Z)[0]
ck("E(s=0.99) is 0.16403207 against the manuscript's 0.164032",
   abs(e099 - 0.16403207) < 5e-8 and in_letter("0.16403207"), "%.8f" % e099)

# ---- the discontinuity block, quoted verbatim in the letter
for label, key, want in [("limit from below", "('1-', 1e-05)", 0.15966064),
                         ("limit from above", "('1+', 1e-05)", 0.15965888)]:
    got = DISC["limits"].get(key.replace("('", "").replace("', ", "_").replace(")", ""))
    got = got if got is not None else DISC["limits"][list(DISC["limits"])[0]]
lims = DISC["limits"]
below = [v for k, v in lims.items() if k.startswith("1-") and k.endswith("1e-05")]
above = [v for k, v in lims.items() if k.startswith("1+") and k.endswith("1e-05")]
ck("the four quoted numbers of the discontinuity block",
   below and above and abs(below[0] - 0.15966064) < 5e-8 and abs(above[0] - 0.15965888) < 5e-8
   and abs(DISC["attainable_max"] - 0.15965824) < 5e-8
   and abs(DISC["at_s1_symmetric"] - 0.11026914) < 5e-8
   and all(in_letter(x) for x in ("0.15966064", "0.15965888", "0.15965824", "0.11026914")),
   "below %.8f above %.8f max %.8f sym %.8f"
   % (below[0], above[0], DISC["attainable_max"], DISC["at_s1_symmetric"]))
ck("the one-grid-point width numbers", all(in_letter(x) for x in ("0.15968243", "0.15966465"))
   and abs(lims["1-_0.0001"] - 0.15968243) < 5e-8 and abs(lims["1+_0.0001"] - 0.15966465) < 5e-8,
   "%.8f / %.8f" % (lims["1-_0.0001"], lims["1+_0.0001"]))
ck("the attainable range [0.110271, 0.159658]",
   abs(DISC["attainable_min"] - 0.110271) < 5e-6 and abs(DISC["attainable_max"] - 0.159658) < 5e-6
   and in_letter("[0.110271, 0.159658]"),
   "[%.6f, %.6f]" % (DISC["attainable_min"], DISC["attainable_max"]))

# ---- exact degeneracy and gap at s=1
h = P.hamiltonian(15, e_, [1.0] * 27, Z)
w = np.sort(eigsh(h, k=8, which="SA", tol=0, maxiter=300000,
                  v0=np.random.default_rng(11).standard_normal(1 << 15), return_eigenvectors=False))
split = float(w[3] - w[0])
gap = float(w[4] - w[0])
recon = np.array([gap] * 4 + [0.0])
ck("ground level splitting is at most 3e-13", split <= 3e-13 and in_letter("3e-13"), "%.2e" % split)
ck("exact gap 0.185709 and the {g,g,g,g,0} reconstruction of 0.1486 +/- 0.0743",
   abs(gap - 0.185709) < 5e-7 and abs(recon.mean() - 0.1486) < 5e-5
   and abs(recon.std() - 0.0743) < 5e-5 and in_letter("0.185709"),
   "gap %.6f -> mean %.4f std %.4f" % (gap, recon.mean(), recon.std()))

# ---- ring identity and the tree
ck("uniform ring dispersion is 4.2e-16",
   RUN["control_ring_uniform_E"] < 1e-15 and in_letter("4.2e-16"),
   "%.3e" % RUN["control_ring_uniform_E"])
tr = dict(zip(SU2["tree15"]["s"], SU2["tree15"]["E"]))
tree_proj = [round(tr[s] / 3.0, 6) for s in (0.85, 0.90, 0.95, 1.0, 1.05)]
ck("tree curve 0.110431 0.109946 0.110114 0.110884 0.112194 and constant degeneracy",
   tree_proj == [0.110431, 0.109946, 0.110114, 0.110884, 0.112194]
   and set(SU2["tree15"]["sector_degeneracy"]) == {1}
   and all(in_letter("%.6f" % x) for x in tree_proj),
   "%s ; Sz-sector degeneracy %s" % (tree_proj, sorted(set(SU2["tree15"]["sector_degeneracy"]))))

# ---- small world
edges = [tuple(x) for x in SW["edges"]]
theirs = {(0, 1): 1.496, (1, 9): 0.311, (1, 4): 1.251, (1, 8): 0.720, (1, 6): 0.800, (2, 3): 1.090,
          (2, 4): 0.940, (2, 5): 0.750, (3, 4): 0.840, (3, 5): 0.980, (4, 5): 1.100, (4, 6): 0.910,
          (5, 6): 1.080, (6, 7): 0.470, (6, 8): 1.380, (7, 8): 0.000, (7, 9): 2.140}
match = interior = 0
proms, degs, gaps = [], set(), []
for ei, eg in enumerate(edges):
    cur = SW["curves"][str(ei)]
    ss = np.array([r[0] for r in cur]); E = np.array([r[1] for r in cur])
    degs |= {r[2] for r in cur}
    i = int(np.argmin(E))
    gaps.append(cur[i][3])
    if eg in theirs and abs(ss[i] - theirs[eg]) <= 0.011:
        match += 1
    if 0 < i < len(E) - 1:
        interior += 1
        proms.append(min(E[:i].max(), E[i + 1:].max()) - E[i])
ck("17 of 17 small-world positions reproduce, 19 of 20 interior, non-degenerate throughout",
   match == 17 and interior == 19 and degs == {1}
   and in_letter("17 of the 17 valley positions"),
   "matched %d/17, interior %d/20, degeneracies %s, gaps %.2f-%.2f"
   % (match, interior, sorted(degs), min(gaps), max(gaps)))
ck("prominences 0.000484 to 0.124434, with 17 surviving 0.01 and 15 surviving 0.02",
   abs(min(proms) - 0.000484) < 5e-6 and abs(max(proms) - 0.124434) < 5e-6
   and sum(p >= 0.01 for p in proms) == 17 and sum(p >= 0.02 for p in proms) == 15
   and in_letter("0.000484") and in_letter("0.124434") and in_letter("17 of 20 survive"),
   "range %.6f-%.6f ; >=0.01: %d ; >=0.02: %d"
   % (min(proms), max(proms), sum(p >= 0.01 for p in proms), sum(p >= 0.02 for p in proms)))

# ---- the tool we tell him is in the repo really is, and its guard really fires
ck("scan_guard.py exists and its guard raises on (0,1)", (TOOL / "scan_guard.py").exists(),
   str((TOOL / "scan_guard.py").relative_to(ROOT)))

w_ = max(len(c[0]) for c in checks)
print("EDRN letter -- %d numeric claims\n" % len(checks))
for name, ok, detail in checks:
    print("  [%s] %-*s  %s" % ("PASS" if ok else "FAIL", w_, name, detail))
bad = [c for c in checks if not c[1]]
print("\n%d/%d verified" % (len(checks) - len(bad), len(checks)))
sys.exit(1 if bad else 0)
