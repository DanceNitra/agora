"""The resolution, checked independently: is the relation EXACT when D/J is uniform per bond?

The gauge argument is a statement about the RATIO D/J on each bond -- the rotation angle is
theta_b = arctan(D_b / J_b). Their sweep sets the defect bond to J = 1+s while leaving D = 0.3 on every
bond, so D/J is NOT uniform and no single rotation exists. That is not a higher-order correction, which is
what I called it in public; it is the precondition of the argument being violated by the sweep parameter.

Two arms, everything else identical:
    UNIFORM D      D_b = D on every bond            <- what they ran, and what I checked
    BOND-SCALED D  D_b = D * J_b  (so D/J is fixed) <- the condition the gauge argument actually requires

If the second gives 1/sqrt(1+D^2) at every s to machine precision, the relation is exact under its stated
condition, the residual is fully explained, and the right correction to their paper is much stronger than
the one I posted: not "cite SEA and report the deviation" but "state the condition, and there is no
deviation left to report".

Also checks the mechanism claim: the factor is a ROTATION (cos of the angle), not an energy rescaling --
which matters because a ground-state <sigma^z sigma^z> is invariant under H -> lambda*H (measured
separately at 1e-16), so my original "renormalises the exchange" sentence could not have been the reason.
"""
import sys

import networkx as nx
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import eigsh

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
N = 12
D = 0.3


def build(G, D=0.0, bond_scaled=False):
    dim = 2 ** G.number_of_nodes()
    H = lil_matrix((dim, dim), dtype=float)
    for i, j, w in G.edges(data="weight"):
        w = w if w else 1.0
        d = (D * w) if bond_scaled else D          # D_b = D*J_b  keeps D/J fixed
        for state in range(dim):
            bi, bj = (state >> i) & 1, (state >> j) & 1
            H[state, state] += w if bi == bj else -w
            H[state, state ^ (1 << i) ^ (1 << j)] += w
            if d:
                H[state, state ^ (1 << j)] += d * (1 - 2 * bi)
                H[state, state ^ (1 << i)] -= d * (1 - 2 * bj)
    return H.tocsr()


def gs(H):
    e, v = eigsh(H, k=4, which="SA")
    return v[:, int(np.argmin(e))]


def corrs(G, g):
    p = np.abs(g) ** 2
    idx = np.arange(len(g))
    return np.array([float(np.sum(p * (1 - 2 * ((idx >> i) & 1)) * (1 - 2 * ((idx >> j) & 1))))
                     for i, j in G.edges()])


def chain(s):
    G = nx.path_graph(N)
    for u, v in G.edges():
        G[u][v]["weight"] = 1.0
    G[N // 2 - 1][N // 2]["weight"] = 1.0 + s
    return G


target = 1 / np.sqrt(1 + D * D)
print(f"D = {D};  1/sqrt(1+D^2) = {target:.9f}\n")
print(f"{'s':>6} {'uniform D':>12} {'bond-scaled D':>15} {'|scaled - target|':>18}")
uni, sca = [], []
for s in np.linspace(0.0, 3.0, 9):
    G = chain(s)
    a = np.std(corrs(G, gs(build(G, D=0.0))))
    u = np.std(corrs(G, gs(build(G, D=D)))) / a
    b = np.std(corrs(G, gs(build(G, D=D, bond_scaled=True)))) / a
    uni.append(u)
    sca.append(b)
    print(f"{s:>6.2f} {u:>12.6f} {b:>15.9f} {abs(b-target):>18.2e}")

print(f"\nuniform D    : mean {np.mean(uni):.6f}  spread {max(uni)-min(uni):.2e}")
print(f"bond-scaled D: mean {np.mean(sca):.9f}  spread {max(sca)-min(sca):.2e}")
print(f"\nIf the bond-scaled spread is at machine precision, the relation is EXACT under the condition")
print(f"D/J uniform, and everything I described as a growing higher-order correction was the sweep")
print(f"breaking that condition.")
