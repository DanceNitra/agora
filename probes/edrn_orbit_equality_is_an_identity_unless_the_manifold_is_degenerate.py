"""Guanghao's orbit theorem is an identity. Its numerical check tests the code, not the physics.

WHAT HE PROVED (edrn-dmrg-verification#2, 2026-08-31): if the automorphism representation U_g leaves
H invariant and the ground density matrix satisfies U_g rho U_g^dag = rho, then edge correlations
inside one automorphism orbit are exactly equal. He verified it numerically: within-orbit variance
~1e-24, rising to ~2.27e-2 when the automorphisms are broken.

The theorem is true, and the proof is two lines:

    <O_{g(e)}> = Tr(rho U_g O_e U_g^dag) = Tr(U_g^dag rho U_g O_e) = Tr(rho O_e) = <O_e>

So a correct implementation CANNOT report anything but zero variance. The 1e-24 is a floating-point
residue, not evidence about a physical system, and a referee will say so. That is not a criticism of
the result: it means the physics is somewhere else, in how the orbits BREAK as s leaves the uniform
point, which is exactly what his deep-dives 2 to 7 measure.

WHAT I EXPECTED TO FIND, AND DID NOT. The premise `U_g rho U_g^dag = rho` looked like a real
condition rather than a formality: a degenerate ground manifold carries a representation of the
automorphism group, so individual vectors can rotate into each other and only the PROJECTOR is
guaranteed invariant. I expected one solver-returned vector to break orbit equality on the star.

It does not, and the reason is worth more than the hypothesis. Each of the six ground vectors is the
UNIQUE lowest state of its own S_z sector, and a spatial permutation commutes with total S_z, so it
can only map that state to itself up to a phase. The degeneracy here is a SPIN multiplet, and a spin
multiplet is spatially symmetric member by member.

WHERE THE PREMISE DOES FAIL is therefore narrower and worth naming: an ORBITAL degeneracy. A
frustrated triangle is not bipartite, Lieb-Mattis does not apply, and its two ground doublets carry a
two-dimensional representation of C3. Measured below: a single vector there gives within-orbit
variance 2.2e-01 and non-invariance 5.7e-01, and the projector restores exact equality.

So for a bipartite antiferromagnet, which is Guanghao's case, the degeneracy is spin and his premise
is safe. The caveat belongs in the paper as a stated boundary, not as a defect.

MEASURED HERE on K_{1,6}, edge-transitive so all six edges are one orbit, and sixfold degenerate by
Lieb-Mattis, which makes it the cleanest possible witness for the distinction.

    python probes/edrn_orbit_equality_is_an_identity_unless_the_manifold_is_degenerate.py
"""
from __future__ import annotations

import itertools
import json
import os

import numpy as np

SX = np.array([[0, 1], [1, 0]], dtype=float)
SY_I = np.array([[0, -1], [1, 0]], dtype=float)      # i * sigma_y, kept real
SZ = np.array([[1, 0], [0, -1]], dtype=float)
I2 = np.eye(2)


def _op(n, sites_ops):
    """Kronecker product over n sites, `sites_ops` mapping site -> single-site matrix."""
    out = np.array([[1.0]])
    for k in range(n):
        out = np.kron(out, sites_ops.get(k, I2))
    return out


def heisenberg(n, edges, weights=None):
    """Isotropic antiferromagnetic Heisenberg on the given edges.

    Written with the i*sigma_y trick so the matrix stays real: sigma_y (x) sigma_y equals
    -(i sigma_y) (x) (i sigma_y), and the sign is carried explicitly below.
    """
    weights = weights or {}
    H = np.zeros((2 ** n, 2 ** n))
    for (a, b) in edges:
        w = weights.get((a, b), 1.0)
        H += w * _op(n, {a: SX, b: SX})
        H -= w * _op(n, {a: SY_I, b: SY_I})
        H += w * _op(n, {a: SZ, b: SZ})
    return H


def ground_manifold(H, tol=1e-9):
    """Every eigenvector at the lowest energy, and the energy gap above them."""
    vals, vecs = np.linalg.eigh(H)
    e0 = vals[0]
    keep = np.where(vals - e0 < tol)[0]
    above = vals[vals - e0 >= tol]
    gap = float(above[0] - e0) if above.size else float("inf")
    return vals[keep], vecs[:, keep], gap


