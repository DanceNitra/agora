"""Is the 'half-chain parity sets the valley position' rule a rule, or an argmin at the scan edge?

WHAT IS BEING CHECKED. Guanghao's displacement experiment (edrn-dmrg-verification#2) reports that the
valley position s* of the fine diagnostic is fixed by the parity of the half-chains flanking the
contradiction bond, from four points: N=6 -> 0.125, N=8 -> 1.750, N=10 -> 0.375, N=12 -> 1.625. Marat
reads this as a clean structural rule. Two things in the generating script make that reading unsafe,
and neither is visible in the summary CSV:

  1. `s_values = np.linspace(0.0, 3.0, 25)`, so the grid is 0, 0.125, ..., 3.0, and `find_valley` is a
     bare `np.argmin` over that grid with NO interiority test. The two "even" results sit at grid
     indices 1 and 3 of 0..24. A minimum one step from the boundary is what a monotone curve gives,
     not what a valley gives. So the parity split may be the split between "edge of scan" and "real
     interior minimum" -- two different phenomena sharing a name.
  2. At s = 0 the contradiction bond's coupling is exactly zero, so the chain SEPARATES into two
     independent open Heisenberg segments. For N = 6 and 10 each segment has an ODD number of spins
     and therefore a degenerate S=1/2 ground state; for N = 8 and 12 each segment is even and has a
     singlet ground state. That even/odd distinction is textbook for open Heisenberg chains, and DMRG
     inside a degenerate manifold returns an arbitrary member of it.

METHOD. Independent of the original: exact diagonalisation in the Sz=0 sector, no DMRG, no variational
convergence to argue about. Sector dimensions are small (924 at L=12, 48620 at L=18). The same
observable is used -- fine(s) = std over nearest-neighbour <Sz_i Sz_{i+1}> -- on the same s grid.

WHAT IT REPORTS, and each of these can contradict the rule:
  * s* and whether the argmin is INTERIOR to the scan or sits at an endpoint-adjacent grid point;
  * the gap between the two lowest eigenvalues, so a degenerate ground state is visible rather than
    silently resolved;
  * N = 14, 16, 18, which is exactly the data Guanghao says is needed to lock or break the rule, and
    which parity predicts in advance. The parity is of the BOND count per half-chain, N/2 - 1, not of
    N: 14 -> 6 and 18 -> 8 are EVEN and so predict SMALL s*, while 16 -> 7 is ODD and predicts LARGE.
    An earlier draft of this line had it backwards by reading the parity off N instead of off the
    half-chain, which would have scored a correct prediction as a failed one.

CONTROLS:
  * POSITIVE: the four published points must reproduce, or this file is measuring something else and
    nothing below it means anything.
  * The observable is recomputed from the ED ground state, not read from any of their files.

Run: python probes/edrn_valley_parity_independent_ed.py
"""
import itertools
import math
import sys
import time

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

S_GRID = np.linspace(0.0, 3.0, 25)


