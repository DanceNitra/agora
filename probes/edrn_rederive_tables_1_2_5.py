"""Re-derive Tables I, II and V, and say plainly which cells nobody can re-derive from the paper.

Tables III and IV came back 45/46 in `edrn_rederive_the_tables.py`. These three are the rest, and
they are more interesting because two of them contain cells that are **not reproducible by anyone**,
for reasons that are properties of the paper rather than of any implementation:

  * Table I is a five-SEED audit. Exact diagonalisation is deterministic, and at s = 1.000 the ground
    level is exactly two-fold, so a solver returns one arbitrary vector of the manifold. The seed
    spread is not a quantity a deterministic run can reproduce. What IS checkable is the valley
    POSITION (all five rows say 1.0000) and whether our value lands inside the published spread.
  * Table II scans a ring, a tree and a random graph at N=15. A ring on 15 vertices is unique. A tree
    with 14 edges on 15 vertices is one of 15^13 labelled trees, and a "random graph, 27 edges"
    names no seed. **Neither is determined by the text**, so those rows are NOT_DERIVABLE for any
    reader, and saying so is the finding.
  * Table V is the fine multi-seed audit on three small-world edges, on the same graph whose 20-edge
    survey reproduced 40/40. Fully derivable.

SPEED, because it changes what is affordable. H(s) is linear in s: the defect edge contributes
s * H_defect and everything else is fixed. Building the matrix once and reusing it turns 3,001
matrix constructions into one, which is what makes a step-0.001 scan possible at all. The identity
is checked against the original builder rather than assumed.

Run:  python probes/edrn_rederive_tables_1_2_5.py
"""
from __future__ import annotations
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import scipy.sparse as sp  # noqa: E402
import scipy.sparse.linalg as spla  # noqa: E402

from edrn_gap_structure_and_sector import (  # noqa: E402
    sierpinski, sector_basis, sector_H, observables,
)

TEX = os.path.join(ROOT, "agora_output", "edrn_final", "_main_snapshot.tex")
TOL = 5e-4
results: list[dict] = []


def record(table, cell, published, got, note=""):
    v = ("NOT_DERIVABLE" if got is None else
         "REPRODUCED" if abs(float(published) - float(got)) <= TOL else "DISAGREES")
    results.append({"table": table, "cell": cell, "published": None if published is None
                    else float(published), "recomputed": None if got is None else float(got),
                    "verdict": v, "note": note})
    return v


def split_H(n, edges, defect, states, index):
    """H(s) = base + s*delta. Verified against the original builder, not assumed."""
    rest = [e for e in edges if e != defect]
    base = sector_H(n, rest, (-1, -1), 0.0, states, index)
    both = sector_H(n, edges, defect, 1.0, states, index)
    delta = (both - base).tocsr()
    chk = (base + 0.37 * delta - sector_H(n, edges, defect, 0.37, states, index))
    assert abs(chk).max() < 1e-10, "the linear split does not reproduce the original builder"
    return base.tocsr(), delta


def ground_vec(H):
    if H.shape[0] <= 512:
        w, v = np.linalg.eigh(H.toarray())
        i = int(np.argmin(w))
        return v[:, i]
    w, v = spla.eigsh(H, k=2, which="SA", tol=1e-12)
    return v[:, int(np.argmin(w))]


def curve(base, delta, states, edges, svals):
    out = {}
    for s in svals:
        psi = ground_vec((base + float(s) * delta).tocsr())
        d, e = observables(psi, states, edges)
        out[round(float(s), 4)] = (d, e)
    return out


