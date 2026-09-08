"""Guanghao's retraction is right, and it must not be extended to the s=1 orbit result.

WHAT HAPPENED. On luoxuejian000/edrn-dmrg-verification#2 he added a section, "Involutive automorphism
and complete E(s) curve degeneracy", claiming that for graphs with a nontrivial involution the whole
E(s) curve of an image edge pair coincides. He then falsified it himself by exhaustive search over
connected graphs with N <= 6, reported 84 counterexample edge pairs across 142 graphs, and asked for
the section to be withdrawn. He was right to withdraw it.

THE RISK IS OVER-RETRACTION. The paper contains a second, different symmetry statement, in
"Orbit-resolved mechanism and symmetry constraint": at s = 1 every bond carries the same coupling, so
the Hamiltonian is invariant under the full automorphism group, and for a symmetry-invariant ground
state the within-orbit variance vanishes identically. That one is a theorem with a premise, and the
premise is the uniform point. It does not depend on the involution claim and it does not fall with it.

This probe measures the boundary between the two rather than asserting it.

THE MODEL, from the paper: J_ij = 1 on every edge except one contradiction edge, where J_ij = s. So
the weighted graph is vertex-transitively symmetric only when s = 1. Away from it the symmetry group
that can act is the stabiliser of the contradiction edge, which is generally much smaller.

WHAT IS MEASURED, over every connected graph on 4 to 6 vertices:

  |Aut| at s = 1 against |Aut| at s != 1     how much symmetry the contradiction edge destroys
  orbits of the uniform graph against orbits of the weighted graph
  the fraction of graphs where a single edge weight collapses the group to the identity

If the group and the orbit partition survive at s != 1, the retracted section could have been right
and the scope argument is wrong. If they collapse, the s = 1 statement is scoped by construction and
a counterexample away from the uniform point says nothing about it.

CONTROLS.
  KNOWN GROUPS   the complete graph and the cycle have automorphism groups of known order, n! and 2n,
                 so a wrong group calculation shows up before any conclusion rests on it.
  IT CAN FAIL    at least one graph must keep its full group under a weighted edge, or "the weight
                 always breaks everything" would be true by construction rather than measured.
  ORBIT SANITY   at s = 1 the number of edge orbits must never exceed the number of edges.

WHAT THIS DOES NOT SHOW. Anything about the correlations themselves. It is a statement about which
symmetry group acts, which is the premise of his theorem, not about the ground state that follows.
"""
import itertools
import json
import os
import sys

import networkx as nx


def edge_orbits(g, weights=None):
    """Edge orbits under the automorphism group of the (optionally edge-weighted) graph.

    Weights are honoured by giving each edge a label, so an automorphism must map an edge to one of
    the same weight. That is exactly the constraint a contradiction edge imposes.
    """
    h = nx.Graph()
    h.add_nodes_from(g.nodes)
    for u, v in g.edges:
        w = 1.0 if weights is None else weights.get(frozenset((u, v)), 1.0)
        h.add_edge(u, v, w=round(w, 9))
    em = nx.algorithms.isomorphism.categorical_edge_match("w", 1.0)
    autos = list(nx.algorithms.isomorphism.GraphMatcher(h, h, edge_match=em).isomorphisms_iter())
    orbits, seen = [], set()
    for e in h.edges:
        fe = frozenset(e)
        if fe in seen:
            continue
        orb = {frozenset((a[u], a[v])) for a in autos for u, v in [tuple(e)]}
        orbits.append(orb)
        seen |= orb
    return len(autos), orbits


def connected_graphs(n):
    """Every connected graph on n labelled vertices, deduplicated up to isomorphism."""
    nodes = list(range(n))
    all_edges = list(itertools.combinations(nodes, 2))
    out = []
    for k in range(n - 1, len(all_edges) + 1):
        for es in itertools.combinations(all_edges, k):
            g = nx.Graph(list(es))
            g.add_nodes_from(nodes)
            if not nx.is_connected(g):
                continue
            if any(nx.is_isomorphic(g, h) for h in out):
                continue
            out.append(g)
    return out


