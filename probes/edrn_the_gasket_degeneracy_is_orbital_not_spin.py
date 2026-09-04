"""COUNTER-PROBE 2. The draft tells Guanghao his 15-site gasket is 'safe' because 15 is odd, so the
degeneracy is a Kramers SPIN degeneracy. Test that on the actual L2 Sierpinski gasket.

The draft's OWN control is a 3-site frustrated triangle -- also an odd number of spin-1/2 -- with
degeneracy 4, where a single ground vector DOES break orbit equality. So the parity argument is
already refuted inside the draft. Here we run the real graph.
"""
import numpy as np, networkx as nx, itertools, time
from scipy.sparse import csr_matrix, identity, kron, coo_matrix
from scipy.sparse.linalg import eigsh


def gasket(level):
    nv, E, C = 3, [(0, 1), (1, 2), (0, 2)], (0, 1, 2)
    for _ in range(level):
        off = [0, nv, 2 * nv]
        E2 = [(a + o, b + o) for o in off for (a, b) in E]
        par = list(range(3 * nv))
        def find(x):
            while par[x] != x: par[x] = par[par[x]]; x = par[x]
            return x
        def uni(a, b):
            ra, rb = find(a), find(b)
            if ra != rb: par[max(ra, rb)] = min(ra, rb)
        A = [c + off[0] for c in C]; B = [c + off[1] for c in C]; D = [c + off[2] for c in C]
        uni(A[1], B[0]); uni(A[2], D[0]); uni(B[2], D[1])
        roots = sorted({find(x) for x in range(3 * nv)})
        idx = {r: i for i, r in enumerate(roots)}
        rel = lambda x: idx[find(x)]
        E = sorted({tuple(sorted((rel(a), rel(b)))) for (a, b) in E2})
        C = (rel(A[0]), rel(B[1]), rel(D[2]))
        nv = len(roots)
    return nv, E, C


N, EDGES, _ = gasket(2)
G = nx.Graph(); G.add_nodes_from(range(N)); G.add_edges_from(EDGES)
print("L2 gasket: %d vertices, %d edges  (Guanghao reports 15 and 27)" % (N, len(EDGES)))

GM = nx.algorithms.isomorphism.GraphMatcher(G, G)
autos = [tuple(m[i] for i in range(N)) for m in GM.isomorphisms_iter()]
print("|Aut| = %d" % len(autos))

# vertex orbits
vo = {}
for v in range(N):
    orb = frozenset(p[v] for p in autos)
    vo[orb] = vo.get(orb, 0) + 1
print("vertex orbits: %d  sizes %s  (Guanghao reports 4)" % (len(vo), sorted(vo.keys(), key=len) and [len(o) for o in vo]))
eo = {}
for e in EDGES:
    orb = frozenset(tuple(sorted((p[e[0]], p[e[1]]))) for p in autos)
    eo[orb] = True
print("edge orbits  : %d  sizes %s  (Guanghao reports 5)" % (len(eo), sorted(len(o) for o in eo)))

# ---- sparse isotropic AF Heisenberg on 2^15 ----
DIM = 1 << N
def build_H():
    rows, cols, vals = [], [], []
    for (a, b) in EDGES:
        ma, mb = 1 << (N - 1 - a), 1 << (N - 1 - b)
        for s in range(DIM):
            za = 1 if (s & ma) else -1
            zb = 1 if (s & mb) else -1
            rows.append(s); cols.append(s); vals.append(float(za * zb))       # sigma^z sigma^z
            if za != zb:                                                       # flip-flop, 2*(xx+yy)
                rows.append(s ^ ma ^ mb); cols.append(s); vals.append(2.0)
    return csr_matrix(coo_matrix((vals, (rows, cols)), shape=(DIM, DIM)))

