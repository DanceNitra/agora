"""The perturbed-gasket within-orbit variance is a LIMIT, not a strength.

Two adversarial passes over the draft letter to @luoxuejian000 disagreed about this, so neither
number was safe to send. One read the eps-squared decay of the rank-4 statistic as "the remedy
destroys his measurement". The other read the same decay as "a real zero, which is what you need".
They also reported different magnitudes. This file measures all three quantities on one grid, in one
convention, so the letter can quote something that exists.

The three quantities, all scored against the UNPERTURBED orbit partition, which is what the
collaborator does:

  rank2(eps)   variance within orbits of <sz sz> from the projector onto the perturbed ground
               manifold, which is twofold for any eps > 0. This is his 2.27e-2.
  rank4(eps)   the same, from the projector onto the LOWEST FOUR states of the perturbed
               Hamiltonian. At eps = 0 these are the unperturbed quadruplet.
  floor        rank2 evaluated at eps = 0 by picking a twofold subspace INSIDE the unperturbed
               fourfold manifold. No symmetry is broken anywhere in this arm, so whatever it
               returns is not symmetry breaking.

THE ANSWER, and it is not the one the first draft of this file expected. The floor does NOT dominate:
rank2 sits about 4.5 times above it at small eps. What settles the question instead is that rank2
CONVERGES. Summed over the 27 edges it reaches 2.2716e-2 at eps = 0.01 and then stops moving, giving
2.2512e-2 at 0.001 and 2.2498e-2 at 0.0001. A quantity that no longer depends on the perturbation is
not measuring the perturbation.

The measure with a null is the lowest-four projector. It falls as eps squared and is machine zero at
eps = 0, so it can report "no symmetry breaking here" and the rank-2 statistic cannot.

Controls, so this cannot report a comforting answer by construction:

  ZERO      rank4 at eps = 0 must be machine zero. The unperturbed manifold is exactly symmetric,
            so a non-zero value means the orbit partition or the projector is wrong.
  ORDER     rank4 must fall faster than rank2 as eps -> 0. If they fall together the two projectors
            are not distinguishing anything.
  LINEAR    the orbital splitting must vanish at eps = 0 and grow. If it does not, the perturbation
            is not lifting the degeneracy and every row is meaningless.

Run:  python -X utf8 probes/edrn_the_perturbation_statistic_has_a_floor_that_is_not_symmetry_breaking.py
"""
from __future__ import annotations

import itertools
import json
import os
import sys

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix, identity
from scipy.sparse.linalg import eigsh

LEVEL = 2
EPS_GRID = (0.5, 0.1, 0.05, 0.01, 0.001, 0.0001)
TOL = 1e-9


def gasket(level):
    """Vertices and edges of the level-`level` Sierpinski gasket, as the thread builds it."""
    tri = [(0, 1, 2)]
    pts = {0: (0.0, 0.0), 1: (1.0, 0.0), 2: (0.5, 0.866025403784)}
    nxt = 3
    for _ in range(level):
        new = []
        for (a, b, c) in tri:
            mid = {}
            for (u, v) in ((a, b), (b, c), (c, a)):
                key = tuple(sorted((u, v)))
                mid[key] = nxt
                pts[nxt] = ((pts[u][0] + pts[v][0]) / 2.0, (pts[u][1] + pts[v][1]) / 2.0)
                nxt += 1
            ab, bc, ca = mid[tuple(sorted((a, b)))], mid[tuple(sorted((b, c)))], \
                mid[tuple(sorted((c, a)))]
            new += [(a, ab, ca), (ab, b, bc), (ca, bc, c)]
        tri = new
    # merge coincident points
    keys, remap = {}, {}
    for i, p in pts.items():
        k = (round(p[0], 9), round(p[1], 9))
        remap[i] = keys.setdefault(k, len(keys))
    edges = set()
    for (a, b, c) in tri:
        for (u, v) in ((a, b), (b, c), (c, a)):
            edges.add(tuple(sorted((remap[u], remap[v]))))
    return len(keys), sorted(edges)


N, EDGES = gasket(LEVEL)
# ASSERT ON THE TARGET. The first run of this file silently used a 6-vertex graph, because the
# subdivision loop ran level-1 times instead of level. Every number it printed was about an object
# nobody in the thread is discussing. The three controls caught it, and this line makes it loud.
assert N == 15 and len(EDGES) == 27, (
    "expected the L2 gasket the thread discusses, 15 vertices and 27 edges; got %d and %d"
    % (N, len(EDGES)))
DIM = 1 << N


