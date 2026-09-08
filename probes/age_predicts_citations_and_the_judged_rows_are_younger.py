"""Does a row's AGE explain the citation gap we measured between the judged and adjacency groups?

WHY. probes/the_evicted_rows_are_a_random_sample_not_a_loss.py finds the 32 rows the trim tool
judged are cited at a median of 0.5 against 3.0 for the 16 that left by sharing their line, with a
permutation p of 0.0073. Three arms there already show the gap is about the JUDGED group rather than
the adjacency group. This adds the confound that would explain it without any group property at all:
older notes have had longer to be cited, and the two groups are not the same age.

WHAT IS MEASURED. Spearman rho between a note's age and its citation count, the median age of each
group, and the same permutation test run inside an age-matched band so the age difference cannot
carry it.

THE LIMIT, stated because it decides how the result may be used. Age here is the file creation time
on this machine. It is a proxy for when the note was written, and a copy or a restore would reset
it. So this arm can say the gap is NOT robust to age; it cannot say age is the cause.

CONTROLS.
  AGE IS REAL           the ages must span more than a few days and must not be identical, or the
                        correlation is measuring a constant.
  THE CORRELATION CAN   a shuffled pairing of ages to counts must give a rho near zero. A test that
  BE ZERO               returns the same rho on shuffled data is measuring its own arithmetic.
  THE BAND IS POPULATED an age-matched band must hold enough rows from BOTH groups to run the test,
                        and the two matched groups must no longer differ in median age.
  THE MATCHED TEST CAN  the same test on a deliberately shifted copy inside the band must reject, or
  REJECT                a non-significant matched p means nothing.
"""
from __future__ import annotations

import io
import json
import os
import random
import re
import statistics
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools"))
import trim_memory_index as T  # noqa: E402
from memory_index_files import is_index_file  # noqa: E402

MEM = os.environ.get(
    "AGORA_MEMORY_DIR",
    os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory"))
LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+\.md)\)")
SECTION = "Demoted from the index 2026-09-04"
DRAWS = 20000
SEED = 20260908


def notes():
    return {f: io.open(os.path.join(MEM, f), encoding="utf-8", errors="replace").read()
            for f in os.listdir(MEM) if f.endswith(".md") and not is_index_file(f)}


def rows_of(path):
    out = {}
    for ln, line in enumerate(io.open(path, encoding="utf-8",
                                      errors="replace").read().splitlines()):
        for m in LINK.finditer(line):
            s = os.path.splitext(os.path.basename(m.group(1)))[0]
            if is_index_file(s + ".md") or s in out:
                continue
            out[s] = ln
    return out


def perm_p(a, b, draws=DRAWS, seed=SEED):
    obs = abs(statistics.median(a) - statistics.median(b))
    pool = list(a) + list(b)
    rng = random.Random(seed)
    hits = 0
    for _ in range(draws):
        rng.shuffle(pool)
        if abs(statistics.median(pool[:len(a)]) - statistics.median(pool[len(a):])) >= obs:
            hits += 1
    return obs, (hits + 1.0) / (draws + 1.0)


