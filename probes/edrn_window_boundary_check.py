"""Where does |sd_1(s)| = |sd_2(s)| stop holding for the different-orbit pairs of graphs 38, 60, 103 (N=6)?

sd_e(s) = <sigma_i . sigma_j> on defect edge e, full space, degenerate manifold averaged (tol 1e-8).
For every different-orbit pair that is equal at s=-1, scan s upward from -1 in steps of 1e-3 and
report the first s where |sd_1| and |sd_2| differ by more than 1e-8, plus the ground-state total
spin of each defect just below and just above that point. His paper reports s_max = -0.05 (graph 38,
one pair of 60), 0.95 (two pairs of 60), 1.00 (graph 103) on a 0.05 grid.
"""
import itertools, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from edrn_orbit_response_independent_check import connected_atlas, sdot_matrix, ground, edge_orbits, total_spin

N = 6
out = {}
for gid in (38, 60, 103):
    g = connected_atlas(N)[gid]
    edges = [tuple(sorted(e)) for e in g.edges()]
    mats = {e: sdot_matrix(N, *e) for e in edges}
    h0 = sum(mats.values())
    orb = edge_orbits(g, edges)
    def sd(d, s):
        _, v, k = ground(h0 + (s - 1.0) * mats[d])
        return float(np.real(np.einsum("ik,ij,jk->", v.conj(), mats[d], v))) / k
    def spin(d, s):
        _, v, k = ground(h0 + (s - 1.0) * mats[d])
        return round(2 * total_spin(v[:, 0], N)) / 2, k
    rows = []
    for e1, e2 in itertools.combinations(edges, 2):
        if orb[e1] == orb[e2] or abs(abs(sd(e1, -1.0)) - abs(sd(e2, -1.0))) > 1e-8:
            continue
        s, brk = -1.0, None
        while s <= 2.0:
            if abs(abs(sd(e1, s)) - abs(sd(e2, s))) > 1e-8:
                brk = s
                break
            s = round(s + 1e-3, 6)
        rec = {"pair": [list(e1), list(e2)], "breaks_at": brk}
        if brk is not None:
            rec["spin_below"] = [spin(e1, brk - 2e-3), spin(e2, brk - 2e-3)]
            rec["spin_above"] = [spin(e1, brk + 2e-3), spin(e2, brk + 2e-3)]
        rows.append(rec)
        print(gid, rec, flush=True)
    out[str(gid)] = rows
json.dump(out, open(os.path.splitext(__file__)[0] + ".result.json", "w"), indent=1)