def automorphisms():
    """Backtracking search with degree pruning.

    The first version enumerated itertools.permutations(range(15)), which is 1.3e12 candidates and
    does not finish. It never printed a wrong answer, it simply never printed one, so the defect was
    a timeout rather than a bad number. Recorded because the two failure modes need different fixes.
    """
    adj = {i: set() for i in range(N)}
    for (a, b) in EDGES:
        adj[a].add(b)
        adj[b].add(a)
    deg = {i: len(adj[i]) for i in range(N)}
    eset = set(EDGES)
    order = sorted(range(N), key=lambda i: (-deg[i], -len(adj[i])))
    out = []

    def bt(pos, mapping, used):
        if pos == N:
            out.append(tuple(mapping[i] for i in range(N)))
            return
        v = order[pos]
        for c in range(N):
            if c in used or deg[c] != deg[v]:
                continue
            ok = True
            for u in adj[v]:
                if u in mapping:
                    if tuple(sorted((c, mapping[u]))) not in eset:
                        ok = False
                        break
            if not ok:
                continue
            # also forbid creating a non-edge where an edge is required
            for u in order[:pos]:
                if (u not in adj[v]) and tuple(sorted((c, mapping[u]))) in eset:
                    ok = False
                    break
            if not ok:
                continue
            mapping[v] = c
            used.add(c)
            bt(pos + 1, mapping, used)
            del mapping[v]
            used.discard(c)

    bt(0, {}, set())
    return out


AUT = automorphisms()
ORBITS = []
seen = set()
for e in EDGES:
    if e in seen:
        continue
    orb = {tuple(sorted((p[e[0]], p[e[1]]))) for p in AUT}
    ORBITS.append(sorted(orb))
    seen |= orb
assert len(ORBITS) == 5, "expected the 5 edge orbits the thread reports; got %d" % len(ORBITS)
assert len(AUT) == 6, "expected |Aut| = 6 for the L2 gasket; got %d" % len(AUT)


def build_H(weights):
    rows, cols, vals = [], [], []
    for s in range(DIM):
        diag = 0.0
        for (k, (a, b)) in enumerate(EDGES):
            ba, bb = (s >> (N - 1 - a)) & 1, (s >> (N - 1 - b)) & 1
            J = weights[k]
            if ba == bb:
                diag += 0.25 * J
            else:
                diag -= 0.25 * J
                t = s ^ (1 << (N - 1 - a)) ^ (1 << (N - 1 - b))
                rows.append(s); cols.append(t); vals.append(0.5 * J)
        rows.append(s); cols.append(s); vals.append(diag)
    return csr_matrix(coo_matrix((vals, (rows, cols)), shape=(DIM, DIM)))


def lowest(H, k=8):
    w, v = eigsh(H, k=k, which="SA")
    o = np.argsort(w)
    return w[o], v[:, o]


_BITS = ((np.arange(1 << N)[:, None] >> (N - 1 - np.arange(N))[None, :]) & 1)
_SIGNS = {}
for _a in range(N):
    for _b in range(N):
        if _a < _b:
            _SIGNS[(_a, _b)] = np.where(_BITS[:, _a] == _BITS[:, _b], 0.25, -0.25)


def zz_from_projector(V, a, b):
    """<sz_a sz_b> in the state P/rank, with P the projector onto the columns of V."""
    return float(_SIGNS[(min(a, b), max(a, b))] @ (V ** 2).sum(axis=1)) / V.shape[1]


def within_orbit_var(V):
    """Largest within-orbit variance of <sz sz> over the five edge orbits."""
    worst = 0.0
    for orb in ORBITS:
        cs = [zz_from_projector(V, a, b) for (a, b) in orb]
        worst = max(worst, float(np.var(cs)))
    return worst


def total_within_orbit_var(V):
    """Summed over orbits, weighted by orbit size: the aggregate a paper would quote."""
    tot = 0.0
    for orb in ORBITS:
        cs = [zz_from_projector(V, a, b) for (a, b) in orb]
        tot += float(np.var(cs)) * len(orb)
    return tot


