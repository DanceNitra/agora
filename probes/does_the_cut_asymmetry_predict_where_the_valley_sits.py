"""Guanghao says the valley sits where it does because the entry edge cuts the graph asymmetrically.
That is a testable claim, so this tests it rather than repeating it.

WHY IT MATTERS. A physicist he consulted objected that the mechanism is incomplete: nothing in the
paper explains why the tree valley is at s=1.70 rather than 1.0. Guanghao's answer is that the
position is a marker of relational structure, because the entry edge splits the tree into two
asymmetric subnetworks. As prose that is a boundary statement. As a claim it predicts something
specific and checkable: the valley POSITION should be a function of how asymmetric the cut is, and
the paper already contains fourteen cuts of the same tree with their positions measured.

WHAT IS TESTED. For each edge of the N=15 tree, remove it, and describe the two components by
quantities that need no diagonalisation:

  * the size imbalance |n_A - n_B|;
  * the Lieb-Mattis ground spins S = |n_1 - n_2| / 2 from the sublattice sizes, which a tree always
    has because a tree is bipartite;
  * their sum and difference.

Each is ranked against the measured valley position s*. Spearman, with an EXACT permutation p-value,
because thirteen points is small enough that a correlation coefficient alone means very little.

THE CONTROLS, because a correlation on thirteen points is easy to fool:
  * the tree this reconstructs must be the tree the data came from, asserted edge by edge against the
    scan file rather than assumed from the generator name;
  * the degeneracy criterion must reproduce the census already sent to Guanghao (four of fourteen
    edges degenerate at |S_z| = 1/2), or the component machinery here is not the machinery that was
    published;
  * a NEGATIVE control that must NOT correlate: the sum of the two endpoint labels, which carries no
    structure at all. If that ranks as well as the structural quantities, thirteen points cannot
    separate anything and every verdict below is void.

WHAT A NULL WOULD MEAN. If no structural quantity ranks with the position, Guanghao's explanation is
not supported by his own fourteen cuts, and the honest move is to put the question in the paper as
open rather than answer it with a phrase.

WHAT ACTUALLY HAPPENED, recorded here because the first run said the opposite. `spin_sum` ranked at
rho -0.738, p 0.0035, and the negative control did not, so the probe printed SUPPORTED. It takes
exactly two values across the thirteen cuts: 0.5 on every edge with a unique s=0 reference and 1.5
on every edge without one. It is the degeneracy flag wearing a structural name, the rho is a
two-group difference, and within the ten non-degenerate edges the quantity has no variance at all.
A feature constant inside the non-degenerate group is now disqualified explicitly, because the run
that produced the flattering number was the run that ran first.
"""
import itertools
import json
import math
import os
import re
import sys

try:
    import networkx as nx
except ImportError:                                              # noqa: BLE001
    print("networkx is required")
    raise SystemExit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN = os.path.join(
    os.path.dirname(HERE), "agora_output", "edrn_submission", "guanghao_archive_2026-09-03",
    "树形图和随机图需要修改问题的解答",
    "生成论文表II所需的树图和随机图完整数据",
    "=== tree N=15, 14 edges, s∈[0.0, 3实验数据.txt")

EDGE_LINE = re.compile(r"Edge \((\d+), (\d+)\): s=([\d.]+|None), depth=([\d.]+|None)")


def read_scan():
    """The measured valley position for each tree edge, from the file the paper's table came from."""
    rows = []
    with open(SCAN, encoding="utf-8") as fh:
        for line in fh:
            if line.strip().startswith("=== random"):
                break                                            # the tree block ends here
            m = EDGE_LINE.search(line)
            if m:
                a, b, s, d = m.groups()
                rows.append({"edge": (int(a), int(b)),
                             "s": None if s == "None" else float(s),
                             "depth": None if d == "None" else float(d)})
    return rows


def bipartite_halves(g):
    """A tree is bipartite, so two-colour it and return the two sublattice sizes."""
    colour = nx.algorithms.bipartite.color(g)
    n1 = sum(1 for v in colour.values() if v == 0)
    return n1, g.number_of_nodes() - n1


