"""Re-derive the paper's TABLES, cell by cell, instead of matching numbers against any JSON.

The first attempt at this audit reported 241 of 242 numbers as "having a receipt" and passed the one
claim already known to be false -- it matched the control edge's `0.000000` against a file about the
coefficient of variation of two peaks. 181 of 242 matched on three decimals alone. A check that
cannot fail on a known defect has measured nothing, so this one recomputes each cell with the same
exact diagonalisation that produced it and compares in place.

Three outcomes, kept apart on purpose:

    REPRODUCED     recomputed here, agrees to the precision the paper prints
    DISAGREES      recomputed here, does not agree
    NOT_DERIVABLE  no path from this repository to that number (seed-dependent, or a graph we
                   cannot reconstruct from the text)

NOT_DERIVABLE is not a pass. It is the count of published numbers nobody outside the original run
can check, and it belongs in the output beside the others rather than folded into them.

CONTROLS
  C0 CALIBRATION  E(0) on the fractal graph must return 0.246731 before any verdict is believed;
                  if the instrument disagrees with the paper's own anchor, every DISAGREES below is
                  about this script rather than about the paper.
  C1 CAN FAIL     a deliberately corrupted expectation must come back DISAGREES, so the comparator
                  is not returning REPRODUCED for everything.

Run:  python probes/edrn_rederive_the_tables.py
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
import scipy.sparse.linalg as spla  # noqa: E402

from edrn_gap_structure_and_sector import (  # noqa: E402
    sierpinski, sector_basis, sector_H, observables,
)

TEX = os.path.join(ROOT, "agora_output", "edrn_final", "_main_snapshot.tex")
TOL = 5e-4
results: list[dict] = []


def record(table, cell, published, got, note=""):
    if got is None:
        v = "NOT_DERIVABLE"
    elif abs(float(published) - float(got)) <= TOL:
        v = "REPRODUCED"
    else:
        v = "DISAGREES"
    results.append({"table": table, "cell": cell, "published": float(published),
                    "recomputed": None if got is None else float(got), "verdict": v,
                    "note": note})
    return v


def ground(H):
    if H.shape[0] <= 512:
        w, v = np.linalg.eigh(H.toarray())
        i = int(np.argmin(w))
        return w[i], v[:, i]
    w, v = spla.eigsh(H, k=2, which="SA", tol=1e-12)
    i = int(np.argmin(w))
    return w[i], v[:, i]


def E_of(n, edges, defect, s, states, index):
    _, psi = ground(sector_H(n, edges, defect, float(s), states, index))
    d, e = observables(psi, states, edges)
    return d, e


def gap_of(n, edges, defect, s, states, index):
    H = sector_H(n, edges, defect, float(s), states, index)
    if H.shape[0] <= 512:
        w = np.sort(np.linalg.eigvalsh(H.toarray()))
    else:
        w = np.sort(spla.eigsh(H, k=4, which="SA", tol=1e-12)[0])
    return float(w[1] - w[0])


def tables_from_tex():
    """Every tabular in the manuscript, with its label and its data rows."""
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
            if not line or line.startswith("\\toprule") or line.startswith("\\midrule") \
               or line.startswith("\\bottomrule"):
                continue
            cells = [c.strip() for c in line.rstrip("\\\\").split("&")]
            rows.append(cells)
        out[lab.group(1)] = rows
    return out


def num(s):
    m = re.search(r"-?\d+\.?\d*", s.replace("$", ""))
    return float(m.group(0)) if m else None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    t0 = time.time()
    tabs = tables_from_tex()
    print("tables found:", list(tabs))

    # ---- C0 calibration -------------------------------------------------------------------
    n, edges = sierpinski(2)
    tips = {v for v in range(n) if sum(1 for e in edges if v in e) == 2}
    defect = next(e for e in edges if (e[0] in tips) != (e[1] in tips))
    st15, ix15 = sector_basis(n, 8)
    _, e0 = E_of(n, edges, defect, 0.0, st15, ix15)
    ok0 = abs(e0 - 0.246731) < 5e-6
    print(f"C0 calibration  E(0) = {e0:.6f} vs published 0.246731  "
          f"{'OK' if ok0 else 'FAIL -- everything below is about this script'}")
    if not ok0:
        return 1

    # ---- Table III: the default observable at three points --------------------------------
    t3 = tabs.get("tab:default_control") or tabs.get("tab:default")
    if t3 is None:
        for k, rows in tabs.items():
            if rows and len(rows[0]) == 3 and "D" in rows[0][1]:
                t3 = rows
                break
    if t3:
        print("\nTable III -- default observable, edge (0,6), s = 0.99 / 1.00 / 1.01")
        for r in t3[1:]:
            s = num(r[0])
            if s is None:
                continue
            d, e = E_of(n, edges, defect, s, st15, ix15)
            v1 = record("III", f"D_default(s={s})", num(r[1]), 3 * d,
                        "x3: paper tabulates the full dot product")
            v2 = record("III", f"E_enhanced(s={s})", num(r[2]), e)
            print(f"   s={s:<5} D {num(r[1]):.6f} vs {3*d:.6f} {v1:14} | "
                  f"E {num(r[2]):.6f} vs {e:.6f} {v2}")

    # ---- Table IV: the small-world full edge survey ----------------------------------------
    g = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
    we = sorted(tuple(sorted(e)) for e in g.edges())
    st10, ix10 = sector_basis(10, 5)
    t4 = None
    for k, rows in tabs.items():
        if rows and len(rows[0]) == 4 and rows[0][0].strip().lower().startswith("edge"):
            t4 = rows
            break
    if t4:
        print(f"\nTable IV -- small-world, {len(t4)-1} edges, N=10 "
              f"({time.time()-t0:.0f}s so far)")
        grid = [round(x, 2) for x in np.arange(0.0, 3.001, 0.01)]
        for r in t4[1:]:
            em = re.findall(r"\d+", r[0])
            if len(em) != 2:
                continue
            edge = (int(em[0]), int(em[1]))
            if edge not in we:
                record("IV", f"edge {edge}", 0, None, "edge not in the reconstructed graph")
                continue
            curve = {s: E_of(10, we, edge, s, st10, ix10)[1] for s in grid}
            rng = max(curve.values()) - min(curve.values())
            smin = min(curve, key=curve.get)
            v1 = record("IV", f"{edge} fine range", num(r[1]), rng)
            v2 = record("IV", f"{edge} valley s", num(r[2]), smin)
            print(f"   {str(edge):8} range {num(r[1]):.6f} vs {rng:.6f} {v1:14} | "
                  f"valley {num(r[2]):.3f} vs {smin:.3f} {v2}")

    # ---- C1: the comparator must be able to say DISAGREES ----------------------------------
    v = record("CONTROL", "deliberately corrupted expectation", 0.123456, 0.654321,
               "must read DISAGREES")
    print(f"\nC1 can-fail control: {v}")

    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    bad = [r for r in results if r["verdict"] == "DISAGREES" and r["table"] != "CONTROL"]
    if bad:
        print(f"\n{len(bad)} cells disagree:")
        for r in bad[:25]:
            print(f"   [{r['table']}] {r['cell']:28} published {r['published']:.6f}  "
                  f"recomputed {r['recomputed']:.6f}")

    out = os.path.join(HERE, "edrn_rederive_the_tables.result.json")
    json.dump({"calibration_E0": e0, "counts": counts, "cells": results},
              open(out, "w", encoding="utf-8"), indent=1)
    print(f"\nreceipt -> {out}   ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
