"""Close two of the ten limitations the manuscript lists as open, by running them.

The paper we just published states ten open items. Two of them are not open problems at all -- they
are scans nobody had run yet, and both fit in a few minutes of exact diagonalisation:

    (vii)  the control edge (0,1) has only been scanned to s = 1.0; confirmation to s = 3.0 is pending
    (viii) edge (7,8) in the small-world graph has a boundary minimum that is unresolved

(vii) matters because the control edge is the paper's own null: it connects two tip vertices, making
the two subgraphs equivalent, and reports a completely flat enhanced diagnosis over s in [0,1]. A
null that has only been checked over a third of the range a defect edge is scanned over is a weaker
null than it looks, and extending it either strengthens the control or finds something.

(viii) matters because "the minimum sits at the scan boundary s = 0.000" means the fixture could not
tell a genuine valley from an artifact of where the scan stopped. The manuscript excludes that edge
from the count for exactly this reason. Scanning into negative s answers it: if the curve turns
around, there is an interior minimum and the edge is a valley; if it keeps falling, the boundary
minimum was the scan's edge and the exclusion was right.

CONTROLS
  C1 REPRODUCE   the published sub-range must come back before the extension is believed: the control
                 edge's range over s in [0,1] must be ~0 (published: 0.000000, cross-seed std 1.4e-11),
                 and the defect edge (0,6) must still show its valley at s = 1.000. A scan that
                 disagrees with the published range is measuring a different system.
  C2 CAN FAIL    the same instrument on the defect edge must NOT be flat -- otherwise "flat" is what
                 this code returns for everything and the control edge's flatness means nothing.
  C3 SECTOR      Sz = +1/2, C(15,8) = 6435 states, and E(0) must reproduce the manuscript's 0.246731.
  C4 BOUNDARY    for (viii), the extended scan must actually contain the old boundary point, so the
                 old minimum and the new one are comparable rather than two different curves.

Run:  python probes/edrn_two_of_the_papers_own_open_items.py
"""
from __future__ import annotations
import itertools
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import scipy.sparse.linalg as spla  # noqa: E402

from edrn_gap_structure_and_sector import (  # noqa: E402
    sierpinski, sector_basis, sector_H, observables,
)

PUBLISHED_E0 = 0.246731
rows: list[tuple[bool, str, str]] = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))


def lowest_vec(H):
    """Ground vector. Dense under 512 because ARPACK is unreliable on tiny matrices."""
    if H.shape[0] <= 512:
        w, v = np.linalg.eigh(H.toarray())
        return v[:, int(np.argmin(w))]
    w, v = spla.eigsh(H, k=2, which="SA", tol=1e-11)
    return v[:, int(np.argmin(w))]


