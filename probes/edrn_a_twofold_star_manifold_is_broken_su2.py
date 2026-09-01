# -*- coding: utf-8 -*-
"""Marat measures a twofold star ground manifold where we measure sixfold. This is why, and it is
not his graph.

HIS REPORT (edrn-dmrg-verification#2, 2026-08-29 22:11): "the ground manifold of the star N=7 is
twofold degenerate for all s, not sixfold. The sixfold degeneracy appears only in the excited part
of the spectrum for s >= 1. Our rank detector with a small energy gap threshold consistently returns
rank 2." He asks four questions about our setup; this answers them from the code.

THE CLAIM THIS FILE REPLACES, killed by our own red team before it was sent. The first version said
a twofold manifold at every s is "the signature of |nA - nB| = 1", so his code was probably not
building K_{1,6}. Three separate measurements refute that:

  * The RING C_7 is not bipartite at all and is twofold at 4 of 5 s. So is a triangle with pendants.
    Twofold does not imply a 4-against-3 bipartition.
  * A GENUINE K_{1,6} goes twofold the moment SU(2) is broken. Writing the off-diagonal exchange as
    J instead of 2J -- the Pauli-versus-spin factor of two, one of the most common slips in an ED
    build -- gives ground degeneracy 2 in sectors S_z = +/-5/2, at every s. Ising-only does the same.
  * The check that carried the old claim could not fail. Seven spin-1/2 sites contain six S = 5/2
    multiplets, so EVERY graph on N = 7 has sixfold levels somewhere; the star has one at 4 of 5 s.
    "The chain has a sixfold excited level" measured nothing about the chain.

WHAT WE ACTUALLY SHOW. Our star is sixfold at every s > 0 tested, one state per S_z sector, which is
Lieb-Mattis (Lieb and Mattis, J. Math. Phys. 3, 749 (1962)) for a connected bipartite graph with
antiferromagnetic couplings: S = |nA - nB| / 2 = 5/2, degeneracy 6. The theorem constrains only the
SIGN of the couplings and the connectivity, never their magnitudes, so the weight s on one edge does
not move it for any s > 0. A twofold manifold on that same graph therefore means the Hamiltonian is
not isotropic Heisenberg, or that only part of the spectrum is being seen.

THE DISCRIMINATOR IS THE DEGENERACY ACROSS N, not the S_z sector. An isotropic star must give
2S+1 = |nA-nB|+1, so 6, 7 and 8 at N = 7, 8 and 9; a broken-SU(2) operator gives 2 at all three.

An earlier version of this file offered S_z instead, and that was wrong. It said S_z = +/-5/2 means a
genuine star with SU(2) broken and S_z = +/-1/2 means a 4-against-3 bipartition. The scan behind it
stopped at xy = 2.0, so it only ever saw easy-AXIS anisotropy. Under easy-PLANE anisotropy a genuine
star is twofold at S_z = +/-1/2, in 35 of 35 configurations measured here. The claim was sent to a
collaborator on 30 August; the retraction is checked in section 2 rather than only written here.

HONEST LIMIT. We have not read his code. Every cause named here is a candidate consistent with his
numbers, not a verdict on his work.
"""
from __future__ import annotations

import importlib.util
import io
import itertools
import json
import os
import sys

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix

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
# connected, 7 sites, NOT bipartite: a triangle carrying pendants. The counterexample that kills
# "twofold implies |nA - nB| = 1" without leaving the connected graphs.
TRI = [(0, 1), (1, 2), (2, 0), (0, 3), (1, 4), (2, 5), (3, 6)]
# a MIS-BUILT star that stays connected: one leaf re-hung on another leaf. The old control could not
# catch this, because it only asked whether some site was unreachable.
STAR_REHUNG = [(0, i) for i in range(1, N - 1)] + [(1, N - 1)]


def build_H(edges, weights, n_up, xy=2.0):
    """The builder our pipeline uses, with the off-diagonal coefficient exposed.

    `xy = 2.0` is isotropic Heisenberg in this convention. `xy = 1.0` is the Pauli-versus-spin factor
    of two written wrong, and `xy = 0.0` is Ising. The parameter exists so the anisotropy hypothesis
    can be MEASURED rather than argued.
    """
    basis = list(itertools.combinations(range(N), n_up))
    idx = {s: i for i, s in enumerate(basis)}
    H = lil_matrix((len(basis), len(basis)))
    for (a, b), J in zip(edges, weights):
        for k, s in enumerate(basis):
            H[k, k] += J * (1 if a in s else -1) * (1 if b in s else -1)
            ua, ub = a in s, b in s
            if ua and not ub:
                H[k, idx[tuple(sorted(set(s) - {a} | {b}))]] += xy * J
            elif ub and not ua:
                H[k, idx[tuple(sorted(set(s) - {b} | {a}))]] += xy * J
    return csr_matrix(H), basis


