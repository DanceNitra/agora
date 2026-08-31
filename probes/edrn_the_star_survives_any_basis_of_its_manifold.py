"""COUNTER-PROBE 1. Is 'every single ground vector is separately invariant' an artefact of eigh?

eigh may return ANY orthonormal basis of a degenerate eigenspace. The draft's claim rests on the six
vectors it happened to return. Test: re-mix them with a random orthogonal matrix and re-measure.
Also compute the restriction V^T U V directly, which is basis-INDEPENDENT up to conjugation.
"""
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Danculus\agora\probes")
m = __import__("edrn_orbit_equality_is_an_identity_unless_the_manifold_is_degenerate")

rng = np.random.default_rng(20260831)
n = 7
star = [(0, k) for k in range(1, n)]
H = m.heisenberg(n, star)
_, V, _ = m.ground_manifold(H)
deg = V.shape[1]
print("star degeneracy:", deg)

# every automorphism generator of Aut(K_{1,6}) = S_6 on the leaves
def perm_from(cycle):
    p = list(range(n)); 
    for a, b in cycle: p[a], p[b] = p[b], p[a]
    return p

Us = {}
Us["swap(1,2)"] = m.permutation_matrix(n, perm_from([(1, 2)]))
Us["swap(3,6)"] = m.permutation_matrix(n, perm_from([(3, 6)]))
cyc = [0, 2, 3, 4, 5, 6, 1]   # 6-cycle on the leaves
Us["6-cycle"] = m.permutation_matrix(n, cyc)

print("\n-- A. the RESTRICTION of U to the ground manifold (basis-independent) --")
for name, U in Us.items():
    R = V.T @ U @ V
    dev = float(np.max(np.abs(R - np.eye(deg))))
    print("  %-10s  max|V^T U V - I| = %.3e   -> %s"
          % (name, dev, "IDENTITY on the manifold" if dev < 1e-12 else "NON-trivial rep"))

print("\n-- B. deliberate random re-mixing of the six ground vectors --")
worst_var, worst_inv = 0.0, 0.0
for trial in range(200):
    A = rng.standard_normal((deg, deg))
    Q, _ = np.linalg.qr(A)            # Haar-ish orthogonal
    W = V @ Q                         # a completely different orthonormal basis of the SAME space
    for i in range(deg):
        v = W[:, i:i + 1]
        r = v @ v.T
        c = [m.edge_correlation(r, n, a, b) for (a, b) in star]
        worst_var = max(worst_var, float(np.var(c)))
        for U in Us.values():
            worst_inv = max(worst_inv, float(np.max(np.abs(U @ r @ U.T - r))))
print("  200 random re-mixings x 6 vectors x 3 automorphisms")
print("  worst within-orbit variance : %.3e" % worst_var)
print("  worst non-invariance        : %.3e" % worst_inv)
print("  VERDICT:", "SURVIVES re-mixing" if worst_var < 1e-20 and worst_inv < 1e-12
      else "ARTEFACT of the eigh basis")

print("\n-- C. does eigh really return S_z-pure vectors? (the draft's stated REASON) --")
SZtot = sum(m._op(n, {k: m.SZ}) for k in range(n))
for i in range(deg):
    v = V[:, i]
    ez = float(v @ SZtot @ v)
    var = float(v @ SZtot @ SZtot @ v) - ez ** 2
    print("  vec %d  <2Sz> = %+7.4f   Var(2Sz) = %.3e" % (i, ez, var))
W = V @ np.linalg.qr(rng.standard_normal((deg, deg)))[0]
print("  after ONE random re-mix:")
for i in range(deg):
    v = W[:, i]
    ez = float(v @ SZtot @ v); var = float(v @ SZtot @ SZtot @ v) - ez ** 2
    print("  vec %d  <2Sz> = %+7.4f   Var(2Sz) = %.3e" % (i, ez, var))

print("\n-- D. the same restriction on the FRUSTRATED TRIANGLE (the draft's own control) --")
tri = [(0, 1), (1, 2), (0, 2)]
Ht = m.heisenberg(3, tri)
_, Vt, _ = m.ground_manifold(Ht)
Ut = m.permutation_matrix(3, [1, 2, 0])
Rt = Vt.T @ Ut @ Vt
print("  triangle degeneracy: %d   (3 sites = ODD number of spin-1/2)" % Vt.shape[1])
print("  max|V^T U V - I| = %.3e  -> NON-trivial rep, so the manifold is NOT spatially trivial"
      % float(np.max(np.abs(Rt - np.eye(Vt.shape[1])))))
print("  eigenvalues of the restriction:", np.round(np.linalg.eigvals(Rt), 4))
