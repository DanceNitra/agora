"""Crucible replication: 'No two nonisomorphic threshold graphs are cospectral'
(Lazzarin, Marquez, Tura 2018). Also checks the adjacency-determinant behaviour.

A threshold graph on n vertices is built from K1 by repeatedly adding an ISOLATED (0) or a
DOMINATING (1) vertex -> a creation sequence b in {0,1}^(n-1). Threshold graphs are uniquely
determined by their degree sequence, so distinct (sorted) degree sequences = nonisomorphic classes.
Claim REPRODUCED iff no two distinct iso-classes share a (rounded) adjacency spectrum.
"""
import itertools, numpy as np

def build_adj(seq):
    n = len(seq) + 1
    A = np.zeros((n, n), dtype=int)
    for i in range(1, n):
        if seq[i - 1] == 1:          # dominating: connect to all previous
            for j in range(i):
                A[i, j] = A[j, i] = 1
        # isolated: no edges
    return A

def spectrum_key(A):
    ev = np.linalg.eigvalsh(A.astype(float))
    return tuple(np.round(np.sort(ev), 6))

max_violation = None
summary = []
for n in range(2, 10):
    iso = {}                                  # degree-seq -> spectrum key (one representative)
    spec_to_iso = {}                          # spectrum key -> set of degree-seqs
    for seq in itertools.product((0, 1), repeat=n - 1):
        A = build_adj(seq)
        deg = tuple(sorted(int(x) for x in A.sum(1)))     # iso invariant for threshold graphs
        if deg in iso:
            continue
        sk = spectrum_key(A)
        iso[deg] = sk
        spec_to_iso.setdefault(sk, set()).add(deg)
    # cospectral nonisomorphic pair = a spectrum shared by >1 distinct degree-seq
    cospectral = {sk: ds for sk, ds in spec_to_iso.items() if len(ds) > 1}
    summary.append((n, len(iso), len(cospectral)))
    if cospectral and max_violation is None:
        max_violation = (n, list(cospectral.values())[0])

print("n | #nonisomorphic threshold graphs | #cospectral-nonisomorphic spectra")
for n, niso, nco in summary:
    print(f"{n:2d} | {niso:6d}                          | {nco}")

# determinant of adjacency matrix: known result det(A) in {-1,0,1}*... check parity/values
dets = set()
for seq in itertools.product((0, 1), repeat=6):
    dets.add(int(round(np.linalg.det(build_adj(seq).astype(float)))))
print("\nadjacency determinants observed (n=7 threshold graphs):", sorted(dets))

verdict = "REPRODUCED" if max_violation is None else "FAILED"
print(f"\n=== VERDICT: {verdict} ===")
if max_violation is None:
    print("No two nonisomorphic threshold graphs (n=2..9, all", sum(s[1] for s in summary),
          "classes) share an adjacency spectrum. Claim holds computationally.")
else:
    print("COUNTEREXAMPLE at n=", max_violation[0], ":", max_violation[1])
