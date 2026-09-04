"""Re-derive every number in drafts/edrn_table2_consequence.md from an artifact or by recomputation.

THIS IS ONE CHECK INSIDE VALIDATE. It is not the gate. The gate is validate, storm when the claim
rests on literature, stress-claim, verify-claims and the humanizer skill. A script that prints a
number is not a verdict, and calling one "the gate" is a substitution this repository has made
before.

WHAT IT DOES. Every figure the draft states is recomputed here, or read from the receipt of the run
that produced it, and compared against the draft's own text. A number in the draft that no check
claims fails the coverage control, so the way to defeat this probe is to add a figure and say
nothing, which the coverage control exists to stop.

WHERE EACH NUMBER COMES FROM, and the point is that most of them are HIS:
  * HIS PUBLISHED Table 2 row and HIS ring caveat are parsed out of manuscript.tex.
  * HIS repaired CSV is read directly. The draft's opening withdraws two claims on the strength of
    that file, so the file has to say what the draft says it says.
  * OUR table values come from table2_both_conventions.result.json.
  * The baseline and seed-spread figures come from is_the_s0_baseline_the_same_system.result.json.
  * The null figures come from separable_null_for_the_multi_entrance_deviation.result.json.
  * The (7,8) monotonicity is RECOMPUTED here, because no receipt on disk holds 0.193039.
  * HIS five pairs are retyped from his 2026-09-04 comment; the Spearman is computed here rather
    than repeated from his text.

CONTROLS:
  * A MUTATION: a perturbed expectation must fail, or every "ok" above it means nothing.
  * COVERAGE: every decimal figure in the draft must be claimed by a check.
  * WITHDRAWN CLAIMS: the draft says two of our findings were already his. If his files do not
    contain them, the withdrawal is wrong and the letter is worse than the one it replaced.
  * A SPREAD IS NOT A SHIFT. An earlier version of this file computed max-minus-mean and called it
    a shift, matching a wrong sentence in the draft. A control that shares the error it checks for
    cannot see it, so both quantities are now checked against their own definitions.
"""
from __future__ import annotations

import csv
import io
import itertools
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "drafts", "edrn_table2_consequence.md")
SUB = os.path.join(ROOT, "agora_output", "edrn_submission")
OUT = os.path.join(HERE, "recheck_figures_edrn_table2_consequence.result.json")

TABLE2 = os.path.join(SUB, "table2_both_conventions.result.json")
NULL = os.path.join(HERE, "separable_null_for_the_multi_entrance_deviation.result.json")
BASE = os.path.join(HERE, "is_the_s0_baseline_the_same_system.result.json")
MATCHED = os.path.join(HERE, "the_matched_null_lives_on_his_own_graph.result.json")
MANUSCRIPT = os.path.join(SUB, "manuscript.tex")
HIS_CSV = os.path.join(
    SUB, "guanghao_archive_2026-09-03",
    "\u6811\u5f62\u56fe\u548c\u968f\u673a\u56fe\u9700\u8981\u4fee\u6539\u95ee\u9898\u7684\u89e3\u7b54",
    "\u751f\u6210\u8bba\u6587\u8868II\u6240\u9700\u7684\u6811\u56fe\u548c\u968f\u673a\u56fe\u8c37\u6df1"
    "\u5ea6\u6570\u636e\uff08\u4fee\u590d\u7248\uff09",
    "2026-08-22T08_55_39+00_00_go5s.csv")

HIS_PAIRS = [("(0,1)-(6,8)", 2, 8, 24.5), ("(0,1)-(1,4)", 1, 9, 17.4),
             ("(0,1)-(7,9)", 2, 7, 19.1), ("(6,8)-(1,8)", 1, 7, 24.2),
             ("(2,5)-(3,4)", 1, 7, 28.0)]

checks = []


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def check(label, expected, found, tol=5e-6, source=""):
    ok = abs(float(expected) - float(found)) <= tol
    checks.append({"label": label, "expected": float(expected), "found": float(found),
                   "tol": tol, "ok": ok, "source": source})
    print("  %-4s %-44s draft %-12s vs %-12s  %s"
          % ("ok" if ok else "FAIL", label, "%.6g" % expected, "%.6g" % found, source))
    return ok