def tables():
    tex = open(TEX, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", tex, re.S):
        blk = m.group(1)
        lab = re.search(r"\\label\{([^}]*)\}", blk)
        tab = re.search(r"\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}", blk, re.S)
        if not (lab and tab):
            continue
        rows = []
        for line in tab.group(1).splitlines():
            line = line.strip()
            if line and not re.match(r"\\(top|mid|bottom)rule", line):
                rows.append([c.strip() for c in line.rstrip("\\\\").split("&")])
        out[lab.group(1)] = rows
    return out


def num(s):
    m = re.search(r"-?\d+\.?\d*", s.replace("$", "").replace("\\textbf{", ""))
    return float(m.group(0)) if m else None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    t0 = time.time()
    T = tables()

    n, edges = sierpinski(2)
    tips = {v for v in range(n) if sum(1 for e in edges if v in e) == 2}
    defect = next(e for e in edges if (e[0] in tips) != (e[1] in tips))
    st15, ix15 = sector_basis(n, 8)
    b15, d15 = split_H(n, edges, defect, st15, ix15)
    print(f"linear-split check passed  ({time.time()-t0:.0f}s)")

    grid101 = [round(x, 4) for x in np.linspace(0.0, 1.0, 101)]
    c15 = curve(b15, d15, st15, edges, grid101)
    E0 = c15[0.0][1]
    print(f"C0 calibration E(0) = {E0:.6f} vs 0.246731")
    if abs(E0 - 0.246731) > 5e-6:
        print("FAIL -- instrument disagrees with the paper's anchor"); return 1
    smin = min(c15, key=lambda s: c15[s][1])
    Emin = c15[smin][1]
    print(f"   our valley: s = {smin:.4f}, E = {Emin:.6f}, depth = {E0-Emin:.6f}")

    # ---- Table I -----------------------------------------------------------------------------
    print("\nTable I -- five-seed audit at the fractal defect edge")
    vals, depths = [], []
    for r in T.get("tab:l2_valley", [])[1:]:
        if len(r) < 4 or num(r[0]) is None:
            continue
        record("I", f"seed {r[0]} valley position", num(r[1]), smin)
        vals.append(num(r[2])); depths.append(num(r[3]))
        record("I", f"seed {r[0]} valley value", num(r[2]), None,
               "seed-dependent: s=1.000 is an exact two-fold crossing, a deterministic solver "
               "returns one arbitrary vector of the manifold")
        record("I", f"seed {r[0]} valley depth", num(r[3]), None, "same reason")
    if vals:
        inside = min(vals) - 1e-9 <= Emin <= max(vals) + 1e-9
        print(f"   positions: all five say 1.0000, ours {smin:.4f}  "
              f"{'REPRODUCED' if abs(smin-1.0)<1e-9 else 'DISAGREES'}")
        print(f"   values: published span {min(vals):.6f}-{max(vals):.6f}, ours {Emin:.6f}  "
              f"{'INSIDE the published spread' if inside else 'OUTSIDE -- worth a look'}")
        record("I", "our value lies inside the published seed spread", 1.0,
               1.0 if inside else 0.0, f"span {min(vals):.6f}-{max(vals):.6f}, ours {Emin:.6f}")

    # ---- Table II ----------------------------------------------------------------------------
    print("\nTable II -- control graphs")
    ring = [(i, (i + 1) % 15) for i in range(15)]
    ring = sorted(tuple(sorted(e)) for e in ring)
    for r in T.get("tab:control_graphs", [])[1:]:
        g = r[0].strip().lower()
        if g.startswith("ring"):
            rdef = ring[0]
            rb, rd = split_H(15, ring, rdef, st15, ix15)
            gr = [round(x, 3) for x in np.arange(0.0, 3.001, 0.01)]
            cc = curve(rb, rd, st15, ring, gr)
            rE0 = cc[0.0][1]
            rmin = min(cc, key=lambda s: cc[s][1])
            v1 = record("II", "ring valley s", num(r[1]), rmin)
            v2 = record("II", "ring depth (single)", num(r[2]), rE0 - cc[rmin][1])
            print(f"   ring  valley s {num(r[1])} vs {rmin:.3f} {v1:14} | "
                  f"depth {num(r[2]):.4f} vs {rE0-cc[rmin][1]:.4f} {v2}")
        else:
            why = ("a tree with 14 edges on 15 vertices is not determined by the text"
                   if g.startswith("tree") else
                   "a random graph with 27 edges is given with no seed or edge list")
            for lbl, col in (("valley s", 1), ("depth (single)", 2), ("depth (multi)", 3)):
                record("II", f"{g} {lbl}", num(r[col]), None, why)
            print(f"   {g:6} NOT_DERIVABLE -- {why}")

    # ---- Table V -----------------------------------------------------------------------------
    gph = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
    we = sorted(tuple(sorted(e)) for e in gph.edges())
    st10, ix10 = sector_basis(10, 5)
    fine = [round(x, 3) for x in np.arange(0.0, 3.0005, 0.001)]
    print(f"\nTable V -- fine audit, step 0.001, {len(fine)} points per edge")
    for r in T.get("tab:sw_multiseed", [])[1:]:
        em = re.findall(r"\d+", r[0])
        if len(em) != 2:
            continue
        edge = (int(em[0]), int(em[1]))
        if edge not in we:
            record("V", f"{edge}", num(r[1]), None, "edge absent from the reconstructed graph")
            continue
        b, d = split_H(10, we, edge, st10, ix10)
        cc = curve(b, d, st10, we, fine)
        Es = {s: v[1] for s, v in cc.items()}
        smn = min(Es, key=Es.get)
        # topographic prominence: drop below the LOWER of the two flanking maxima
        ks = sorted(Es)
        i = ks.index(smn)
        left = max([Es[k] for k in ks[:i]] or [Es[ks[0]]])
        right = max([Es[k] for k in ks[i + 1:]] or [Es[ks[-1]]])
        prom = min(left, right) - Es[smn]
        v1 = record("V", f"{edge} valley s", num(r[1]), smn)
        v2 = record("V", f"{edge} prominence", num(r[2]), prom)
        print(f"   {str(edge):8} valley {num(r[1]):.3f} vs {smn:.3f} {v1:14} | "
              f"prominence {num(r[2]):.6f} vs {prom:.6f} {v2}   ({time.time()-t0:.0f}s)")

    record("CONTROL", "corrupted expectation", 0.111111, 0.999999, "must read DISAGREES")

    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    bad = [r for r in results if r["verdict"] == "DISAGREES" and r["table"] != "CONTROL"]
    for r in bad:
        print(f"   DISAGREES [{r['table']}] {r['cell']:30} {r['published']:.6f} vs "
              f"{r['recomputed']:.6f}")

    out = os.path.join(HERE, "edrn_rederive_tables_1_2_5.result.json")
    json.dump({"calibration_E0": E0, "counts": counts, "cells": results},
              open(out, "w", encoding="utf-8"), indent=1)
    print(f"\nreceipt -> {out}   ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
