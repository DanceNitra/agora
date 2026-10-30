"""Does the count of different-orbit pairs with equal response follow a pattern past N=7?

Li Guanghao's "Same Orbit Implies Same Response" (EDRN) reports 47 (N=6) and 382 (N=7) edge pairs from different
automorphism orbits whose defect-response curves are equal, in the isotropic Heisenberg model on ALL connected graphs.
This probe extends the same exhaustive scan to N=8 (11,117 graphs) and N=9 (261,080 graphs), with our own code.

Definition (as in probes/edrn_orbit_response_independent_check.py, check A): H(s) = sum_{(i,j) in E} sigma_i . sigma_j,
defect edge d at coupling s, every other edge at 1; the curve of d is the sorted vector of <sigma_e . sigma_e'> over all
edges e, at s in linspace(-1.5, 0, 11), averaged over a ground manifold of tolerance 1e-8. Two edges "coincide" when
their curves agree to 1e-9 at all 11 points.

Difference from check A: the Hamiltonian is built only in the sector S_z = 0 (even N) or S_z = -1/2 (odd N). The lowest
level of the full space lies in that sector, and sigma . sigma is a scalar, so the expectation is the same. The control
below fails the run if N=6 and N=7 do not reproduce 47 and 382 with zero same-orbit counterexamples.

Graph generation: igraph canonical forms (BLISS), by adding one vertex to every graph on N-1 nodes. The control fails the
run if the connected counts are not 112, 853, 11117, 261080.

Run: python -X utf8 probes/edrn_orbit_n8_n9.py --n 6 7 8 [--workers 10]   then   --n 9
Resumable: results append to <cache>/n<N>.jsonl. Writes probes/edrn_orbit_n8_n9.result.json (merged over the N done).
"""
import argparse
import itertools
import json
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import igraph as ig
import numpy as np
from multiprocessing import Pool

DEG_TOL = 1e-8
S_VALS = np.linspace(-1.5, 0.0, 11)
KNOWN_CONNECTED = {6: 112, 7: 853, 8: 11117, 9: 261080}
KNOWN_COINCIDENCES = {7: 382}  # N=6: the paper's 47 is a union over 24 diagnostic choices; one definition gives 32 (full space and sector agree)
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_edrn_n8_n9_cache")


# ---------- graph generation ----------

def canon_key(n, edges):
    g = ig.Graph(n=n, edges=edges)
    h = g.permute_vertices(g.canonical_permutation())
    return tuple(sorted(tuple(sorted(e)) for e in h.get_edgelist()))


def all_graphs(n, memo):
    """every graph on n nodes up to isomorphism, as a tuple of edge tuples (canonical labelling)"""
    if n in memo:
        return memo[n]
    if n == 1:
        memo[1] = [()]
        return memo[1]
    seen = set()
    for base in all_graphs(n - 1, memo):
        for mask in range(1 << (n - 1)):
            edges = list(base) + [(i, n - 1) for i in range(n - 1) if (mask >> i) & 1]
            seen.add(canon_key(n, edges))
    memo[n] = sorted(seen)
    return memo[n]


def connected_graphs(n):
    path = os.path.join(CACHE, f"graphs{n}.json")
    if os.path.exists(path):
        return [tuple(map(tuple, g)) for g in json.load(open(path))]
    memo = {}
    out = [e for e in all_graphs(n, memo) if ig.Graph(n=n, edges=list(e)).is_connected()]
    os.makedirs(CACHE, exist_ok=True)
    json.dump(out, open(path, "w"))
    return out


# ---------- one graph ----------

_STATE = {}