t0 = time.time()
H = build_H()
print("H built: %d x %d, nnz %d, %.1fs" % (DIM, DIM, H.nnz, time.time() - t0))
t0 = time.time()
w, V = eigsh(H, k=12, which="SA", tol=0, maxiter=20000)
order = np.argsort(w); w = w[order]; V = V[:, order]
print("lowest 12 energies (%.1fs):" % (time.time() - t0))
print("  ", np.round(w, 10))
e0 = w[0]
deg = int(np.sum(w - e0 < 1e-8))
gap = float(w[deg] - e0) if deg < len(w) else float("nan")
print("GROUND DEGENERACY = %d   gap above = %.6f" % (deg, gap))
Vg = V[:, :deg]

def perm_state_map(p):
    """index array: new_index[s] for the site relabelling p."""
    out = np.empty(DIM, dtype=np.int64)
    bits = ((np.arange(DIM)[:, None] >> (N - 1 - np.arange(N))[None, :]) & 1)
    moved = np.zeros_like(bits)
    for k in range(N):
        moved[:, p[k]] = bits[:, k]
    weights = (1 << (N - 1 - np.arange(N)))
    out = (moved * weights).sum(axis=1)
    return out

nontrivial = [p for p in autos if p != tuple(range(N))]
print("\n-- restriction of each automorphism to the ground manifold --")
worst_rest = 0.0
for p in nontrivial:
    idx = perm_state_map(p)
    UV = np.zeros_like(Vg); UV[idx, :] = Vg      # (U v)[idx[s]] = v[s]
    R = Vg.T @ UV
    dev = float(np.max(np.abs(R - np.eye(deg))))
    worst_rest = max(worst_rest, dev)
    print("  perm %-40s max|V^T U V - I| = %.3e" % (str(p), dev))
print("WORST = %.3e  ->  %s" % (worst_rest,
      "manifold is spatially TRIVIAL, single vectors are safe"
      if worst_rest < 1e-8 else "NON-TRIVIAL rep: single vectors are NOT invariant"))

# orbit equality, single vector vs projector, per edge orbit
def zz(vec, a, b):
    ma, mb = 1 << (N - 1 - a), 1 << (N - 1 - b)
    s = np.arange(DIM)
    sgn = np.where(((s & ma) > 0) == ((s & mb) > 0), 1.0, -1.0)
    return float(np.sum(sgn * vec * vec))

orbits = [sorted(o) for o in eo]
print("\n-- within-orbit variance of <sz sz>, per edge orbit --")
for oi, orb in enumerate(orbits):
    cs_full = []
    for (a, b) in orb:
        ma, mb = 1 << (N - 1 - a), 1 << (N - 1 - b)
        s = np.arange(DIM)
        sgn = np.where(((s & ma) > 0) == ((s & mb) > 0), 1.0, -1.0)
        cs_full.append(float(np.sum(sgn[:, None] * Vg * Vg) / deg))
    v1 = Vg[:, 0]
    cs_one = [zz(v1, a, b) for (a, b) in orb]
    print("  orbit %d (|%d|): projector var %.3e   single-vector var %.3e"
          % (oi, len(orb), float(np.var(cs_full)), float(np.var(cs_one))))

# ---- is the fourfold SPIN (S=3/2) or ORBITAL (two S=1/2 doublets)? ----
print("\n-- total spin content of the gasket ground manifold --")
s = np.arange(DIM)
nup = np.zeros(DIM, dtype=np.int64)
for k in range(N):
    nup += (s >> k) & 1
twoSz = (2 * nup - N).astype(float)          # 2*S_z
for i in range(deg):
    v = Vg[:, i]
    ez = float(np.sum(twoSz * v * v))
    vz = float(np.sum(twoSz ** 2 * v * v)) - ez ** 2
    print("  vec %d  <2Sz> = %+8.5f   Var(2Sz) = %.3e" % (i, ez, vz))

