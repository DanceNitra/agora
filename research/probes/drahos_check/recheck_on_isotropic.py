"""Two questions Guanghao asked, plus one I have to ask about my own result.

MINE FIRST. I derived the ratio as the DM gauge factor 1/sqrt(1+D^2) and checked it against his
final_ed_scan.py. That script turns out to build the XY term at half the weight of ZZ (off-diagonal 1
where the Pauli construction gives 2) -- an XXZ model, not the isotropic Heisenberg the paper states. So
my agreement to six decimals at D=0.1 was measured on the wrong model and has to be re-checked before it
goes in anyone's paper. If the gauge factor is a property of the DM term it should survive; if it was an
artifact of the anisotropy it will not, and I need to say so before they build on it.

THEN HIS TWO:
  1. which script to trust -- answered by the model difference above, but the D-sweep on the isotropic
     model is what tells him whether the physics conclusion survives the fix
  2. the degeneracy check at s=0.38 on N=12 -- the low-lying spectrum and the gap, which decides whether
     the N=14 anomaly is a near-degenerate ground state (solver picks a different vector) or real physics

N=12 only: N=14 dense is 16384^2 and the point is decided at N=12 first.
"""
import sys

import networkx as nx
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import eigsh

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
N = 12


def build(G, D=0.0, isotropic=True):
    """isotropic=True -> Pauli sx.sx+sy.sy+sz.sz (off-diagonal 2). False -> the 'direct' builder (1)."""
    dim = 2 ** G.number_of_nodes()
    H = lil_matrix((dim, dim), dtype=float)
    xy = 2.0 if isotropic else 1.0
    for i, j, w in G.edges(data="weight"):
        w = w if w else 1.0
        for state in range(dim):
            bi, bj = (state >> i) & 1, (state >> j) & 1
            H[state, state] += w if bi == bj else -w
            H[state, state ^ (1 << i) ^ (1 << j)] += w * xy
            if D != 0.0:
                si, sj = 1 - 2 * bi, 1 - 2 * bj
                H[state, state ^ (1 << j)] += D * si
                H[state, state ^ (1 << i)] -= D * sj
    return H.tocsr()


def ground(H, k=6):
    e, v = eigsh(H, k=k, which="SA")
    o = np.argsort(e)
    return e[o], v[:, o[0]]


def fine(G, gs):
    corrs = []
    p = np.abs(gs) ** 2
    for i, j in G.edges():
        idx = np.arange(len(gs))
        si = 1 - 2 * ((idx >> i) & 1)
        sj = 1 - 2 * ((idx >> j) & 1)
        corrs.append(float(np.sum(p * si * sj)))
    return float(np.std(corrs))


def chain(defect_s):
    G = nx.path_graph(N)
    for u, v in G.edges():
        G[u][v]["weight"] = 1.0
    a, b = N // 2 - 1, N // 2
    G[a][b]["weight"] = 1.0 + defect_s
    return G


print("=== 1. Does the DM gauge factor survive on the ISOTROPIC model? (N=12, s grid as theirs) ===")
strengths = np.linspace(0.0, 3.0, 9)
print(f"{'D':>5} {'isotropic ratio':>16} {'anisotropic ratio':>18} {'1/sqrt(1+D^2)':>14}")
for D in (0.1, 0.2, 0.3, 0.5, 1.0):
    out = {}
    for iso in (True, False):
        rs = []
        for s in strengths:
            G = chain(s)
            _, g0 = ground(build(G, D=0.0, isotropic=iso))
            _, g1 = ground(build(G, D=D, isotropic=iso))
            fh, fs = fine(G, g0), fine(G, g1)
            if fh:
                rs.append(fs / fh)
        out[iso] = float(np.mean(rs))
    print(f"{D:>5.1f} {out[True]:>16.6f} {out[False]:>18.6f} {1/np.sqrt(1+D*D):>14.6f}")

print("\n=== 2. Degeneracy at the valley: low-lying spectrum near s=0.38 (N=12, isotropic, D=0.3) ===")
print(f"{'s':>6} {'E0':>12} {'E1':>12} {'gap':>10} {'E2-E1':>10}")
for s in (0.30, 0.35, 0.375, 0.38, 0.385, 0.40, 0.45):
    G = chain(s)
    e, _ = ground(build(G, D=0.3, isotropic=True), k=6)
    print(f"{s:>6.3f} {e[0]:>12.6f} {e[1]:>12.6f} {e[1]-e[0]:>10.6f} {e[2]-e[1]:>10.6f}")
print("\nA gap collapsing toward zero at s=0.38 means eigsh may return either of two near-degenerate")
print("vectors, which would explain both the N=14 outlier and the two scripts disagreeing at small N.")
print("A gap that stays open means the anomaly is not a solver artifact and is worth chasing as physics.")