def lieb_mattis_spin(g):
    """S = |n_1 - n_2| / 2 for a bipartite component, no diagonalisation needed."""
    n1, n2 = bipartite_halves(g)
    return abs(n1 - n2) / 2.0


def reference_is_degenerate(g, edge, total_sz=0.5):
    """The criterion sent to Guanghao: more than one way to write S_z as m_A + m_B."""
    h = g.copy()
    h.remove_edge(*edge)
    comps = [h.subgraph(c).copy() for c in nx.connected_components(h)]
    if len(comps) != 2:
        return None                                              # the edge is not a bridge
    sa, sb = (lieb_mattis_spin(c) for c in comps)
    ways = 0
    ma = -sa
    while ma <= sa + 1e-9:
        mb = total_sz - ma
        if abs(mb) <= sb + 1e-9 and abs((mb - (-sb)) % 1.0) < 1e-9:
            ways += 1
        ma += 1.0
    return ways > 1


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return 0.0 if den == 0 else num / den


def exact_p(xs, ys, rho, cap=200000):
    """Two-sided permutation p. Exact while the permutations fit, sampled beyond that."""
    n = len(xs)
    if math.factorial(n) <= cap:
        perms = itertools.permutations(ys)
        total, hits = 0, 0
        for p in perms:
            total += 1
            if abs(spearman(xs, list(p))) >= abs(rho) - 1e-12:
                hits += 1
        return hits / total, total, True
    import random
    rng = random.Random(20260907)
    ys2, hits = list(ys), 0
    for _ in range(cap):
        rng.shuffle(ys2)
        if abs(spearman(xs, ys2)) >= abs(rho) - 1e-12:
            hits += 1
    return hits / cap, cap, False