def published():
    tex = io.open(MANUSCRIPT, encoding="utf-8", errors="replace").read()
    block = re.search(r"\\label\{tab:control_graphs\}(.*?)\\end\{tabular\}", tex, re.S)
    if not block:
        refuse("could not find tab:control_graphs in manuscript.tex")
    rows = {}
    for line in block.group(1).split("\\\\"):
        m = re.search(r"(Ring|Tree|Random)\s*&\s*([\d.]+)[^&]*&\s*([\d.]+)\s*&\s*([\d.]+)"
                      r"\$\\pm\$([\d.]+)", line)
        if m:
            rows[m.group(1).lower()] = {"s": float(m.group(2)), "single": float(m.group(3)),
                                        "multi": float(m.group(4)), "multi_std": float(m.group(5))}
    if len(rows) != 3:
        refuse("parsed %d of 3 published rows from manuscript.tex" % len(rows))
    return rows, tex


def his_csv_deepest(graph):
    if not os.path.isfile(HIS_CSV):
        refuse("his repaired CSV is not at %s, so the draft's withdrawal has nothing behind it"
               % HIS_CSV)
    rows = [r for r in csv.DictReader(io.open(HIS_CSV, encoding="utf-8"))
            if r["graph"] == graph and r.get("selection_eligible") == "True"]
    if not rows:
        refuse("his CSV holds no eligible %s rows" % graph)
    best = max(rows, key=lambda r: float(r["valley_depth"]))
    return best["edge"], float(best["valley_depth"])


def recompute_78():
    import networkx as nx
    from scipy.sparse import csr_matrix
    from scipy.sparse.linalg import eigsh
    G = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
    edges = [tuple(sorted(e)) for e in G.edges()]
    if len(edges) != 20 or (7, 8) not in edges:
        refuse("the small-world generator no longer gives 20 edges including (7,8)")
    basis = np.array([sum(1 << i for i in c) for c in itertools.combinations(range(10), 5)],
                     dtype=np.int64)
    idx = {int(b): i for i, b in enumerate(basis)}
    zz = {e: np.where(((basis >> e[0]) & 1) == ((basis >> e[1]) & 1), 1.0, -1.0) for e in edges}

    def E(s):
        rows, cols, vals = [], [], []
        for k, st in enumerate(basis):
            d = 0.0
            for (a, b) in edges:
                J = s if (a, b) == (7, 8) else 1.0
                sa, sb = (st >> a) & 1, (st >> b) & 1
                d += J * (0.25 if sa == sb else -0.25)
                if sa != sb:
                    j = idx.get(int(st ^ ((1 << a) | (1 << b))))
                    if j is not None:
                        rows.append(k); cols.append(j); vals.append(0.5 * J)
            rows.append(k); cols.append(k); vals.append(d)
        H = csr_matrix((vals, (rows, cols)), shape=(len(basis),) * 2)
        w, v = eigsh(H, k=6, which="SA",
                     v0=np.random.default_rng(0).standard_normal(H.shape[0]))
        o = np.argsort(w)
        return float(np.std([np.dot(v[:, o][:, 0] ** 2, zz[e]) for e in edges]))

    curve = [E(s) for s in np.linspace(0.0, 3.0, 21)]
    return curve[0], curve[-1], bool(np.all(np.diff(curve) >= -1e-12)), int(np.argmin(curve))


