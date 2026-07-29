"""Are the two scripts solving the same physics? Compare the SPECTRA, do not reason from the source.

The two Hamiltonian builders differ in construction:

  constant_validation.py   Pauli matrices via kron:  w * (sx_i sx_j + sy_i sy_j + sz_i sz_j)
  final_ed_scan.py         direct in the basis:      H[state, flipped] += w ;  H[s,s] += w if aligned else -w

Reading the algebra, sx_i sx_j + sy_i sy_j applied to |up down> gives 2|down up>, so the Pauli version has
an off-diagonal element of 2 where the direct version has 1, while both have +-1 on the diagonal. If that
holds, the second script is an XXZ model with a different anisotropy -- not the isotropic Heisenberg model
the paper says it solves, and it is the script that produced the N=12 and N=14 numbers.

That is too consequential to assert from reading code. Build both operators, at a size small enough to be
exact and dense, and compare the eigenvalues.
"""
import sys

import networkx as nx
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def pauli_version(G, D=0.0):
    N = G.number_of_nodes()
    dim = 2 ** N
    sx = np.array([[0, 1], [1, 0]], dtype=complex)
    sy = np.array([[0, -1j], [1j, 0]], dtype=complex)
    sz = np.array([[1, 0], [0, -1]], dtype=complex)
    I2 = np.eye(2, dtype=complex)

    def full(op, site):
        ops = [I2] * N
        ops[site] = op
        out = ops[0]
        for k in range(1, N):
            out = np.kron(out, ops[k])
        return out

    H = np.zeros((dim, dim), dtype=float)
    for i, j, w in G.edges(data="weight"):
        w = w if w else 1.0
        H += w * (full(sx, i) @ full(sx, j)).real
        H += w * (full(sy, i) @ full(sy, j)).real
        H += w * (full(sz, i) @ full(sz, j)).real
    return H


def direct_version(G, D=0.0):
    N = G.number_of_nodes()
    dim = 2 ** N
    H = np.zeros((dim, dim), dtype=float)
    for i, j, w in G.edges(data="weight"):
        w = w if w else 1.0
        for state in range(dim):
            bit_i = (state >> i) & 1
            bit_j = (state >> j) & 1
            flipped = state ^ (1 << i) ^ (1 << j)
            H[state, flipped] += w
            if bit_i == bit_j:
                H[state, state] += w
            else:
                H[state, state] -= w
    return H


for N in (4, 6):
    G = nx.path_graph(N)
    for u, v in G.edges():
        G[u][v]["weight"] = 1.0
    A, B = pauli_version(G), direct_version(G)
    ea = np.sort(np.linalg.eigvalsh(A))
    eb = np.sort(np.linalg.eigvalsh(B))
    print(f"=== N={N} chain, D=0 (pure Heisenberg) ===")
    print(f"  Pauli  ground state {ea[0]:+.6f}   first excited {ea[1]:+.6f}   gap {ea[1] - ea[0]:.6f}")
    print(f"  direct ground state {eb[0]:+.6f}   first excited {eb[1]:+.6f}   gap {eb[1] - eb[0]:.6f}")
    same = np.allclose(ea, eb, atol=1e-9)
    print(f"  spectra identical: {same}")
    if not same:
        # is the direct one the XXZ model, i.e. the same operator with the XY part halved?
        off_a = A[np.eye(len(A)) == 0]
        off_b = B[np.eye(len(B)) == 0]
        nz_a = np.abs(off_a[off_a != 0])
        nz_b = np.abs(off_b[off_b != 0])
        print(f"  off-diagonal magnitudes: Pauli {sorted(set(np.round(nz_a, 6)))[:4]}  "
              f"direct {sorted(set(np.round(nz_b, 6)))[:4]}")
        print(f"  diagonal range:          Pauli [{A.diagonal().min():+.1f},{A.diagonal().max():+.1f}]  "
              f"direct [{B.diagonal().min():+.1f},{B.diagonal().max():+.1f}]")
        half = np.allclose(ea, np.sort(np.linalg.eigvalsh((A + A.T) / 2)), atol=1e-9)
        print(f"  -> the two scripts do NOT solve the same model. The one used for N=12/14 is the "
              f"'direct' builder.")
    print()
