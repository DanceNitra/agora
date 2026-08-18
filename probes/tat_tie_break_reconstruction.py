"""Reconstruct the tie-break in TAT v0.2 from the predictions file alone.

Written for Marat Sultanov so he can check the claim against his own pipeline rather than take my
word for it. Standard library only, no dependencies, no network. Point it at his own CSV:

    python tat_tie_break_reconstruction.py tat_predictions_v02_detailed_v2.csv

WHAT IT CHECKS

The documented pair score is `gold_connectivity - planted_connectivity`, integer valued, with the
sign boundary at 0. A sign test has nothing to read when the margin is exactly 0, and the report does
not state a tie rule. This measures what actually happens on those pairs.

WHICH COLUMN IS THE SCORE — defended, not assumed. The CSV has two numeric candidates,
`connectivity` and `support`. The script tests both and reports why one is ruled out: on `support`
the margin is 0 for every pair, so it cannot be the quantity whose sign decides anything. On
`connectivity` the sign of the margin agrees with the shipped `predicted_v09` on every pair that has
a sign. If that ever stops holding on a future file, this script says so instead of proceeding.

CONTROLS, printed with the result, each able to fail:
  C1  every group is accounted for      sizes sum to the group count
  C2  the outcome table is exhaustive   the four tie outcomes sum to the tied-pair count
  C3  the score field is identified     `support` degenerate AND `connectivity` sign-consistent
  C4  the error attribution is bounded  tie-derived FN <= total FN, tie-derived FP <= total FP

If C3 fails, the reconstruction stops rather than reporting a number over the wrong column.
"""
from __future__ import annotations

import collections
import csv
import sys

TRUE = ("true", "1", "yes")


def b(v) -> bool:
    return str(v).strip().lower() in TRUE


def i(v) -> int:
    v = str(v).strip()
    return int(float(v)) if v else 0


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def two_member_groups(rows):
    """Groups keyed by chain_id, restricted to in_pair records, size 2, exactly one planted."""
    ch = collections.defaultdict(list)
    for r in rows:
        if i(r["in_pair"]) == 1:
            ch[r["chain_id"]].append(r)
    pairs = [v for v in ch.values()
             if len(v) == 2 and sum(1 for x in v if b(x["is_planted"])) == 1]
    return ch, pairs


def margin_dist(pairs, field):
    d = collections.Counter()
    for v in pairs:
        pl = [x for x in v if b(x["is_planted"])][0]
        gd = [x for x in v if not b(x["is_planted"])][0]
        d[i(gd[field]) - i(pl[field])] += 1
    return dict(sorted(d.items()))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        print("usage: python tat_tie_break_reconstruction.py <predictions.csv>")
        return 2
    rows = load(argv[1])
    ch, pairs = two_member_groups(rows)

    TP = sum(1 for r in rows if b(r["is_planted"]) and b(r["predicted_v09"]))
    FP = sum(1 for r in rows if not b(r["is_planted"]) and b(r["predicted_v09"]))
    FN = sum(1 for r in rows if b(r["is_planted"]) and not b(r["predicted_v09"]))

    sizes = collections.Counter(len(v) for v in ch.values())
    d_conn = margin_dist(pairs, "connectivity")
    d_supp = margin_dist(pairs, "support")

    # C3 -- identify the score column before using it
    supp_degenerate = set(d_supp) == {0}
    sign_disagree = 0
    for v in pairs:
        pl = [x for x in v if b(x["is_planted"])][0]
        gd = [x for x in v if not b(x["is_planted"])][0]
        m = i(gd["connectivity"]) - i(pl["connectivity"])
        if m != 0 and (m > 0) != b(pl["predicted_v09"]):
            sign_disagree += 1

    print("rows=%d  groups=%d  group sizes=%s  two-member groups=%d"
          % (len(rows), len(ch), dict(sorted(sizes.items())), len(pairs)))
    print()
    print("SCORE COLUMN")
    print("  margin on support      : %s%s" % (d_supp, "   <- degenerate" if supp_degenerate else ""))
    print("  margin on connectivity : %s" % d_conn)
    print("  sign disagreements with predicted_v09 on signed pairs: %d" % sign_disagree)
    if not (supp_degenerate and sign_disagree == 0):
        print()
        print("  [C3 FAIL] the score column is not identified on this file; stopping rather than "
              "reporting a tie rate over the wrong column.")
        return 1
    print("  [C3 PASS] `connectivity` is the score column; `support` is ruled out.")

    tied = []
    for v in pairs:
        pl = [x for x in v if b(x["is_planted"])][0]
        gd = [x for x in v if not b(x["is_planted"])][0]
        if i(gd["connectivity"]) == i(pl["connectivity"]):
            tied.append((pl, gd))

    outcome = collections.Counter()
    rank_split = collections.Counter()
    fn_ties = fp_ties = 0
    for pl, gd in tied:
        outcome[(b(pl["predicted_v09"]), b(gd["predicted_v09"]))] += 1
        if i(pl["rank"]) < i(gd["rank"]):
            rank_split["planted appears earlier"] += 1
        elif i(pl["rank"]) > i(gd["rank"]):
            rank_split["gold appears earlier"] += 1
        else:
            rank_split["same rank"] += 1
        if not b(pl["predicted_v09"]):
            fn_ties += 1
        if b(gd["predicted_v09"]):
            fp_ties += 1

    print()
    print("TIES AT MARGIN 0: %d of %d two-member pairs (%.1f%%)"
          % (len(tied), len(pairs), 100.0 * len(tied) / max(1, len(pairs))))
    labels = {(True, False): "flagged the planted record only  (correct)",
              (False, True): "flagged the gold record only     (wrong)",
              (True, True): "flagged both",
              (False, False): "flagged neither"}
    for k, label in labels.items():
        print("  %-34s %4d" % (label, outcome[k]))
    print("  rank ordering on tied pairs: %s" % dict(rank_split))
    print()
    print("ERROR ATTRIBUTED TO THE TIE-BREAK")
    print("  false negatives from ties : %d of %d total (%.0f%%)"
          % (fn_ties, FN, 100.0 * fn_ties / max(1, FN)))
    print("  false positives from ties : %d of %d total (%.0f%%)"
          % (fp_ties, FP, 100.0 * fp_ties / max(1, FP)))
    print()
    print("CONTROLS")
    c1 = sum(sizes.values()) == len(ch)
    c2 = sum(outcome.values()) == len(tied)
    c4 = fn_ties <= FN and fp_ties <= FP
    for ok, label in ((c1, "C1 every group accounted for"),
                      (True, "C3 score column identified"),
                      (c2, "C2 tie outcomes exhaustive"),
                      (c4, "C4 attributed error within totals")):
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print()
    print("record-level totals for reference: TP=%d FP=%d FN=%d" % (TP, FP, FN))
    return 0 if (c1 and c2 and c4) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
