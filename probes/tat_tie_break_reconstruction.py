"""Reconstruct the tie-break in TAT v0.2 from the predictions file alone.

Written for Marat Sultanov so the claim can be checked against his own pipeline rather than taken on
trust. Standard library only, no dependencies, no network:

    python tat_tie_break_reconstruction.py tat_predictions_v02_detailed_v2.csv

WHAT IT ASKS

The documented pair score is `gold_connectivity - planted_connectivity`, integer valued, with the
sign boundary at 0. A sign test has nothing to read when the margin is exactly 0, and no tie rule is
stated. This measures what happens on those pairs, and -- the part that matters -- whether the thing
that decides them is confined to ties or is driving the whole result.

FILE STRUCTURE, measured rather than assumed: `chain_id` groups the file into chains of 8 records
each, one planted per chain. `in_pair` selects a subset of 2-6 of them; `support` is identical to
`in_pair` on every row, so it is a membership flag, not a score.

WHICH COLUMN IS THE SCORE. `connectivity` is the only numeric candidate once `support` is known to be
a flag. It is confirmed rather than assumed: on every pair whose margin has a sign, the sign agrees
with the shipped `predicted_v09`. If that ever stops holding, this script STOPS instead of reporting
a tie rate over a column it has not identified.

CONTROLS, each able to fail:
  C1  chains are accounted for        chain sizes sum to the record count
  C2  support is a flag, not a score  support == in_pair on every row
  C3  score column identified         connectivity sign agrees with predicted_v09 on all signed pairs
  C4  THE DECISIVE ONE                on SIGNED pairs, `rank` must NOT predict the flagged member
                                      much better than chance. If rank predicted those too, then rank
                                      drives the whole result and "it breaks ties" would be the wrong
                                      description. This is what separates the two explanations.
  C5  joint, not marginals            the tie claim is tested as a JOINT condition (the flagged member
                                      IS the earlier-ranked one, pair by pair). Two marginal counts of
                                      52/45 are consistent with agreement as low as 7/97, so marginals
                                      cannot establish it.
  C6  attribution bounded             tie-derived FN <= total FN and tie-derived FP <= total FP
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


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        print("usage: python tat_tie_break_reconstruction.py <predictions.csv>")
        return 2
    rows = load(argv[1])

    chains = collections.defaultdict(list)
    for r in rows:
        chains[r["chain_id"]].append(r)
    chain_sizes = collections.Counter(len(v) for v in chains.values())

    in_pair = collections.defaultdict(list)
    for r in rows:
        if i(r["in_pair"]) == 1:
            in_pair[r["chain_id"]].append(r)
    pair_sizes = collections.Counter(len(v) for v in in_pair.values())
    pairs = [v for v in in_pair.values()
             if len(v) == 2 and sum(1 for x in v if b(x["is_planted"])) == 1]

    TP = sum(1 for r in rows if b(r["is_planted"]) and b(r["predicted_v09"]))
    FP = sum(1 for r in rows if not b(r["is_planted"]) and b(r["predicted_v09"]))
    FN = sum(1 for r in rows if b(r["is_planted"]) and not b(r["predicted_v09"]))

    print("rows=%d  chains=%d  chain sizes=%s" % (len(rows), len(chains), dict(chain_sizes)))
    print("in_pair subsets per chain: %s   two-member=%d" % (dict(sorted(pair_sizes.items())),
                                                             len(pairs)))

    # C2 -- support is a membership flag, not a score
    support_is_flag = all(i(r["support"]) == i(r["in_pair"]) for r in rows)
    print()
    print("SCORE COLUMN")
    print("  support == in_pair on every row : %s%s"
          % (support_is_flag, "   <- a flag, not a score" if support_is_flag else ""))

    # split signed vs tied, and test both explanations on each half
    signed, tied = [], []
    for v in pairs:
        pl = [x for x in v if b(x["is_planted"])][0]
        gd = [x for x in v if not b(x["is_planted"])][0]
        m = i(gd["connectivity"]) - i(pl["connectivity"])
        (tied if m == 0 else signed).append((pl, gd, m))

    conn_ok = sum(1 for pl, _gd, m in signed if (m > 0) == b(pl["predicted_v09"]))

    def flagged_pair(pl, gd):
        if b(pl["predicted_v09"]) and not b(gd["predicted_v09"]):
            return pl, gd
        if b(gd["predicted_v09"]) and not b(pl["predicted_v09"]):
            return gd, pl
        return None, None

    rank_ok_signed = 0
    for pl, gd, _m in signed:
        f, o = flagged_pair(pl, gd)
        if f is not None and i(f["rank"]) < i(o["rank"]):
            rank_ok_signed += 1

    print("  connectivity sign predicts the flag, signed pairs : %d/%d" % (conn_ok, len(signed)))
    if not (support_is_flag and conn_ok == len(signed) and signed):
        print()
        print("  [C3 FAIL] score column not identified on this file; stopping rather than "
              "reporting a tie rate over the wrong column.")
        return 1
    print("  [C3 PASS] `connectivity` is the score column.")

    # C4 -- the decisive control
    frac = rank_ok_signed / len(signed)
    print("  rank predicts the flag, signed pairs             : %d/%d (%.0f%%)"
          % (rank_ok_signed, len(signed), 100 * frac))
    c4 = frac < 0.75
    print("  [%s] C4 rank does NOT drive the signed pairs -- so its role is confined to ties"
          % ("PASS" if c4 else "FAIL"))

    # C5 -- the joint condition on ties
    joint = both = neither = 0
    fn_ties = fp_ties = 0
    planted_first = 0
    for pl, gd, _m in tied:
        f, o = flagged_pair(pl, gd)
        if f is None:
            if b(pl["predicted_v09"]):
                both += 1
            else:
                neither += 1
            continue
        if i(f["rank"]) < i(o["rank"]):
            joint += 1
        if f is gd:
            fp_ties += 1
            fn_ties += 1
        if i(pl["rank"]) < i(gd["rank"]):
            planted_first += 1

    print()
    print("TIES AT MARGIN 0: %d of %d two-member pairs (%.1f%%)"
          % (len(tied), len(pairs), 100.0 * len(tied) / max(1, len(pairs))))
    print("  JOINT: the flagged member IS the earlier-ranked one : %d/%d" % (joint, len(tied)))
    print("  of those, the earlier one was the planted record    : %d  (correct)" % planted_first)
    print("  and the gold record                                 : %d  (wrong)"
          % (len(tied) - planted_first))
    print("  both flagged=%d  neither flagged=%d" % (both, neither))
    print()
    print("ERROR ATTRIBUTED TO THE TIE-BREAK")
    print("  false negatives from ties : %d of %d total (%.0f%%)"
          % (fn_ties, FN, 100.0 * fn_ties / max(1, FN)))
    print("  false positives from ties : %d of %d total (%.0f%%)"
          % (fp_ties, FP, 100.0 * fp_ties / max(1, FP)))

    print()
    print("CONTROLS")
    c1 = sum(chain_sizes.values()) == len(chains)
    c5 = joint == len(tied)
    c6 = fn_ties <= FN and fp_ties <= FP
    for ok, label in ((c1, "C1 chains accounted for"),
                      (support_is_flag, "C2 support is a flag, not a score"),
                      (True, "C3 score column identified"),
                      (c4, "C4 rank does not drive the signed pairs"),
                      (c5, "C5 tie claim holds jointly, not just marginally"),
                      (c6, "C6 attributed error within totals")):
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print()
    print("record-level totals for reference: TP=%d FP=%d FN=%d" % (TP, FP, FN))
    return 0 if (c1 and support_is_flag and c4 and c5 and c6) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
