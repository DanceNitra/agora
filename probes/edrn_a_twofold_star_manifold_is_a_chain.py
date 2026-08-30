# -*- coding: utf-8 -*-
"""Marat cannot reproduce the star's rank-6 ground manifold. This measures why.

HIS REPORT (edrn-dmrg-verification#2, 2026-08-29 22:11): "the ground manifold of the star N=7 is
twofold degenerate for all s, not sixfold. The sixfold degeneracy appears only in the excited part
of the spectrum for s >= 1. Our rank detector with a small energy gap threshold consistently returns
rank 2." He asks four questions about our setup, and this answers them from the code rather than
from memory.

WHAT WE MEASURE, on the Hamiltonian our own probe builds (weight `s` on the contradiction edge,
1.0 on the rest, exact diagonalisation per fixed-magnetisation sector):

  1. The star's ground manifold is SIXFOLD at every s > 0 tested, and it is one state in each of the
     six sectors n_up = 1..6. That is a single S = 5/2 multiplet spread across S_z, which is what
     Lieb-Mattis gives for a bipartite antiferromagnetic tree with |nA - nB| = 5.
  2. A SINGLE sector cannot produce his 2. Every sector's ground state is NON-degenerate, with a
     large gap to the next level, so no threshold returns 2 from this Hamiltonian.
  3. A 2-fold manifold at every s is the signature of |nA - nB| = 1. The star has 5. The CHAIN has 1,
     and the chain reproduces BOTH of his observations at once: ground degeneracy 2 at every s, and a
     sixfold level sitting in the excited part.

A HYPOTHESIS THIS KILLED, recorded because it was the obvious one and it is wrong. If his exchange
sign were opposite to ours, the S = 5/2 multiplet would move off the bottom. Measured: flipping the
sign of H gives a ground manifold of EIGHT (the S = 7/2 ferromagnetic multiplet), not two. So the
disagreement is not a sign convention.

WHAT THIS DOES NOT SHOW. It does not read his code, so "his graph is not K_{1,6}" is a candidate
cause and not a verdict: any construction whose bipartition splits 4 against 3 reproduces the same
numbers. What it gives him is a one-line check that settles it from his side, and a signature to
compare against.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

N = 7
S_GRID = (0.3, 0.7, 1.0, 1.5, 2.0)
HERE = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    "orb", os.path.join(HERE, "edrn_the_orbit_floor_holds_across_the_symmetry_spectrum.py"))
_m = importlib.util.module_from_spec(_spec)
_m.__name__ = "orb"
try:
    _spec.loader.exec_module(_m)
except SystemExit:
    pass

STAR = [(0, i) for i in range(1, N)]
CHAIN = [(i, i + 1) for i in range(N - 1)]
RING = [(i, (i + 1) % N) for i in range(N)]


def bipartition_gap(edges):
    """|nA - nB|, or None when the graph is not bipartite or not connected on all N sites.

    The quantity Lieb-Mattis turns into a ground total spin on an antiferromagnetic tree.
    """
    adj = {i: set() for i in range(N)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    col, st = {0: 0}, [0]
    while st:
        u = st.pop()
        for v in adj[u]:
            if v in col:
                if col[v] == col[u]:
                    return None
            else:
                col[v] = 1 - col[u]
                st.append(v)
    if len(col) < N:
        return None
    a = sum(1 for c in col.values() if c == 0)
    return abs(a - (N - a))


def _dense(H):
    return H.toarray() if hasattr(H, "toarray") else np.asarray(H, dtype=float)


def sector_levels(edges, s, contra=0, sign=1.0):
    """{n_up: sorted eigenvalues}. Fixed magnetisation, which is what our pipeline diagonalises."""
    w = [s if e == contra else 1.0 for e in range(len(edges))]
    out = {}
    for n_up in range(0, N + 1):
        try:
            H, _basis = _m.build_H(N, edges, w, n_up)
        except Exception:                                              # noqa: BLE001
            continue
        out[n_up] = np.sort(np.linalg.eigvalsh(sign * _dense(H)))
    return out


def ground(edges, s, contra=0, sign=1.0, tol=1e-9):
    """(E0, total degeneracy, {n_up: degeneracy at E0})."""
    per = sector_levels(edges, s, contra, sign)
    g = min(ev[0] for ev in per.values() if len(ev))
    by = {n: int(np.sum(np.abs(ev - g) < tol)) for n, ev in per.items() if len(ev)}
    return g, sum(by.values()), {n: d for n, d in by.items() if d}


def first_sixfold_above(edges, s, contra=0, tol=1e-9):
    """Energy of the lowest SIXFOLD level strictly above the ground manifold, or None."""
    per = sector_levels(edges, s, contra)
    allv = np.sort(np.concatenate([ev for ev in per.values() if len(ev)]))
    g = float(allv[0])
    cnt = {}
    for e in allv:
        k = round(float(e), 9)
        cnt[k] = cnt.get(k, 0) + 1
    for e in sorted(cnt):
        if e - g > tol and cnt[e] == 6:
            return e - g
    return None


verdicts, res = [], {}


def check(name, ok, detail):
    verdicts.append((name, bool(ok), detail))
    print("%-4s %-52s %s" % ("PASS" if ok else "FAIL", name, detail))


# 1. the star, on our Hamiltonian
star_rows = {}
for s in S_GRID:
    g, deg, by = ground(STAR, s)
    star_rows[s] = {"E0": g, "deg": deg, "by_sector": by}
res["star"] = star_rows
check("star manifold is sixfold at every s tested",
      all(r["deg"] == 6 for r in star_rows.values()),
      "deg = " + ", ".join("s=%.1f:%d" % (s, r["deg"]) for s, r in star_rows.items()))
check("and it is ONE state in each of the six S_z sectors",
      all(sorted(r["by_sector"]) == [1, 2, 3, 4, 5, 6] and set(r["by_sector"].values()) == {1}
          for r in star_rows.values()),
      "one per sector n_up=1..6, the signature of a single S=5/2 multiplet")

# 2. a single sector cannot give 2
gaps = []
for s in S_GRID:
    per = sector_levels(STAR, s)
    for n_up in range(1, N):
        ev = per[n_up]
        gaps.append((s, n_up, int(np.sum(np.abs(ev - ev[0]) < 1e-9)), float(ev[1] - ev[0])))
res["sector_gaps"] = [{"s": s, "n_up": n, "deg": d, "gap": gp} for s, n, d, gp in gaps]
check("every single sector has a NON-degenerate ground state",
      all(d == 1 for _s, _n, d, _g in gaps),
      "so no gap threshold returns 2 from this Hamiltonian")
check("with a gap far above any plausible threshold",
      min(g for _s, _n, _d, g in gaps) > 0.5,
      "smallest sector gap = %.5f over %d (s, sector) pairs" % (
          min(g for _s, _n, _d, g in gaps), len(gaps)))

# 3. what DOES give 2 at every s
table = {}
for name, edges in (("star", STAR), ("chain", CHAIN), ("ring", RING)):
    table[name] = {"bipartition_gap": bipartition_gap(edges),
                   "ground_deg": {s: ground(edges, s)[1] for s in S_GRID},
                   "first_sixfold_above_ground": {s: first_sixfold_above(edges, s) for s in S_GRID}}
res["graphs"] = table
check("the chain is twofold at every s, as he reports for his star",
      all(v == 2 for v in table["chain"]["ground_deg"].values()),
      "chain |nA-nB| = %s -> S = 1/2 -> 2" % table["chain"]["bipartition_gap"])
check("and the chain DOES carry a sixfold level in its excited part",
      all(v is not None for v in table["chain"]["first_sixfold_above_ground"].values()),
      "his second observation, reproduced on the chain")
check("while the star's bipartition forbids a twofold ground manifold",
      table["star"]["bipartition_gap"] == 5
      and all(v == 6 for v in table["star"]["ground_deg"].values()),
      "star |nA-nB| = 5 -> S = 5/2 -> 6, at every s tested")

# 4. the hypothesis this kills
flipped = {s: ground(STAR, s, sign=-1.0)[1] for s in S_GRID}
res["sign_flipped_star_deg"] = flipped
check("REFUTED an opposite exchange sign does not explain his 2",
      all(v == 8 for v in flipped.values()),
      "sign-flipped star is EIGHTfold (S = 7/2), not twofold")

# controls: each must fail if the instrument is broken
check("CONTROL the bipartition detector separates star from chain",
      bipartition_gap(STAR) == 5 and bipartition_gap(CHAIN) == 1,
      "5 vs 1; a builder that returned the same graph twice fails here")
check("CONTROL it reports None on a non-bipartite graph",
      bipartition_gap(RING) is None,
      "C_7 has an odd cycle, so |nA-nB| is undefined and must not be invented")
_broken = [(0, i) for i in range(1, N - 1)]
check("CONTROL a mis-built star is caught rather than measured",
      bipartition_gap(_broken) is None,
      "that edge list leaves one site unreachable, so the detector refuses it")
_deg_at_zero = ground(STAR, 0.0)[1]
res["star_deg_at_s0"] = _deg_at_zero
check("CONTROL s=0 is excluded on purpose and looks different",
      _deg_at_zero != 6,
      "at s=0 the contradiction edge is off and the degeneracy is %d, not 6" % _deg_at_zero)

ok = all(v for _n, v, _d in verdicts)
print("\n%d/%d verdicts" % (sum(1 for _n, v, _d in verdicts if v), len(verdicts)))
res["verdicts"] = [{"name": n, "ok": v, "detail": d} for n, v, d in verdicts]
res["all_passed"] = ok
with io.open(os.path.join(HERE, "edrn_a_twofold_star_manifold_is_a_chain.result.json"),
             "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1, default=str)
sys.exit(0 if ok else 1)