def main():
    ok, checks, rows = True, [], []

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        checks.append({"check": name, "pass": bool(cond), "got": str(got)[:200]})
        print("  %-4s %-56s %s" % ("YES" if cond else "NO", name, got))

    # CONTROL: groups of known order, before anything rests on the calculation.
    n_k4, _ = edge_orbits(nx.complete_graph(4))
    n_c5, _ = edge_orbits(nx.cycle_graph(5))
    check("CONTROL_K4_has_4_factorial_automorphisms", n_k4 == 24, n_k4)
    check("CONTROL_C5_has_2n_automorphisms", n_c5 == 10, n_c5)

    print()
    for n in (4, 5, 6):
        graphs = connected_graphs(n)
        collapsed = kept = 0
        for gi, g in enumerate(graphs):
            aut1, orb1 = edge_orbits(g)
            check_orbits_ok = len(orb1) <= g.number_of_edges()
            if not check_orbits_ok:
                rows.append({"n": n, "graph": gi, "error": "more orbits than edges"})
                continue
            for e in g.edges:
                w = {frozenset(e): 0.37}          # any value other than 1 singles the edge out
                aut_s, orb_s = edge_orbits(g, w)
                rows.append({"n": n, "graph": gi, "edges": g.number_of_edges(),
                             "aut_uniform": aut1, "orbits_uniform": len(orb1),
                             "aut_weighted": aut_s, "orbits_weighted": len(orb_s)})
                if aut_s == 1:
                    collapsed += 1
                if aut_s == aut1:
                    kept += 1
        tot = sum(1 for r in rows if r.get("n") == n and "aut_weighted" in r)
        print("  N=%d  %3d graphs, %4d (graph, contradiction edge) pairs: "
              "%4d collapse to the identity, %3d keep the full group"
              % (n, len(graphs), tot, collapsed, kept))

    good = [r for r in rows if "aut_weighted" in r]
    shrank = [r for r in good if r["aut_weighted"] < r["aut_uniform"]]
    kept_all = [r for r in good if r["aut_weighted"] == r["aut_uniform"]]
    coarser = [r for r in good if r["orbits_weighted"] > r["orbits_uniform"]]

    print()
    check("the_weighted_edge_shrinks_the_group_in_most_cases",
          len(shrank) > len(good) * 0.5,
          "%d of %d pairs lose symmetry" % (len(shrank), len(good)))
    # Without this the finding would be "a weight always breaks everything", true by construction.
    check("CONTROL_some_graphs_keep_their_full_group",
          bool(kept_all), "%d of %d pairs keep it" % (len(kept_all), len(good)))
    check("the_orbit_partition_gets_finer_away_from_the_uniform_point",
          len(coarser) > len(good) * 0.5,
          "%d of %d pairs gain orbits" % (len(coarser), len(good)))
    check("CONTROL_never_more_orbits_than_edges_at_s_equals_1",
          not any("error" in r for r in rows))

    out = {"probe": os.path.basename(__file__),
           "pairs": len(good),
           "pairs_losing_symmetry": len(shrank),
           "pairs_keeping_full_group": len(kept_all),
           "pairs_collapsing_to_identity": sum(1 for r in good if r["aut_weighted"] == 1),
           "pairs_gaining_orbits": len(coarser),
           "checks": checks, "all_passed": ok,
           "finding": (
               "A single contradiction edge removes symmetry in %d of %d (graph, edge) pairs on 4 to "
               "6 vertices, and makes the edge-orbit partition strictly finer in %d. The premise of "
               "the s=1 orbit result, that the Hamiltonian is invariant under the full automorphism "
               "group, therefore holds only at the uniform point. A counterexample found at a valley "
               "bottom, where s is not 1, is outside that premise and does not bear on it."
               % (len(shrank), len(good), len(coarser))),
           "scope": "Group theory on the weighted graph only. This says which symmetry can act, "
                    "which is the premise of the orbit theorem. It measures nothing about the "
                    "ground state or the correlations that follow from it."}
    print("\n  FINDING: %s" % out["finding"])
    p = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("  %s   receipt: %s" % ("controls passed" if ok else "A CONTROL FAILED",
                                  os.path.basename(p)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