def basis(L):
    """Sz = 0 sector: every bitstring with L//2 up spins. Index by integer for O(1) lookup."""
    states = []
    for pos in itertools.combinations(range(L), L // 2):
        v = 0
        for p in pos:
            v |= 1 << p
        states.append(v)
    states.sort()
    return states, {s: i for i, s in enumerate(states)}


def hamiltonian(L, couplings, states, index):
    """Isotropic Heisenberg with per-bond J: sum_b J_b (Sz Sz + 1/2 (S+S- + S-S+))."""
    rows, cols, vals = [], [], []
    for i, s in enumerate(states):
        diag = 0.0
        for b in range(L - 1):
            up_i = (s >> b) & 1
            up_j = (s >> (b + 1)) & 1
            diag += couplings[b] * (0.25 if up_i == up_j else -0.25)
            if up_i != up_j:                                   # flip-flop term
                t = s ^ ((1 << b) | (1 << (b + 1)))
                rows.append(index[t]); cols.append(i); vals.append(0.5 * couplings[b])
        rows.append(i); cols.append(i); vals.append(diag)
    n = len(states)
    return csr_matrix((vals, (rows, cols)), shape=(n, n))


def fine_of(L, s, want_gap=True):
    """fine(s) = std over nearest-neighbour <Sz_i Sz_{i+1}> in the ground state, plus the gap."""
    states, index = basis(L)
    J = np.ones(L - 1)
    J[L // 2 - 1] = s                                          # the contradiction bond
    H = hamiltonian(L, J, states, index)
    k = 2 if want_gap else 1
    if H.shape[0] <= 12:                                       # tiny sector: dense is exact and safe
        w = np.linalg.eigvalsh(H.toarray())
        vecs = np.linalg.eigh(H.toarray())[1]
        e, psi = w[0], vecs[:, 0]
        gap = float(w[1] - w[0]) if len(w) > 1 else float("inf")
    else:
        w, v = eigsh(H, k=k, which="SA")
        order = np.argsort(w)
        e, psi = w[order[0]], v[:, order[0]]
        gap = float(w[order[1]] - w[order[0]]) if k > 1 else float("inf")
    p2 = psi ** 2
    corr = []
    for b in range(L - 1):
        c = 0.0
        for i, st in enumerate(states):
            zi = 0.5 if (st >> b) & 1 else -0.5
            zj = 0.5 if (st >> (b + 1)) & 1 else -0.5
            c += p2[i] * zi * zj
        corr.append(c)
    return float(np.std(corr)), gap, float(e)


PUBLISHED = {6: 0.125, 8: 1.750, 10: 0.375, 12: 1.625}


def main():
    print(f"  grid: {len(S_GRID)} points from {S_GRID[0]} to {S_GRID[-1]}, step {S_GRID[1]-S_GRID[0]:.3f}\n")
    print(f"  {'N':>3} {'half-chain':>11} {'s*':>7} {'idx':>4} {'interior':>9} "
          f"{'gap@s*':>9} {'gap@s=0':>9} {'depth':>8} {'secs':>6}")
    rows = []
    for L in (6, 8, 10, 12, 14, 16, 18):
        t0 = time.time()
        fines, gaps = [], []
        for s in S_GRID:
            f, g, _ = fine_of(L, float(s))
            fines.append(f); gaps.append(g)
        fines = np.array(fines)
        idx = int(np.argmin(fines))
        s_star = float(S_GRID[idx])
        interior = 0 < idx < len(S_GRID) - 1
        # depth against the shallower endpoint, the same convention a valley needs
        depth = float(min(fines[0], fines[-1]) - fines[idx])
        bonds = L // 2 - 1
        par = "even" if bonds % 2 == 0 else "odd"
        rows.append(dict(L=L, s_star=s_star, idx=idx, interior=interior, parity=par,
                         gap_at_star=gaps[idx], gap_at_0=gaps[0], depth=depth,
                         fines=fines.tolist()))
        print(f"  {L:>3} {str(bonds)+' '+par:>11} {s_star:>7.3f} {idx:>4} {str(interior):>9} "
              f"{gaps[idx]:>9.2e} {gaps[0]:>9.2e} {depth:>8.4f} {time.time()-t0:>6.1f}")

    print("\n  POSITIVE CONTROL -- do the four published points reproduce?")
    ok = 0
    for r in rows:
        if r["L"] in PUBLISHED:
            hit = abs(r["s_star"] - PUBLISHED[r["L"]]) < 1e-9
            ok += hit
            print(f"    N={r['L']:>3}  ED {r['s_star']:.3f}  published {PUBLISHED[r['L']]:.3f}  "
                  f"{'MATCH' if hit else 'DIFFERS'}")
    if ok < 4:
        print(f"    -> {4-ok} of 4 differ. Either the observable or the model is not the same one,")
        print("       and NOTHING below this line is a statement about their result.")

    print("\n  IS THE MINIMUM EVEN INTERIOR?")
    for r in rows:
        if not r["interior"]:
            print(f"    N={r['L']}: argmin at grid index {r['idx']} -- an ENDPOINT, not a valley")
        elif r["idx"] <= 2 or r["idx"] >= len(S_GRID) - 3:
            print(f"    N={r['L']}: argmin at grid index {r['idx']} of 0..{len(S_GRID)-1} -- "
                  f"inside, but adjacent to the scan boundary")

    print("\n  DEGENERACY AT s=0 (the chain is cut in two there)")
    for r in rows:
        half = r["L"] // 2
        print(f"    N={r['L']:>3}  halves of {half} spins ({'odd' if half % 2 else 'even'})  "
              f"gap at s=0 = {r['gap_at_0']:.2e}"
              f"{'   <-- degenerate, DMRG picks arbitrarily' if r['gap_at_0'] < 1e-8 else ''}")

    print("\n  THE PARITY RULE ON 7 POINTS")
    lo = sorted(rows, key=lambda r: r["s_star"])[:len(rows) // 2]
    lo_set = {r["L"] for r in lo}
    even_set = {r["L"] for r in rows if r["parity"] == "even"}
    print(f"    lowest-s* half : {sorted(lo_set)}")
    print(f"    even half-chain: {sorted(even_set)}")
    print(f"    rule holds: {lo_set == even_set}")

    import json
    out = "probes/edrn_valley_parity_independent_ed.result.json"
    json.dump(rows, open(out, "w"), indent=1)
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
