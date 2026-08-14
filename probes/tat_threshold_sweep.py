"""Threshold sweep for the TAT/RAMR per-record predictions. Stdlib only, no numpy, no pandas.

Marat asked for the exact sweep so both sides run the same thing on a 2 GB Colab CPU. This is it.
It is also, deliberately, a different sweep from the one the thread has been quoting, for two reasons.

THE ENDPOINTS ARE NOT EVIDENCE. "100% false positives at 100% detection" was read in the thread as
showing that connectivity alone cannot resolve every planted defect. It shows nothing of the kind: a
threshold that flags everything gives 100/100 for any scorer that has ever existed, including a coin.
Both ends of a ROC curve are fixed by construction. What separates a useful signal from a useless one
is the middle, so this reports AUC and detection at FIXED false-positive rates, where a random scorer
scores 0.5 and 1%/5%/10% respectively and has nowhere to hide.

THE ROWS ARE NOT INDEPENDENT. 2400 records grouped into chains means the unit of independence is the
CHAIN, not the row. Records in one chain share a generator, a topology and a planted defect, so a
confidence interval computed as though there were 2400 independent draws is too narrow by roughly the
square root of the mean chain size. The bootstrap here resamples CHAINS with replacement and keeps each sampled chain whole.

It does NOT always widen the interval, and an earlier version of this file asserted that it would.
Measured on a synthetic set with one planted record per chain it came out 0.8x, narrower, because
chain resampling holds the positive count fixed at one per sampled chain while row resampling lets it
swing. The direction is not the point and depends on the design; the unit is. Both intervals are
printed so the difference is visible rather than argued.

    python tat_threshold_sweep.py predictions.csv
    python tat_threshold_sweep.py predictions.csv --score connectivity --label is_planted

Expected columns, overridable: a score, a binary label, and a chain id. Everything else is ignored.
"""
import argparse
import csv
import io
import json
import os
import random
import sys


def load(path, score_col, label_col, chain_col):
    rows, skipped = [], []
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if score_col not in r or label_col not in r:
                raise SystemExit("columns %r and %r are required; found %s"
                                 % (score_col, label_col, sorted(r)))
            try:
                score = float(r[score_col])
            except (TypeError, ValueError):
                skipped.append(r[score_col])
                continue
            raw = str(r[label_col]).strip().lower()
            label = 1 if raw in ("1", "true", "yes", "planted", "y") else 0
            rows.append((score, label, r.get(chain_col, "")))
    if not rows:
        # A loader that skips every row and returns an empty list hands the caller a crash three
        # frames later instead of the reason. Measured:  in the real file is a boolean
        # DECISION, not a score, so every float() failed and the run reported "rows 0" then died.
        raise SystemExit(
            "no usable rows: every value in %r failed to parse as a number (saw %s). "
            "If that column is a boolean decision rather than a score, pass the score column, "
            "e.g. --score connectivity." % (score_col, sorted(set(skipped))[:4]))
    return rows


def auc(rows):
    """Mann-Whitney U as a fraction, ties counted as half. No dependencies, O(n log n)."""
    pos = sorted(s for s, y, _ in rows if y == 1)
    neg = sorted(s for s, y, _ in rows if y == 0)
    if not pos or not neg:
        return None
    i = wins = 0
    ties = 0
    for p in pos:
        while i < len(neg) and neg[i] < p:
            i += 1
        wins += i
        j = i
        while j < len(neg) and neg[j] == p:
            j += 1
        ties += j - i
    return (wins + 0.5 * ties) / (len(pos) * len(neg))


def detection_at_fpr(rows, target_fpr):
    """Highest detection rate achievable without exceeding `target_fpr`.

    Reported instead of a single operating point because a single point can be tuned; a curve read at
    a fixed false-positive budget cannot.
    """
    neg = sorted((s for s, y, _ in rows if y == 0), reverse=True)
    pos = [s for s, y, _ in rows if y == 1]
    if not neg or not pos:
        return None
    allowed = int(target_fpr * len(neg))
    if allowed >= len(neg):
        return 1.0
    threshold = neg[allowed] if allowed < len(neg) else neg[-1]
    return sum(1 for s in pos if s > threshold) / len(pos)


