"""Two questions his Sec. 6 note raises, and one it settles about our own reading.

WHY THIS EXISTS. A red team pass caught a real error in a draft reply. The draft said the ring row
of Table 3 does not reproduce and that we could not explain it. His paper explains it, one paragraph
past the footnote the draft cited:

  "Real-arithmetic Lanczos searches converge to real superpositions whose E(1) can be as large as
   0.1310, while the symmetric mixed density matrix returns zero. The value 0.0993 +- 0.0286
   reported in Table 3 likely arises from a mixture of different S_z sectors and should not be read
   as a violation of the symmetry constraint."

Our own numbers are his: the single-eigenvector reading gives E(1) = 0.131 on the ring and the
manifold average gives 4.6e-16. So the ring is a positive control for the manifold reading rather
than a gap in it, and this probe asks the two questions that finish the argument.

QUESTION 1, AND THE ANSWER IS NO. The guess was that his ring row does not fix the magnetisation
sector, and that pooling the sectors would return his 0.0891 single-seed and his 0.0286 spread.
Measured: pooling changes nothing. The globally lowest state lives in the same sector the fixed
reading picks, so pooled and fixed agree to 1e-15 and neither shows any cross-seed spread at all.
The instrument cannot construct the mixture his note describes, which is a fact about this probe
rather than about his row, and the control that says so is red on purpose.

QUESTION 2. The reply proposes reporting the manifold valley for random edge (8,14) at s = 0.90.
The paper's own criterion for a significant valley is a non-zero ground-state gap, so a proposal
that never measures the gap there is not ready. The gap is measured at the manifold valley and at
his single-eigenvector valley, s = 1.20, for comparison.

CONTROLS:
  * THE POOLED READING MUST DIFFER FROM THE FIXED-SECTOR ONE somewhere on the ring, or pooling is
    a no-op and question 1 is unanswerable rather than answered.
  * THE MANIFOLD AVERAGE MUST STILL GIVE E(1) = 0 on the ring under pooling, because that is his
    exact statement and it does not depend on how the single state was chosen.
  * THE GAP INSTRUMENT MUST SEE A KNOWN DEGENERACY: at s = 1 the ring's ground manifold is
    degenerate, so the instrument must report more than one state at the ground energy, with a
    finite gap above them. The first version of this control demanded a ZERO gap and could only
    fail: gap_at measures the distance to the first level ABOVE the manifold.
"""
import io
import itertools
import json
import os
import sys
import time

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import eigsh

try:
    import networkx as nx
except ImportError:                                   # pragma: no cover
    print("CANNOT RUN: networkx is not installed")
    raise SystemExit(2)

N = 15
SECTORS = tuple(range(N + 1))          # POOLED: every magnetisation sector, as his ring row does
NARROW = (6, 7, 8, 9)
EPS_DEGEN = 1e-8
GRID = np.linspace(0.0, 3.0, 61)
SEEDS = (0, 1, 2)
RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"


def ring_edges():
    return [(i, (i + 1) % N) for i in range(N)]


def random_edges():
    return sorted(tuple(sorted(e)) for e in nx.gnm_random_graph(N, 27, seed=42).edges())


def build(edges, J_vals, n_up):
    basis = list(itertools.combinations(range(N), n_up))
    if not basis:
        return None, basis
    index = {st: i for i, st in enumerate(basis)}
    H = lil_matrix((len(basis), len(basis)), dtype=float)
    for (i, j), J in zip(edges, J_vals):
        for idx, st in enumerate(basis):
            H[idx, idx] += J * (1 if i in st else -1) * (1 if j in st else -1)
        for idx, st in enumerate(basis):
            iu, ju = i in st, j in st
            if iu and not ju:
                ns = list(st); ns.remove(i); ns.append(j)
                H[idx, index[tuple(sorted(ns))]] += 2.0 * J
            elif ju and not iu:
                ns = list(st); ns.remove(j); ns.append(i)
                H[idx, index[tuple(sorted(ns))]] += 2.0 * J
    return csr_matrix(H), basis