# S^2 = sum_ij S_i . S_j ; build S^2 sparsely using the same flip-flop trick over ALL pairs
rows, cols, vals = [], [], []
for a in range(N):
    for b in range(N):
        if a == b:
            rows.append(0); cols.append(0); vals.append(0.0)
            continue
        ma, mb = 1 << (N - 1 - a), 1 << (N - 1 - b)
        za = np.where((s & ma) > 0, 1.0, -1.0); zb = np.where((s & mb) > 0, 1.0, -1.0)
        rows.append(s); cols.append(s); vals.append(0.25 * za * zb)
        diff = za != zb
        idx = s[diff]
        rows.append(idx ^ ma ^ mb); cols.append(idx); vals.append(np.full(idx.size, 0.5))
rows = np.concatenate([np.atleast_1d(r) for r in rows])
cols = np.concatenate([np.atleast_1d(c) for c in cols])
vals = np.concatenate([np.atleast_1d(v) for v in vals])
S2 = csr_matrix(coo_matrix((vals, (rows, cols)), shape=(DIM, DIM)))
S2 = S2 + identity(DIM) * (0.75 * N)          # add the a==b diagonal terms S_a.S_a = 3/4
M = Vg.T @ (S2 @ Vg)
ev = np.linalg.eigvalsh(M)
print("  eigenvalues of S^2 on the manifold:", np.round(ev, 6))
print("  implied S:", np.round((-1 + np.sqrt(1 + 4 * np.clip(ev, 0, None))) / 2, 4))

# re-mixing robustness on the gasket
rng = np.random.default_rng(7)
worst = 0.0
for _ in range(50):
    Q, _ = np.linalg.qr(rng.standard_normal((deg, deg)))
    W = Vg @ Q
    for i in range(deg):
        v = W[:, i]
        for orb in orbits:
            cs = [zz(v, a, b) for (a, b) in orb]
            worst = max(worst, float(np.var(cs)))
print("\n  50 random re-mixings: LARGEST single-vector within-orbit variance = %.3e" % worst)

# ---------------------------------------------------------------------------------------------
# WHICH IRREP, and how the fourfold splits by S_z sector.
#
# Added 2026-08-31 because the letter to Guanghao makes both claims and neither had a receipt here.
# "Orbital" was asserted from the S = 1/2 content alone, which does not distinguish a genuine
# two-dimensional irrep from an accidental pair of one-dimensional ones. The character does.
#
# For D3 the E irrep has characters 2 on the identity, -1 on the two three-fold rotations and 0 on
# the three reflections. The ground manifold is spin (2) tensor orbital, so on a fourfold manifold
# the expected characters are 4, -2 and 0. An accidental A1 + A2 pair would give +4 on the rotations,
# so this test can fail.
print("\n-- which irrep does the ground manifold carry --")
_order = {}
for p in autos:
    q, k = list(p), 1
    while q != list(range(N)):
        q = [p[i] for i in q]
        k += 1
    _order.setdefault(k, []).append(p)
chars = {}
for k in sorted(_order):
    vals = []
    for p in _order[k]:
        idx = perm_state_map(p)
        UV = np.zeros_like(Vg)
        UV[idx, :] = Vg
        vals.append(float(np.trace(Vg.T @ UV)))
    chars[k] = (len(_order[k]), float(np.mean(vals)), float(np.std(vals)))
    print("  order %d (%d elements): character = %+.6f  (spread %.2e)"
          % (k, len(_order[k]), chars[k][1], chars[k][2]))
_is_E = (abs(chars.get(1, (0, 0, 0))[1] - 4.0) < 1e-6
         and abs(chars.get(3, (0, 0, 0))[1] + 2.0) < 1e-6
         and abs(chars.get(2, (0, 0, 0))[1]) < 1e-6)
print("  -> %s" % ("spin doublet TENSOR the E irrep of D3, so the extra twofold is ORBITAL"
                   if _is_E else "NOT the E pattern; the orbital claim does not hold as stated"))

