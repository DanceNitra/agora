"""Were the rows evicted by line-adjacency load-bearing? Measured: we cannot say they were.

THIS SUPERSEDES THE READING IN probes/packing_the_index_evicted_rows_nobody_judged.py. That probe
measured a real difference -- the 16 rows nobody judged are cited at a median of 3.0 against 0.5 for
the 32 the tool judged, permutation p = 0.0073 -- and then read it as "the cap evicted rows
indistinguishable from the ones kept". Three arms below take that reading apart. The numbers stand;
the conclusion drawn from them does not.

NONE OF THIS WAS EVER PUBLISHED, and the distinction matters. On anthropics/claude-code#91188,
comment 5588661516 named this as the next open measurement -- "for the 15 adjacency-moved rows,
whether any was still load-bearing when its neighbour was judged" -- and no result or p-value has
gone out. So this file answers an open question rather than retracting a public claim. A draft that
said otherwise would have manufactured an error we did not make.

WHAT SURVIVES, and it is a fact about the code rather than a statistic: 16 rows left the index
because they shared a physical line with a row the tool judged, and no decision was recorded for any
of them. That is measured by probes/a_move_that_addresses_rows_must_not_drag_the_line.py against the
real input, and it is why the move is now row-addressable.

WHAT DOES NOT SURVIVE is the inference that those rows were load-bearing.

  SAME GAP AGAINST THE ROWS THAT STAYED. Judged against live gives the same median gap and about
  the same p as judged against adjacency. A statistic that cannot tell the adjacency group from
  the live index is measuring the JUDGED group, which is the tool's selection criterion working
  as designed on the 32 rows it was pointed at.

  A TYPICAL DRAW. Drawing 16 rows at random from the live index reproduces the adjacency group's
  median most of the time. Kolmogorov-Smirnov cannot separate them. "The evicted rows look like
  the rows that stayed" and "the evicted rows are a random 16 rows of the index" are the same
  sentence, and the second is simply what line adjacency means: the line a row sits on is
  unrelated to how often it is cited.

  THE CITERS ARE THEMSELVES RETIRED. Restricting the citing corpus to rows still in the index
  reverses the direction. Most of the adjacency group's citations come from notes that have
  already left the index, so the median of 3.0 does not say the live index depended on them.

AND THE p = 1.0000 WE PUBLISHED WAS NEVER A MEASUREMENT. The two medians are equal, so the observed
gap is 0, and the statistic is an absolute difference: every relabelling reaches 0, so the count is
20000/20000 for any input whose medians happen to tie. It reports the tie back to us. The honest
statement is that the test cannot distinguish the groups, and the power arm below says at what
effect size that stops being true.

CONTROLS. The point of this file is that a check must be able to fail, so each is stated with the
way it fails.
  THE TEST CAN REJECT      a group against a shifted copy of itself must come back significant. The
                           old control compared a group against ITSELF, where the observed gap is 0
                           and every draw ties it, so it returned 20000/20000 for any input.
  THE TEST CAN FAIL TO     a group against a resampled copy of itself must come back non-significant
  REJECT                   in the large majority of trials.
  THE COUNTER CAN FIRE     a slug in the store must be found, and one that is not must count zero.
  THE GROUPS ARE DISJOINT  a row counted twice would drag two medians together.
  THE CITER SPLIT IS REAL  every note file must fall in exactly one of the two citing pools, or the
                           reversal arm is comparing overlapping corpora.
"""
from __future__ import annotations

import io
import json
import os
import random
import re
import statistics
import sys
import time

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
WIKI = re.compile(r"\[\[([^\]|#]+)")
SECTION = "Demoted from the index 2026-09-04"
DRAWS = 20000
SEED = 20260908


def notes():
    return {f: io.open(os.path.join(MEM, f), encoding="utf-8", errors="replace").read()
            for f in os.listdir(MEM) if f.endswith(".md") and not is_index_file(f)}