def solve(H, seed, k=4):
    if H.shape[0] == 1:
        return np.array([H.toarray()[0, 0]]), np.array([[1.0]])
    rng = np.random.default_rng(seed)
    v0 = rng.standard_normal(H.shape[0])
    kk = min(k, H.shape[0] - 1)
    vals, vecs = eigsh(H, k=kk, which="SA", v0=v0, maxiter=20000, tol=1e-10)
    o = np.argsort(vals)
    return vals[o], vecs[:, o]


def zz(basis, psi, edges):
    w = np.abs(psi) ** 2
    return np.array([float(np.dot(w, np.fromiter(
        (((1 if i in st else -1) * (1 if j in st else -1)) for st in basis),
        dtype=float, count=len(basis)))) for (i, j) in edges])


def sectors_at(edges, J, sectors, seed):
    out = {}
    for n_up in sectors:
        H, basis = build(edges, J, n_up)
        if H is None:
            continue
        vals, vecs = solve(H, seed + 1000 * n_up)
        out[n_up] = (vals, vecs, basis)
    return out


def e_pooled_single(edges, J, seed, sectors):
    """One real eigenvector, the globally lowest across pooled sectors. His ring reading."""
    per = sectors_at(edges, J, sectors, seed)
    n_up = min(per, key=lambda n: per[n][0][0])
    vals, vecs, basis = per[n_up]
    return float(np.std(zz(basis, vecs[:, 0], edges))), per


def e_manifold(per, edges):
    e0 = min(v[0][0] for v in per.values())
    acc, n = None, 0
    for vals, vecs, basis in per.values():
        for k in range(len(vals)):
            if abs(vals[k] - e0) < EPS_DEGEN:
                c = zz(basis, vecs[:, k], edges)
                acc = c if acc is None else acc + c
                n += 1
    return float(np.std(acc / n)), n


def gap_at(edges, J, seed, sectors):
    """The lowest two distinct energies across the pooled sectors."""
    per = sectors_at(edges, J, sectors, seed)
    levels = sorted(float(v) for vals, _, _ in per.values() for v in vals)
    e0 = levels[0]
    for e in levels:
        if e - e0 > EPS_DEGEN:
            return e - e0, sum(1 for x in levels if abs(x - e0) < EPS_DEGEN)
    return 0.0, len(levels)


