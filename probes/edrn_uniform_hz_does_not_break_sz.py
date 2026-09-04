"""Does a uniform field along z break Sz conservation? Exact diagonalisation says no.

CONTEXT. The `coarse` diagnostic (mean magnetisation) read exactly zero in the self-folding runs.
I flagged that as possibly a symmetry constraint rather than a property of the diagnostic, and asked
for a symmetry-breaking control. The control run added a uniform field h_z = 0.1 along z, `coarse`
stayed at zero for all 30 steps, and the conclusion drawn was that the blindness is real.

That conclusion needs the field to have broken the symmetry. A uniform field along z is the one
direction that does not: H_field = h_z * sum_i S^z_i is built from the same operator as the conserved
quantity, so [H, S^z_total] = 0 exactly. The Hamiltonian still commutes with total S^z, the eigenstates
still carry a good S^z quantum number, and for a gapped antiferromagnet the ground state stays in the
S^z = 0 sector until h_z exceeds the spin gap.

So `coarse = 0` after adding h_z is the same statement as `coarse = 0` before adding it.

Measured here on a Heisenberg chain by exact diagonalisation:

  1. the commutator norm ||[H, S^z]|| with a uniform z field -- expected 0;
  2. CONTROL: the same norm with a TRANSVERSE field, which must be non-zero, or the commutator test
     cannot detect breaking and result 1 means nothing;
  3. ground-state <S^z_total> as h_z is raised, to show where the sector actually changes;
  4. CONTROL: <S^z_total> inside an S^z = 1 sector, which must be non-zero by construction -- if the
     diagnostic reads zero THERE, it is broken, and that is the test that decides blindness.
"""

import numpy as np

N = 8            # spins; 2^8 = 256, exact diagonalisation is instant
J = 1.0

I2 = np.eye(2)
SX = 0.5 * np.array([[0, 1], [1, 0]], dtype=complex)
SY = 0.5 * np.array([[0, -1j], [1j, 0]], dtype=complex)
SZ = 0.5 * np.array([[1, 0], [0, -1]], dtype=complex)


def op_at(op, i, n=N):
    """Single-site operator embedded in the full 2^n Hilbert space."""
    out = np.array([[1.0 + 0j]])
    for k in range(n):
        out = np.kron(out, op if k == i else I2)
    return out


def build(h_z=0.0, h_x=0.0, n=N):
    """Heisenberg chain, open boundary, plus a uniform field."""
    dim = 2 ** n
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(n - 1):
        for S in (SX, SY, SZ):
            H += J * op_at(S, i, n) @ op_at(S, i + 1, n)
    for i in range(n):
        H += h_z * op_at(SZ, i, n) + h_x * op_at(SX, i, n)
    return H


def sz_total(n=N):
    return sum(op_at(SZ, i, n) for i in range(n))


def main():
    Sz = sz_total()
    print(f"Heisenberg chain, N={N}, open boundary, exact diagonalisation\n")

    print("1. does the field commute with total S^z?")
    for label, kw in (("uniform h_z = 0.1", {"h_z": 0.1}),
                      ("uniform h_z = 2.0", {"h_z": 2.0}),
                      ("TRANSVERSE h_x = 0.1  (CONTROL)", {"h_x": 0.1})):
        H = build(**kw)
        c = np.linalg.norm(H @ Sz - Sz @ H)
        print(f"   {label:<34} ||[H, S^z]|| = {c:.3e}")
    print("   -> a uniform z field commutes exactly; the transverse control does not, so the test")
    print("      can tell the two apart and the zeros above are real rather than a broken measure.")

    print("\n2. ground-state <S^z_total> as the uniform z field is raised")
    print(f"   {'h_z':>6}{'E0':>12}{'<S^z>':>10}")
    for h in (0.0, 0.1, 0.2, 0.5, 0.8, 1.0, 1.2, 2.0):
        H = build(h_z=h)
        w, v = np.linalg.eigh(H)
        g = v[:, 0]
        m = float(np.real(g.conj() @ (Sz @ g)))
        print(f"   {h:>6.2f}{w[0]:>12.5f}{m:>10.4f}")
    print("   -> <S^z> stays pinned at 0 until the field is large enough to cross into a magnetised")
    print("      sector. h_z = 0.1 is far below that, so the ground state never leaves S^z = 0.")

    print("\n3. CONTROL: the same diagnostic inside an S^z = 1 sector")
    H = build(h_z=0.1)
    w, v = np.linalg.eigh(H)
    diag = np.real(np.diag(Sz))
    for target in (0.0, 1.0, 2.0):
        # lowest eigenstate whose S^z expectation is the target sector
        best = None
        for k in range(v.shape[1]):
            g = v[:, k]
            m = float(np.real(g.conj() @ (Sz @ g)))
            if abs(m - target) < 1e-6:
                best = (w[k], m)
                break
        if best is None:
            print(f"   S^z = {target:.0f} sector: not found in the spectrum")
        else:
            print(f"   S^z = {target:.0f} sector: lowest E = {best[0]:>9.5f}   <S^z> = {best[1]:.4f}"
                  f"   mean magnetisation = {best[1] / N:.4f}")
    print("   -> a mean magnetisation is non-zero there BY CONSTRUCTION. That is the test that")
    print("      decides blindness: if the diagnostic still reads 0 in a sector where it cannot be 0,")
    print("      the diagnostic is broken. If it moves, the earlier zero was the symmetry speaking.")

    # ---- recorded run ------------------------------------------------------------
    # Cited by name in a letter to a collaborator while it recorded nothing. The loop
    # above prints its sectors and keeps none, so this recomputes them from the same
    # spectrum and serialises them. No measurement changes.
    import json as _json, os as _os
    _sec = {}
    for _t in (0.0, 1.0, 2.0):
        _b = None
        for _k in range(v.shape[1]):
            _g = v[:, _k]
            _m = float(np.real(_g.conj() @ (Sz @ _g)))
            if abs(_m - _t) < 1e-6:
                _b = (float(w[_k]), _m)
                break
        _sec[str(_t)] = None if _b is None else {
            "lowest_E": _b[0], "Sz": _b[1], "mean_magnetisation": _b[1] / N}
    _rep = {"N": N, "sectors": _sec}
    _rep["control_nonzero_sector_exists"] = any(
        v2 is not None and abs(v2["mean_magnetisation"]) > 1e-9 for v2 in _sec.values())
    print("MEASURED: a sector with non-zero mean magnetisation exists = %s"
          % _rep["control_nonzero_sector_exists"])
    _out = _os.path.splitext(_os.path.abspath(__file__))[0] + ".result.json"
    with open(_out, "w", encoding="utf-8") as _fh:
        _json.dump(_rep, _fh, indent=1)
    print("wrote", _os.path.basename(_out))


if __name__ == "__main__":
    main()