def main():
    if not os.path.exists(SCAN):
        print("the scan file is not here, so there is nothing to test against:\n  %s" % SCAN)
        return 2

    rows = read_scan()
    g = nx.random_labeled_tree(15, seed=42)

    # CONTROL: the reconstructed tree must be the tree the numbers came from.
    scanned = {tuple(sorted(r["edge"])) for r in rows}
    built = {tuple(sorted(e)) for e in g.edges()}
    if scanned != built:
        print("the generator does not reproduce the scanned tree, so nothing below is about the "
              "same object.\n  only in the scan: %s\n  only in the graph: %s"
              % (sorted(scanned - built), sorted(built - scanned)))
        return 1
    print("  control: the generator reproduces all %d scanned edges" % len(built))

    # CONTROL: the degeneracy criterion must reproduce the published census.
    degenerate = [r["edge"] for r in rows if reference_is_degenerate(g, r["edge"])]
    print("  control: the criterion calls %d of %d edges degenerate at |S_z| = 1/2  -> %s"
          % (len(degenerate), len(rows), degenerate))

    usable = [r for r in rows if r["s"] is not None]
    print("  %d of %d edges have a measured valley position\n" % (len(usable), len(rows)))

    feats = {}
    for r in usable:
        h = g.copy()
        h.remove_edge(*r["edge"])
        ca, cb = (h.subgraph(c).copy() for c in nx.connected_components(h))
        na, nb = ca.number_of_nodes(), cb.number_of_nodes()
        sa, sb = lieb_mattis_spin(ca), lieb_mattis_spin(cb)
        r["size_imbalance"] = abs(na - nb)
        r["spin_sum"] = sa + sb
        r["spin_difference"] = abs(sa - sb)
        r["smaller_side"] = min(na, nb)
        r["endpoint_label_sum"] = r["edge"][0] + r["edge"][1]     # the negative control

    names = ["size_imbalance", "spin_sum", "spin_difference", "smaller_side",
             "endpoint_label_sum"]
    ys = [r["s"] for r in usable]
    out = {"n_edges_with_a_valley": len(usable), "positions": ys, "features": {}}
    print("  %-22s %8s %10s %s" % ("quantity", "rho", "p", ""))
    for nm in names:
        xs = [r[nm] for r in usable]
        rho = spearman(xs, ys)
        p, tried, is_exact = exact_p(xs, ys, rho)
        tag = "  <- NEGATIVE CONTROL, must not rank" if nm == "endpoint_label_sum" else ""
        print("  %-22s %8.3f %10.4f%s" % (nm, rho, p, tag))
        out["features"][nm] = {"spearman": round(rho, 4), "p": round(p, 5),
                               "permutations": tried, "exact": is_exact,
                               "values": xs}

    # 1. MULTIPLE COMPARISONS. Four structural quantities were ranked before one was reported.
    n_structural = len(names) - 1
    for nm in names:
        out["features"][nm]["p_bonferroni"] = min(1.0, out["features"][nm]["p"] * n_structural)

    # 2. WITHOUT THE DEGENERATE EDGES. Their depth is unreliable by our own published finding; if
    #    the position result needs them, it is a result about the artefact rather than the cut.
    deg = {tuple(sorted(e)) for e in degenerate}
    clean = [r for r in usable if tuple(sorted(r["edge"])) not in deg]
    print()
    print("  dropping the %d edges with a degenerate reference leaves %d:" % (len(deg), len(clean)))
    out["without_degenerate_edges"] = {"n": len(clean), "features": {}}
    if len(clean) >= 5:
        ys2 = [r["s"] for r in clean]
        for nm in names:
            xs2 = [r[nm] for r in clean]
            rho2 = spearman(xs2, ys2)
            p2, tried2, exact2 = exact_p(xs2, ys2, rho2)
            print("    %-22s %8.3f %10.4f" % (nm, rho2, p2))
            out["without_degenerate_edges"]["features"][nm] = {
                "spearman": round(rho2, 4), "p": round(p2, 5), "exact": exact2}
    else:
        print("    too few edges remain to rank anything")

    # 3. COLLINEARITY. Rank `spin_sum` against the position with the size imbalance held fixed.
    def _rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    def _pearson(a, b):
        n = len(a)
        ma, mb = sum(a) / n, sum(b) / n
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
        return 0.0 if den == 0 else num / den

    r_xy = spearman([r["spin_sum"] for r in usable], ys)
    r_xz = spearman([r["spin_sum"] for r in usable], [r["size_imbalance"] for r in usable])
    r_yz = spearman(ys, [r["size_imbalance"] for r in usable])
    denom = math.sqrt(max(1e-12, (1 - r_xz ** 2) * (1 - r_yz ** 2)))
    partial = (r_xy - r_xz * r_yz) / denom
    print()
    print("  spin_sum against the position with size_imbalance held fixed: partial rho %.3f "
          "(spin_sum and size_imbalance themselves rank at %.3f)" % (partial, r_xz))
    out["partial_spin_sum_given_size"] = {"partial_rho": round(partial, 4),
                                          "spin_vs_size_rho": round(r_xz, 4)}

    out["scope"] = ("thirteen cuts of ONE tree, in sample. This is a lead strong enough to justify "
                    "a confirming measurement on a graph whose positions have not been seen, not a "
                    "law. The confirming test is to predict positions from the sublattice counts "
                    "alone and then measure them.")

    ctrl = out["features"]["endpoint_label_sum"]

    # A FEATURE CONSTANT WITHIN THE NON-DEGENERATE GROUP IS THE GROUP FLAG, NOT A PREDICTOR. This is
    # the check that changed the verdict: `spin_sum` is 0.5 on all ten edges with a unique reference
    # and 1.5 on the three without one, so its rho is a two-group difference and the "asymmetry of
    # the cut" never enters. Reporting the pre-check number would have made this probe agree with the
    # claim it was written to test.
    disqualified = {}
    for nm in names:
        if nm == "endpoint_label_sum":
            continue
        vals = {r[nm] for r in clean}
        if len(vals) <= 1:
            disqualified[nm] = sorted(vals)
    out["disqualified_as_group_indicator"] = disqualified
    if disqualified:
        print()
        for nm, vals in disqualified.items():
            print("  %s is CONSTANT (%s) across every edge with a unique reference, so it is the "
                  "degeneracy flag under another name and cannot speak about the cut." % (nm, vals))

    structural = {k: v for k, v in out["features"].items()
                  if k != "endpoint_label_sum" and k not in disqualified}
    best = (max(structural.items(), key=lambda kv: abs(kv[1]["spearman"]))
            if structural else (None, {"spearman": 0.0, "p": 1.0}))

    # The finding that survives: WHERE the degenerate-reference edges sit among the positions.
    deg_pos = sorted(r["s"] for r in usable if tuple(sorted(r["edge"])) in deg)
    oth_pos = sorted(r["s"] for r in usable if tuple(sorted(r["edge"])) not in deg)
    k, n = len(deg_pos), len(usable)
    all_below = bool(deg_pos and oth_pos and max(deg_pos) < min(oth_pos))
    extreme_p = (2.0 / math.comb(n, k)) if all_below else None
    out["degenerate_edges_sit_lowest"] = {
        "degenerate_positions": deg_pos, "other_positions": oth_pos,
        "all_below_every_other": all_below, "two_sided_p_if_all_below": extreme_p}

    # AND IT MUST SURVIVE THE EDGES WE TRUST. size_imbalance is not constant within the clean group,
    # so the check above lets it through -- and its p goes from 0.037 on all thirteen to 0.496 on the
    # ten with a unique reference. A quantity whose significance lives entirely in the three rows we
    # have already called unreliable has not predicted anything about the cut.
    cleanf = out.get("without_degenerate_edges", {}).get("features", {})
    survives = bool(best[0] is not None and cleanf.get(best[0], {}).get("p", 1.0) < 0.05)
    out["verdict"] = {
        "cut_asymmetry_predicts_position": bool(
            best[0] is not None and best[1]["p"] < 0.05 and ctrl["p"] >= 0.05 and survives),
        "survives_dropping_the_degenerate_edges": survives,
        "p_on_the_clean_subset": cleanf.get(best[0], {}).get("p"),
        "best_structural": best[0], "best_rho": best[1]["spearman"], "best_p": best[1]["p"],
        "negative_control_p": ctrl["p"],
        "what_the_ranking_was_carrying": sorted(disqualified) or None,
    }

    print()
    if out["verdict"]["cut_asymmetry_predicts_position"]:
        print("  SUPPORTED: %s ranks with the valley position (rho %.3f, p %.4f) and is not constant "
              "within the non-degenerate group, while the negative control does not rank (p %.4f)."
              % (best[0], best[1]["spearman"], best[1]["p"], ctrl["p"]))
    else:
        print("  NOT SUPPORTED. Once the quantity that is merely the degeneracy flag is set aside, "
              "the best remaining structural quantity is %s at rho %.3f, p %.4f on all thirteen "
              "cuts -- and p %s on the ten whose reference is unique. Its significance lives in the "
              "three rows we have already called unreliable, so the asymmetry of the cut has not "
              "predicted where the valley sits."
              % (best[0], best[1]["spearman"], best[1]["p"],
                 out["verdict"].get("p_on_the_clean_subset")))
        print("  That is an answer rather than a failure: the position belongs in the paper as an "
              "open question, not as an explanation.")

    if all_below:
        print()
        print("  AND A SEPARATE FINDING, about the measurement rather than the cut: the %d edges "
              "with a degenerate s=0 reference hold the %d LOWEST positions of %d, at %s against "
              "%s for the rest. That is the most extreme arrangement available, two-sided p %.4f."
              % (k, k, n, deg_pos, [oth_pos[0], oth_pos[-1]], extreme_p))
        print("  The degeneracy was reported to affect the DEPTH. These positions sit against the "
              "reference point itself, so the same three rows need a dense re-scan before the table "
              "ships; the paper currently treats their positions as measured.")

    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("  receipt: %s" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