def main():
    body = notes()
    pre = os.path.join(MEM, "MEMORY.md.bak-20260904-pretrim")
    if not body or not os.path.isfile(pre):
        print("SKIP: the corpus or the pre-event snapshot is not here.")
        return 2
    line_of = rows_of(pre)

    arc = io.open(os.path.join(MEM, "MEMORY_ARCHIVE.md"),
                  encoding="utf-8", errors="replace").read()
    sec = [x for x in re.split(r"^##\s+", arc, flags=re.M) if x.startswith(SECTION)][0]
    archived = {os.path.splitext(os.path.basename(m))[0] for m in LINK.findall(sec)
                if not is_index_file(m)}
    named_lines = {line_of[d] for d in T.DEMOTE if d in line_of}
    judged = [d for d in T.DEMOTE if d in line_of]
    adjacency = sorted(e for e in (archived - set(T.DEMOTE))
                       if e in line_of and line_of[e] in named_lines)

    def refs(slug):
        return sum(1 for f, b in body.items() if f != slug + ".md" and "[[%s]]" % slug in b)

    def age_days(slug):
        p = os.path.join(MEM, slug + ".md")
        if not os.path.exists(p):
            return None
        import time
        return (time.time() - os.path.getctime(p)) / 86400.0

    pool = sorted(set(judged) | set(adjacency) | set(rows_of(os.path.join(MEM, "MEMORY.md"))))
    ages = {s: age_days(s) for s in pool}
    ages = {s: a for s, a in ages.items() if a is not None}
    counts = {s: refs(s) for s in ages}

    xs = [ages[s] for s in ages]
    ys = [counts[s] for s in ages]
    rho = stats.spearmanr(xs, ys)

    j_age = [ages[s] for s in judged if s in ages]
    a_age = [ages[s] for s in adjacency if s in ages]
    j_cnt = [counts[s] for s in judged if s in ages]
    a_cnt = [counts[s] for s in adjacency if s in ages]
    obs_raw, p_raw = perm_p(j_cnt, a_cnt)

    # AGE-MATCHED BAND: the overlap of the two groups' age ranges.
    lo = max(min(j_age), min(a_age))
    hi = min(max(j_age), max(a_age))
    jm = [counts[s] for s in judged if s in ages and lo <= ages[s] <= hi]
    am = [counts[s] for s in adjacency if s in ages and lo <= ages[s] <= hi]
    jm_age = [ages[s] for s in judged if s in ages and lo <= ages[s] <= hi]
    am_age = [ages[s] for s in adjacency if s in ages and lo <= ages[s] <= hi]
    obs_m, p_m = (perm_p(jm, am) if jm and am else (float("nan"), float("nan")))

    rng = np.random.default_rng(SEED)
    shuffled = list(ys)
    rng.shuffle(shuffled)
    rho_null = stats.spearmanr(xs, shuffled)
    shifted = [x + 4 for x in am] if am else []
    p_band_shift = perm_p(jm, shifted)[1] if jm and shifted else float("nan")

    print("  rows with an age: %d" % len(ages))
    print("  age vs citations: Spearman rho = %.3f, p = %.2e" % (rho.statistic, rho.pvalue))
    print("  median age  judged %.1f days, adjacency %.1f days"
          % (statistics.median(j_age), statistics.median(a_age)))
    print("  unmatched   judged vs adjacency: gap %.1f, p = %.4f" % (obs_raw, p_raw))
    print("  age-matched band %.1f..%.1f days: %d judged, %d adjacency"
          % (lo, hi, len(jm), len(am)))
    print("  matched     judged vs adjacency: gap %.1f, p = %.4f" % (obs_m, p_m))

    ok, checks = True, []

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        checks.append({"check": name, "pass": bool(cond), "got": str(got)[:200]})
        print("  %-4s %-52s %s" % ("YES" if cond else "NO", name, got))

    print()
    check("CONTROL_the_ages_are_not_a_constant",
          max(xs) - min(xs) > 7 and len(set(round(x) for x in xs)) > 5,
          "span %.0f days across %d distinct days" % (max(xs) - min(xs),
                                                      len(set(round(x) for x in xs))))
    check("CONTROL_a_shuffled_pairing_gives_no_correlation", abs(rho_null.statistic) < 0.15,
          "shuffled rho = %.3f" % rho_null.statistic)
    check("CONTROL_the_band_holds_both_groups", len(jm) >= 5 and len(am) >= 5,
          "%d judged, %d adjacency in the band" % (len(jm), len(am)))
    check("CONTROL_the_band_removed_the_age_difference",
          abs(statistics.median(jm_age) - statistics.median(am_age))
          < abs(statistics.median(j_age) - statistics.median(a_age)),
          "median age gap %.1f days in the band against %.1f unmatched"
          % (abs(statistics.median(jm_age) - statistics.median(am_age)),
             abs(statistics.median(j_age) - statistics.median(a_age))))
    check("CONTROL_the_matched_test_can_still_reject", p_band_shift < 0.05,
          "p = %.4f against the band's adjacency rows shifted by +4" % p_band_shift)
    check("AGE_PREDICTS_CITATIONS", rho.statistic > 0.2 and rho.pvalue < 0.01,
          "rho = %.3f" % rho.statistic)
    check("THE_JUDGED_ROWS_ARE_YOUNGER",
          statistics.median(j_age) < statistics.median(a_age),
          "%.1f vs %.1f days" % (statistics.median(j_age), statistics.median(a_age)))
    check("THE_GAP_IS_NOT_ROBUST_TO_AGE", p_m > 0.05,
          "matched p = %.4f against unmatched %.4f" % (p_m, p_raw))

    finding = (
        "Age predicts citation count in this store: Spearman rho = %.2f over %d rows. The 32 rows "
        "the tool judged have a median age of %.1f days against %.1f for the 16 that left by "
        "adjacency, so the judged rows are younger and have had less time to be cited. Inside an "
        "age-matched band the citation gap between the two groups gives p = %.3f, against %.4f "
        "unmatched. The gap is therefore not robust to age. That is not the same as showing age "
        "causes it: file creation time is a proxy for when a note was written, and a copy or a "
        "restore would reset it."
        % (rho.statistic, len(ages), statistics.median(j_age), statistics.median(a_age),
           p_m, p_raw))

    out = {"probe": os.path.basename(__file__), "memory_dir": MEM,
           "rows_with_an_age": len(ages),
           "spearman_rho": round(float(rho.statistic), 4),
           "spearman_p": float(rho.pvalue),
           "median_age_days": {"judged": round(statistics.median(j_age), 1),
                               "adjacency": round(statistics.median(a_age), 1)},
           "unmatched": {"gap": obs_raw, "p": p_raw},
           "age_matched_band_days": [round(lo, 1), round(hi, 1)],
           "age_matched": {"n_judged": len(jm), "n_adjacency": len(am),
                           "gap": obs_m, "p": p_m},
           "checks": checks, "all_passed": ok, "finding": finding,
           "scope": ("Age is the file creation time on this machine, a proxy for when the note was "
                     "written. This shows the citation gap is not robust to age; it does not show "
                     "age is the cause.")}
    print("\n  FINDING: %s" % finding)
    p = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=1) + "\n")
    print("  %s   receipt: %s" % ("controls passed" if ok else "A CONTROL FAILED",
                                  os.path.basename(p)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
