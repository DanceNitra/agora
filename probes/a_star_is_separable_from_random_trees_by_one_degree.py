"""Is the star/random-tree label recoverable from one degree, exactly, without a classifier?

WHY. Marat Sultanov reports a learned TAT classifier at 1.000 +/- 0.000 on 5-fold CV at N = 7, 8 and
9, with his own shuffled-label control at chance. That control rules out the failure it is built for:
it shows the features carry signal. It does not show WHERE the signal is. If the label is recoverable
from the graph alone, any feature set touching connectivity returns the same score, and a size sweep
makes that MORE reliable rather than less.

This measures the premise instead of arguing it, and it does so EXACTLY. A tree on N nodes has N-1
edges, so a vertex of degree N-1 is adjacent to every other vertex and the tree IS the star. By
Cayley's formula there are N labelled stars among N^(N-2) labelled trees, so the probability that a
uniformly random labelled tree reaches the star's maximum degree is exactly N^(3-N).

AN EARLIER VERSION OF THIS PROBE SAMPLED 2000 TREES PER SIZE AND REPORTED "0 of 2000". That figure
reproduces in 17 of 40 disjoint seed blocks at N=7, so it was a 43 percent event reported as a fact.
The exact form needs no seed, no sampler and no NetworkX version. The sampled table and the Cayley
sentence were also the same quantity twice, presented as if they corroborated each other.

CONTROLS, because a measurement that can only report separation has measured nothing:
  * ENUMERATION. Every Prufer sequence at N = 5..8 is enumerated. Under the Prufer bijection a
    vertex's degree is one more than its multiplicity in the sequence, so max degree N-1 means a
    constant sequence. The count must equal N and the total must equal N^(N-2), at every size. If
    either disagrees the arithmetic is wrong and the probe refuses.
  * A DECODE BRIDGE. The multiplicity rule is checked against real graphs: sequences are decoded with
    NetworkX and the degree sequences compared element by element. This is what connects the
    arithmetic to the object Marat classifies. Without it the enumeration is numerology.
  * A NEGATIVE ARM. The same one-threshold rule is pointed at two disjoint samples of the SAME
    population, where no separation exists. If it separates them, the method is broken.
  * A POSITIVE CONTROL ON THE NEGATIVE ARM. The identical code is pointed at star-versus-random, where
    it MUST separate. A negative arm that cannot fire has measured nothing.
  * THE ALTERNATIVE POPULATION. Every figure here assumes the negatives are uniformly random LABELLED
    trees. The non-isomorphic case is computed alongside rather than argued away, because it moves the
    star fraction by 218x to 11,307x and reverses the conclusion.
"""
from __future__ import annotations

import collections
import io
import itertools
import json
import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "a_star_is_separable_from_random_trees_by_one_degree.result.json")

SIZES = (7, 8, 9)
ENUMERATE_UP_TO = 8          # 5..8 is 280,372 sequences; 9 would be 4.8M for no extra information
HIS_DESIGN_NEGATIVES = 50    # Marat's reported design: 50 stars + 50 random trees, 5-fold CV
SAMPLE_TRIALS = 2000         # for the CONTROLS only; no published figure comes from a sample
NULL_REFUSE_ABOVE = 0.62


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def best_threshold_accuracy(pos, neg, n_max):
    """Accuracy of the best single threshold on max degree, either polarity."""
    best = 0.0
    for thr in range(2, n_max + 1):
        acc = (sum(1 for x in pos if x >= thr) + sum(1 for x in neg if x < thr)) / \
              float(len(pos) + len(neg))
        best = max(best, acc, 1.0 - acc)
    return best


def enumerate_prufer(N):
    """Full enumeration. Returns (total, stars, max_degree_histogram)."""
    hist = collections.Counter()
    counts = [0] * N
    total = 0
    for seq in itertools.product(range(N), repeat=N - 2):
        for x in seq:
            counts[x] += 1
        hist[max(counts) + 1] += 1
        for x in seq:
            counts[x] -= 1
        total += 1
    return total, hist[N - 1], dict(sorted(hist.items()))


