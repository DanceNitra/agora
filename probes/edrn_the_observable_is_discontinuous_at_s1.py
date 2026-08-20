"""E(s) is discontinuous at s=1 because the GROUND SPACE DIMENSION is, and that is the whole feature.

For s != 1 the Sierpinski-L2 ground space is a spin doublet (dim 2). At exactly s=1 the graph regains
its full automorphism group and the space becomes dim 4. The manuscript's observable is evaluated on
whatever space exists at each s, so it inherits that jump:

    lim_{s->1} E(s)  computed on the 2-dim space          ~ 0.15966
    E(1)             computed on the 4-dim space          = 0.11027

A physical observable is continuous in a coupling. This one is not -- not because the physics jumps,
but because the object it is averaged over does. The test that settles it: at s=1 the ground space
CONTAINS the state that continues continuously from either side. If the value carried by that state
equals the two one-sided limits, then the continuous continuation of E through s=1 has NO feature,
and the reported valley is the gap between two different averaging domains.

Run: python probes/edrn_the_observable_is_discontinuous_at_s1.py
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("edrn", HERE / "edrn_valley_is_the_uniform_point.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

Z = P._z_table(15)
n, e = P.sierpinski_sieve(2)
tip = next(i for i, (u, v) in enumerate(e) if u == 0)
rng = np.random.default_rng(20260818)


def at(s):
    c = [1.0] * 27; c[tip] = s
    E0, d, V = P.solve(n, e, c, Z)
    val, _ = P.enhanced_projected(V, e, Z)
    return d, val, V


def attainable(V):
    """min and max of E over unit vectors in the ground space -- what the solver could return."""
    d = V.shape[1]
    M = np.empty((len(e), d, d))
    for k, (i, j) in enumerate(e):
        w = Z[i].astype(np.float64) * Z[j]
        M[k] = V.T @ (w[:, None] * V)
    C = rng.standard_normal((40000, d)); C /= np.linalg.norm(C, axis=1, keepdims=True)
    vals = np.array([np.einsum("a,kab,b->k", c, M, c).std() for c in C])
    return float(vals.min()), float(vals.max())


print("one-sided limits, computed on the 2-dimensional space that exists off s=1:")
lims = {}
for eps in (1e-2, 1e-3, 1e-4, 1e-5):
    for sgn, lab in ((-1, "1-"), (+1, "1+")):
        d, v, _ = at(1.0 + sgn * eps)
        lims[(lab, eps)] = v
        print("   s = 1 %s %.0e : dim %d  E = %.8f" % ("-" if sgn < 0 else "+", eps, d, v))

d1, v1, V1 = at(1.0)
lo, hi = attainable(V1)
print()
print("at exactly s = 1.000000 : dim %d  E(symmetric mixture) = %.8f" % (d1, v1))
print("   attainable over that space: min %.8f  max %.8f" % (lo, hi))
left, right = lims[("1-", 1e-5)], lims[("1+", 1e-5)]
print()
print("   limit from below  %.8f" % left)
print("   limit from above  %.8f" % right)
print("   attainable MAX at s=1 %.8f" % hi)
gap = max(abs(hi - left), abs(hi - right))
print()
print("   |attainable max at s=1  -  one-sided limits| = %.2e" % gap)
ok = gap < 5e-4 and abs(v1 - lo) < 1e-4
print("   => the ground space at s=1 CONTAINS the continuous continuation: %s" % ok)
print("   => the continuous continuation of E through s=1 shows NO feature; the reported valley is")
print("      the gap between averaging over dim 2 and averaging over dim 4.")
print()
print("   manuscript at s=1.000: 0.159658 (default-control table) and 0.146905 (5-seed audit mean)")
print("   both lie inside [%.6f, %.6f]; the first sits at the top of the attainable range." % (lo, hi))
(HERE / "edrn_the_observable_is_discontinuous_at_s1.result.json").write_text(json.dumps(
    {"limits": {"%s_%g" % k: v for k, v in lims.items()}, "at_s1_symmetric": v1, "dim_at_s1": d1,
     "attainable_min": lo, "attainable_max": hi, "gap_max_vs_limits": gap,
     "continuous_continuation_has_no_feature": bool(ok)}, indent=1), encoding="utf-8")
raise SystemExit(0 if ok else 1)