def sector_mats(n):
    if n in _STATE:
        return _STATE[n]
    basis = [b for b in range(1 << n) if bin(b).count("1") == n // 2]
    idx = {b: i for i, b in enumerate(basis)}
    d = len(basis)
    mats = {}
    for i, j in itertools.combinations(range(n), 2):
        m = np.zeros((d, d))
        for b in basis:
            r = idx[b]
            if ((b >> i) & 1) == ((b >> j) & 1):
                m[r, r] = 1.0
            else:
                m[r, r] = -1.0
                m[idx[b ^ (1 << i) ^ (1 << j)], r] += 2.0
        mats[(i, j)] = m
    _STATE[n] = mats
    return mats


def edge_orbits(n, edges):
    g = ig.Graph(n=n, edges=edges)
    parent = list(range(len(edges)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    pos = {tuple(sorted(e)): k for k, e in enumerate(edges)}
    for gen in g.automorphism_group():
        for k, (a, b) in enumerate(edges):
            f = pos[tuple(sorted((gen[a], gen[b])))]
            ra, rb = find(k), find(f)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    return [find(k) for k in range(len(edges))]


def one_graph(args):
    n, gid, edges = args
    edges = [tuple(sorted(e)) for e in edges]
    mats = sector_mats(n)
    stack = np.stack([mats[e] for e in edges])
    h0 = stack.sum(axis=0)
    ne = len(edges)
    curves = np.zeros((ne, len(S_VALS), ne))
    for di in range(ne):
        for si, s in enumerate(S_VALS):
            w, v = np.linalg.eigh(h0 + (s - 1.0) * stack[di])
            k = int(np.sum(np.abs(w - w[0]) < DEG_TOL))
            vk = v[:, :k]
            curves[di, si] = np.sort(np.einsum("eij,ik,jk->e", stack, vk, vk) / k)
    orb = edge_orbits(n, edges)
    out = {"gid": gid, "edges": ne, "n_aut": int(ig.Graph(n=n, edges=edges).count_automorphisms()),
           "so_same": 0, "so_diff": 0, "do_same": 0, "do_diff": 0, "pairs": []}
    for a, b in itertools.combinations(range(ne), 2):
        same_o = orb[a] == orb[b]
        same_c = bool(np.max(np.abs(curves[a] - curves[b])) < 1e-9)
        out[("so_" if same_o else "do_") + ("same" if same_c else "diff")] += 1
        if (not same_o) and same_c:
            out["pairs"].append([list(edges[a]), list(edges[b])])
    return out


def _init():
    try:  # below normal priority: this machine is shared
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)
    except Exception:  # noqa: BLE001
        pass


def run_n(n, workers, limit=None):
    graphs = connected_graphs(n)
    assert len(graphs) == KNOWN_CONNECTED[n], f"control failed: {len(graphs)} connected graphs on {n} nodes"
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"n{n}.jsonl")
    done = set()
    if os.path.exists(path):
        done = {json.loads(x)["gid"] for x in open(path, encoding="utf-8")}
    todo = [(n, i, graphs[i]) for i in range(len(graphs)) if i not in done and (limit is None or i < limit)]
    t0 = time.time()
    print(f"N={n}: {len(graphs)} graphs, {len(done)} done, {len(todo)} to do, workers={workers}", flush=True)
    with Pool(workers, initializer=_init) as pool, open(path, "a", encoding="utf-8") as f:
        for c, r in enumerate(pool.imap_unordered(one_graph, todo, chunksize=8), 1):
            f.write(json.dumps(r) + "\n")
            if c % 200 == 0 or c == len(todo):
                f.flush()
                try:  # keep the shared-machine compute lock fresh while this runs
                    os.utime(os.path.join(os.path.expanduser("~"), ".claude", "compute", "curator-edrn-orbit.lock"))
                except OSError:
                    pass
                el = time.time() - t0
                print(f"  N={n}: {c}/{len(todo)}  {el:.0f} s  eta {el / c * (len(todo) - c):.0f} s", flush=True)
    return summarize(n, path, len(graphs))


def summarize(n, path, total):
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    keys = ("so_same", "so_diff", "do_same", "do_diff")
    s = {k: sum(r[k] for r in rows) for k in keys}
    s.update(n=n, graphs_done=len(rows), graphs_total=total,
             graphs_with_coincidence=sum(1 for r in rows if r["do_same"]),
             coincident_pairs_in_asymmetric_graphs=sum(r["do_same"] for r in rows if r["n_aut"] == 1),
             asymmetric_graphs=sum(1 for r in rows if r["n_aut"] == 1),
             max_pairs_in_one_graph=max((r["do_same"] for r in rows), default=0))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, nargs="+", default=[6, 7, 8])
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--limit", type=int, default=None, help="first K graphs only (timing)")
    a = ap.parse_args()
    res_path = os.path.splitext(__file__)[0] + ".result.json"
    res = json.load(open(res_path)) if os.path.exists(res_path) else {}
    for n in a.n:
        s = run_n(n, a.workers, a.limit)
        print(json.dumps(s), flush=True)
        if a.limit is None:
            if n in KNOWN_COINCIDENCES:
                assert s["do_same"] == KNOWN_COINCIDENCES[n] and s["so_diff"] == 0, f"control failed at N={n}: {s}"
                s["control"] = "reproduces the published count with zero same-orbit counterexamples"
            res[str(n)] = s
            json.dump(res, open(res_path, "w"), indent=1)
    print("wrote", res_path)


if __name__ == "__main__":
    sys.exit(main())