def bipartition_gap(edges):
    """|nA - nB|, or None when the graph is not bipartite or leaves a site unreachable."""
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


def ground(edges, s, contra=0, xy=2.0, sign=1.0, tol=1e-9):
    """(E0, total degeneracy, sectors carrying it). Degeneracy is summed over ALL S_z sectors."""
    w = [s if e == contra else 1.0 for e in range(len(edges))]
    per = {}
    for n_up in range(0, N + 1):
        H, _b = build_H(edges, w, n_up, xy)
        per[n_up] = np.sort(np.linalg.eigvalsh(sign * H.toarray()))
    g = min(ev[0] for ev in per.values())
    by = {n: int(np.sum(np.abs(ev - g) < tol)) for n, ev in per.items()}
    return float(g), sum(by.values()), sorted(n for n, d in by.items() if d)


def _ground_n(n, edges, s, xy=2.0, contra=0, tol=1e-9):
    """Ground degeneracy at arbitrary N, summed over all S_z sectors. Used for the N=8/N=9 arm."""
    import itertools as _it
    w = [s if e == contra else 1.0 for e in range(len(edges))]
    best, per = None, {}
    for n_up in range(0, n + 1):
        basis = list(_it.combinations(range(n), n_up))
        idx = {b: i for i, b in enumerate(basis)}
        H = lil_matrix((len(basis), len(basis)))
        for (a, b), J in zip(edges, w):
            for k, st in enumerate(basis):
                H[k, k] += J * (1 if a in st else -1) * (1 if b in st else -1)
                ua, ub = a in st, b in st
                if ua and not ub:
                    H[k, idx[tuple(sorted(set(st) - {a} | {b}))]] += xy * J
                elif ub and not ua:
                    H[k, idx[tuple(sorted(set(st) - {b} | {a}))]] += xy * J
        per[n_up] = np.sort(np.linalg.eigvalsh(csr_matrix(H).toarray()))
    g = min(ev[0] for ev in per.values())
    return sum(int(np.sum(np.abs(ev - g) < tol)) for ev in per.values())


def sz_of(n_up):
    return (N - 2 * n_up) / 2.0


verdicts, res = [], {}


def check(name, ok, detail):
    verdicts.append((name, bool(ok), detail))
    print("%-4s %-54s %s" % ("PASS" if ok else "FAIL", name, detail))


# 1. what our Hamiltonian gives, and the theorem it agrees with
star = {s: ground(STAR, s) for s in S_GRID}
res["star_isotropic"] = {str(s): {"E0": v[0], "deg": v[1], "sectors": v[2]} for s, v in star.items()}
check("star is sixfold at every s tested, one state per sector",
      all(v[1] == 6 and v[2] == [1, 2, 3, 4, 5, 6] for v in star.values()),
      "S_z = +5/2..-5/2, a single S=5/2 multiplet (Lieb-Mattis 1962, |nA-nB|=%d)"
      % bipartition_gap(STAR))
check("no single sector can return 2 from this Hamiltonian",
      all(ground(STAR, s)[1] == 6 for s in S_GRID)
      and all(int(np.sum(np.abs(np.sort(np.linalg.eigvalsh(
          build_H(STAR, [s if e == 0 else 1.0 for e in range(6)], n, 2.0)[0].toarray()))
          - min(np.linalg.eigvalsh(build_H(
              STAR, [s if e == 0 else 1.0 for e in range(6)], n, 2.0)[0].toarray()))) < 1e-9)) == 1
          for s in S_GRID for n in range(1, N)),
      "every sector's ground state is non-degenerate, so no threshold yields 2")

# 2. THE CAUSE THAT SURVIVED: broken SU(2) on the CORRECT graph
aniso = {}
for label, xy in (("isotropic", 2.0), ("off_diag_J_not_2J", 1.0), ("ising_only", 0.0)):
    aniso[label] = {str(s): {"deg": ground(STAR, s, xy=xy)[1],
                             "sectors": ground(STAR, s, xy=xy)[2]} for s in S_GRID}
res["star_anisotropy"] = aniso
check("a genuine star goes TWOFOLD when the off-diagonal is written J not 2J",
      all(v["deg"] == 2 and v["sectors"] == [1, 6]
          for v in aniso["off_diag_J_not_2J"].values()),
      "deg 2 in sectors S_z = %+.1f and %+.1f, at every s tested" % (sz_of(1), sz_of(6)))
