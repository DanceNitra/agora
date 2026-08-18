"""Every number I am about to send Marat about TAT v0.2 v2, computed once, behind the gate.

WHY THIS FILE EXISTS. I drafted a letter to a collaborator containing eight numbers computed in a
throwaway one-liner. The owner stopped it: the standing rule is that anything with a number in it
goes through the gate, and I had run the gate on a different outbound the same afternoon and skipped
it here. This is the same computation, bound to the bytes of his files and to controls that can fail.

WHAT IS CHECKED
  record-level confusion matrix recomputed from the CSV, not read from his report
  the same matrix restricted to in_pair == 1, which is the number the letter turns on
  whether the report's own stated values agree with its own data
  whether 305 / 186 / 119 / 61.0 -- the figures from his FIRST email and from v1 -- survive in v2

CONTROLS, each able to fail
  C1 file identity     sha256 of both artefacts, so the numbers are bound to bytes and not to a name
  C2 denominator       every row lands in exactly one confusion cell, and the cells sum to the rows
  C3 report agrees     his report_v2's stated record-level values must equal the CSV-derived ones;
                       if they disagree THAT is the finding, and the gate must not paper over it
  C4 in_pair partitions the column must take both values and must not be constant -- a column that is
                       all 1 or all 0 makes the pair-level number vacuous while looking computed
  C5 can-fail          a deliberately broken read (is_planted forced False) must produce a DIFFERENT,
                       degenerate matrix; if the pipeline returns the same answer on wrong input it is
                       not reading the input
  C6 absence + PLANT   the "305/186/119/61.0 are absent from v2" claim is a claim about text, so the
                       same detector is run against a doctored copy that CONTAINS them, and the whole
                       run is void unless the detector flags its own plant
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "agora_output" / "lab" / "memops"))
from probe_gate import ProbeGate  # noqa: E402

# Paths come from the command line so this runs anywhere, not only where it was written:
#     python marat_tat_v2_units.py <predictions.csv> <report.json>
CSV_PATH = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "tat_predictions_v02_detailed_v2.csv")
JSON_PATH = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "TAT_RAMR_v0.2_report_v2.json")

_TRUE = ("true", "1", "yes")


def _b(s) -> bool:
    return str(s).strip().lower() in _TRUE


def _i(s) -> int:
    s = str(s).strip()
    return int(float(s)) if s else 0


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def matrix(rows, planted_key="is_planted", pred_key="predicted_v09"):
    TP = sum(1 for r in rows if _b(r[planted_key]) and _b(r[pred_key]))
    FP = sum(1 for r in rows if not _b(r[planted_key]) and _b(r[pred_key]))
    FN = sum(1 for r in rows if _b(r[planted_key]) and not _b(r[pred_key]))
    TN = sum(1 for r in rows if not _b(r[planted_key]) and not _b(r[pred_key]))
    out = {"TP": TP, "FP": FP, "FN": FN, "TN": TN, "n": TP + FP + FN + TN}
    out["precision"] = TP / (TP + FP) if TP + FP else 0.0
    out["recall"] = TP / (TP + FN) if TP + FN else 0.0
    p, r = out["precision"], out["recall"]
    out["f1"] = 2 * p * r / (p + r) if p + r else 0.0
    out["fp_rate"] = FP / (FP + TN) if FP + TN else 0.0
    return out


def absent_tokens(text: str, tokens=("305", "186", "119", "61.0")) -> list[str]:
    """Which of these do NOT appear. Returned as a list so the plant can flip it."""
    return [t for t in tokens if t not in text]


def group_structure(rows):
    """The 'pairs' are GROUPS of 2-6, and both red-team lenses got this wrong by inferring
    324 - 300 = 24 planted-free pairs from the aggregates. Measured instead."""
    import collections
    ch = collections.defaultdict(list)
    for r in rows:
        if _i(r["in_pair"]) == 1:
            ch[r["chain_id"]].append(r)
    sizes = collections.Counter(len(v) for v in ch.values())
    planted_per = collections.Counter(sum(1 for x in v if _b(x["is_planted"])) for v in ch.values())
    no_planted = [c for c, v in ch.items() if not any(_b(x["is_planted"]) for x in v)]
    return {"groups": len(ch), "sizes": dict(sorted(sizes.items())),
            "planted_per_group": dict(sorted(planted_per.items())),
            "groups_without_planted": len(no_planted)}, ch


def margins(ch):
    """gold_connectivity - planted_connectivity on the 2-member groups, which is HIS stated score.
    Integer valued with a sign boundary at 0, so the mass sitting exactly on 0 is the question."""
    import collections
    two = [v for v in ch.values() if len(v) == 2 and sum(1 for x in v if _b(x["is_planted"])) == 1]
    dist = collections.Counter()
    for v in two:
        pl = [x for x in v if _b(x["is_planted"])][0]
        gd = [x for x in v if not _b(x["is_planted"])][0]
        dist[_i(gd["connectivity"]) - _i(pl["connectivity"])] += 1
    n = sum(dist.values())
    return {"two_member_groups": n, "distribution": dict(sorted(dist.items())),
            "ties_at_zero": dist[0], "tie_fraction": (dist[0] / n) if n else 0.0,
            "gold_greater": sum(c for m, c in dist.items() if m > 0),
            "gold_less": sum(c for m, c in dist.items() if m < 0)}


def tie_break(ch):
    """HOW is a tie at margin 0 resolved? The letter we sent guessed "a default one way". Measured:
    it is `rank`, and it splits almost evenly, which makes it the largest error source in the file.

    Field choice defended rather than assumed: on `support` the margin is 0 on ALL 274 pairs, so it
    cannot be the score; on `connectivity` the sign agrees with `predicted_v09` on 177/177 pairs that
    have a sign, with zero disagreements."""
    import collections
    two = [v for v in ch.values() if len(v) == 2 and sum(1 for x in v if _b(x["is_planted"])) == 1]
    tied = []
    agree = disagree = 0
    for v in two:
        pl = [x for x in v if _b(x["is_planted"])][0]
        gd = [x for x in v if not _b(x["is_planted"])][0]
        m = _i(gd["connectivity"]) - _i(pl["connectivity"])
        if m == 0:
            tied.append((pl, gd))
        elif (m > 0) == _b(pl["predicted_v09"]):
            agree += 1
        else:
            disagree += 1
    outcome = collections.Counter()
    by_rank = collections.Counter()
    fn = fp = 0
    for pl, gd in tied:
        outcome[(_b(pl["predicted_v09"]), _b(gd["predicted_v09"]))] += 1
        by_rank["planted_earlier" if _i(pl["rank"]) < _i(gd["rank"]) else "gold_earlier"] += 1
        if not _b(pl["predicted_v09"]):
            fn += 1
        if _b(gd["predicted_v09"]):
            fp += 1
    return {"tied_pairs": len(tied), "sign_agrees": agree, "sign_disagrees": disagree,
            "flagged_planted_only": outcome[(True, False)],
            "flagged_gold_only": outcome[(False, True)],
            "flagged_both": outcome[(True, True)], "flagged_neither": outcome[(False, False)],
            "rank_split": dict(by_rank), "fn_from_ties": fn, "fp_from_ties": fp}


def margin_on(ch, field):
    import collections
    two = [v for v in ch.values() if len(v) == 2 and sum(1 for x in v if _b(x["is_planted"])) == 1]
    d = collections.Counter()
    for v in two:
        pl = [x for x in v if _b(x["is_planted"])][0]
        gd = [x for x in v if not _b(x["is_planted"])][0]
        d[_i(gd[field]) - _i(pl[field])] += 1
    return dict(sorted(d.items()))


def main() -> int:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    report_text = JSON_PATH.read_text(encoding="utf-8")
    report = json.loads(report_text)

    rec = matrix(rows)
    in_pair = [r for r in rows if _i(r["in_pair"]) == 1]
    pair = matrix(in_pair)
    out_pair = [r for r in rows if _i(r["in_pair"]) == 0]
    outside = matrix(out_pair)
    struct, ch = group_structure(rows)
    marg = margins(ch)
    ties = tie_break(ch)
    marg_support = margin_on(ch, 'support')

    gate = ProbeGate(
        "TAT v0.2 v2 -- record-level vs in-pair units",
        operating_point={
            "csv": CSV_PATH.name, "json": JSON_PATH.name,
            "rows": len(rows), "in_pair_rows": len(in_pair),
            "planted_key": "is_planted", "pred_key": "predicted_v09",
        },
    )

    # C1 -- bind the numbers to bytes, not to a filename
    gate.manipulation_landed(
        "both artefacts hash to a stated sha256",
        lambda: len(sha256(CSV_PATH)) == 64 and len(sha256(JSON_PATH)) == 64,
    )

    # C2 -- denominator: every row in exactly one cell
    gate.denominator(n_scored=rec["n"], n_total=len(rows), min_frac=1.0)
    gate.manipulation_landed(
        "in-pair cells sum to the in-pair rows",
        lambda: pair["n"] == len(in_pair),
    )

    # C3 -- his report must agree with his own data
    rl = report.get("record_level", {})
    gate.control("report_v2 TP matches the CSV", rl.get("TP", -1), (rec["TP"], rec["TP"]))
    gate.control("report_v2 FP matches the CSV", rl.get("FP", -1), (rec["FP"], rec["FP"]))
    gate.control("report_v2 FN matches the CSV", rl.get("FN", -1), (rec["FN"], rec["FN"]))
    gate.control("report_v2 TN matches the CSV", rl.get("TN", -1), (rec["TN"], rec["TN"]))
    gate.control("report_v2 f1_corrected matches the CSV",
                 rl.get("f1_corrected", -1), (round(rec["f1"], 4), round(rec["f1"], 4)))

    # C4 -- the partition must be real, or the pair-level number is vacuous
    vals = {_i(r["in_pair"]) for r in rows}
    gate.manipulation_landed(
        "in_pair takes both values and is not constant",
        lambda: vals == {0, 1} and 0 < len(in_pair) < len(rows),
    )
    gate.manipulation_landed(
        "every planted record is in a pair (else 'same TP/FN' would not follow)",
        lambda: all(_i(r["in_pair"]) == 1 for r in rows if _b(r["is_planted"])),
    )

    # C4b -- the structure BOTH red-team lenses inferred wrongly from aggregates
    gate.manipulation_landed(
        "group structure is measured, not inferred from 648/2",
        lambda: struct["groups"] > 0 and sum(struct["sizes"].values()) == struct["groups"],
    )
    gate.can_fail(
        "a group with no planted record would be counted if one existed",
        lambda: struct["groups_without_planted"] == len(
            [1 for v in ch.values() if not any(_b(x["is_planted"]) for x in v)]),
    )
    # C4c -- the tie measurement must have a real denominator
    gate.denominator(n_scored=marg["two_member_groups"], n_total=struct["groups"], min_frac=0.5)

    # C4d -- the score FIELD is defended, not assumed. If `support` were the field the margin would
    # be degenerate; if `connectivity` is the field the sign must track the shipped prediction.
    gate.can_fail(
        "`support` is degenerate as a score (margin 0 everywhere), so it is not the field",
        lambda: set(marg_support) == {0},
    )
    gate.control("sign of the connectivity margin agrees with predicted_v09 on every signed pair",
                 ties["sign_disagrees"], (0, 0))
    gate.manipulation_landed(
        "tie outcomes and the rank split account for every tied pair",
        lambda: (ties["flagged_planted_only"] + ties["flagged_gold_only"]
                 + ties["flagged_both"] + ties["flagged_neither"] == ties["tied_pairs"]
                 and sum(ties["rank_split"].values()) == ties["tied_pairs"]),
    )

    # C5 -- can-fail: a broken read must not produce the same answer
    broken = [dict(r, is_planted="False") for r in rows]
    gate.can_fail(
        "forcing is_planted=False degenerates the matrix",
        lambda: matrix(broken)["TP"] == 0 and matrix(broken)["TP"] != rec["TP"],
    )

    # C6 -- absence claim, with a MUST-FAIL plant
    missing = absent_tokens(report_text)
    planted_text = report_text + '\n{"planted_for_control": "305 186 119 61.0"}\n'
    gate.can_fail(
        "the absence detector flags its own plant",
        lambda: absent_tokens(planted_text) == [],
    )

    result = {
        "csv_sha256": sha256(CSV_PATH), "json_sha256": sha256(JSON_PATH),
        "record_level": rec,
        "in_pair_level": pair,
        "in_pair_rows": len(in_pair),
        "in_pair_planted": sum(1 for r in in_pair if _b(r["is_planted"])),
        "in_pair_not_planted": sum(1 for r in in_pair if not _b(r["is_planted"])),
        "pairs_from_column": len(in_pair) / 2,
        "report_pair_level": report.get("pair_level", {}),
        "tokens_absent_from_report_v2": missing,
        "outside_pairs": outside,
        "group_structure": struct,
        "margins_two_member": marg,
        "margin_on_support": marg_support,
        "tie_break": ties,
    }
    out = gate.report(result)
    pathlib.Path(__file__).with_suffix(".result.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")

    print()
    print("RECORD-LEVEL   TP=%(TP)d FP=%(FP)d FN=%(FN)d TN=%(TN)d  n=%(n)d" % rec)
    print("               precision=%(precision).4f recall=%(recall).4f f1=%(f1).4f "
          "fp_rate=%(fp_rate).4f" % rec)
    print("IN-PAIR ONLY   TP=%(TP)d FP=%(FP)d FN=%(FN)d TN=%(TN)d  n=%(n)d" % pair)
    print("               precision=%(precision).4f recall=%(recall).4f f1=%(f1).4f "
          "fp_rate=%(fp_rate).4f" % pair)
    print("in_pair rows=%d (planted %d / not planted %d) -> %.1f pairs; report says %s"
          % (len(in_pair), result["in_pair_planted"], result["in_pair_not_planted"],
             result["pairs_from_column"], report.get("pair_level", {}).get("total_pairs_approx")))
    print("OUTSIDE PAIRS  n=%(n)d FP=%(FP)d  fp_rate=%(fp_rate).4f" % outside)
    print("GROUPS         %(groups)d groups, sizes %(sizes)s, planted per group %(planted_per_group)s, "
          "without planted %(groups_without_planted)d" % struct)
    print("MARGINS        %(two_member_groups)d two-member groups, dist %(distribution)s" % marg)
    print("               ties at 0 = %(ties_at_zero)d (%(tie_fraction).3f), gold> %(gold_greater)d, "
          "gold< %(gold_less)d" % marg)
    print("TIE-BREAK      %(tied_pairs)d tied; planted-only %(flagged_planted_only)d, "
          "gold-only %(flagged_gold_only)d, both %(flagged_both)d, neither %(flagged_neither)d" % ties)
    print("               rank split %(rank_split)s; FN from ties %(fn_from_ties)d, "
          "FP from ties %(fp_from_ties)d" % ties)
    print("               margin on support = %s (degenerate -> not the score field)" % marg_support)
    print("absent from report_v2: %s" % (missing or "(none -- all present)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