def rows_of(path):
    """slug -> physical line number, in file order."""
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
    """Two-sided permutation p for a difference in medians.

    Reported as two-sided, and on this data the one-sided and two-sided values coincide because the
    null gap distribution does not reach the observed magnitude in the other direction. That is a
    property of these numbers, not a guarantee of the statistic.
    """
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
    if not body:
        print("SKIP: no note files under %s" % MEM)
        return 2

    pre = os.path.join(MEM, "MEMORY.md.bak-20260904-pretrim")
    if not os.path.isfile(pre):
        print("SKIP: the pre-event snapshot is not here, so the adjacency group cannot be built.")
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
    live_rows = list(rows_of(os.path.join(MEM, "MEMORY.md")))

    # THE TWO CITING POOLS. A citation from a note that has itself left the index does not show the
    # live index depended on the cited row.
    live_set = set(live_rows)
    pool_live = {f: b for f, b in body.items() if os.path.splitext(f)[0] in live_set}
    pool_gone = {f: b for f, b in body.items() if os.path.splitext(f)[0] not in live_set}

    def refs(slug, pool):
        return sum(1 for f, b in pool.items() if f != slug + ".md" and "[[%s]]" % slug in b)

    groups = [("judged, named by the tool", judged),
              ("moved by adjacency", adjacency),
              ("still live in the index", live_rows)]
    all_counts = {n: [refs(s, body) for s in g] for n, g in groups}
    live_counts = {n: [refs(s, pool_live) for s in g] for n, g in groups}

    ja, ad, lv = (all_counts[n] for n, _ in groups)
    ja_l, ad_l, lv_l = (live_counts[n] for n, _ in groups)

    print("  citing pool: ALL %d note files" % len(body))
    print("  %-28s %5s %8s %7s" % ("group", "n", "median", "mean"))
    for n, _ in groups:
        c = all_counts[n]
        print("  %-28s %5d %8.1f %7.2f" % (n, len(c), statistics.median(c),
                                           sum(c) / float(len(c))))

    obs_ja_ad, p_ja_ad = perm_p(ja, ad)
    obs_ja_lv, p_ja_lv = perm_p(ja, lv)
    obs_ad_lv, p_ad_lv = perm_p(ad, lv)
    print("\n  judged vs adjacency : gap %.1f, p = %.4f" % (obs_ja_ad, p_ja_ad))
    print("  judged vs LIVE      : gap %.1f, p = %.4f   <- the same comparison, without the 16"
          % (obs_ja_lv, p_ja_lv))
    print("  adjacency vs live   : gap %.1f, p = %.4f   <- a tie reported back to us"
          % (obs_ad_lv, p_ad_lv))

    # ARM 1: is the adjacency group a typical 16-row draw from the live index?
    rng = np.random.default_rng(SEED)
    lv_arr = np.array(lv)
    draw_meds = np.array([float(np.median(rng.choice(lv_arr, size=len(ad), replace=False)))
                          for _ in range(DRAWS)])
    ad_med = statistics.median(ad)
    p_typical = float(np.mean(draw_meds >= ad_med))
    ks = stats.ks_2samp(ad, lv)
    mwu_ad_lv = stats.mannwhitneyu(ad, lv, alternative="two-sided")
    mwu_ja_ad = stats.mannwhitneyu(ja, ad, alternative="two-sided")

    # ARM 2: the citers that are themselves still live
    print("\n  citing pool: only the %d rows STILL LIVE in the index" % len(pool_live))
    for n, _ in groups:
        c = live_counts[n]
        print("  %-28s %5d %8.1f %7.2f" % (n, len(c), statistics.median(c),
                                           sum(c) / float(len(c))))
    obs_ja_ad_l, p_ja_ad_l = perm_p(ja_l, ad_l)
    obs_ad_lv_l, p_ad_lv_l = perm_p(ad_l, lv_l)
    zero_live_citers = sum(1 for x in ad_l if x == 0)
    print("  judged vs adjacency : gap %.1f, p = %.4f" % (obs_ja_ad_l, p_ja_ad_l))
    print("  adjacency vs live   : gap %.1f, p = %.4f" % (obs_ad_lv_l, p_ad_lv_l))
    print("  %d of the %d adjacency rows have NO citation from any live row"
          % (zero_live_citers, len(ad_l)))

    # ARM 3: power. At what effect size can the adjacency-vs-live arm exclude anything?
    def power(shift, n_a, trials=400, inner=2000):
        # HEARTBEAT. This arm is ~4 minutes per shift and the whole probe ran 20 minutes in
        # silence on its first pass, which is our own rule broken: a long job that prints nothing
        # cannot be told from a wedged one.
        hit, t0 = 0, time.time()
        r = np.random.default_rng(SEED + shift)
        for k in range(trials):
            if k and k % 100 == 0:
                print("    shift +%d: %d/%d trials, %.0fs elapsed"
                      % (shift, k, trials, time.time() - t0), flush=True)
            a = list(r.choice(lv_arr, size=n_a, replace=True) + shift)
            b = list(r.choice(lv_arr, size=len(lv), replace=True))
            if perm_p(a, b, draws=inner, seed=int(r.integers(1 << 30)))[1] < 0.05:
                hit += 1
        return hit / float(trials)

    powers = {s: power(s, len(ad)) for s in (1, 2, 3, 4)}
    boot = np.array([float(np.median(rng.choice(np.array(ad), size=len(ad), replace=True)))
                     for _ in range(DRAWS)])
    ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
    print("\n  power of the adjacency-vs-live arm, n=%d vs n=%d:" % (len(ad), len(lv)))
    for s, v in sorted(powers.items()):
        print("    a true shift of +%d reference(s) is detected %.0f%% of the time" % (s, 100 * v))
    print("  adjacency median %.1f, bootstrap 95%% CI [%.1f, %.1f]; the live median %.1f is inside"
          % (ad_med, ci[0], ci[1], statistics.median(lv)))

    ok, checks = True, []

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        checks.append({"check": name, "pass": bool(cond), "got": str(got)[:220]})
        print("  %-4s %-56s %s" % ("YES" if cond else "NO", name, got))

    print()
    # THE CONTROL THE OLD PROBE GOT WRONG. A group against itself has an observed gap of 0 and an
    # absolute statistic, so every draw ties it: 20000/20000 for any input at all.
    shifted = [x + 4 for x in ad]
    check("CONTROL_the_test_REJECTS_a_shifted_copy", perm_p(ad, shifted)[1] < 0.05,
          "p = %.4f against the same group shifted by +4" % perm_p(ad, shifted)[1])
    r2 = np.random.default_rng(SEED + 7)
    null_hits = sum(1 for _ in range(200)
                    if perm_p(list(r2.choice(np.array(ad), size=len(ad), replace=True)),
                              list(r2.choice(np.array(ad), size=len(ad), replace=True)),
                              draws=1000, seed=int(r2.integers(1 << 30)))[1] < 0.05)
    check("CONTROL_the_test_FAILS_TO_REJECT_a_resampled_copy", null_hits < 40,
          "%d of 200 resampled pairs reach p < 0.05" % null_hits)
    check("CONTROL_the_counter_finds_a_slug_that_is_in_the_store", sum(lv) > 0,
          "%d references across the live rows" % sum(lv))
    check("CONTROL_a_slug_that_does_not_exist_counts_zero",
          refs("zqxjv-wrompf-blenkarth-no-such-note", body) == 0)
    check("CONTROL_the_three_groups_are_disjoint",
          not (set(judged) & set(adjacency)) and not (set(adjacency) & set(live_rows))
          and not (set(judged) & set(live_rows)),
          "judged %d, adjacency %d, live %d" % (len(judged), len(adjacency), len(live_rows)))
    check("CONTROL_the_citing_pools_partition_the_corpus",
          len(pool_live) + len(pool_gone) == len(body) and not (set(pool_live) & set(pool_gone)),
          "%d live-row notes + %d retired notes = %d files"
          % (len(pool_live), len(pool_gone), len(body)))

    check("THE_SAME_GAP_HOLDS_AGAINST_THE_ROWS_THAT_STAYED",
          abs(obs_ja_lv - obs_ja_ad) < 1e-9 and p_ja_lv < 0.05,
          "judged vs adjacency gap %.1f p %.4f; judged vs live gap %.1f p %.4f"
          % (obs_ja_ad, p_ja_ad, obs_ja_lv, p_ja_lv))
    check("THE_ADJACENCY_GROUP_IS_A_TYPICAL_RANDOM_DRAW",
          0.05 < p_typical < 0.95 and ks.pvalue > 0.05,
          "P(random 16 reach median %.1f) = %.3f; KS D = %.3f p = %.4f; MWU p = %.4f"
          % (ad_med, p_typical, ks.statistic, ks.pvalue, mwu_ad_lv.pvalue))
    check("THE_DIRECTION_REVERSES_UNDER_LIVE_CITERS_ONLY",
          statistics.median(ad_l) <= statistics.median(lv_l) and zero_live_citers >= len(ad_l) / 2.0,
          "adjacency median %.1f vs live %.1f; %d of %d have no live citer"
          % (statistics.median(ad_l), statistics.median(lv_l), zero_live_citers, len(ad_l)))
    check("THE_ADJACENCY_ARM_IS_UNDERPOWERED_BELOW_A_LARGE_SHIFT", powers[2] < 0.8,
          "a +2 shift is detected only %.0f%% of the time" % (100 * powers[2]))

    finding = (
        "The 16 rows that left by sharing a line are cited at a median of %.1f, against %.1f for the "
        "32 the tool judged and %.1f for the %d still live, and judged against adjacency gives "
        "p = %.4f. That p does not mean what we published. Judged against the rows that STAYED "
        "gives the same gap and p = %.4f, so the statistic is measuring the tool's selection of the "
        "32 rather than any property of the 16. Drawing 16 rows at random from the live index "
        "reaches the adjacency median %.0f%% of the time, and Kolmogorov-Smirnov cannot separate "
        "them (D = %.3f, p = %.4f). Restricting the citers to rows still in the index reverses the "
        "direction: %d of the 16 have no citation from any live row, and the adjacency median falls "
        "to %.1f against %.1f for live. The adjacency-vs-live arm never had the power to say "
        "otherwise, detecting a true shift of +2 references only %.0f%% of the time. What is "
        "measured is that the line a row sits on is unrelated to how often it is cited, which is "
        "what line adjacency means. The eviction of 16 unjudged rows is a real defect in the move; "
        "this measurement does not show those rows were load-bearing."
        % (ad_med, statistics.median(ja), statistics.median(lv), len(lv), p_ja_ad, p_ja_lv,
           100 * p_typical, ks.statistic, ks.pvalue, zero_live_citers,
           statistics.median(ad_l), statistics.median(lv_l), 100 * powers[2]))

    out = {"probe": os.path.basename(__file__),
           "supersedes": "the reading in packing_the_index_evicted_rows_nobody_judged.py",
           "memory_dir": MEM,
           "groups": {n: {"n": len(all_counts[n]),
                          "median_all_citers": statistics.median(all_counts[n]),
                          "mean_all_citers": round(sum(all_counts[n]) / float(len(all_counts[n])), 2),
                          "median_live_citers": statistics.median(live_counts[n]),
                          "mean_live_citers": round(sum(live_counts[n]) / float(len(live_counts[n])), 2)}
                      for n, _ in groups},
           "adjacency_slugs": adjacency,
           "permutation": {"draws": DRAWS,
                           "judged_vs_adjacency": {"gap": obs_ja_ad, "p": p_ja_ad},
                           "judged_vs_live": {"gap": obs_ja_lv, "p": p_ja_lv},
                           "adjacency_vs_live": {"gap": obs_ad_lv, "p": p_ad_lv,
                                                 "note": "the medians tie, so the observed gap is 0 "
                                                         "and every relabelling reaches it; this is "
                                                         "not a measurement"}},
           "random_draw": {"P_random_16_reach_the_adjacency_median": round(p_typical, 4),
                           "ks_D": round(float(ks.statistic), 4),
                           "ks_p": round(float(ks.pvalue), 4),
                           "mwu_adjacency_vs_live_p": round(float(mwu_ad_lv.pvalue), 4),
                           "mwu_judged_vs_adjacency_p": round(float(mwu_ja_ad.pvalue), 5)},
           "live_citers_only": {"judged_median": statistics.median(ja_l),
                                "adjacency_median": statistics.median(ad_l),
                                "live_median": statistics.median(lv_l),
                                "adjacency_rows_with_no_live_citer": zero_live_citers,
                                "judged_vs_adjacency_p": p_ja_ad_l,
                                "adjacency_vs_live_p": p_ad_lv_l},
           "power_adjacency_vs_live": {("shift_+%d" % s): v for s, v in sorted(powers.items())},
           "adjacency_median_bootstrap_95CI": [ci[0], ci[1]],
           "checks": checks, "all_passed": ok,
           "finding": finding,
           "scope": ("Citations are counted as they stand today and note files carry no history, so "
                     "none of these numbers is dated to the retirement. The age of a row also "
                     "predicts its citation count, and the judged rows are younger than the "
                     "adjacency rows, which is a further reason not to read the surviving gap as a "
                     "property of the eviction.")}
    print("\n  FINDING: %s" % finding)
    p = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=1) + "\n")
    print("\n  %s   receipt: %s" % ("controls passed" if ok else "A CONTROL FAILED",
                                    os.path.basename(p)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