check("and Ising-only does the same, on the same correct graph",
      all(v["deg"] == 2 and v["sectors"] == [1, 6] for v in aniso["ising_only"].values()),
      "so twofold is a statement about the Hamiltonian, not about the graph")
# RETRACTED 2026-08-31, and the retraction is the point of this block.
# This check used to read "the two cases are told apart by S_z, which costs him one line", and it
# passed, because it only ever compared S_z = +/-5/2 against S_z = +/-1/2 on the two cases it had
# already built. It never asked whether a GENUINE star can also sit at +/-1/2. It can. The scan
# above stops at xy = 2.0, so every anisotropy it tested was easy-AXIS. Easy-PLANE is xy > 2.0 and
# was never run. Measured below: a genuine K_{1,6} under easy-plane anisotropy is twofold at
# S_z = +/-1/2, which is exactly the signature the retracted check assigned to a 4-against-3
# bipartition. The discriminator was sent to a collaborator on 30 August and is corrected here.
easy_plane = {}
for xy in (2.001, 2.1, 2.5, 3.0, 5.0, 10.0, 100.0):
    easy_plane[str(xy)] = {str(s_): ground(STAR, s_, xy=xy)[1:] for s_ in S_GRID}
res["star_easy_plane_anisotropy"] = easy_plane
_ep = [v for row in easy_plane.values() for v in row.values()]
check("a GENUINE star under easy-plane anisotropy also sits at S_z = +/-1/2",
      all(v[0] == 2 and v[1] == [3, 4] for v in _ep),
      "%d of %d configurations give deg 2 in sectors S_z = %+.1f and %+.1f, so S_z does NOT "
      "separate a broken operator from a wrong graph" % (len(_ep), len(_ep), sz_of(3), sz_of(4)))
check("the S_z discriminator sent on 30 August is therefore RETRACTED",
      all(v[1] == [3, 4] for v in _ep) and all(
          v["sectors"] == [1, 6] for v in aniso["off_diag_J_not_2J"].values()),
      "easy-axis puts a broken star at +/-5/2 and easy-plane puts it at +/-1/2, so the sector "
      "alone is not a test; the degeneracy across N below is the one that works")

# 2a. "THE MOMENT SU(2) IS BROKEN" IS A CLAIM ABOUT THE NEIGHBOURHOOD OF ISOTROPY, and the arm above
# only held xy = 1.0 and 0.0, which are 50% and 100% away from it. A verdict that never approaches
# the point it is making about cannot support the word "moment".
near = {}
for xy in (1.999, 1.99, 1.9, 1.5, 0.5):
    near[str(xy)] = {str(s_): ground(STAR, s_, xy=xy)[1:] for s_ in (0.3, 1.0, 2.0)}
res["star_anisotropy_near_isotropic"] = near
check("twofold appears immediately below isotropy, not only far from it",
      all(v[0] == 2 and v[1] == [1, 6] for row in near.values() for v in row.values())
      and all(ground(STAR, s_, xy=2.0)[1] == 6 for s_ in (0.3, 1.0, 2.0)),
      "xy = 1.999 down to 0.5 all give deg 2 in sectors [1,6]; xy = 2.0 exactly still gives 6, "
      "so a builder that returned 2 for every xy would fail this")

# 2b. THE DISCRIMINATOR HE HAS ALREADY RUN. He reports N=8 and N=9 among his seven controls, and an
# isotropic bipartite antiferromagnetic star must give 2S+1 = |nA-nB|+1 there: 7 and 8, not 2. A
# broken-SU(2) operator gives 2 at EVERY N. So his own control set already separates the two causes.
nscan = {}
for n in (7, 8, 9):
    edges = [(0, i) for i in range(1, n)]
    g = _ground_n(n, edges, 1.0, xy=2.0)
    a = _ground_n(n, edges, 1.0, xy=1.0)
    nscan[n] = {"bipartition_gap": n - 2, "predicted": n - 1, "isotropic": g, "anisotropic": a}
res["n_scan"] = nscan
check("N=8 and N=9 separate the two causes on his own controls",
      all(v["isotropic"] == v["predicted"] for v in nscan.values())
      and all(v["anisotropic"] == 2 for v in nscan.values()),
      "isotropic gives %s; anisotropic gives 2 at every N"
      % ", ".join("N=%d:%d" % (n, v["isotropic"]) for n, v in nscan.items()))