def main():
    report = {"N": N, "edges": len(EDGES), "orbits": [len(o) for o in ORBITS], "aut": len(AUT)}
    failures = []
    print("L2 gasket: %d vertices, %d edges, %d edge orbits, |Aut| = %d"
          % (N, len(EDGES), len(ORBITS), len(AUT)))

    base = [1.0] * len(EDGES)
    w0, v0 = lowest(build_H(base))
    deg0 = int(np.sum(np.abs(w0 - w0[0]) < TOL))
    print("unperturbed ground degeneracy = %d\n" % deg0)
    report["unperturbed_degeneracy"] = deg0

    # -- the floor: a twofold subspace INSIDE the unperturbed fourfold manifold ------------------
    V4 = v0[:, :deg0]
    rng = np.random.default_rng(31)
    floors = []
    for _ in range(60):
        Q, _ = np.linalg.qr(rng.standard_normal((deg0, deg0)))
        W = V4 @ Q
        floors.append(within_orbit_var(W[:, :2]))
    floor = float(np.mean(floors))
    report["floor_rank2_inside_unperturbed_manifold"] = {
        "mean": floor, "sd": float(np.std(floors)),
        "min": float(np.min(floors)), "max": float(np.max(floors))}
    print("FLOOR, rank-2 projector inside the UNPERTURBED manifold (no symmetry broken):")
    print("  largest within-orbit variance = %.4e  (sd %.1e, min %.4e, max %.4e over 60 draws)\n"
          % (floor, np.std(floors), np.min(floors), np.max(floors)))

    # control: the full unperturbed manifold must give machine zero
    z = within_orbit_var(V4)
    report["control_rank4_at_eps0"] = z
    if z > 1e-20:
        failures.append("rank-4 at eps=0 gave %.3e, not machine zero" % z)

    # -- the sweep -------------------------------------------------------------------------------
    rows = []
    print("%-9s %-6s %-14s %-14s %-14s %s"
          % ("eps", "deg", "rank2", "rank4", "rank2 total", "orbital splitting"))
    for eps in EPS_GRID:
        wts = list(base)
        wts[0] = 1.0 + eps
        w, v = lowest(build_H(wts))
        deg = int(np.sum(np.abs(w - w[0]) < TOL))
        r2 = within_orbit_var(v[:, :max(deg, 2)])
        r4 = within_orbit_var(v[:, :4])
        tot2 = total_within_orbit_var(v[:, :max(deg, 2)])
        split = float(w[2] - w[0])
        rows.append({"eps": eps, "deg": deg, "rank2": r2, "rank4": r4,
                     "rank2_total": tot2, "splitting": split,
                     "rank2_over_floor": r2 / floor if floor else None})
        print("%-9s %-6d %-14.4e %-14.4e %-14.4e %.4e"
              % (eps, deg, r2, r4, tot2, split))
    report["sweep"] = rows

    print("\nrank2 relative to the floor, which is what decides whether the number is his effect:")
    for r in rows:
        print("  eps = %-8s ratio = %.4f" % (r["eps"], r["rank2_over_floor"]))

    # -- controls --------------------------------------------------------------------------------
    small = [r for r in rows if r["eps"] <= 0.01]
    big = [r for r in rows if r["eps"] >= 0.1]
    if any(r["rank4"] >= r["rank2"] for r in small):
        failures.append("rank4 did not fall below rank2 at small eps; the projectors agree")
    ratios = [r["rank4"] / (r["eps"] ** 2) for r in rows if r["eps"] <= 0.05]
    report["rank4_over_eps_squared"] = ratios
    if max(ratios) / min(ratios) > 5.0:
        failures.append("rank4 is not eps^2 across the small-eps rows: ratios %s"
                        % [round(x, 4) for x in ratios])
    slopes = [r["splitting"] / r["eps"] for r in rows if r["eps"] <= 0.01]
    report["splitting_over_eps"] = slopes
    if max(slopes) / min(slopes) > 1.5:
        failures.append("the splitting is not linear in eps: slopes %s" % [round(x, 4) for x in slopes])

    print("\nrank4 / eps^2 at eps <= 0.05: %s" % [float("%.4g" % x) for x in ratios])
    print("splitting / eps at eps <= 0.01: %s" % [float("%.4g" % x) for x in slopes])

    # -- the finding -----------------------------------------------------------------------------
    r001 = [r for r in rows if r["eps"] == 0.001][0]
    print()
    tots = [r["rank2_total"] for r in rows if r["eps"] <= 0.01]
    print("FINDING, and it is the CONVERGENCE rather than the floor.")
    print("  Summed over the %d edges the rank-2 statistic gives %s at eps = 0.01, 0.001 and 0.0001."
          % (len(EDGES), ", ".join("%.4e" % t for t in tots)))
    print("  It stops moving by eps = 0.01, so it does not depend on the perturbation and therefore")
    print("  does not measure it. What it measures is which two-dimensional subspace of the fourfold")
    print("  manifold the perturbation selects.")
    print("  The floor does NOT dominate: rank2 sits %.2fx above it at eps = 0.001, so that is not"
          % r001["rank2_over_floor"])
    print("  the objection, and a reader of this file must not be told it is.")
    print("  The lowest-four projector is the measure with a null: it falls as eps^2 and is machine")
    print("  zero at eps = 0. The rank-2 statistic has no value that means 'nothing broke here'.")

    print()
    if failures:
        for f in failures:
            print("CONTROL FAILED: %s" % f)
        report["verdict"] = "FAILED"
    else:
        report["verdict"] = "OK"
        print("VERDICT: OK. All three controls behaved.")

    out = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print("wrote %s" % os.path.basename(out))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
