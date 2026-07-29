"""Is the gauge factor dead, or did I compare two conventions?

On the isotropic build the ratio came out ABOVE 1 (1.011 at D=0.1 rising to 1.232 at D=0.5) instead of
tracking 1/sqrt(1+D^2). Before concluding my own derivation was an artifact, the obvious confound has to
be ruled out: I doubled the XY exchange to make the model isotropic and left the DM term at its original
magnitude. The gauge argument is EXACTLY about the ratio of the DM term to the exchange -- a rotation
renormalises J to sqrt(J^2+D^2) -- so changing one without the other changes the very quantity the
prediction is about.

Three arms, same everything else:
   A  exchange x1 (their 'direct' builder), DM x1     <- what they ran, and what I checked against
   B  exchange x2 (isotropic), DM x1                  <- my re-check: conventions MIXED
   C  exchange x2 (isotropic), DM x2                  <- isotropic with the DM scaled to match

If C tracks 1/sqrt(1+D^2), the gauge factor is real and B was my error. If C does not, the factor was a
property of the anisotropic model and my contribution needs retracting from their paper.
"""
import sys

import networkx as nx
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import eigsh

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
N = 12


def build(G, D=0.0, xy=1.0, dm=1.0):
    dim = 2 ** G.number_of_nodes()
    H = lil_matrix((dim, dim), dtype=float)
    for i, j, w in G.edges(data="weight"):
        w = w if w else 1.0
        for state in range(dim):
            bi, bj = (state >> i) & 1, (state >> j) & 1
            H[state, state] += w if bi == bj else -w
            H[state, state ^ (1 << i) ^ (1 << j)] += w * xy
            if D != 0.0:
                si, sj = 1 - 2 * bi, 1 - 2 * bj
                H[state, state ^ (1 << j)] += D * dm * si
                H[state, state ^ (1 << i)] -= D * dm * sj
    return H.tocsr()


def gs(H):
    e, v = eigsh(H, k=4, which="SA")
    return v[:, int(np.argmin(e))]


def fine(G, g):
    p = np.abs(g) ** 2
    idx = np.arange(len(g))
    return float(np.std([float(np.sum(p * (1 - 2 * ((idx >> i) & 1)) * (1 - 2 * ((idx >> j) & 1))))
                         for i, j in G.edges()]))


def chain(s):
    G = nx.path_graph(N)
    for u, v in G.edges():
        G[u][v]["weight"] = 1.0
    G[N // 2 - 1][N // 2]["weight"] = 1.0 + s
    return G


ARMS = (("A  exchange x1, DM x1", 1.0, 1.0),
        ("B  exchange x2, DM x1", 2.0, 1.0),
        ("C  exchange x2, DM x2", 2.0, 2.0))
strengths = np.linspace(0.0, 3.0, 9)

print(f"{'D':>5} " + " ".join(f"{n.split()[0]:>10}" for n, _, _ in ARMS) + f" {'1/sqrt(1+D^2)':>14}")
for D in (0.1, 0.2, 0.3, 0.5):
    row = []
    for _, xy, dm in ARMS:
        rs = []
        for s in strengths:
            G = chain(s)
            fh = fine(G, gs(build(G, D=0.0, xy=xy, dm=dm)))
            fs = fine(G, gs(build(G, D=D, xy=xy, dm=dm)))
            if fh:
                rs.append(fs / fh)
        row.append(float(np.mean(rs)))
    print(f"{D:>5.1f} " + " ".join(f"{v:>10.6f}" for v in row) + f" {1/np.sqrt(1+D*D):>14.6f}")

for n, _, _ in ARMS:
    print(f"   {n}")
print("\nIf C tracks the analytic curve, the gauge factor is real and arm B was a mixed convention.")
print("If C does not, the factor belongs to the anisotropic model only and I have to say so to them.")
