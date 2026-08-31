"""Three things Marat's triadic coherence C depends on, measured before I tell him any of them.

Written because a draft reply quoted three numbers I had not measured. They came from an adversarial
pass over my own letter, and citing another reader's measurement as mine is the defect I keep
correcting in other people's work.

  DEMEAN     My null probe demeans each stream before the Hilbert transform. His stated definition
             does not. Does that change the null, and by how much?
  RANK       I told him the ground-manifold rank gates C, because Omega(s) and I(s) are built from
             the projector. Does changing the rank actually move C, against his tree spread of 0.020?
  MISMATCH   I recommended a null built by taking one stream from each of three different graphs.
             Is it calibrated, or does mixing graphs move C by itself?

The star K_{1,6} is the object, because it is the graph his claim is about. E(s) is the ground-level
energy, Omega(s) the cumulative trace distance between successive ground projectors, I(s) a mean
pairwise mutual information proxy from the two-site reduced states. This is a reconstruction of his
pipeline from his description, not his code, so absolute values are not expected to match his.

Controls, so no arm can report a comfortable answer by construction:

  IDENTITY   C of three copies of one stream is exactly 1.0, or the phase extraction is broken.
  FLOOR      C of three independent smooth streams sits near 0.52, matching the published null.
  SPIN       the isotropic star ground level is sixfold with S = 5/2, or the Hamiltonian is wrong.
  POWER      the mismatch arm must be able to SEE a real shared mechanism, or its null result is
             the instrument having no power rather than an absence.

Run:  python -X utf8 probes/edrn_what_the_triadic_null_depends_on.py
"""
from __future__ import annotations

import itertools
import json
import math
import os
import sys

import numpy as np
from scipy.signal import hilbert

N = 7                       # K_{1,6}, the star his claim is about
S_GRID = np.linspace(0.3, 3.0, 60)
TRIALS = 300
SEED = 20260901
TOL = 1e-9


# ---------------------------------------------------------------- the statistic
def phases(stream, demean=True):
    x = np.asarray(stream, dtype=float)
    if demean:
        x = x - x.mean()
    return np.angle(hilbert(x))


def coherence(streams, demean=True):
    phi = np.array([phases(x, demean) for x in streams])
    return float(np.abs(np.exp(1j * phi).mean(axis=0)).mean())


# ---------------------------------------------------------------- the star
DIM = 1 << N
EDGES = [(0, i) for i in range(1, N)]


def build_H(s, xy=2.0):
    """Heisenberg on the star, edge (0,1) carrying weight s and the rest 1."""
    H = np.zeros((DIM, DIM))
    for st in range(DIM):
        diag = 0.0
        for (k, (a, b)) in enumerate(EDGES):
            J = s if k == 0 else 1.0
            ba, bb = (st >> (N - 1 - a)) & 1, (st >> (N - 1 - b)) & 1
            if ba == bb:
                diag += 0.25 * J
            else:
                diag -= 0.25 * J
                H[st, st ^ (1 << (N - 1 - a)) ^ (1 << (N - 1 - b))] += 0.5 * xy * J / 2.0
        H[st, st] += diag
    return H


def ground(s):
    w, v = np.linalg.eigh(build_H(s))
    deg = int(np.sum(np.abs(w - w[0]) < TOL))
    return float(w[0]), deg, v[:, :deg]


def rho_from(V):
    return (V @ V.T) / V.shape[1]


def two_site_mi(rho, a, b):
    """A mutual-information proxy: S(rho_a) + S(rho_b) - S(rho_ab) on the reduced states."""
    def reduce_to(sites):
        keep = sorted(sites)
        k = len(keep)
        out = np.zeros((1 << k, 1 << k))
        idx = np.arange(DIM)
        bits = [(idx >> (N - 1 - q)) & 1 for q in range(N)]
        key = np.zeros(DIM, dtype=np.int64)
        for j, q in enumerate(keep):
            key |= bits[q] << (k - 1 - j)
        rest = np.zeros(DIM, dtype=np.int64)
        others = [q for q in range(N) if q not in keep]
        for j, q in enumerate(others):
            rest |= bits[q] << (len(others) - 1 - j)
        for r in range(1 << len(others)):
            sel = np.where(rest == r)[0]
            if sel.size:
                blk = rho[np.ix_(sel, sel)]
                kk = key[sel]
                for i1 in range(sel.size):
                    for i2 in range(sel.size):
                        out[kk[i1], kk[i2]] += blk[i1, i2]
        return out

    def ent(m):
        ev = np.linalg.eigvalsh(m)
        ev = ev[ev > 1e-12]
        return float(-np.sum(ev * np.log(ev)))

    return ent(reduce_to([a])) + ent(reduce_to([b])) - ent(reduce_to([a, b]))


