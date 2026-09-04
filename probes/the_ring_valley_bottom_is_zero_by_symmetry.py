"""Is the ring's manifold-average valley bottom a measurement, or is it zero by symmetry?

WHY. A red-team lens raised this as a possible fatal defect: a 15-cycle is edge-transitive and the
projector onto a degenerate ground manifold commutes with translations, so the manifold-averaged
edge correlator is the same on every edge and E is identically zero. On that reading our reported
0.208052 would be a bug.

The reading is half right, and the half that is right matters more than the objection. The
contradiction edge carries coupling s, so the ring is only uniform AT s = 1. That is exactly where
its valley sits.

MEASURED, in sector n_up=7 on the 15-cycle with the contradiction edge at RING[8]:

    s      degeneracy   E single      E manifold     spread of averaged correlators
    0.0        1        0.208052      0.208052       8.9e-01
    1.0        2        0.130979      0.000000       3.8e-15
    3.0        1        0.222404      0.222404       8.0e-01

So the manifold-average depth is E(0) minus zero. The bottom is fixed by symmetry, not measured,
and away from s=1 the ground level is simple, so the two conventions agree exactly. The whole
difference between them lives at the single uniform point.

THE CONTROLS ARE IN THE TABLE ITSELF and either could have refuted the claim:
  * If E manifold were zero at every s, the objection would stand and our number would be a bug.
    It is not: 0.208052 at s=0 and 0.222404 at s=3.
  * If the correlator spread at s=1 were not numerical zero, the symmetry argument would be wrong.
    It is 3.8e-15 against 0.57 to 0.89 elsewhere.
  * If the degeneracy at s=1 were 1, there would be nothing to average and the point would be
    vacuous. It is 2.

Owner's standing instruction: at most 4 cores. This runs on one and takes under a minute.
"""
import itertools, numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh
N = 15
RING = [tuple(sorted((i, (i + 1) % N))) for i in range(N)]
CONTRA = RING[8]
basis = np.array([sum(1 << i for i in c) for c in itertools.combinations(range(N), 7)], dtype=np.int64)
idx = {int(b): i for i, b in enumerate(basis)}
zz = {e: np.where(((basis >> e[0]) & 1) == ((basis >> e[1]) & 1), 1.0, -1.0) for e in RING}
def both(s, seed=0):
    rows, cols, vals = [], [], []
    for k, st in enumerate(basis):
        d = 0.0
        for (a, b) in RING:
            J = s if (a, b) == CONTRA else 1.0
            sa, sb = (st >> a) & 1, (st >> b) & 1
            d += J * (0.25 if sa == sb else -0.25)
            if sa != sb:
                j = idx.get(int(st ^ ((1 << a) | (1 << b))))
                if j is not None:
                    rows.append(k); cols.append(j); vals.append(0.5 * J)
        rows.append(k); cols.append(k); vals.append(d)
    H = csr_matrix((vals, (rows, cols)), shape=(len(basis),) * 2)
    w, v = eigsh(H, k=12, which="SA", v0=np.random.default_rng(seed).standard_normal(H.shape[0]))
    o = np.argsort(w); w, v = w[o], v[:, o]
    deg = int(np.sum(w <= w[0] + 1e-9))
    single = [float(np.dot(v[:, 0] ** 2, zz[e])) for e in RING]
    avg = [float(np.mean([np.dot(v[:, j] ** 2, zz[e]) for j in range(deg)])) for e in RING]
    return float(np.std(single)), float(np.std(avg)), deg, avg
import json, os
print("  the ring is uniform ONLY at s=1, where the contradiction edge carries J=1 like the rest.")
rows = {}
for s in (0.0, 0.5, 1.0, 1.5, 3.0):
    sg, av, deg, corrs = both(s)
    spread = max(corrs) - min(corrs)
    rows["%.1f" % s] = {"degeneracy": deg, "E_single": sg, "E_manifold": av,
                        "corr_spread": spread}
    tag = "  <-- uniform ring here" if s == 1.0 else ""
    print("  s=%.1f  deg=%2d  E_single=%.9f  E_manifold=%.9f  spread of avg corrs=%.2e%s"
          % (s, deg, sg, av, spread, tag))
av0, av1 = rows["0.0"]["E_manifold"], rows["1.0"]["E_manifold"]
print()
print("  depth from the MANIFOLD average = E(0) - E(1) = %.9f - %.9f = %.9f" % (av0, av1, av0 - av1))
print("  our published-to-him figure was 0.208052")

# The controls named in the docstring, each able to fail.
assert rows["1.0"]["corr_spread"] < 1e-12, "the s=1 correlators are not identical; the symmetry argument is wrong"
assert rows["1.0"]["degeneracy"] > 1, "no degeneracy at s=1, so there is nothing to average and the point is vacuous"
assert rows["0.0"]["E_manifold"] > 0.1 and rows["3.0"]["E_manifold"] > 0.1,     "E manifold is near zero away from s=1 too, so the objection stands and our number is a bug"
print("  CONTROLS: s=1 correlators identical to %.1e, degeneracy %d, E manifold non-zero elsewhere"
      % (rows["1.0"]["corr_spread"], rows["1.0"]["degeneracy"]))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "the_ring_valley_bottom_is_zero_by_symmetry.result.json")
json.dump({"script": os.path.basename(__file__), "graph": "15-cycle", "contradiction_edge": list(CONTRA),
           "sector_n_up": 7, "rows": rows,
           "manifold_depth": av0 - av1,
           "verdict": "THE_BOTTOM_IS_ZERO_BY_SYMMETRY_AT_THE_UNIFORM_POINT",
           "controls": {"s1_correlators_identical": True, "s1_degenerate": True,
                        "E_manifold_nonzero_away_from_s1": True}},
          open(out, "w", encoding="utf-8"), indent=1)
print("  written: %s" % out)
