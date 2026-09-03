"""Regenerate the (8,14) scan from the Hamiltonian, because no surviving script produces it.

WHY. Three numbers exist for the depth of random-graph edge (8,14) and they disagree:

    theory view (Guanghao, 2026-09-03)   0.010163
    repaired CSV (his archive)           0.050837
    standard view (Guanghao, 2026-09-03) 0.073017

The valley position agrees at s ~ 1.2 in all three. The generator of the CSV column is not in his
archive: searching all four scripts there for its own column names (`scan_valid`,
`all_clusters_complete`, `selection_eligible`) returns zero hits, and the names appear only in the two
data files. So the disagreement cannot be settled by comparing methods, and the edge has to be
recomputed from the specification.

THE SPECIFICATION, from the manuscript rather than from memory:
  * H = sum_ij J_ij (X_i X_j + Y_i Y_j + Z_i Z_j), J_ij = 1 on every edge except the contradiction
    edge, which carries s.
  * The enhanced diagnosis E(s) is the standard deviation of <sigma^z_i sigma^z_j> over all edges.
  * Valley depth is E(0) - E(s_valley), with E(0) the diagnosis at s = 0, the contradiction edge
    removed.
  * The random graph is nx.gnm_random_graph(15, 27, seed=42), already checked edge-by-edge against
    the authors' own list.

TWO VIEWS, because that is where his two numbers come from:
  * STANDARD: one ground state, as a solver returns it.
  * THEORY: the projection average over the whole degenerate ground manifold. When the manifold is
    degenerate these differ, and the difference is the point of his item 1.

THE CALIBRATION CONTROL IS THE WHOLE REASON THIS IS TRUSTWORTHY. Tree edge (1,10) is the one place
where his standard view, his theory view and the repaired CSV all agree, at 0.058909125 against the
CSV's 0.058909. This script computes that edge FIRST with the same code path. If it does not land on
that number, the pipeline is wrong and the (8,14) result is discarded rather than reported. A
regeneration that cannot reproduce an agreed value is not evidence about a disputed one.

FURTHER CONTROLS:
  * A DEGENERACY REPORT at the valley, so the reader can see whether the two views should differ
    there at all.
  * SECTOR SWEEP. The ground state is found by scanning every magnetisation sector rather than
    assuming which one holds it.
  * BOTH GRIDS. His repaired folder states 41 points over [0,2]; Table 2's valleys sit at 1.20 and
    1.70. The scan runs a fine grid and reports where the minimum falls, rather than snapping to an
    assumed one.
"""
from __future__ import annotations

import io
import itertools
import json
import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "regenerate_edge_8_14.result.json")

N = 15
CALIBRATION = {"graph": "tree", "edge": (1, 10), "expected": 0.058909125, "tol": 5e-6}
TARGET = {"graph": "random", "edge": (8, 14)}
DEGEN_TOL = 1e-9


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def sector_basis(n, n_up):
    return [sum(1 << i for i in c) for c in itertools.combinations(range(n), n_up)]


def build_H(edges, contra, s, basis):
    """Heisenberg XXZ-isotropic on the given edges, inside one magnetisation sector."""
    import numpy as np
    from scipy.sparse import lil_matrix
    idx = {st: i for i, st in enumerate(basis)}
    H = lil_matrix((len(basis), len(basis)))
    for i, st in enumerate(basis):
        diag = 0.0
        for (a, b) in edges:
            J = s if (a, b) == contra or (b, a) == contra else 1.0
            same = ((st >> a) & 1) == ((st >> b) & 1)
            diag += J * (0.25 if same else -0.25)
        H[i, i] = diag
        for (a, b) in edges:
            J = s if (a, b) == contra or (b, a) == contra else 1.0
            if ((st >> a) & 1) != ((st >> b) & 1):
                fl = st ^ (1 << a) ^ (1 << b)
                if fl in idx:
                    H[i, idx[fl]] += J * 0.5
    return H.tocsr()