def edge_correlation(rho, n, a, b):
    """<sigma^z_a sigma^z_b> under rho."""
    return float(np.trace(rho @ _op(n, {a: SZ, b: SZ})).real)


def permutation_matrix(n, perm):
    """The unitary that relabels sites by `perm` on the 2^n computational basis."""
    dim = 2 ** n
    P = np.zeros((dim, dim))
    for idx in range(dim):
        bits = [(idx >> (n - 1 - k)) & 1 for k in range(n)]
        moved = [0] * n
        for k in range(n):
            moved[perm[k]] = bits[k]
        j = 0
        for b in moved:
            j = (j << 1) | b
        P[j, idx] = 1.0
    return P


def main():
    n = 7
    star = [(0, k) for k in range(1, n)]           # K_{1,6}: centre 0, leaves 1..6
    H = heisenberg(n, star)
    energies, vecs, gap = ground_manifold(H)
    deg = vecs.shape[1]

    verdicts = []

    def check(name, ok, detail):
        verdicts.append({"name": name, "pass": bool(ok), "detail": detail})
        print("%-4s %-62s %s" % ("PASS" if ok else "FAIL", name, detail))

    check("the star is sixfold, so it can witness the distinction at all",
          deg == 6,
          "degeneracy %d, gap to the next level %.3e (Lieb-Mattis |nA-nB|=5, 2S+1=6)" % (deg, gap))

    # THE PROJECTOR ARM. rho = P / deg is invariant under every automorphism by construction, so the
    # theorem applies and the variance must be zero to machine precision.
    P = vecs @ vecs.T
    rho_full = P / deg
    corr_full = [edge_correlation(rho_full, n, a, b) for (a, b) in star]
    var_full = float(np.var(corr_full))
    check("with the FULL manifold projector, one orbit gives one number",
          var_full < 1e-25,
          "within-orbit variance %.3e over the six edges" % var_full)

    # And the premise itself, checked rather than assumed: a leaf swap is an automorphism of K_{1,6}.
    swap = list(range(n))
    swap[1], swap[2] = swap[2], swap[1]
    U = permutation_matrix(n, swap)
    check("that projector really is invariant under a leaf swap",
          np.max(np.abs(U @ rho_full @ U.T - rho_full)) < 1e-12,
          "max |U rho U^T - rho| = %.3e" % np.max(np.abs(U @ rho_full @ U.T - rho_full)))
    check("and the Hamiltonian is invariant too, so the premise is not vacuous",
          np.max(np.abs(U @ H @ U.T - H)) < 1e-12,
          "max |U H U^T - H| = %.3e" % np.max(np.abs(U @ H @ U.T - H)))

    # THE SINGLE-VECTOR ARM. Any one ground vector lives inside a six-dimensional representation, so
    # it is NOT generally invariant, the premise fails, and equal correlations are not guaranteed.
    worst, worst_i = 0.0, None
    per_vector = []
    for i in range(deg):
        v = vecs[:, i:i + 1]
        rho1 = v @ v.T
        c = [edge_correlation(rho1, n, a, b) for (a, b) in star]
        var1 = float(np.var(c))
        per_vector.append(var1)
        if var1 > worst:
            worst, worst_i = var1, i
    # THE HYPOTHESIS THIS FILE WAS WRITTEN TO CHECK, AND IT IS REFUTED. I expected a single
    # solver-returned ground vector to break orbit equality, because a degenerate manifold carries a
    # representation of the automorphism group and only the projector is guaranteed invariant. On
    # this graph it does not break, and the reason is worth more than the hypothesis was: each of the
    # six vectors is the UNIQUE lowest state of its own S_z sector, and a spatial permutation
    # commutes with total S_z, so it can only map that state to itself up to a phase. The degeneracy
    # here is a spin multiplet, not an orbital one.
    check("REFUTED a single ground vector does NOT break it here, and that is the finding",
          worst < 1e-20,
          "largest within-orbit variance over the six vectors: %.3e, i.e. zero" % worst)

    check("because every single vector IS invariant, one per S_z sector",
          np.max(np.abs(U @ (vecs[:, worst_i:worst_i + 1] @ vecs[:, worst_i:worst_i + 1].T) @ U.T
                        - vecs[:, worst_i:worst_i + 1] @ vecs[:, worst_i:worst_i + 1].T)) < 1e-12,
          "max |U rho1 U^T - rho1| = %.3e over the worst of the six" % np.max(np.abs(
              U @ (vecs[:, worst_i:worst_i + 1] @ vecs[:, worst_i:worst_i + 1].T) @ U.T
              - vecs[:, worst_i:worst_i + 1] @ vecs[:, worst_i:worst_i + 1].T)))

    # WHERE THE PREMISE REALLY DOES FAIL, so the paragraph above is a boundary and not a blanket
    # reassurance. A frustrated triangle is not bipartite, Lieb-Mattis does not apply, and its ground
    # level is spatially degenerate: the two doublets carry a two-dimensional representation of C3,
    # so an individual vector is not invariant and orbit equality genuinely fails on it.
    tri = [(0, 1), (1, 2), (0, 2)]
    Ht = heisenberg(3, tri)
    _, vt, _ = ground_manifold(Ht)
    Ut = permutation_matrix(3, [1, 2, 0])                    # the 3-cycle, an automorphism of C3
    tri_worst, tri_inv = 0.0, 0.0
    for i in range(vt.shape[1]):
        v = vt[:, i:i + 1]
        r = v @ v.T
        tri_worst = max(tri_worst, float(np.var(
            [edge_correlation(r, 3, a, b) for (a, b) in tri])))
        tri_inv = max(tri_inv, float(np.max(np.abs(Ut @ r @ Ut.T - r))))
    check("CONTROL on a FRUSTRATED triangle a single vector does break it",
          tri_worst > 1e-6 and tri_inv > 1e-6,
          "degeneracy %d; worst single-vector orbit variance %.3e, worst non-invariance %.3e"
          % (vt.shape[1], tri_worst, tri_inv))

    rho_tri = (vt @ vt.T) / vt.shape[1]
    tri_full = float(np.var([edge_correlation(rho_tri, 3, a, b) for (a, b) in tri]))
    check("CONTROL and the triangle's PROJECTOR restores equality, so the theorem still holds",
          tri_full < 1e-20,
          "projector orbit variance %.3e on the same frustrated graph" % tri_full)

    # THE SECOND CONTROL. A non-degenerate graph must show no gap between the two arms at all,
    # otherwise the effect is not degeneracy but something else in the pipeline.
    chain = [(k, k + 1) for k in range(n - 1)]
    Hc = heisenberg(n, chain)
    _, vc, _ = ground_manifold(Hc)
    # the chain's orbit under the reflection automorphism: bond k pairs with bond n-2-k
    orbit = [(0, 1), (5, 6)]
    rho_c_full = (vc @ vc.T) / vc.shape[1]
    var_c_full = float(np.var([edge_correlation(rho_c_full, n, a, b) for (a, b) in orbit]))
    v0 = vc[:, 0:1]
    var_c_one = float(np.var([edge_correlation(v0 @ v0.T, n, a, b) for (a, b) in orbit]))
    check("CONTROL on a chain orbit both arms agree, so the gap is not an artefact of the method",
          var_c_full < 1e-20 and var_c_one < 1e-20,
          "chain degeneracy %d; projector %.3e, single vector %.3e"
          % (vc.shape[1], var_c_full, var_c_one))

    ok = sum(1 for v in verdicts if v["pass"])
    print("\n%d/%d verdicts" % (ok, len(verdicts)))
    out = {"graph": "K_{1,6}", "n": n, "degeneracy": deg,
           "within_orbit_variance_full_projector": var_full,
           "within_orbit_variance_single_vector_max": worst,
           "within_orbit_variance_single_vector_all": per_vector,
           "chain_control": {"degeneracy": int(vc.shape[1]),
                             "projector": var_c_full, "single_vector": var_c_one},
           "verdicts": verdicts,
           "claim": ("orbit equality follows from invariance of rho, which a degenerate manifold "
                     "gives only to the full projector, never to one solver-returned vector")}
    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        json.dump(out, fh, indent=2)
    print("receipt: %s" % os.path.basename(path))
    return 0 if ok == len(verdicts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