# 2c. his sharp turn sits exactly where the RANK changes
rank_turn = {str(s_): ground(STAR, s_)[1] for s_ in (0.0, 0.005, 0.01, 0.05)}
res["rank_at_the_turn"] = rank_turn
check("the s=0 -> 0.01 turn he reports is a RANK CHANGE",
      rank_turn["0.0"] == 10 and all(v == 6 for k, v in rank_turn.items() if k != "0.0"),
      "deg 10 at s=0 (S=5/2 + S=3/2, the leaf detaches) and 6 immediately after")

# 2d. THE OTHER HALF OF THE S_z TEST, MEASURED RATHER THAN ASSERTED. The check above compared
# sz_of(1) and sz_of(4) against constants, which is arithmetic on the labelling function and never
# diagonalises a 4-against-3 graph. That is a check that cannot see its target. The chain IS such a
# graph, it is already defined here, and its ground manifold has to sit at S_z = +/-1/2.
chain_sz = {str(s_): ground(CHAIN, s_)[1:] for s_ in S_GRID}
res["four_against_three_sz"] = chain_sz
check("a 4-against-3 graph really does put its twofold at S_z = +/-1/2",
      all(v[0] == 2 and v[1] == [3, 4] for v in chain_sz.values())
      and bipartition_gap(CHAIN) == 1,
      "chain deg 2 in sectors n_up 3 and 4, i.e. S_z = %+.1f and %+.1f, at all five s"
      % (sz_of(3), sz_of(4)))

# 2e. HIS SHARP TURN, AND THE FALSY ZERO WE ALREADY REPORTED TWICE. `graph_to_hamiltonian` in the
# collaborators' code carries `w = w if w else 1.0`, so a contradiction strength of exactly 0.0 is
# rebuilt as 1.0. We reported that on 2026-08-12 and again in comment 5303073894 on 2026-08-15. If it
# is still there, his "s = 0" is our s = 1, and the turn he measures between "s=0" and s=0.01 is a
# jump between two quite different Hamiltonians rather than a feature of the physics.
#
# It does NOT reproduce his number, and the probe says so rather than claiming the case is closed.
def _manifold_basis(s, tol=1e-9):
    import itertools as _it
    w = [s if e == 0 else 1.0 for e in range(len(STAR))]
    per = {}
    for n_up in range(0, N + 1):
        H, basis = build_H(STAR, w, n_up)
        ev, V = np.linalg.eigh(H.toarray())
        per[n_up] = (ev, V, basis)
    g = min(ev[0] for ev, _, _ in per.values())
    cols = []
    for n_up, (ev, V, basis) in per.items():
        for j in np.where(np.abs(ev - g) < tol)[0]:
            f = np.zeros(2 ** N)
            for bi, b in enumerate(basis):
                f[sum(1 << t for t in b)] = V[bi, j]
            cols.append(f / np.linalg.norm(f))
    Q, _ = np.linalg.qr(np.array(cols).T)
    return Q


def _theta1(A, B):
    sv = np.linalg.svd(A.T @ B, compute_uv=False)
    return float(np.arccos(np.clip(sv.min(), -1.0, 1.0)))


_ref = _manifold_basis(0.01)
turn = {"honest_1e-9": _theta1(_manifold_basis(1e-9), _ref),
        "honest_0": _theta1(_manifold_basis(0.0), _ref),
        "falsy_zero_is_s1": _theta1(_manifold_basis(1.0), _ref),
        "his_reported": 0.819}
res["sharp_turn_theta1_vs_s001"] = turn
check("an HONEST s -> 0 produces no sharp turn in our manifold",
      turn["honest_1e-9"] < 0.01,
      "theta1 = %.4f rad between s = 1e-9 and s = 0.01" % turn["honest_1e-9"])
check("the falsy zero DOES produce a turn, about 100x larger",
      turn["falsy_zero_is_s1"] > 20 * turn["honest_1e-9"],
      "theta1 = %.4f rad if s=0 is silently rebuilt as 1.0" % turn["falsy_zero_is_s1"])
check("but it does NOT reach his 0.819, so it is not the whole story",
      turn["falsy_zero_is_s1"] < 0.5 * turn["his_reported"],
      "%.4f against his %.3f; the gap is left open rather than explained away"
      % (turn["falsy_zero_is_s1"], turn["his_reported"]))