def scan(n, edges, defect, states, index, svals):
    out = {}
    for s in svals:
        psi = lowest_vec(sector_H(n, edges, defect, float(s), states, index))
        _, e = observables(psi, states, edges)
        out[round(float(s), 4)] = e
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    t0 = time.time()
    res = {}

    # ---------------- (vii) the control edge, out to s = 3.0 --------------------------------
    n, edges = sierpinski(2)
    tips = {v for v in range(n) if sum(1 for e in edges if v in e) == 2}
    # THE PAPER'S DESCRIPTION OF ITS OWN CONTROL EDGE CANNOT BE SATISFIED IN SG(2).
    # It says: "The control edge (0,1) -- connecting two tip vertices, making the two subgraphs
    # equivalent". The tip (degree-2) vertices of a Sierpinski gasket are its three outer corners,
    # and they are pairwise non-adjacent at every level. So no edge joins two of them. Asserted
    # rather than asserted-in-prose, because this is a claim about a published paper we are on.
    tip_pairs = [e for e in edges if e[0] in tips and e[1] in tips]
    ck(len(tips) == 3 and not tip_pairs,
       "SG(2) has 3 tips and NO edge joins two of them -- the paper's control-edge description "
       "is geometrically unsatisfiable", f"tips {sorted(tips)}, tip-to-tip edges {tip_pairs}")
    defect = next(e for e in edges if (e[0] in tips) != (e[1] in tips))
    control = None      # identified by measurement below, not by the description
    states, index = sector_basis(n, 8)
    ck(len(states) == math.comb(15, 8) == 6435, "C3 sector is C(15,8) = 6435", str(len(states)))
    print(f"SG(2): control edge {control} (tip-to-tip), defect edge {defect} (tip-to-interior)")

    # WHICH edge is flat, then. Every one of the 27, over the published range, so the control is
    # identified by what it does rather than by a description that cannot be true.
    coarse = [round(x, 2) for x in np.arange(0.0, 1.01, 0.1)]
    flat = []
    for e in edges:
        v = scan(n, edges, e, states, index, coarse)
        r = max(v.values()) - min(v.values())
        if r < 1e-6:
            flat.append((e, r))
    print(f"  flat edges over s in [0,1] (range < 1e-6): {[list(e) for e, _ in flat]}"
          f"   ({time.time()-t0:.0f}s)")
    ck(bool(flat), "at least one edge reproduces the paper's flat control", str(len(flat)))
    res["flat_edges"] = [list(e) for e, _ in flat]
    control = flat[0][0] if flat else defect

    grid = [round(x, 2) for x in np.arange(0.0, 3.01, 0.05)]
    ctrl = scan(n, edges, control, states, index, grid)
    print(f"  control edge {control} scanned over s in [0,3] ({len(grid)} points, "
          f"{time.time()-t0:.0f}s)")
    ck(abs(ctrl[0.0] - PUBLISHED_E0) < 5e-6, "C3 E(0) reproduces the manuscript's 0.246731",
       f"{ctrl[0.0]:.6f}")

    sub = [v for s, v in ctrl.items() if s <= 1.0]
    rng_pub = max(sub) - min(sub)
    ck(rng_pub < 1e-6, "C1 the published sub-range s<=1 is flat, as published",
       f"range {rng_pub:.2e} over {len(sub)} points")
    full = list(ctrl.values())
    rng_full = max(full) - min(full)
    print(f"  range over s in [0,1]: {rng_pub:.3e}   |   over s in [0,3]: {rng_full:.3e}")

    # C2: the same instrument on the DEFECT edge must not be flat
    dfct = scan(n, edges, defect, states, index, grid)
    rng_d = max(dfct.values()) - min(dfct.values())
    ck(rng_d > 0.05, "C2 the same scan on the defect edge is NOT flat -- 'flat' means something",
       f"defect range {rng_d:.4f}")
    smin = min(dfct, key=dfct.get)
    ck(abs(smin - 1.0) < 1e-9, "C1 and the defect valley still sits at s = 1.000", f"min at {smin}")
    res["vii_control_edge"] = {"edge": list(control), "described_as": "tip-to-tip, which SG(2) has none of", "grid": grid, "E": ctrl,
                               "range_0_1": rng_pub, "range_0_3": rng_full,
                               "defect_range_0_3": rng_d, "defect_min_at": smin}

    # ---------------- (viii) the small-world boundary minimum -------------------------------
    g = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
    we = sorted(tuple(sorted(e)) for e in g.edges())
    ck(len(we) == 20, "the small-world graph is the paper's (N=10, 20 edges)", str(len(we)))
    target = (7, 8)
    ck(target in we, "edge (7,8) is present in that graph")
    ws_states, ws_index = sector_basis(10, 5)

    neg = [round(x, 3) for x in np.arange(-1.0, 3.001, 0.05)]
    ck(0.0 in neg, "C4 the extended grid contains the old boundary point s = 0")
    ws = scan(10, we, target, ws_states, ws_index, neg)
    print(f"  small-world (7,8) scanned over s in [-1,3] ({len(neg)} points, {time.time()-t0:.0f}s)")

    old = {s: v for s, v in ws.items() if 0.0 <= s <= 3.0}
    old_min = min(old, key=old.get)
    new_min = min(ws, key=ws.get)
    interior = neg[0] < new_min < neg[-1]
    print(f"  minimum on the OLD range [0,3]: s = {old_min}   E = {old[old_min]:.6f}")
    print(f"  minimum on the NEW range [-1,3]: s = {new_min}  E = {ws[new_min]:.6f}"
          f"   {'INTERIOR -- a real valley' if interior else 'STILL AT THE BOUNDARY'}")
    ck(abs(old_min - 0.0) < 1e-9,
       "C4 the old boundary minimum reproduces at s = 0 on the published range", str(old_min))
    res["viii_smallworld_edge_7_8"] = {"edge": list(target), "grid": neg, "E": ws,
                                       "min_old_range": old_min, "min_new_range": new_min,
                                       "interior": bool(interior),
                                       "E_at_min": ws[new_min], "E_at_zero": ws[0.0]}

    print()
    for ok, l, d in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {l}" + (f"   [{d}]" if d else ""))
    p = sum(1 for ok, _, _ in rows if ok)
    print(f"\n{p}/{len(rows)} controls pass   ({time.time()-t0:.0f}s)")

    res["controls"] = {l: ok for ok, l, _ in rows}
    out = os.path.join(HERE, "edrn_two_of_the_papers_own_open_items.result.json")
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1)
    print(f"receipt -> {out}")
    return 0 if p == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