def main() -> int:
    import networkx as nx
    from networkx.generators.nonisomorphic_trees import nonisomorphic_trees

    if not hasattr(nx, "random_labeled_tree"):
        refuse("networkx %s has no random_labeled_tree; the controls cannot run" % nx.__version__)

    t0 = time.time()

    # CONTROL 1: enumeration must reproduce Cayley and the constant-sequence identity.
    enumerated = {}
    for N in range(5, ENUMERATE_UP_TO + 1):
        total, stars, hist = enumerate_prufer(N)
        if total != N ** (N - 2):
            refuse("enumeration at N=%d counted %d trees, Cayley says %d" % (N, total, N ** (N - 2)))
        if stars != N:
            refuse("enumeration at N=%d found %d trees of max degree %d, there must be exactly %d"
                   % (N, stars, N - 1, N))
        enumerated[N] = {"trees": total, "max_degree_histogram": hist}
        print("  enumerated N=%d: %d trees, %d of max degree %d  [%.1fs]"
              % (N, total, stars, N - 1, time.time() - t0))

    # CONTROL 2: the multiplicity rule is a statement about graphs, so decode and compare.
    bridge = 0
    for N in range(5, ENUMERATE_UP_TO + 1):
        for seq in itertools.islice(itertools.product(range(N), repeat=N - 2), 0, None, 97):
            g = nx.from_prufer_sequence(list(seq))
            want = sorted(1 + collections.Counter(seq)[v] for v in range(N))
            got = sorted(d for _, d in g.degree())
            if want != got:
                refuse("the Prufer multiplicity rule disagrees with the decoded graph at N=%d, "
                       "sequence %r: %r vs %r" % (N, seq, want, got))
            bridge += 1
    print("  decode bridge: %d sequences decoded, degree sequences identical" % bridge)

    rows = []
    for N in SIZES:
        star_deg = N - 1
        total = N ** (N - 2)
        p_star = float(N) / total                       # == N ** (3 - N)
        p_no_star_in_his_draw = (1.0 - p_star) ** HIS_DESIGN_NEGATIVES

        # THE POPULATION IS AN ASSUMPTION, so measure the alternative rather than assume it away.
        # If the negatives are non-isomorphic trees instead of labelled ones, the star is far commoner
        # and the same shortcut stops being reliable. That difference is what makes the question
        # answerable by asking him one thing.
        n_iso = sum(1 for _ in nonisomorphic_trees(N))
        p_star_iso = 1.0 / n_iso
        p_no_star_iso = (1.0 - p_star_iso) ** HIS_DESIGN_NEGATIVES

        # CONTROL 3: the negative arm. Two disjoint draws from ONE population must not separate.
        a = [max(d for _, d in nx.random_labeled_tree(N, seed=s).degree())
             for s in range(SAMPLE_TRIALS)]
        b = [max(d for _, d in nx.random_labeled_tree(N, seed=SAMPLE_TRIALS + s).degree())
             for s in range(SAMPLE_TRIALS)]
        null_acc = best_threshold_accuracy(a, b, N)
        if null_acc > NULL_REFUSE_ABOVE:
            refuse("the negative arm separates two samples of the SAME population at %.3f, so a "
                   "perfect score in the positive arm would say nothing" % null_acc)

        # CONTROL 4: the same code, pointed where it MUST separate.
        stars = [star_deg] * SAMPLE_TRIALS
        pos_acc = best_threshold_accuracy(stars, a, N)
        if pos_acc <= NULL_REFUSE_ABOVE:
            refuse("the positive control failed: star-versus-random scored only %.3f, so the "
                   "negative arm's refusal bound is untested and means nothing" % pos_acc)

        rows.append({
            "N": N,
            "star_max_degree": star_deg,
            "labelled_trees": total,
            "labelled_stars": N,
            "exact_p_random_tree_reaches_star_degree": p_star,
            "exact_p_as_one_in": round(1.0 / p_star),
            "exact_star_percent": round(100.0 * p_star, 4),
            "exact_p_perfect_at_his_design": round(p_no_star_in_his_draw, 6),
            "non_isomorphic_trees": n_iso,
            "exact_p_perfect_at_his_design_if_non_isomorphic": round(p_no_star_iso, 4),
            "his_design_negatives": HIS_DESIGN_NEGATIVES,
            "control_negative_arm_accuracy": round(null_acc, 4),
            "control_positive_arm_accuracy": round(pos_acc, 4),
        })
        print("  N=%d  star degree %d | a random labelled tree is a star 1 in %d (%.4f%%) | "
              "a %d-negative draw is star-free %.4f of the time | null arm %.3f, positive control %.3f"
              % (N, star_deg, round(1.0 / p_star), 100.0 * p_star, HIS_DESIGN_NEGATIVES,
                 p_no_star_in_his_draw, null_acc, pos_acc))
        print("        if the negatives were non-isomorphic trees instead: %d of them, star-free "
              "draw only %.4f of the time" % (n_iso, p_no_star_iso))

    json.dump({"probe": os.path.basename(__file__),
               "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "networkx": nx.__version__,
               "python": sys.version.split()[0],
               "elapsed_s": round(time.time() - t0, 1),
               "rows": rows,
               "enumeration": enumerated,
               "controls": {
                   "enumeration_reproduces_cayley_and_the_star_count": True,
                   "prufer_multiplicity_rule_checked_against_decoded_graphs": bridge,
                   "negative_arm_cannot_separate_one_population": True,
                   "positive_control_proves_the_negative_arm_can_fire": True,
                   "no_published_figure_comes_from_a_sample": True,
                   "the_alternative_population_is_measured_not_assumed_away": True,
               }},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
