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


def lowest_in_sector(H, Sz, target, tol=1e-9):
    """Lowest eigenstate INSIDE the S^z = target block. Returns (energy, mean magnetisation).

    This projects onto the block and diagonalises there. The first version did not: it diagonalised
    the whole space and took the first eigenvector whose MEAN <S^z> matched the target. A mean is not
    a sector test -- a cross-sector superposition passes it -- and the bond-scale variant is the one
    case here that keeps full SU(2), so its levels are degenerate multiplets and `eigh` returns an
    arbitrary basis inside them. Measured: at s = 1.5, 202 of 256 eigenvectors have non-integer <S^z>.

    The consequence was silent, which is why it is worth writing down. Against a true projected
    diagonalisation the old routine returned the WRONG level from s = 1.0 onward:

        s      true E0        returned      dE
        0.5   -2.7232091     -2.7232091     2.7e-15
        1.0   -2.9822405     -2.5037291     4.8e-01
        2.0   -3.6350268     -2.2781332     1.4e+00

    It still reported the right magnetisation, because <m> is pinned in EVERY level of the sector --
    so the one observable this file is about could not reveal the defect. Ask it for an energy or a
    gap and it lies. The 7.55e-08 'spread' the first version reported for bond-scale was degeneracy
    mixing, not physics; in the true block it is ~1e-16 like the others.

        SECOND correction, and it was worse than the first: the fix above originally returned `target / n`
    for the magnetisation. That is the answer by construction, not a measurement -- the table would
    have printed my own assumption back at me and called it evidence. The value is now computed from
    the eigenvector, and the sector is REFUSED outright when H does not commute with S^z, because
    projecting onto a block of a Hamiltonian that mixes blocks produces a number with no meaning."""
    if np.linalg.norm(H @ Sz - Sz @ H) > 1e-9:
        return None, None                      # not a good quantum number; there is no such sector
    diag = np.real(np.diag(Sz))
    idx = np.where(np.abs(diag - target) < 1e-9)[0]
    if idx.size == 0:
        return None, None
    w, v = np.linalg.eigh(H[np.ix_(idx, idx)])
    g = np.zeros(H.shape[0], dtype=complex)
    g[idx] = v[:, 0]                           # lift the block eigenvector back to the full space
    n = int(round(np.log2(H.shape[0])))
    m = float(np.real(g.conj() @ (Sz @ g))) / n
    var = float(np.real(g.conj() @ (Sz @ Sz @ g))) - (m * n) ** 2
    assert abs(var) < 1e-9, f"the returned state is not an S^z eigenstate: Var = {var:.2e}"
    return w[0], m



def quantisation_and_robustness():
    """Two things I asserted without checking, added after being called on it.

    (1) I read the reported 0.1250 as 1/N for N = 8 and called it exact agreement. That is an
        ASSUMPTION about their chain length. <S^z_total> is quantised in integer steps, so
        <S^z_total>/N can only ever be k/N -- and the folding runs in the same thread name bonds
        (7,8) and (8,9), which need N >= 10, where the attainable values are multiples of 0.1 and
        0.1250 is not among them at all.

    (2) I checked the pinning for ONE way a 'contradiction strength' could enter the Hamiltonian.
        Whether the mean magnetisation is free to move depends entirely on whether that term commutes
        with total S^z, so the claim is only as good as the coverage of that question."""
    print("\n   which N could give a mean magnetisation of exactly 0.1250?")
    for n in (6, 8, 10, 12, 14):
        print(f"      N={n:<3} S^z=1 -> {1/n:.4f}   S^z=2 -> {2/n:.4f}   attainable values are multiples of {1/n:.4f}")
    print("      0.1250 needs N to be a multiple of 8. Bonds (7,8) and (8,9) need N >= 10, and at")
    print("      N = 10 the attainable values are multiples of 0.1000, which does not include 0.1250.")

    print("\n   is the pinning robust to HOW the contradiction enters?")
    Sz = sz_total()
    scan = (0.0, 0.5, 1.0, 1.5, 2.0)
    for kind in ("bond-scale", "xxz-anisotropy", "dm-z", "ising-x-only", "dm-x"):
        H = variant(kind, 1.3)
        comm = np.linalg.norm(H @ Sz - Sz @ H)
        ms = []
        for s in scan:
            _, m = lowest_in_sector(variant(kind, s), Sz, 1.0)
            ms.append(m)
        spread = (max(ms) - min(ms)) if all(m is not None for m in ms) else float("nan")
        verdict = "conserves" if comm < 1e-9 else "BREAKS   "
        print(f"      {kind:<16} ||[H,S^z]||={comm:9.2e}  {verdict}  <m> spread = {spread:.2e}")
    print("      -> pinned for every S^z-conserving form; the sector does not exist for the two that")
    print("         break it. So a rise is possible exactly when the contradiction term breaks S^z.")


def variant(kind, s, bond=(3, 4), n=N):
    """The same chain with `s` entering five different ways -- three conserve S^z, two do not."""
    d = 2 ** n
    H = np.zeros((d, d), dtype=complex)
    for i in range(n - 1):
        a, b = i, i + 1
        if (a, b) != bond:
            for S in (SX, SY, SZ):
                H += op_at(S, a, n) @ op_at(S, b, n)
        elif kind == "bond-scale":
            for S in (SX, SY, SZ):
                H += s * op_at(S, a, n) @ op_at(S, b, n)
        elif kind == "xxz-anisotropy":
            H += (op_at(SX, a, n) @ op_at(SX, b, n) + op_at(SY, a, n) @ op_at(SY, b, n)
                  + s * op_at(SZ, a, n) @ op_at(SZ, b, n))
        elif kind == "dm-z":
            H += sum(op_at(S, a, n) @ op_at(S, b, n) for S in (SX, SY, SZ))
            H += s * (op_at(SX, a, n) @ op_at(SY, b, n) - op_at(SY, a, n) @ op_at(SX, b, n))
        elif kind == "ising-x-only":
            H += s * op_at(SX, a, n) @ op_at(SX, b, n)
        elif kind == "dm-x":
            H += sum(op_at(S, a, n) @ op_at(S, b, n) for S in (SX, SY, SZ))
            H += s * (op_at(SY, a, n) @ op_at(SZ, b, n) - op_at(SZ, a, n) @ op_at(SY, b, n))
    return H


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

    # ---- recorded run ------------------------------------------------------------
    # Cited by name in a letter to a collaborator while it recorded nothing. Nothing
    # below changes a measurement; it serialises what the run already computed.
    import json as _json, os as _os
    _rep = {"N": N, "control_probe_can_see_movement": bool(moved),
            "scan": [float(x) for x in scan]}
    _out = _os.path.splitext(_os.path.abspath(__file__))[0] + ".result.json"
    with open(_out, "w", encoding="utf-8") as _fh:
        _json.dump(_rep, _fh, indent=1)
    print("wrote", _os.path.basename(_out))
    quantisation_and_robustness()
    if not moved:
        print("   ...it cannot, so the flat lines above measure nothing and must not be cited.")


if __name__ == "__main__":
    main()