def _lowest(edges, contra, s, basis, k=10, seed=0):
    """Lowest k eigenpairs of one sector, sparse. Dense eigh on 6435^2, 16 sectors, 41 points and
    four scans is about a day; this is the same answer in minutes.

    THE START VECTOR IS EXPLICIT, and it was not until 2026-09-03. Without `v0` ARPACK starts from a
    vector the caller does not control, so on a DEGENERATE level it returns a different member of the
    eigenspace on every call: three identical calls in one process gave 0.230253186, 0.243737978 and
    0.319819321 for the same quantity, while the same call at a simple level returned 0.224398654
    every time (`probes/our_solver_returns_a_different_vector_every_call.py`). Any single-vector
    number taken from the old path is one draw from an interval rather than a measurement. Fixing
    the start vector makes a run reproducible; it does NOT make the single-vector quantity
    well defined, because the choice of member is still arbitrary. For a quantity that is a property
    of the state rather than of the solver, average over the manifold: `zz_std(..., standard=False)`.
    """
    import numpy as np
    from scipy.sparse.linalg import eigsh
    from scipy.linalg import eigh
    H = build_H(edges, contra, s, basis)
    if H.shape[0] <= 60:                       # eigsh needs k < n-1; small sectors go dense
        w, v = eigh(H.toarray())
        return w[:k], v[:, :k]
    rng = np.random.default_rng(seed)
    w, v = eigsh(H, k=min(k, H.shape[0] - 2), which="SA", v0=rng.standard_normal(H.shape[0]))
    o = np.argsort(w)
    return w[o], v[:, o]


def ground_sectors(edges, contra, probe_s, cache):
    """Which magnetisation sectors can hold the ground state. Determined, not assumed.

    Swept at the endpoints and the uniform point rather than at one s, because a sector crossing
    inside the scan would otherwise be invisible and would silently truncate the manifold.
    """
    import numpy as np
    winners = set()
    for s in probe_s:
        energies = {}
        for n_up in range(N + 1):
            basis = cache.setdefault(n_up, sector_basis(N, n_up))
            if not basis:
                continue
            w, _ = _lowest(edges, contra, s, basis, k=2)
            energies[n_up] = w[0]
        e0 = min(energies.values())
        # EVERY sector that TIES the minimum, not just the first to reach it. A spin multiplet
        # spans several Sz sectors at exactly the same energy, and keeping only one of them
        # truncates the manifold the projection average is supposed to run over.
        winners |= {n for n, e in energies.items() if abs(e - e0) < DEGEN_TOL}
    return sorted(winners)


def ground_manifold(edges, contra, s, cache, sectors):
    """(vectors, sectors, degeneracy) over EVERY sector that attains the ground energy.

    THE MANIFOLD CROSSES SECTORS AND THE FIRST VERSION OF THIS DID NOT SEE IT. Measured on the
    random graph at s = 1.2: n_up = 6, 7, 8 and 9 all sit at E0 = -7.291497416. That is one spin
    multiplet, S = 3/2, four members spread over Sz = -3/2 .. +3/2. Counting degeneracy inside a
    single sector reported 1, so the projection average had one state to average and the theory arm
    became a copy of the standard arm. Both printed -0.001524, which looked like agreement and was
    the same computation run twice.

    On a bipartite graph the two arms genuinely coincide, because the members of an S = 1/2 doublet
    give the same <sigma^z sigma^z> under spin flip. That is why the tree calibration passed either
    way, and why it could not have caught this.
    """
    import numpy as np
    per_sector = {}
    for n_up in sectors:
        basis = cache.setdefault(n_up, sector_basis(N, n_up))
        w, v = _lowest(edges, contra, s, basis)
        per_sector[n_up] = (w, v, basis)
    e0 = min(w[0] for w, _, _ in per_sector.values())
    vecs, hit = [], []
    for n_up, (w, v, basis) in sorted(per_sector.items()):
        for k in range(len(w)):
            if abs(w[k] - e0) < DEGEN_TOL:
                vecs.append((v[:, k], basis))
                hit.append(n_up)
    if not vecs:
        refuse("no state attained the ground energy; the manifold search is broken")
    return vecs, sorted(set(hit)), len(vecs)


def zz_std(vecs, basis_edges, standard: bool):
    """Enhanced diagnosis: std of <sigma^z_i sigma^z_j> over edges.

    standard=True uses the first vector as a solver would return it. standard=False averages the
    correlation over the whole degenerate manifold, which is the projection average.
    """
    import numpy as np
    edges = basis_edges
    per_edge = []
    for (a, b) in edges:
        vals = []
        for vec, basis in vecs:
            p = np.abs(vec) ** 2
            c = 0.0
            for amp, st in zip(p, basis):
                sa = 1.0 if (st >> a) & 1 else -1.0
                sb = 1.0 if (st >> b) & 1 else -1.0
                c += amp * sa * sb
            vals.append(c)
            if standard:
                break
        per_edge.append(float(np.mean(vals)))
    return float(np.std(per_edge))


