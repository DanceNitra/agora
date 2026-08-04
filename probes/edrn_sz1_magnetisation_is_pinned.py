"""In a conserved S^z = 1 sector, can the mean magnetisation move at all?

CONTEXT. I asked for the blindness test to be re-run inside a sector with total S^z != 0, because a
uniform field along z commutes with total S^z and could not decide it. That was done, and the headline
result is exactly what the sector argument predicts: in S^z = 0 the default diagnostic is pinned at
zero; in S^z = 1 it is not. Blindness was the symmetry, not the instrument.

The reported S^z = 1 curve, though, is "0.1250 rising monotonically to 0.2016", and 0.1250 is precisely
1/N for N = 8 -- the value this probe predicted for that sector. That agreement is the reason the rest
of the curve is worth checking rather than accepting: if total S^z is conserved, the mean magnetisation
in that sector is 1/N EXACTLY, for every value of the contradiction strength, because the operator
being averaged is the conserved quantity divided by N. It has no freedom to rise.

So one of these must hold, and they have different consequences:

  (a) the Hamiltonian in that scan does NOT conserve S^z, in which case "the S^z = 1 sector" is a label
      on the initial state rather than a good quantum number, and the monotonic rise is the state
      leaving the sector;
  (b) `coarse` is not <S^z_total>/N but something else -- mean |m_i|, a staggered average, a max --
      in which case the quantity is free to move and the finding stands, but under a different name;
  (c) something in the measurement.

This measures (a) directly: a Heisenberg chain whose bond coupling is scanned the way a contradiction
strength would be, inside a fixed S^z sector, with the mean magnetisation recorded at every point.

CONTROLS: the same scan in S^z = 0 must give exactly 0 (the case already agreed on), and a scan under a
field that genuinely breaks the conservation must show the magnetisation MOVING, or this probe cannot
detect movement and its flat lines mean nothing.

That second control failed on its first version and the fix is worth stating, because the trap is the
same one that produced the original h_z = 0.1 experiment. A purely TRANSVERSE field does break S^z
conservation, but it leaves a residual symmetry -- rotation by pi about x sends S^z -> -S^z -- so
<S^z> is still exactly zero and the control reported no movement while the symmetry was genuinely
broken. Breaking a conservation law is not the same as making the quantity move. The control uses a
TILTED field (h_x and h_z together), which removes the residual symmetry as well, and then it moves.
"""

import numpy as np

N = 8
I2 = np.eye(2)
SX = 0.5 * np.array([[0, 1], [1, 0]], dtype=complex)
SY = 0.5 * np.array([[0, -1j], [1j, 0]], dtype=complex)
SZ = 0.5 * np.array([[1, 0], [0, -1]], dtype=complex)


def op_at(op, i, n=N):
    out = np.array([[1.0 + 0j]])
    for k in range(n):
        out = np.kron(out, op if k == i else I2)
    return out


def chain(s, bond=(3, 4), h_x=0.0, h_z=0.0, n=N):
    """Heisenberg chain with ONE bond scaled by `s` -- the shape a 'contradiction strength' scan takes."""
    dim = 2 ** n
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(n - 1):
        w = s if (i, i + 1) == bond else 1.0
        for S in (SX, SY, SZ):
            H += w * op_at(S, i, n) @ op_at(S, i + 1, n)
    for i in range(n):
        if h_x:
            H += h_x * op_at(SX, i, n)
        if h_z:
            H += h_z * op_at(SZ, i, n)
    return H


def sz_total(n=N):
    return sum(op_at(SZ, i, n) for i in range(n))


def lowest_in_sector(H, Sz, target, tol=1e-6):
    """Lowest eigenstate whose <S^z> equals `target`. Returns (energy, mean magnetisation)."""
    w, v = np.linalg.eigh(H)
    for k in range(v.shape[1]):
        g = v[:, k]
        m = float(np.real(g.conj() @ (Sz @ g)))
        if abs(m - target) < tol:
            return w[k], m / N
    return None, None


def main():
    Sz = sz_total()
    scan = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
    print(f"N={N}, one bond scaled by s, exact diagonalisation\n")
    print(f"   {'s':>6}{'  <m> in S^z=0':>18}{'  <m> in S^z=1':>18}{'  <m> in S^z=2':>18}")
    rows = {0.0: [], 1.0: [], 2.0: []}
    for s in scan:
        H = chain(s)
        line = f"   {s:>6.2f}"
        for target in (0.0, 1.0, 2.0):
            _, m = lowest_in_sector(H, Sz, target)
            rows[target].append(m)
            line += f"{m:>18.4f}" if m is not None else f"{'--':>18}"
        print(line)

    flat1 = max(rows[1.0]) - min(rows[1.0])
    print(f"\n   S^z=1 spread across the whole scan: {flat1:.2e}  (1/N = {1/N:.4f})")
    print(f"   S^z=0 is exactly zero everywhere:   {all(abs(m) < 1e-9 for m in rows[0.0])}")
    print("   -> with S^z conserved the mean magnetisation is the CONSERVED QUANTITY over N. It cannot")
    print("      respond to the contradiction strength, because it is not free to move.")

    # A TILTED field, not a purely transverse one. A pure h_x breaks the conservation but leaves a
    # residual symmetry -- rotation by pi about x sends S^z -> -S^z -- so <S^z> stays exactly 0 and the
    # control reports no movement while the symmetry IS broken. The first version of this control did
    # exactly that and failed, which is the only reason the comment exists: a control that cannot see
    # the effect makes every flat line above it meaningless. Tilting removes the residual symmetry too.
    print("\n   CONTROL: the same scan under a TILTED field (h_x and h_z), which breaks it properly")
    print(f"   {'s':>6}{'  <m> of the ground state':>28}")
    prev = None
    moved = False
    for s in scan:
        H = chain(s, h_x=0.35, h_z=0.25)
        w, v = np.linalg.eigh(H)
        g = v[:, 0]
        m = float(np.real(g.conj() @ (Sz @ g))) / N
        print(f"   {s:>6.2f}{m:>28.4f}")
        if prev is not None and abs(m - prev) > 1e-6:
            moved = True
        prev = m
    print(f"   the probe CAN see movement when the symmetry is broken: {moved}")
    if not moved:
        print("   ...it cannot, so the flat lines above measure nothing and must not be cited.")


if __name__ == "__main__":
    main()
