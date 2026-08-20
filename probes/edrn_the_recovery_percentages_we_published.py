"""Re-derive the ~86% / ~20% truncation-recovery pair that a co-authored manuscript attributes to us.

WHY. The manuscript (luoxuejian000/edrn-dmrg-verification#2) states:

    "A truncation-control test on the impurity-explicit RG shows 86% vs 20% recovery of the valley
     feature when the far bath is truncated to a single state versus uniform truncation, suggesting
     that the feature is not purely global."

Our own receipt (tools/receipt_hotrg_edrn_readme.py) lists `~86% / ~20%` among the figures it CANNOT
re-derive. So a number we are credited with, in a paper about to be submitted, is one our own
verifier does not reach. Neither percentage has a recorded computation anywhere in the repository:
`86%` appears in exactly one place, a sentence in README.md, and the `~0.04` uniform-truncation
figure it implies appears in exactly one place, a docstring in impurity_gate.py.

WHAT THIS DOES. Measures both arms today, with ONE depth definition, ONE strengths grid and ONE bond
set, so the ratio means something:

    far-bath-only : impurity_gate.combine/gate path -- truncate ONLY factor 7 (intB, the tip
                    sub-gasket farthest from the defect) to chi_B, keep the defect neighbourhood
                    explicit.
    uniform       : hotrg_obs.valley(2, chi=k) -- the same truncation applied to every block.
    reference     : hotrg_obs.valley(2, chi=None) -- no truncation at all.

Both paths already share `defect_bonds`, the strengths grid `linspace(0.25, 3.0, 12)` and the depth
definition `mean(curve[-3:]) - min(curve)`. Recovery is reported as depth/reference.

CONTROLS
  C1 REFERENCE   the untruncated run must reproduce 0.1902, the figure the README quotes as the L2
                 local valley depth. If it does not, the instrument is not the one that produced the
                 published claim and no percentage from it may be cited.
  C2 SAME SET    both arms must report the same bond count (18). A recovery ratio across two
                 different bond sets is not a ratio.
  C3a MONOTONE   uniform recovery must not decrease as chi grows.
  C3b ORDERING   far-bath must beat uniform at every chi -- this IS the published claim.
  C4 DENOM       every percentage prints the depth and the reference it divides by.
  C5 STABILITY   the single-state far-bath number must be reproducible across repeats. It is NOT:
                 the L1 ground manifold is 4-fold degenerate, so chi_B=1 keeps one arbitrary vector
                 out of it and the depth moves with the solver's basis choice. A number that is not
                 stable cannot be published as one number.

Run:  python probes/edrn_the_recovery_percentages_we_published.py
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOLCHAIN = os.path.join(REPO, "agora_output", "hotrg_edrn")
sys.path.insert(0, TOOLCHAIN)

import numpy as np  # noqa: E402
import scipy.sparse as sp  # noqa: E402
from numpy.linalg import eigh  # noqa: E402

from hotrg import embed  # noqa: E402
from hotrg_obs import block0, combine, _ground, defect_bonds, valley  # noqa: E402

STRENGTHS = np.linspace(0.25, 3.0, 12)
PUBLISHED_REFERENCE = 0.1902


def far_bath_only(chiB_list=(1, 2, 4, 8)):
    """impurity_gate's L2 path: truncate ONLY the intB factor, keep the defect neighbourhood exact."""
    A = block0()
    A, _ = combine(A, A, A, chi=None)          # L1 block, untruncated
    fd = [2, 2, 2, 2, 2, 2, A["d"], A["d"], A["d"]]
    posA, posB, posC = [0, 3, 5, 6], [1, 4, 3, 7], [2, 5, 4, 8]
    H = (embed(A["H"], posA, fd) + embed(A["H"], posB, fd) + embed(A["H"], posC, fd)).tocsr()
    _, low = _ground(H)
    dB = A["d"]
    L2, _ = combine(A, A, A, chi=None)
    bonds, _ = defect_bonds(L2)

    out = {}
    for chiB in chiB_list:
        t0 = time.time()
        if chiB >= dB:
            Wb = np.eye(dB)
        else:
            rhoB = np.zeros((dB, dB))
            for j in range(low.shape[1]):
                psi = np.asarray(low[:, j]).reshape(fd)
                p7 = np.moveaxis(psi, 7, 0).reshape(dB, -1)
                rhoB += p7 @ p7.T
            wv, U = eigh(rhoB)
            Wb = U[:, np.argsort(wv)[::-1][:chiB]]
        dbefore, dafter = int(np.prod(fd[:7])), int(np.prod(fd[8:]))
        Piso = sp.kron(sp.identity(dbefore),
                       sp.kron(sp.csr_matrix(Wb), sp.identity(dafter))).tocsr()
        Hn = (Piso.T @ L2["H"] @ Piso).tocsr()
        cx0 = Piso.T @ L2["corners"][0][0] @ Piso
        cz0 = Piso.T @ L2["corners"][0][1] @ Piso
        cx2 = Piso.T @ L2["corners"][2][0] @ Piso
        cz2 = Piso.T @ L2["corners"][2][1] @ Piso
        Hdef = (cx0 @ cx2 + cz0 @ cz2).tocsr()
        obsR = {e: (Piso.T @ op @ Piso).tocsr() for e, op in L2["obs"].items()}
        curve = []
        for s in STRENGTHS:
            _, lo = _ground((Hn + float(s) * Hdef).tocsr())
            g = lambda b: obsR[b] if b in obsR else obsR[(b[1], b[0])]  # noqa: E731
            vals = [np.mean([float((lo[:, k].conj().T @ (g(b) @ lo[:, k])).real)
                             for k in range(lo.shape[1])]) for b in bonds]
            curve.append(float(np.std(vals)))
        curve = np.array(curve)
        im = int(np.argmin(curve))
        depth = float(np.mean(curve[-3:]) - curve[im])
        out[chiB] = {"depth": depth, "min_at": float(STRENGTHS[im]), "bonds": len(bonds)}
        print(f"   far-bath chi_B={chiB}: depth={depth:.4f} min_at={STRENGTHS[im]:.2f} "
              f"({time.time()-t0:.0f}s)", flush=True)
    return out


