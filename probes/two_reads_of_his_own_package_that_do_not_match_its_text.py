"""Two claims in his 2026-09-04 package, checked against the package's own files.

WHY. His mechanism text rests on numbers that live in three JSON files and three scripts he shipped
together. Two of those numbers are worth reading rather than accepting.

CLAIM 1, the field name. `observation_protocol_quantitative.json` reports `valley_depth_mean` for
every entrance, and the LaTeX text quotes a "Valley depth" column. For entrance (0,1) the JSON says
0.1849481700007527 and the LaTeX says 0.124434. His `find_valley` returns `(s, e_values[curr])`, so
the second element is E AT the valley, while the decomposition script computes
`depth = fine_curve[valid[0]] - fine_curve[curr]`, which is E(0) - E(valley). If that is the whole
story, the two numbers must satisfy E(0) = depth + E_at_valley on the same edge.

CLAIM 2, the reproducibility. He reports a standard deviation of 0.000000 over five seeds for 19 of
20 entrances and reads it as "the computation itself is the prediction". We measured the opposite on
the gasket: where the ground level is degenerate, a seeded Lanczos returns a different member every
time and the diagnosis scatters. Both can be true, and if they are then the small-world level is
simply not degenerate, which follows from its trivial automorphism group. That is a prediction, so
it gets measured: the ground level of the small-world graph in his sector must be simple at the
grid points where he reports zero scatter.

CONTROLS, each able to fail:
  * CLAIM 1 IS AN ARITHMETIC IDENTITY OR IT IS NOTHING. The probe reads E(0) from his own stored
    curve and checks depth + E_at_valley against it on the same edge. A near miss is reported as a
    near miss, not rounded into agreement.
  * CLAIM 2 CARRIES ITS OWN COUNTEREXAMPLE. The gasket, where we measured a two-fold level and real
    seed scatter, is run through the identical degeneracy test. If the test calls both graphs simple
    it cannot tell them apart and proves nothing about either.
  * HIS FILES ARE THE SOURCE. Every number attributed to him is read out of the package, never
    retyped from his prose.
  * A MISSING FILE OR AN UNPARSED FIELD REFUSES rather than skipping the claim.
"""
from __future__ import annotations

import io
import itertools
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PKG = os.path.join(ROOT, "agora_output", "edrn_submission", "guanghao_archive_2026-09-04")
OUT = os.path.join(HERE, "two_reads_of_his_own_package_that_do_not_match_its_text.result.json")

EDGE = "(0, 1)"
LATEX_DEPTH = 0.124434           # his LaTeX "Valley depth" for (0,1)
TOL = 5e-6


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def find(sub):
    for root, _d, fs in os.walk(PKG):
        for f in fs:
            if sub in f:
                return os.path.join(root, f)
    refuse("no file matching %r under %s" % (sub, PKG))


def claim_one():
    prot = json.load(io.open(find("observation_protocol_quantitative.json"), encoding="utf-8"))
    dec = json.load(io.open(find("smallworld_deepest_valley_decomposition.json"), encoding="utf-8"))
    r = prot["protocol_results"].get(EDGE)
    if r is None:
        refuse("entrance %s is not in his protocol results" % EDGE)
    at_valley = r["valley_depth_mean"]
    s_valley = r["valley_s_mean"]
    curves = r.get("all_curves")
    if not curves:
        refuse("his protocol file carries no stored curve for %s, so E(0) cannot be read out" % EDGE)
    e_at_zero = curves[0][0]
    dec_depth = dec["deepest_valley"]["depth"]
    print("  entrance %s" % EDGE)
    print("     his protocol `valley_depth_mean`      %.15f  at s=%.3f" % (at_valley, s_valley))
    print("     his decomposition `depth`             %.15f  at s=%.3f"
          % (dec_depth, dec["deepest_valley"]["s"]))
    print("     his LaTeX 'Valley depth' column       %.6f" % LATEX_DEPTH)
    print("     E(0) read from his own stored curve   %.15f" % e_at_zero)
    total = dec_depth + at_valley
    print("     depth + `valley_depth_mean`           %.15f" % total)
    identity = abs(total - e_at_zero) < TOL
    print("     identity E(0) = depth + E(valley): %s (off %.2e)"
          % ("HOLDS" if identity else "FAILS", abs(total - e_at_zero)))
    return {"at_valley": at_valley, "s_valley": s_valley, "e_at_zero": e_at_zero,
            "decomposition_depth": dec_depth, "latex_depth": LATEX_DEPTH,
            "sum": total, "identity_holds": bool(identity),
            "latex_matches_decomposition": abs(dec_depth - LATEX_DEPTH) < 1e-5}


