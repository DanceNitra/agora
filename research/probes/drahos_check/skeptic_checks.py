"""Check the two load-bearing points of the KILL myself, instead of relaying them.

The red-team verdict rests on two claims that are cheap to test on this very system:

  (1) A ground-state <sigma^z sigma^z> is DIMENSIONLESS and invariant under H -> lambda*H, so an argument
      that renormalises an energy scale cannot predict a change in it. If true, my whole "measured in
      units of the exchange picks up 1/sqrt(1+D^2)" sentence is a category error regardless of how well
      the numbers fit.

  (2) The gauge is PER BOND: J_b -> sqrt(J_b^2 + D^2). With a defect bond of weight 1+s, the defect
      rescales by sqrt(1 + D^2/(1+s)^2), which DEPENDS ON s. Then no s-averaged constant should exist at
      all, and the ratio should drift across the sweep. That is a different, sharper, falsifiable
      description -- and if it holds it is what their paper should say instead of my formula.

Test (1) numerically (it is near-trivial, which is the point: I should have checked it before posting).
Test (2) by looking at the ratio AS A FUNCTION OF s rather than averaged over it.
"""
import sys

import networkx as nx
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import eigsh

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
N = 12


def build(G, D=0.0, xy=1.0, scale=1.0):
    dim = 2 ** G.number_of_nodes()
    H = lil_matrix((dim, dim), dtype=float)
    for i, j, w in G.edges(data="weight"):
        w = (w if w else 1.0) * scale
        for state in range(dim):
            bi, bj = (state >> i) & 1, (state >> j) & 1
            H[state, state] += w if bi == bj else -w
            H[state, state ^ (1 << i) ^ (1 << j)] += w * xy
            if D:
                H[state, state ^ (1 << j)] += D * scale * (1 - 2 * bi)
                H[state, state ^ (1 << i)] -= D * scale * (1 - 2 * bj)
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


print("=== (1) is the observable invariant under an overall energy rescaling? ===")
G = chain(0.38)
base = np.std(corrs(G, gs(build(G, D=0.3))))
for lam in (0.5, 2.0, 10.0):
    got = np.std(corrs(G, gs(build(G, D=0.3, scale=lam))))
    print(f"   H -> {lam:>4}*H :  std(corr) = {got:.9f}   (unscaled {base:.9f})  "
          f"delta {abs(got-base):.2e}")
print("   If these are equal to machine precision, an argument that only renormalises an ENERGY")
print("   cannot predict any change in this observable, however well the numbers happen to fit.\n")

print("=== (2) does the ratio drift with s, as a per-bond gauge predicts? ===")
print(f"{'s':>6} {'ratio(s)':>10} {'sqrt(1+D^2/(1+s)^2)':>21} {'1/sqrt(1+D^2)':>14}")
D = 0.3
for s in np.linspace(0.0, 3.0, 9):
    G = chain(s)
    a = np.std(corrs(G, gs(build(G, D=0.0))))
    b = np.std(corrs(G, gs(build(G, D=D))))
    if a:
        perbond = 1 / np.sqrt(1 + D ** 2 / (1 + s) ** 2)
        print(f"{s:>6.2f} {b/a:>10.6f} {perbond:>21.6f} {1/np.sqrt(1+D*D):>14.6f}")
print("\n   A ratio that is flat in s supports a single constant; one that drifts and tracks the")
print("   middle column supports the per-bond description and kills the constant outright.")