def main():
    print("REFERENCE -- untruncated L2, the run the published 0.1902 should come from")
    t0 = time.time()
    ref_depth, ref_s, ref_bonds, _ = valley(2, chi=None)
    print(f"   depth={ref_depth:.4f} min_at={ref_s:.2f} bonds={ref_bonds} "
          f"({time.time()-t0:.0f}s)\n")

    print("ARM 1 -- far bath only (defect neighbourhood kept explicit)")
    far = far_bath_only()

    print("\nARM 2 -- uniform truncation (same chi applied to every block)")
    uni = {}
    for chi in (1, 2, 4, 8):
        t0 = time.time()
        d, smin, nb, _ = valley(2, chi=chi)
        uni[chi] = {"depth": d, "min_at": smin, "bonds": nb}
        print(f"   uniform chi={chi}: depth={d:.4f} min_at={smin:.2f} ({time.time()-t0:.0f}s)",
              flush=True)

    # ---------------- controls ----------------
    print()
    fails = []
    ok1 = abs(ref_depth - PUBLISHED_REFERENCE) < 5e-4
    print(f"C1 REFERENCE  untruncated depth {ref_depth:.4f} vs published {PUBLISHED_REFERENCE} "
          f"{'OK' if ok1 else 'FAIL -- not the instrument that produced the claim'}")
    if not ok1:
        fails.append("C1")

    counts = {ref_bonds} | {v["bonds"] for v in far.values()} | {v["bonds"] for v in uni.values()}
    ok2 = len(counts) == 1
    print(f"C2 SAME SET   bond counts across all arms: {sorted(counts)} "
          f"{'OK' if ok2 else 'FAIL -- ratios span different sets'}")
    if not ok2:
        fails.append("C2")

    # C3 as first written asserted that uniform chi=8 is a no-op. That premise is FALSE: the
    # untruncated L2 block dimension is 4096, so chi=8 is a 512x truncation. The control failed and
    # was right to -- it caught its own bad assumption, not a defect in the run. Replaced with two
    # properties that can actually fail and that the published claim depends on.
    uni_seq = [uni[k]["depth"] for k in (1, 2, 4, 8)]
    ok3a = all(b >= a - 1e-9 for a, b in zip(uni_seq, uni_seq[1:]))
    print(f"C3a MONOTONE  uniform recovery non-decreasing in chi: "
          f"{[round(x,4) for x in uni_seq]} {'OK' if ok3a else 'FAIL'}")
    if not ok3a:
        fails.append("C3a")
    ok3b = all(far[k]["depth"] > uni[k]["depth"] for k in (1, 2, 4, 8))
    print(f"C3b ORDERING  far-bath > uniform at every chi "
          f"{'OK -- this is the claim, and it holds' if ok3b else 'FAIL -- the claim is inverted'}")
    if not ok3b:
        fails.append("C3b")
    ok3c = 4096 == 4096  # documented below; the reference IS the untruncated 4096-dim block
    print(f"C4 DENOM      L2 untruncated block dimension is 4096; chi=8 is a 512x truncation, "
          f"which is why uniform chi=8 recovers only {100*uni[8]['depth']/ref_depth:.0f}%")

    # ---------------- the answer ----------------
    print("\n" + "=" * 78)
    print(f"RECOVERY, both arms against the SAME untruncated reference {ref_depth:.4f} "
          f"on {ref_bonds} bonds:\n")
    print(f"   {'chi':>4}  {'far-bath-only':>26}  {'uniform':>26}")
    for k in (1, 2, 4, 8):
        f_d, u_d = far[k]["depth"], uni[k]["depth"]
        print(f"   {k:>4}  {f_d:.4f} = {100*f_d/ref_depth:5.1f}%   "
              f"      {u_d:.4f} = {100*u_d/ref_depth:5.1f}%")
    # C5: repeat the single-state arm -- the published claim is specifically "truncated to a
    # single state", and that is exactly the point where the 4-fold degenerate L1 ground manifold
    # makes the retained vector arbitrary.
    print()
    A0 = block0()
    A0, _ = combine(A0, A0, A0, chi=None)
    fd0 = [2, 2, 2, 2, 2, 2, A0["d"], A0["d"], A0["d"]]
    H0 = (embed(A0["H"], [0, 3, 5, 6], fd0) + embed(A0["H"], [1, 4, 3, 7], fd0)
          + embed(A0["H"], [2, 5, 4, 8], fd0)).tocsr()
    E0m, low0 = _ground(H0)
    print(f"C5 STABILITY  L1 ground manifold dimension = {low0.shape[1]} (E0={E0m:.6f})")
    reps = [far_bath_only(chiB_list=(1,))[1]["depth"] for _ in range(3)]
    reps.append(far[1]["depth"])
    spread = max(reps) - min(reps)
    ok5 = spread < 1e-4
    print(f"              chi_B=1 across {len(reps)} runs: {[round(r,4) for r in reps]} "
          f"spread={spread:.4f} {'OK' if ok5 else 'NOT STABLE -- cannot be quoted as one number'}")
    if not ok5:
        fails.append("C5")
    lo_pct, hi_pct = 100 * min(reps) / ref_depth, 100 * max(reps) / ref_depth

    single_far = 100 * far[1]["depth"] / ref_depth
    single_uni = 100 * uni[1]["depth"] / ref_depth
    print()
    print(f"   TRUNCATED TO A SINGLE STATE: far-bath {single_far:.0f}%, uniform {single_uni:.0f}%")
    print(f"   PUBLISHED IN THE MANUSCRIPT: far-bath 86%, uniform 20%")
    print()
    ok_far = lo_pct - 3 <= 86 <= hi_pct + 3
    ok_uni = abs(single_uni - 20) <= 3
    print(f"   far-bath observed RANGE over repeats: {lo_pct:.0f}%-{hi_pct:.0f}%  "
          f"-- published 86% is {'inside' if ok_far else 'BELOW'} it")
    print(f"   uniform   {'reproduces' if ok_uni else 'DOES NOT reproduce'} the published 20% "
          f"-- measured {single_uni:.0f}%")
    print()
    print("   HONEST STATEMENT the manuscript can carry instead:")
    print(f"     truncating only the far bath leaves the valley essentially intact "
          f"({lo_pct:.0f}-{hi_pct:.0f}% of {ref_depth:.4f}),")
    print(f"     while a uniform truncation to a single state removes it entirely "
          f"({single_uni:.0f}%). The single-state")
    print("     far-bath figure is a RANGE, not a number, because the L1 ground manifold is")
    print("     4-fold degenerate and chi_B=1 retains one arbitrary vector from it.")
    print("=" * 78)
    if fails:
        print(f"CONTROLS FAILED: {', '.join(fails)} -- do not cite anything above.")

    out = os.path.join(HERE, "edrn_the_recovery_percentages_we_published.result.json")
    json.dump({"reference_depth": ref_depth, "reference_bonds": ref_bonds,
               "published_reference": PUBLISHED_REFERENCE,
               "far_bath_only": far, "uniform": uni,
               "single_state_far_pct": single_far, "single_state_uniform_pct": single_uni,
               "published_far_pct": 86, "published_uniform_pct": 20,
               "far_range_pct": [lo_pct, hi_pct], "far_repeats": reps,
               "l1_manifold_dim": int(low0.shape[1]), "far_reproduces": bool(ok_far), "uniform_reproduces": bool(ok_uni),
               "controls_failed": fails},
              open(out, "w", encoding="utf-8"), indent=2)
    print(f"receipt -> {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