def streams_for_star(rank=None):
    """(E, Omega, I) over the sweep. `rank` truncates the ground manifold to that many vectors."""
    E, Om, I = [], [], []
    prev = None
    cum = 0.0
    for s in S_GRID:
        e, deg, V = ground(s)
        W = V if rank is None else V[:, :min(rank, V.shape[1])]
        r = rho_from(W)
        if prev is not None:
            cum += float(0.5 * np.sum(np.abs(np.linalg.eigvalsh(r - prev))))
        prev = r
        E.append(e)
        Om.append(cum)
        mis = [two_site_mi(r, a, b) for (a, b) in ((1, 2), (1, 3), (2, 3))]
        I.append(float(np.mean(mis)))
    return np.array(E), np.array(Om), np.array(I)


# ---------------------------------------------------------------- synthetic streams
def smooth(rng, modes=4, trend=0.0, offset=0.0):
    t = np.linspace(0.0, 1.0, len(S_GRID))
    y = np.zeros_like(t)
    for k in range(1, modes + 1):
        y += rng.normal() * np.sin(math.pi * k * t) + rng.normal() * np.cos(math.pi * k * t)
    sd = float(np.std(y)) or 1.0
    y = y / sd + trend * t
    return y + offset


def main():
    rng = np.random.default_rng(SEED)
    rep = {"N": N, "sweep": [float(S_GRID[0]), float(S_GRID[-1]), len(S_GRID)], "seed": SEED}
    fails = []

    # -- control: identity and floor -------------------------------------------------------------
    one = smooth(rng)
    c_id = coherence([one, one, one])
    floor = [coherence([smooth(rng), smooth(rng), smooth(rng)]) for _ in range(TRIALS)]
    rep["control_identity"] = c_id
    rep["control_floor"] = {"mean": float(np.mean(floor)), "sd": float(np.std(floor))}
    print("control  identity C = %.9f   independent-smooth floor C = %.4f +/- %.4f"
          % (c_id, np.mean(floor), np.std(floor)))
    if abs(c_id - 1.0) > 1e-9:
        fails.append("identity control gave %.6f" % c_id)
    if not (0.45 < np.mean(floor) < 0.60):
        fails.append("floor control gave %.4f, off the published 0.52" % np.mean(floor))

    # -- 1. DEMEAN --------------------------------------------------------------------------------
    print("\n1. does demeaning change the null? offset is in units of the stream sd")
    rep["demean"] = {}
    for off in (0.0, 1.0, 2.0, 5.0, 10.0):
        dm, raw = [], []
        for _ in range(TRIALS):
            trio = [smooth(rng, trend=2.0, offset=off) for _ in range(3)]
            dm.append(coherence(trio, demean=True))
            raw.append(coherence(trio, demean=False))
        rep["demean"][str(off)] = {"demeaned": float(np.mean(dm)), "raw": float(np.mean(raw)),
                                   "raw_frac_ge_0977": float(np.mean(np.array(raw) >= 0.977))}
        print("   offset %5.1f sd   demeaned %.4f   RAW %.4f   raw P(C>=0.977) %.3f"
              % (off, np.mean(dm), np.mean(raw), np.mean(np.array(raw) >= 0.977)))
    if rep["demean"]["5.0"]["raw"] <= rep["demean"]["5.0"]["demeaned"] + 0.1:
        fails.append("demeaning made no difference; the claim to Marat does not hold")

    # -- control: the star Hamiltonian ------------------------------------------------------------
    e1, deg1, V1 = ground(1.0)
    rep["star_ground_degeneracy_at_s1"] = deg1
    print("\ncontrol  isotropic star at s=1: ground degeneracy %d (Lieb-Mattis gives 6)" % deg1)
    if deg1 != 6:
        fails.append("the star ground level is %d-fold, not 6; the Hamiltonian is wrong" % deg1)

    # -- 2. RANK -----------------------------------------------------------------------------------
    print("\n2. does the ground-manifold rank move C?")
    rep["rank"] = {}
    for r in (None, 4, 2, 1):
        E, Om, I = streams_for_star(rank=r)
        c = coherence([E, Om, I])
        rep["rank"]["full" if r is None else str(r)] = c
        print("   rank %-5s C = %.4f" % ("full" if r is None else r, c))
    spread = max(rep["rank"].values()) - min(rep["rank"].values())
    rep["rank_spread"] = spread
    print("   spread across ranks = %.4f   (his tree sd 0.020, star-minus-tree gap 0.053)" % spread)

    # -- 3. MISMATCH -------------------------------------------------------------------------------
    print("\n3. is a mismatched-trio null calibrated?")
    # STRICT: each graph's three streams share nothing at all
    strict_m, strict_x = [], []
    graphs = [[smooth(rng) for _ in range(3)] for _ in range(40)]
    for g in graphs:
        strict_m.append(coherence(g))
    for _ in range(TRIALS * 4):
        a, b, c = rng.choice(len(graphs), 3, replace=False)
        strict_x.append(coherence([graphs[a][0], graphs[b][1], graphs[c][2]]))
    # REALISTIC: streams of one graph share a sweep geometry, which is not a mechanism
    real_m, real_x = [], []
    rgraphs = []
    for _ in range(40):
        tr = float(rng.uniform(1.0, 6.0))
        off = float(rng.uniform(0.0, 4.0))
        rgraphs.append([smooth(rng, trend=tr, offset=off) for _ in range(3)])
    for g in rgraphs:
        real_m.append(coherence(g))
    for _ in range(TRIALS * 4):
        a, b, c = rng.choice(len(rgraphs), 3, replace=False)
        real_x.append(coherence([rgraphs[a][0], rgraphs[b][1], rgraphs[c][2]]))

    for name, m, x in (("strict", strict_m, strict_x), ("realistic", real_m, real_x)):
        p95 = float(np.percentile(x, 95))
        frac = float(np.mean(np.array(m) >= p95))
        rep["mismatch_" + name] = {"matched_mean": float(np.mean(m)),
                                   "mismatched_mean": float(np.mean(x)),
                                   "mismatched_p95": p95, "matched_above_p95": frac}
        print("   %-10s matched %.4f  mismatched %.4f  p95 %.4f  matched above p95: %.1f%%"
              % (name, np.mean(m), np.mean(x), p95, 100 * frac))
    if rep["mismatch_strict"]["matched_above_p95"] > 0.12:
        fails.append("even the strict arm is not calibrated (%.1f%%); the recommendation is unsafe"
                     % (100 * rep["mismatch_strict"]["matched_above_p95"]))

    # -- control: POWER. the test must SEE a real shared mechanism ---------------------------------
    shared = []
    for _ in range(40):
        base = smooth(rng)
        shared.append([base + 0.25 * smooth(rng) for _ in range(3)])
    sh_m = [coherence(g) for g in shared]
    sh_x = []
    for _ in range(TRIALS * 2):
        a, b, c = rng.choice(len(shared), 3, replace=False)
        sh_x.append(coherence([shared[a][0], shared[b][1], shared[c][2]]))
    p95 = float(np.percentile(sh_x, 95))
    power = float(np.mean(np.array(sh_m) >= p95))
    rep["control_power"] = {"matched": float(np.mean(sh_m)), "mismatched": float(np.mean(sh_x)),
                            "detected": power}
    print("   POWER    a genuinely shared driver: matched %.4f vs mismatched %.4f, detected %.0f%%"
          % (np.mean(sh_m), np.mean(sh_x), 100 * power))
    if power < 0.5:
        fails.append("the mismatch test cannot detect a real shared driver (%.0f%%); it has no power"
                     % (100 * power))

    print()
    if fails:
        for f in fails:
            print("CONTROL FAILED: %s" % f)
        rep["verdict"] = "FAILED"
    else:
        rep["verdict"] = "OK"
        print("VERDICT: OK. Identity, floor, star degeneracy and power controls all behaved.")

    out = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print("wrote %s" % os.path.basename(out))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