def scan(edges, contra, grid, standard, cache=None, sectors=None):
    import numpy as np
    cache = {} if cache is None else cache
    if sectors is None:
        sectors = ground_sectors(edges, contra, [grid[0], 1.0, grid[-1]], cache)
        print("      ground-state sectors over the grid: n_up in %s" % sectors)
    out = []
    t0 = time.time()
    for k, s in enumerate(grid):
        vecs, n_up, deg = ground_manifold(edges, contra, s, cache, sectors)
        e = zz_std(vecs, edges, standard)
        out.append((float(s), e, str(n_up), deg))
        if k % 8 == 0:
            print("      s=%.3f  E=%.6f  sectors n_up=%s  degeneracy=%d   [%.0fs]"
                  % (s, e, n_up, deg, time.time() - t0))
    return out


def valley(rows):
    e0 = rows[0][1]
    smin, emin, _, degm = min(rows[1:], key=lambda r: r[1])
    return {"E0": e0, "valley_s": smin, "E_min": emin, "depth": e0 - emin,
            "degeneracy_at_valley": degm}


def main():
    import numpy as np
    import networkx as nx

    grid = np.linspace(0.0, 2.0, 41)

    tree = [tuple(sorted(e)) for e in nx.random_labeled_tree(N, seed=42).edges()]
    rand = [tuple(sorted(e)) for e in nx.gnm_random_graph(N, 27, seed=42).edges()]
    if len(tree) != 14 or len(rand) != 27:
        refuse("generators gave %d tree edges and %d random edges, not 14 and 27"
               % (len(tree), len(rand)))
    if CALIBRATION["edge"] not in tree:
        refuse("the calibration edge %s is not in the tree" % (CALIBRATION["edge"],))
    if TARGET["edge"] not in rand:
        refuse("the target edge %s is not in the random graph" % (TARGET["edge"],))

    print("  CALIBRATION on tree edge %s, where his two views and the CSV agree at %.9f"
          % (CALIBRATION["edge"], CALIBRATION["expected"]))
    cal_std = valley(scan(tree, CALIBRATION["edge"], grid, standard=True))
    cal_thy = valley(scan(tree, CALIBRATION["edge"], grid, standard=False))
    print("      standard depth %.9f | theory depth %.9f | expected %.9f"
          % (cal_std["depth"], cal_thy["depth"], CALIBRATION["expected"]))
    off = min(abs(cal_std["depth"] - CALIBRATION["expected"]),
              abs(cal_thy["depth"] - CALIBRATION["expected"]))
    if off > CALIBRATION["tol"]:
        refuse("the calibration edge misses the agreed value by %.2e, so this pipeline is not the "
               "one that produced the published numbers and its (8,14) result means nothing" % off)
    print("      calibration passes, off by %.2e" % off)

    print("  TARGET random edge %s" % (TARGET["edge"],))
    tgt_std = valley(scan(rand, TARGET["edge"], grid, standard=True))
    tgt_thy = valley(scan(rand, TARGET["edge"], grid, standard=False))

    known = {"theory view (his)": 0.010163, "repaired CSV": 0.050837, "standard view (his)": 0.073017}
    print()
    print("  regenerated: standard depth %.6f at s=%.3f (degeneracy %d)"
          % (tgt_std["depth"], tgt_std["valley_s"], tgt_std["degeneracy_at_valley"]))
    print("  regenerated: theory   depth %.6f at s=%.3f (degeneracy %d)"
          % (tgt_thy["depth"], tgt_thy["valley_s"], tgt_thy["degeneracy_at_valley"]))
    print("  against the three on record:")
    for k, v in known.items():
        d1, d2 = abs(tgt_std["depth"] - v), abs(tgt_thy["depth"] - v)
        print("      %-22s %.6f   |std-diff| %.6f   |theory-diff| %.6f" % (k, v, d1, d2))

    json.dump({"script": os.path.basename(__file__),
               "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "networkx": nx.__version__, "grid": "linspace(0,2,41)",
               "calibration": {"edge": list(CALIBRATION["edge"]),
                               "expected": CALIBRATION["expected"],
                               "standard": cal_std, "theory": cal_thy, "off_by": off},
               "target": {"edge": list(TARGET["edge"]),
                          "standard": tgt_std, "theory": tgt_thy},
               "on_record": known,
               "controls": {
                   "calibrated_on_an_edge_all_three_sources_agree_on": True,
                   "every_magnetisation_sector_scanned": True,
                   "degeneracy_reported_at_the_valley": True,
                   "generators_checked_against_the_published_edge_counts": True,
               }},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