# The other half of the same claim: the fourfold is two per S_z sector, not four in one.
print("\n-- the fourfold resolved by S_z sector --")
from itertools import combinations
_sec = {}
for n_up in range(N + 1):
    basis = [c for c in combinations(range(N), n_up)]
    if not basis:
        continue
    idx = {c: i for i, c in enumerate(basis)}
    rows, cols, vals = [], [], []
    for c, k in idx.items():
        st = set(c)
        diag = 0.0
        for (a, b) in EDGES:
            diag += 0.25 if ((a in st) == (b in st)) else -0.25
            if (a in st) != (b in st):
                other = tuple(sorted(st - {a} | {b})) if a in st else tuple(sorted(st - {b} | {a}))
                rows.append(k); cols.append(idx[other]); vals.append(0.5)
        rows.append(k); cols.append(k); vals.append(diag)
    Hs = csr_matrix(coo_matrix((vals, (rows, cols)), shape=(len(basis), len(basis))))
    if len(basis) < 40:
        ws = np.linalg.eigvalsh(Hs.toarray())
    else:
        ws = eigsh(Hs, k=min(6, len(basis) - 2), which="SA", return_eigenvectors=False)[::-1]
        ws = np.sort(ws)
    _sec[n_up] = (float(ws[0]), int(np.sum(np.abs(ws - ws[0]) < 1e-9)))
_E0 = min(v[0] for v in _sec.values())
_carry = {k: v for k, v in _sec.items() if abs(v[0] - _E0) < 1e-9}
for k, v in sorted(_sec.items()):
    if abs(v[0] - _E0) < 1e-6:
        print("  n_up=%2d  S_z=%+.1f  E0=%.8f  in-sector degeneracy %d" % (k, k - N / 2.0, v[0], v[1]))
print("  sectors carrying the ground level: %s, each %s-fold"
      % (sorted(_carry), sorted({v[1] for v in _carry.values()})))
print("  -> %d in the full space" % sum(v[1] for v in _carry.values()))
if sum(v[1] for v in _carry.values()) != deg:
    print("  CONTROL FAILED: the sector sum disagrees with the full-space degeneracy above")

# ---- recorded run -------------------------------------------------------------------
# Cited by name in a letter to a collaborator before it wrote anything a reader could
# check. It printed and stopped, so `main` carried the script and no record of the run.
# Nothing below changes a measurement; it serialises what the run already computed.
import json as _json, os as _os
_rep = {
    "N": N,
    "n_edges": len(EDGES),
    "ground_degeneracy_full_space": deg,
    "orbits": [{"index": _i, "size": len(_o), "edges": [list(_e) for _e in _o]}
               for _i, _o in enumerate(orbits)],
    "single_vector_invariance_worst": float(worst_rest),
    "s2_eigenvalues": [float(_x) for _x in ev],
    "implied_S": [float((-1 + (1 + 4 * _x) ** 0.5) / 2) for _x in ev],
    # chars[k] is the 3-tuple (n_elements, character, spread). An earlier version of this
    # block applied len() and mean() to that tuple and recorded +1.666667 where the run had
    # printed +4.000000, so the receipt contradicted both the run and the letter citing it.
    "characters": {str(_k): {"n_elements": _v[0], "value": _v[1], "spread": _v[2]}
                   for _k, _v in chars.items()},
    "control_is_E_irrep": bool(_is_E),
    "sz_sectors": {str(_k): {"E0": _v[0], "in_sector_degeneracy": _v[1]}
                   for _k, _v in sorted(_sec.items())},
    "sectors_carrying_ground": sorted(_carry),
    "sector_sum": sum(_v[1] for _v in _carry.values()),
}
_rep["control_sector_sum_equals_full_degeneracy"] = (_rep["sector_sum"] == deg)
print("MEASURED: full-space degeneracy %d, sector sum %d, control %s"
      % (deg, _rep["sector_sum"],
         "PASS" if _rep["control_sector_sum_equals_full_degeneracy"] else "FAIL"))
_out = _os.path.splitext(_os.path.abspath(__file__))[0] + ".result.json"
with open(_out, "w", encoding="utf-8") as _fh:
    _json.dump(_rep, _fh, indent=1)
print("wrote", _os.path.basename(_out))