def main():
    started = time.time()
    edges = ring_edges()
    e_idx = 0

    # QUESTION 1. The ring, one real eigenvector, sectors POOLED.
    pooled, fixed = {}, {}
    for seed in SEEDS:
        ys_p, ys_f = [], []
        for s in GRID:
            J = [1.0] * len(edges)
            J[e_idx] = float(s)
            v, _ = e_pooled_single(edges, J, seed, SECTORS)
            ys_p.append(v)
            v2, _ = e_pooled_single(edges, J, seed, (7,))
            ys_f.append(v2)
        pooled[seed] = ys_p
        fixed[seed] = ys_f
        print("  ring seed %d done  %.0fs" % (seed, time.time() - started), flush=True)

    def valley(ys):
        y = np.array(ys)
        k = int(np.argmin(y))
        return float(GRID[k]), float(y[0] - y[k])

    p_pos, p_dep = zip(*(valley(pooled[s]) for s in SEEDS))
    f_pos, f_dep = zip(*(valley(fixed[s]) for s in SEEDS))

    # The manifold reading at s=1 under pooling, and the doublet control.
    J1 = [1.0] * len(edges)
    J1[e_idx] = 1.0
    _, per1 = e_pooled_single(edges, J1, 0, SECTORS)
    e1_manifold, n_states_1 = e_manifold(per1, edges)
    gap_ring_1, degen_ring_1 = gap_at(edges, J1, 0, SECTORS)

    # QUESTION 2. The gap on random edge (8,14) at both valley positions.
    redges = random_edges()
    ridx = redges.index((8, 14))
    gaps = {}
    for s in (0.90, 1.20):
        J = [1.0] * len(redges)
        J[ridx] = s
        g, d = gap_at(redges, J, 0, NARROW)
        gaps["s=%.2f" % s] = {"gap": g, "ground_degeneracy": d}
        print("  random (8,14) s=%.2f gap %.6f  %.0fs" % (s, g, time.time() - started), flush=True)

    checks = []

    def check(nm, ok, got):
        checks.append({"check": nm, "pass": bool(ok), "got": got})

    check("CONTROL_POOLING_CHANGES_THE_RING_READING",
          max(abs(np.array(pooled[s]) - np.array(fixed[s])).max() for s in SEEDS) > 1e-9,
          "largest pooled-minus-fixed difference on the ring is %.4f"
          % max(abs(np.array(pooled[s]) - np.array(fixed[s])).max() for s in SEEDS))
    check("CONTROL_THE_MANIFOLD_STILL_GIVES_E1_ZERO_UNDER_POOLING",
          abs(e1_manifold) < 1e-6,
          "E(1) averaged over %d degenerate states is %.3e" % (n_states_1, e1_manifold))
    # THE CONTROL WAS MIS-SPECIFIED, and the run said so. It asked for a ZERO gap at s=1 on the
    # ring because the ground state is a doublet. gap_at returns the distance to the first level
    # ABOVE the degenerate manifold, which is finite by construction, so the check could only fail.
    # The property that actually tests the instrument is that it SEES the degeneracy.
    check("CONTROL_THE_GAP_INSTRUMENT_SEES_THE_RING_DEGENERACY_AT_s_1",
          degen_ring_1 >= 2 and gap_ring_1 > 1e-6,
          "%d states at the ground energy at s=1 and a gap of %.4f above them"
          % (degen_ring_1, gap_ring_1))
    # NOT RENAMED WHEN IT CAME BACK NO. His note attributes the ring row to a mixture of S_z
    # sectors; pooling the sectors and taking the globally lowest state is the cheapest reading of
    # that, and it changes nothing, so this instrument cannot construct his mixture. The red entry
    # is the finding.
    check("POOLING_PRODUCES_A_CROSS_SEED_SPREAD_ON_THE_RING",
          float(np.std(p_dep)) > 1e-6,
          "pooled depths %s, spread %.4f; fixed-sector depths %s, spread %.4f; his row is "
          "0.0993 +- 0.0286"
          % ([round(x, 4) for x in p_dep], float(np.std(p_dep)),
             [round(x, 4) for x in f_dep], float(np.std(f_dep))))
    check("THE_MANIFOLD_VALLEY_ON_8_14_SITS_AT_A_NON_ZERO_GAP",
          gaps["s=0.90"]["gap"] > 1e-6,
          "gap %.6f with ground degeneracy %d at s=0.90, against gap %.6f and degeneracy %d at "
          "s=1.20" % (gaps["s=0.90"]["gap"], gaps["s=0.90"]["ground_degeneracy"],
                      gaps["s=1.20"]["gap"], gaps["s=1.20"]["ground_degeneracy"]))

    out = {
        "probe": os.path.basename(__file__),
        "his_note": ("Real-arithmetic Lanczos searches converge to real superpositions whose E(1) "
                     "can be as large as 0.1310, while the symmetric mixed density matrix returns "
                     "zero. The value 0.0993 +- 0.0286 reported in Table 3 likely arises from a "
                     "mixture of different S_z sectors."),
        "ring_pooled": {"valley_s": list(p_pos), "depth": list(p_dep),
                        "depth_spread": float(np.std(p_dep))},
        "ring_fixed_sector": {"valley_s": list(f_pos), "depth": list(f_dep),
                              "depth_spread": float(np.std(f_dep))},
        "ring_manifold_E1": e1_manifold,
        "ring_ground_degeneracy_at_s1": degen_ring_1,
        "random_8_14_gaps": gaps,
        "checks": checks,
        "all_passed": all(c["pass"] for c in checks),
        "elapsed_s": round(time.time() - started, 1),
        "scope": ("One ring edge, which suffices because the ring is edge-transitive, 61 points "
                  "over s in [0,3], three seeds, all sixteen magnetisation sectors pooled against "
                  "N_up=7 fixed. The gap on random edge (8,14) is measured over N_up 6 to 9 at two "
                  "positions only, not scanned."),
    }
    with io.open(RESULT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps({"checks": checks, "all_passed": out["all_passed"]}, indent=1))
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
