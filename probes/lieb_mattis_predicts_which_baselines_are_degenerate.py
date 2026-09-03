"""Is the degenerate-baseline test spectral, or does Lieb-Mattis predict it from the graph alone?

WHY. Our draft was about to tell a first author that "the eligibility test has to be spectral, not
topological", on the evidence that three tree edges isolate a node yet keep a simple baseline. A
prior-art pass answered that the topological rule exists and is older than all of us: Lieb and
Mattis, J. Math. Phys. 3, 749 (1962). Sending the stronger claim would have presented a one-line
corollary of a 1962 theorem as an empirical caution. So it gets tested before it gets retracted.

THE RULE, derived rather than quoted. Removing edge (u,v) from a tree splits it into components
C1 and C2. Each is bipartite, so by Lieb-Mattis its ground level has total spin S_i = d_i / 2, where
d_i is the imbalance between its two colour classes, and that level spans M_i = -S_i .. S_i. With
n_up = 7 of 15 the accessible combinations are those with M1 + M2 = 7 - 15/2 = -1/2. The number of
such pairs IS the ground degeneracy of the full system in that sector. One pair means a simple
baseline; more than one means the solver picks arbitrarily.

CONTROLS, each able to fail:
  * THE PREDICTION IS MADE BEFORE THE MEASUREMENT IS READ. The receipt from the spectral enumeration
    is loaded only after every prediction is computed, and the comparison is a confusion matrix over
    all 14 tree edges rather than over the 7 pendant ones. Scoring only the cases the rule was
    invented for is how a rule looks perfect.
  * A NULL THAT CAN FIRE. If the prediction misses any edge, the rule is not sufficient and the
    draft's "spectral, not topological" line stands. That branch is live and reported.
  * IT PREDICTS THE COUNT, NOT A FLAG. Getting 2 where the spectrum says 2 is a stronger test than
    getting "degenerate" where the spectrum says "degenerate".
  * SCOPE IS MEASURED, NOT ASSUMED. Lieb-Mattis needs bipartite components. The random graph is
    tested for bipartiteness after removal, and where it fails the probe says the rule does not
    apply there rather than extending it.
"""
from __future__ import annotations

import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
RECEIPT = os.path.join(HERE, "which_edges_have_an_ill_defined_baseline.result.json")
OUT = os.path.join(HERE, "lieb_mattis_predicts_which_baselines_are_degenerate.result.json")

N = 15
N_UP = 7


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def graph_of(which):
    import networkx as nx
    if which == "tree":
        return [tuple(sorted(e)) for e in nx.random_labeled_tree(15, seed=42).edges()]
    return [tuple(sorted(e)) for e in nx.gnm_random_graph(15, 27, seed=42).edges()]


def predict(which, contra):
    """Ground degeneracy in sector n_up=7 after removing `contra`, from Lieb-Mattis alone."""
    import networkx as nx
    G = nx.Graph()
    G.add_nodes_from(range(N))
    G.add_edges_from(graph_of(which))
    G.remove_edge(*contra)
    comps = [G.subgraph(c).copy() for c in nx.connected_components(G)]
    spins, sizes, bipartite = [], [], True
    for C in comps:
        if not nx.is_bipartite(C):
            bipartite = False
            break
        a, b = nx.bipartite.sets(C) if C.number_of_edges() else (set(C.nodes()), set())
        spins.append(abs(len(a) - len(b)) / 2.0)
        sizes.append(C.number_of_nodes())
    if not bipartite:
        return {"applies": False, "reason": "a component is not bipartite"}

    target = N_UP - N / 2.0                      # sum of M_i for this magnetisation sector
    combos = []

    def walk(i, acc, chosen):
        if i == len(spins):
            if abs(acc - target) < 1e-9:
                combos.append(list(chosen))
            return
        S = spins[i]
        m = -S
        while m <= S + 1e-9:
            walk(i + 1, acc + m, chosen + [m])
            m += 1.0

    walk(0, 0.0, [])
    return {"applies": True, "component_sizes": sizes, "component_spins": spins,
            "degeneracy": len(combos), "combinations": combos}


def main():
    predictions = {}
    for which in ("tree", "random"):
        for e in graph_of(which):
            predictions[(which, e)] = predict(which, e)
    print("  predictions made for %d edges, before any measurement was read" % len(predictions))

    if not os.path.isfile(RECEIPT):
        refuse("no spectral receipt at %s to score against" % RECEIPT)
    rec = json.load(io.open(RECEIPT, encoding="utf-8"))
    measured = {(r["graph"], tuple(r["edge"])): r["baseline_degeneracy"] for r in rec["rows"]}
    if len(measured) != len(predictions):
        refuse("the receipt holds %d edges against %d predictions" % (len(measured), len(predictions)))

    rows, hits, misses, na = [], 0, [], []
    for key, p in sorted(predictions.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        which, e = key
        m = measured[key]
        if not p["applies"]:
            na.append({"graph": which, "edge": list(e), "measured": m, "why": p["reason"]})
            continue
        ok = p["degeneracy"] == m
        rows.append({"graph": which, "edge": list(e), "predicted": p["degeneracy"], "measured": m,
                     "agree": ok, "component_spins": p["component_spins"]})
        if ok:
            hits += 1
        else:
            misses.append(rows[-1])

    print()
    print("  graph   edge      predicted  measured  spins")
    for r in rows:
        print("  %-7s %-8s %6d %9d      %s   %s"
              % (r["graph"], tuple(r["edge"]), r["predicted"], r["measured"],
                 r["component_spins"], "" if r["agree"] else "<-- MISS"))
    if na:
        print()
        for r in na:
            print("  %-7s %-8s rule does not apply (%s); measured %d"
                  % (r["graph"], tuple(r["edge"]), r["why"], r["measured"]))

    total = len(rows)
    print()
    print("  Lieb-Mattis predicts %d of %d edges where it applies; %d misses; %d out of scope"
          % (hits, total, len(misses), len(na)))
    if misses:
        print("  NULL FIRED: the topological rule is not sufficient, so a spectral test is still "
              "needed for these edges.")

    # A rule that predicts "simple" everywhere would score well if almost everything is simple.
    degen = sum(1 for r in rows if r["measured"] > 1)
    print("  base rate: %d of %d in-scope edges are degenerate, so always guessing 'simple' scores "
          "%d of %d" % (degen, total, total - degen, total))

    json.dump({
        "script": os.path.basename(__file__),
        "sector_n_up": N_UP,
        "rule": "each connected component after removal is bipartite, so its ground total spin is "
                "half its SUBLATTICE imbalance (Lieb-Mattis 1962, which needs isotropic "
                "Heisenberg couplings, J >= 0 between sublattices, no site-dependent field, and "
                "no intra-sublattice coupling for equality rather than a bound); the sector "
                "degeneracy is the number of tuples (M_i), |M_i| <= S_i, summing to n_up - N/2",
        "citation": "E. H. Lieb and D. C. Mattis, Ordering energy levels of interacting spin systems, J. Math. Phys. 3, 749-751 (1962), doi:10.1063/1.1724276",
        "rows": rows, "out_of_scope": na,
        "hits": hits, "total_in_scope": total, "misses": misses,
        "base_rate_all_simple_would_score": total - degen,
        "controls": {
            "predictions_computed_before_receipt_was_read": True,
            "scored_on_every_edge_not_only_pendant_ones": True,
            "predicts_the_count_not_a_flag": True,
            "base_rate_reported": True,
            "null_can_fire": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