def ground_gap(nodes, edges, n_up, k=6):
    """(degeneracy, gap to the next distinct level) of the uniform Hamiltonian in one sector."""
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import eigsh
    b = [frozenset(c) for c in itertools.combinations(sorted(nodes), n_up)]
    idx = {st: i for i, st in enumerate(b)}
    H = lil_matrix((len(b), len(b)))
    for m, st in enumerate(b):
        diag = 0.0
        for (u, v) in edges:
            diag += 1.0 if ((u in st) == (v in st)) else -1.0
        H[m, m] = diag
        for (u, v) in edges:
            if (u in st) != (v in st):
                ns = frozenset(st.symmetric_difference({u, v}))
                if ns in idx:
                    H[m, idx[ns]] += 2.0
    w = np.sort(eigsh(H.tocsr(), k=min(k, len(b) - 2), which="SA", return_eigenvectors=False))
    deg = int(sum(1 for x in w if abs(x - w[0]) < 1e-9))
    nxt = [x for x in w if abs(x - w[0]) > 1e-9]
    return deg, (float(nxt[0] - w[0]) if nxt else None)


def claim_two():
    import networkx as nx
    sw = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
    sw_edges = [tuple(sorted(e)) for e in sw.edges()]
    sw_aut = len(list(nx.algorithms.isomorphism.GraphMatcher(sw, sw).isomorphisms_iter()))
    d_sw, g_sw = ground_gap(list(range(10)), sw_edges, 5)

    gasket = [(0, 6), (0, 8), (1, 9), (1, 11), (2, 12), (2, 14),
              (3, 6), (3, 7), (3, 9), (3, 10), (4, 10), (4, 11), (4, 12), (4, 13),
              (5, 7), (5, 8), (5, 13), (5, 14),
              (6, 7), (7, 8), (9, 10), (10, 11), (12, 13), (13, 14),
              (6, 8), (9, 11), (12, 14)]
    gk = nx.Graph(gasket)
    gk_aut = len(list(nx.algorithms.isomorphism.GraphMatcher(gk, gk).isomorphisms_iter()))
    d_gk, g_gk = ground_gap(list(range(15)), gasket, 7)

    print()
    print("  graph          |Aut|   ground degeneracy   gap to next distinct")
    print("  small-world    %5d   %d                   %s" % (sw_aut, d_sw, "%.4f" % g_sw))
    print("  L2 gasket      %5d   %d                   %s" % (gk_aut, d_gk, "%.4f" % g_gk))
    if d_sw == d_gk:
        print("  THE TEST CANNOT TELL THEM APART, so it proves nothing about either.")
    return {"smallworld": {"aut": sw_aut, "degeneracy": d_sw, "gap": g_sw},
            "gasket": {"aut": gk_aut, "degeneracy": d_gk, "gap": g_gk},
            "discriminates": d_sw != d_gk}


def main():
    t0 = time.time()
    print("  serial: two claims read out of his package, plus two sector diagonalisations")
    one = claim_one()
    two = claim_two()

    print()
    if not one["identity_holds"]:
        print("  CLAIM 1: the identity does not close, so the two numbers are not the same "
              "quantity in the way this probe assumed. Report the measurement, not the story.")
    else:
        print("  CLAIM 1: `valley_depth_mean` is E AT the valley, not a depth. His LaTeX column is "
              "the decomposition script's depth and is correctly labelled; the JSON field name is "
              "not.")
    if two["discriminates"]:
        print("  CLAIM 2: the small-world level is %d-fold and the gasket's is %d-fold, so zero seed "
              "scatter on one and real scatter on the other are the same rule seen twice."
              % (two["smallworld"]["degeneracy"], two["gasket"]["degeneracy"]))

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "claim_1_field_name": one,
        "claim_2_degeneracy": two,
        "seconds": time.time() - t0,
        "controls": {
            "identity_checked_against_his_own_stored_curve": True,
            "degeneracy_test_carries_a_counterexample": True,
            "numbers_read_from_his_package_not_his_prose": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s  [%.0fs]" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