# 2f. OUR MANIFOLD ROTATES RIGIDLY, and his does not. All six principal angles between the s=0.01
# manifold and a neighbour are equal here. He reports theta1 = Omega = 0.819 for the star, and since
# Omega is the root-sum-square of the angles, theta1 = Omega forces every other angle to be exactly
# zero. One angle pinned at 0 and one at 0.819 is what an arbitrary two-vector slice of a sixfold
# manifold looks like; it is not what a rigid rotation looks like. His own chain ratio agrees:
# 0.065 / 0.046 = 1.413 = sqrt(2), which is two EQUAL angles.
def _all_angles(a, b):
    sv = np.linalg.svd(_manifold_basis(a).T @ _manifold_basis(b), compute_uv=False)
    return np.arccos(np.clip(sv, -1.0, 1.0))


_ang = {"1e-9_vs_0.01": _all_angles(1e-9, 0.01), "1.0_vs_0.01": _all_angles(1.0, 0.01)}
res["principal_angle_spread"] = {k: [float(x) for x in v] for k, v in _ang.items()}
check("our sixfold manifold rotates RIGIDLY: all six angles equal",
      all(float(np.ptp(v)) < 1e-6 for v in _ang.values()),
      "spread across the six angles is %.2e and %.2e, so theta1 equals the largest"
      % tuple(float(np.ptp(v)) for v in _ang.values()))
check("theta1 = Omega forces every other angle to zero, which rigid rotation forbids",
      abs((2.0 ** 0.5) - (0.065 / 0.046)) < 0.01,
      "his chain 0.065/0.046 = 1.413 = sqrt(2), two equal angles; his star theta1 = Omega = 0.819, "
      "so one angle is 0.819 and the rest are zero")

# 3. the claim this file retracts
other = {}
for name, edges in (("ring_C7", RING), ("triangle_with_pendants", TRI)):
    other[name] = {"bipartition_gap": bipartition_gap(edges),
                   "ground_deg": {str(s): ground(edges, s)[1] for s in S_GRID}}
res["not_bipartite_but_twofold"] = other
check("RETRACTED twofold does NOT imply |nA - nB| = 1",
      other["ring_C7"]["bipartition_gap"] is None
      and sum(1 for v in other["ring_C7"]["ground_deg"].values() if v == 2) >= 4,
      "C_7 is not bipartite and is twofold at %d of %d s"
      % (sum(1 for v in other["ring_C7"]["ground_deg"].values() if v == 2), len(S_GRID)))
check("and a connected non-bipartite graph does it at every s",
      other["triangle_with_pendants"]["bipartition_gap"] is None
      and all(v == 2 for v in other["triangle_with_pendants"]["ground_deg"].values()),
      "triangle with pendants: not bipartite, twofold at all five")

# 4. the hypothesis killed earlier, kept because it was the obvious one
flipped = {str(s): ground(STAR, s, sign=-1.0)[1] for s in S_GRID}
res["sign_flipped_star_deg"] = flipped
check("REFUTED an opposite exchange sign does not explain his 2",
      all(v == 8 for v in flipped.values()),
      "sign-flipped star is EIGHTfold (S = 7/2), not twofold")

# controls
check("CONTROL a CONNECTED mis-built star is caught",
      bipartition_gap(STAR_REHUNG) is not None
      and bipartition_gap(STAR_REHUNG) != bipartition_gap(STAR)
      and ground(STAR_REHUNG, 1.0)[1] != 6,
      "one leaf re-hung: |nA-nB| = %s and deg = %d, both differ from the star; the old control "
      "only caught DISCONNECTED graphs and would have passed this"
      % (bipartition_gap(STAR_REHUNG), ground(STAR_REHUNG, 1.0)[1]))
check("CONTROL the isotropic arm reproduces the theorem it cites",
      ground(CHAIN, 1.0)[1] == bipartition_gap(CHAIN) + 1
      and ground(STAR, 1.0)[1] == bipartition_gap(STAR) + 1,
      "deg = |nA-nB| + 1 on both bipartite graphs; a builder with the wrong sign fails here")
_z = ground(STAR, 0.0)[1]
res["star_deg_at_s0"] = _z
check("CONTROL s=0 detaches the edge and is excluded on purpose",
      _z != 6,
      "at s=0 the degeneracy is %d, not 6, which is why the grid starts above it" % _z)

ok = all(v for _n, v, _d in verdicts)
print("\n%d/%d verdicts" % (sum(1 for _n, v, _d in verdicts if v), len(verdicts)))
res["verdicts"] = [{"name": n, "ok": v, "detail": d} for n, v, d in verdicts]
res["all_passed"] = ok
with io.open(os.path.join(HERE, "edrn_a_twofold_star_manifold_is_broken_su2.result.json"),
             "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1, default=str)
sys.exit(0 if ok else 1)
