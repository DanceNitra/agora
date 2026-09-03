"""By how much does his published tree file split an automorphism orbit, and do those edges have a
degenerate baseline?

WHY. I told him his older scan puts the orbit {(0,7), (13,14)} apart, against an abstract stating
that within-orbit variance vanishes. That figure has been quoted in our own notes without a
receipt, and it is about to appear in a letter to him, so it gets measured from his file.

The second half is the point. If exactly the edges his file splits are the edges whose E(0) is
seed-dependent, the split is an artefact of the reference point rather than a counterexample to his
theorem, and the letter can say which.

CONTROLS, each able to fail:
  * THE ORBITS ARE COMPUTED, NOT NAMED. The automorphism group of the generator's tree is
    enumerated, and every non-trivial edge orbit is scored. Quoting one pair I already knew about
    would find what I went looking for.
  * A CONTROL ORBIT. Orbits whose members his file agrees on are reported too, so the claim is
    "some orbits split", not "orbits split".
  * THE BASELINE STATUS COMES FROM A SEPARATE MEASUREMENT, read from the enumeration probe's
    receipt rather than recomputed here, so agreement between the two is a real cross-check.
  * A NULL THAT CAN FIRE. If no orbit splits by more than the tolerance his supplement uses, the
    claim I made to him was wrong and the probe says so.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ARCHIVE = os.path.join(ROOT, "agora_output", "edrn_submission", "guanghao_archive_2026-09-03")
BASELINE_RECEIPT = os.path.join(HERE, "which_edges_have_an_ill_defined_baseline.result.json")
OUT = os.path.join(HERE, "his_own_file_splits_an_orbit_by_the_baseline.result.json")
HIS_TOL = 1e-9              # the threshold his supplementary material uses for orbit equality


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def his_tree_depths():
    hits = []
    for root, _d, files in os.walk(ARCHIVE):
        for f in files:
            if not f.endswith(".txt"):
                continue
            text = io.open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
            if "=== tree" in text and "FINAL SUMMARY" in text:
                hits.append(text)
    if len(hits) != 1:
        refuse("found %d data files carrying a tree section and a FINAL SUMMARY; expected one"
               % len(hits))
    block = hits[0].split("=== random")[0]
    rows = {}
    for m in re.finditer(r"Edge \((\d+), (\d+)\): s=([\d.]+|None), depth=([\d.]+|None)", block):
        u, v, s, d = m.groups()
        rows[(int(u), int(v))] = None if d == "None" else float(d)
    if len(rows) != 14:
        refuse("parsed %d tree edges from his file, expected 14" % len(rows))
    return rows


def main():
    import networkx as nx
    from networkx.algorithms.isomorphism import GraphMatcher

    depths = his_tree_depths()
    print("  his tree file: %d edges, %d with a depth"
          % (len(depths), sum(1 for v in depths.values() if v is not None)))

    edges = [tuple(sorted(e)) for e in nx.random_labeled_tree(15, seed=42).edges()]
    if sorted(edges) != sorted(depths):
        refuse("his edge list is not the generator's; the comparison would be against another tree")
    G = nx.Graph(edges)
    auts = list(GraphMatcher(G, G).isomorphisms_iter())
    orbits = {}
    for u, v in G.edges():
        key = frozenset(frozenset((m[u], m[v])) for m in auts)
        orbits.setdefault(key, []).append(tuple(sorted((u, v))))
    nontrivial = [sorted(m) for m in orbits.values() if len(m) > 1]
    if not nontrivial:
        refuse("the tree has no non-trivial edge orbit, so there is nothing to test")
    print("  non-trivial edge orbits: %d" % len(nontrivial))

    if not os.path.isfile(BASELINE_RECEIPT):
        refuse("no baseline receipt at %s; run which_edges_have_an_ill_defined_baseline.py first"
               % BASELINE_RECEIPT)
    rec = json.load(io.open(BASELINE_RECEIPT, encoding="utf-8"))
    degenerate = {tuple(e) for e in rec["degenerate_baseline"]["tree"]}

    report, split, agreed = [], [], []
    for members in nontrivial:
        vals = [depths[m] for m in members]
        if any(v is None for v in vals):
            report.append({"members": [list(m) for m in members], "depths": vals,
                           "spread": None, "note": "a member has no valley in his file"})
            continue
        spread = max(vals) - min(vals)
        bad = sorted(m for m in members if m in degenerate)
        row = {"members": [list(m) for m in members], "depths": vals, "spread": spread,
               "members_with_degenerate_baseline": [list(m) for m in bad]}
        report.append(row)
        (split if spread > HIS_TOL else agreed).append(row)
        print("    %-24s depths %s  spread %.3e  degenerate baseline: %s"
              % (str([list(m) for m in members]), ["%.6f" % v for v in vals], spread,
                 [list(m) for m in bad] or "none"))

    if not split:
        print("  NULL FIRED: no orbit in his file splits beyond %g, so the claim I made to him was "
              "wrong." % HIS_TOL)
    print()
    print("  orbits that split: %d, orbits that agree: %d" % (len(split), len(agreed)))

    explained = all(len(r["members_with_degenerate_baseline"]) == len(r["members"]) for r in split)
    clean_are_flat = all(not r["members_with_degenerate_baseline"] for r in agreed)
    print("  every split orbit is entirely degenerate-baseline edges: %s" % explained)
    print("  every agreeing orbit is entirely clean-baseline edges:   %s" % clean_are_flat)

    json.dump({
        "script": os.path.basename(__file__),
        "his_tolerance": HIS_TOL,
        "orbits": report,
        "orbits_that_split": len(split),
        "orbits_that_agree": len(agreed),
        "split_orbits_are_all_degenerate_baseline": explained,
        "agreeing_orbits_are_all_clean_baseline": clean_are_flat,
        "controls": {
            "orbits_computed_from_the_generator": True,
            "control_orbits_reported": bool(agreed),
            "baseline_status_read_from_a_separate_receipt": True,
            "null_can_fire": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