def bootstrap_by_chain(rows, stat, draws=2000, seed=0):
    """Resample CHAINS with replacement, keeping each whole. The row-level bootstrap is wrong here."""
    chains = {}
    for row in rows:
        chains.setdefault(row[2], []).append(row)
    keys = list(chains)
    if len(keys) < 2:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(draws):
        sample = []
        for _ in range(len(keys)):
            sample.extend(chains[keys[rng.randrange(len(keys))]])
        v = stat(sample)
        if v is not None:
            vals.append(v)
    vals.sort()
    if not vals:
        return None
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))], len(keys)


def bootstrap_by_row(rows, stat, draws=2000, seed=0):
    """The comparison the chain-level interval exists to be measured against."""
    rng = random.Random(seed)
    vals = []
    for _ in range(draws):
        sample = [rows[rng.randrange(len(rows))] for _ in range(len(rows))]
        v = stat(sample)
        if v is not None:
            vals.append(v)
    vals.sort()
    return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]) if vals else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--score", default="predicted_v09")
    ap.add_argument("--label", default="is_planted")
    ap.add_argument("--chain", default="chain_id")
    ap.add_argument("--draws", type=int, default=2000)
    a = ap.parse_args(argv)

    rows = load(a.csv, a.score, a.label, a.chain)
    pos = sum(1 for _, y, _ in rows if y == 1)
    chains = len({c for _, _, c in rows})
    print("rows %d | positives %d | chains %d | mean chain size %.1f\n"
          % (len(rows), pos, chains, len(rows) / max(chains, 1)))

    a_all = auc(rows)
    print("AUC                     : %.4f   (a coin scores 0.5000)" % a_all)
    for fpr in (0.01, 0.05, 0.10):
        d = detection_at_fpr(rows, fpr)
        print("detection at %4.0f%% FPR   : %s" % (fpr * 100,
                                                   "%.4f" % d if d is not None else "n/a"))

    print("\nendpoints, stated so nobody quotes them as evidence:")
    print("  at a threshold below every score : detection 1.0000, FPR 1.0000")
    print("  at a threshold above every score : detection 0.0000, FPR 0.0000")
    print("  both hold for a coin. They are properties of the threshold, not the signal.")

    row_ci = bootstrap_by_row(rows, auc, a.draws)
    chain_ci = bootstrap_by_chain(rows, auc, a.draws)
    print("\nAUC 95%% interval, resampling ROWS   : [%.4f, %.4f]" % row_ci)
    if chain_ci:
        lo, hi, nchains = chain_ci
        print("AUC 95%% interval, resampling CHAINS : [%.4f, %.4f]  (%d chains)" % (lo, hi, nchains))
        ratio = (hi - lo) / max(row_ci[1] - row_ci[0], 1e-12)
        print("\nthe chain-level interval is %.2fx the width of the row-level one." % ratio)
        print("Records in one chain share a generator, a topology and a planted defect, so the row")
        print("interval answers a question nobody asked: how much would the number move if we drew")
        print("more records FROM THESE CHAINS. Quote the chain one. It can come out NARROWER when the")
        print("design fixes positives per chain, so the ratio is reported and not predicted.")
    else:
        print("\nonly one chain found -- no chain-level interval is possible, and no row-level")
        print("interval should be quoted either.")

    out = {"rows": len(rows), "positives": pos, "chains": chains, "auc": a_all,
           "detection_at_fpr": {str(f): detection_at_fpr(rows, f) for f in (0.01, 0.05, 0.10)},
           "auc_ci_rows": list(row_ci), "auc_ci_chains": list(chain_ci[:2]) if chain_ci else None}
    dest = os.path.splitext(a.csv)[0] + ".sweep.json"
    io.open(dest, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("\nwrote %s" % os.path.basename(dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