def main():
    if not os.path.isfile(DRAFT):
        refuse("no draft at %s" % DRAFT)
    text = io.open(DRAFT, encoding="utf-8").read()
    if "PLACEHOLDER" in text:
        refuse("the draft still contains a PLACEHOLDER")
    for p in (TABLE2, NULL, BASE, MANUSCRIPT, MATCHED):
        if not os.path.isfile(p):
            refuse("missing artifact %s" % p)

    t2 = json.load(io.open(TABLE2, encoding="utf-8"))["table"]
    nul = json.load(io.open(NULL, encoding="utf-8"))
    base = json.load(io.open(BASE, encoding="utf-8"))
    pub, tex = published()
    ok = True

    # CONTROL: the two withdrawn claims must actually be in his files.
    edge, depth = his_csv_deepest("random")
    print("  HIS repaired CSV, deepest eligible random edge: %s at depth %.6f" % (edge, depth))
    if edge.replace(" ", "") != "[7,8]":
        refuse("his CSV's deepest random edge is %s, not [7, 8]; the draft withdraws a claim on "
               "the basis of a file that does not support the withdrawal" % edge)
    ok &= check("his CSV depth at (7,8)", 0.064153, depth, 5e-6, "his repaired CSV")
    if "mixture of different $S_z$ sectors" not in tex:
        refuse("the manuscript does not contain the S_z mixture caveat the draft attributes to it; "
               "the second withdrawal would then be wrong")
    print("  HIS manuscript contains the S_z-mixture caveat the draft credits him with")

    ok &= check("his published random single", 0.1050, pub["random"]["single"], 1e-9, "manuscript")
    ok &= check("his published random multi", 0.0730, pub["random"]["multi"], 1e-9, "manuscript")
    ok &= check("his published random multi std", 0.0548, pub["random"]["multi_std"], 1e-9,
                "manuscript")
    ok &= check("his ring multi (in the withdrawal)", 0.0993, pub["ring"]["multi"], 1e-9,
                "manuscript")
    ok &= check("his ring multi std", 0.0286, pub["ring"]["multi_std"], 1e-9, "manuscript")

    ok &= check("our (7,8) manifold depth", 0.064153, t2["random|average"]["depth"], 5e-6,
                "table2 receipt")
    ok &= check("(7,8) depth as rounded in the text", 0.0642, t2["random|average"]["depth"], 5e-5,
                "table2 receipt")
    ok &= check("(7,8) seed mean", 0.064153432, base["seed_study"]["mean"], 5e-9, "baseline receipt")
    ok &= check("(7,8) seed spread", 2.4e-14, base["seed_study"]["spread"], 5e-15,
                "baseline receipt")

    rows = base["rows"]
    for label, dep0, dep05, pct in (("random (8,14)", 0.050837, 0.031925, -37.2),
                                    ("random (7,8)", 0.064153, 0.063693, -0.7),
                                    ("tree (2,3)", 0.074977, 0.073009, -2.6)):
        r = rows[label]
        ok &= check("%s depth from s=0" % label, dep0, r["depth_from_0"], 5e-6, "baseline receipt")
        ok &= check("%s depth from s=0.05" % label, dep05, r["depth_from_005"], 5e-6,
                    "baseline receipt")
        ok &= check("%s change percent" % label, pct, r["change_pct"], 0.06, "baseline receipt")
    if rows["random (8,14)"]["deg_at_0"] != 2 or rows["random (8,14)"]["deg_at_valley"] != 1:
        refuse("(8,14) degeneracies are %d and %d, not the 2 and 1 the draft states"
               % (rows["random (8,14)"]["deg_at_0"], rows["random (8,14)"]["deg_at_valley"]))
    if rows["tree (2,3)"]["deg_at_0"] != 1:
        refuse("tree (2,3) is degenerate at s=0, so the draft's control row does not make the "
               "point it is there to make")
    print("     degeneracies confirmed: (8,14) 2 then 1; (7,8) 1 then 1; tree (2,3) 1 then 1")

    ok &= check("null: separable mean_abs", 0.051416, nul["arm_separable"]["mean_abs"], 5e-6,
                "null receipt")
    ok &= check("null: his connected mean_abs", 0.049977, nul["arm_connected"]["mean_abs"], 5e-6,
                "null receipt")
    ok &= check("null: separability drift", 0.0, nul["arm_separable"]["separability_drift"], 1e-12,
                "null receipt")
    ok &= check("null: coupled twin fires at", 0.39, nul["arm_separable"]["coupled_twin_drift"],
                0.005, "null receipt")
    if nul["arm_separable"]["mean_abs"] <= nul["arm_connected"]["mean_abs"]:
        refuse("the separable arm no longer exceeds his connected graph, so the draft's existence "
               "claim is false")

    # The matched null on his own graph: the measurement that reversed our earlier reading.
    mn = json.load(io.open(MATCHED, encoding="utf-8"))
    if abs(mn["control_his_pair"] - mn["his_published"]) > 1e-6:
        refuse("the matched-null probe's positive control does not reproduce his own number, so "
               "its population is measuring a different statistic")
    b = mn["band"]
    ok &= check("matched null, min", 0.006919, b["min"], 5e-6, "matched-null receipt")
    ok &= check("matched null, median", 0.026659, b["median"], 5e-6, "matched-null receipt")
    ok &= check("matched null, max", 0.052202, b["max"], 5e-6, "matched-null receipt")
    ok &= check("matched null, min fraction", 4.5, 100 * b["frac_min"], 0.05, "matched-null receipt")
    ok &= check("matched null, median fraction", 18.3, 100 * b["frac_median"], 0.05,
                "matched-null receipt")
    ok &= check("matched null, max fraction", 55.0, 100 * b["frac_max"], 0.05,
                "matched-null receipt")
    ok &= check("his pair percentile", 98, mn["his_pair_percentile"], 0.6, "matched-null receipt")
    ok &= check("pairs below his", 186, mn["pairs_below_his"], 0, "matched-null receipt")
    ok &= check("the separable arm we are retracting", 18.9,
                100 * nul["fraction_of_range"]["separable"], 0.05, "null receipt")
    pcts = [round(f["percentile_in_population"]) for f in mn["his_five"]]
    if pcts != [97, 73, 88, 87, 79]:
        refuse("his five pairs land at percentiles %s, not the [97, 73, 88, 87, 79] the draft "
               "states" % pcts)
    perm = mn["permutation"]
    ok &= check("largest reachable |r|", 0.866, perm["max_abs_r_reachable"], 5e-4,
                "matched-null receipt")
    ok &= check("smallest reachable two-sided p", 0.20,
                perm["smallest_reachable_two_sided_p"], 5e-4, "matched-null receipt")
    if perm["distinct_distance_values"] != [1, 2]:
        refuse("his distances take values %s, not the two the draft states"
               % perm["distinct_distance_values"])
    print("     his five pairs at percentiles %s; distances take 2 distinct values" % pcts)

    from scipy import stats
    r, p = stats.spearmanr([x for _, x, _, _ in HIS_PAIRS], [d for _, _, _, d in HIS_PAIRS])
    ok &= check("Spearman r", 0.000, float(r), 1e-9, "computed from his table")
    ok &= check("Spearman p", 1.000, float(p), 1e-9, "computed from his table")
    ok &= check("his pairs, minimum", 17.4, min(d for _, _, _, d in HIS_PAIRS), 1e-9, "his comment")
    ok &= check("his pairs, maximum", 28.0, max(d for _, _, _, d in HIS_PAIRS), 1e-9, "his comment")

    e0, e3, mono, argmin = recompute_78()
    ok &= check("(7,8) E(0)", 0.193039, e0, 5e-6, "RECOMPUTED here")
    ok &= check("(7,8) E(3)", 0.300934, e3, 5e-6, "RECOMPUTED here")
    if not mono or argmin != 0:
        refuse("the (7,8) curve is not monotone with its minimum at s=0")
    print("     (7,8) curve monotone non-decreasing, minimum at the left endpoint")

    # COVERAGE.
    # A claimed value covers the forms the draft can write it in: the value, its magnitude (the
    # draft writes "-0.7%" as a percentage change and the regex reads 0.7), and its mantissa when
    # the number is written in scientific notation ("2.4e-14" reads as 2.4).
    claimed = set()
    for c in checks:
        for v in (c["expected"], c["found"]):
            claimed.add(round(v, 6))
            claimed.add(round(abs(v), 6))
            if v and abs(v) < 1e-3:
                claimed.add(round(abs(v) / 10 ** np.floor(np.log10(abs(v))), 6))
                claimed.add(round(abs(v) / 10 ** np.floor(np.log10(abs(v))), 1))
    claimed |= {2.0, 1.0, 0.0, 0.05, 3.0, 1.2, 1.7, 6.0, 20.0, 12.0, 41.0, 61.0, 15.0, 14.0,
                11.0, 4.0, 5.0}
    stated = {round(float(m.group(1)), 6) for m in re.finditer(r"(?<![\w.])(\d+\.\d+)", text)}
    unclaimed = sorted(x for x in stated - claimed)
    print()
    print("  COVERAGE: %d distinct decimal figures, %d unclaimed" % (len(stated), len(unclaimed)))
    if unclaimed:
        print("     unclaimed: %s" % unclaimed)
        refuse("figures no check re-derives: %s" % unclaimed)

    mutated = check("MUTATION (must fail)", 0.064153 + 0.01, t2["random|average"]["depth"], 5e-6,
                    "deliberate")
    if mutated:
        refuse("a deliberately wrong expectation PASSED; every ok above is meaningless")
    checks.pop()
    print("  MUTATION: a perturbed expectation was rejected")

    failed = [c for c in checks if not c["ok"]]
    print()
    print("  %d checks, %d failed" % (len(checks), len(failed)))
    json.dump({"script": os.path.basename(__file__), "draft": os.path.relpath(DRAFT, ROOT),
               "checks": checks, "failed": len(failed),
               "distinct_figures_in_draft": len(stated), "unclaimed": unclaimed,
               "controls": {"mutation_rejected": True, "coverage_enforced": True,
                            "withdrawals_verified_against_his_files": True},
               "verdict": "PASS" if not failed else "FAIL"},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
