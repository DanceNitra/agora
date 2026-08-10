"""Is recency-only actually separated from random, or are those two overlapping means?

WHY THIS EXISTS. Our RAG-freshness post reports, at a 50% keep budget in the realistic regime, that a
recency-only keep policy retains 62% of the value-oracle while random retains 56%. A prior-art review
of the caching literature objected, correctly: 6 points with a stated sd of 1-2% over 20 seeds is not
*obviously* separated, and the number carries weight in the post, so it needs an interval rather than
two means printed side by side.

THE FIRST VERSION OF THIS FILE MEASURED THE WRONG WORLD. It built its own store generator -- a
stronger age-value coupling than ragfresh uses -- and reported recency at 88.2%. The separation was
real for that construction and said nothing about the published 62%. Measuring a reconstruction of
someone else's method is a rule we already have; here the someone else was us.

So the generator and the scoring below are ragfresh's own, copied VERBATIM from its `__main__`
(that block is not importable), and the first thing this file does is REPRODUCE the published means
at the published seed count. If that control fails, nothing after it is about our post.

Exit 0 with the table; the assertions fail loudly if a conclusion inverts.
"""
from __future__ import annotations

import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ragfresh"))
from ragfresh import Item, _retention_score        # noqa: E402  (the library's own scorer)

DAY = 86400.0
NOW = 1_000_000_000.0
N, BUDGET = 1000, 500
PUBLISHED_SEEDS = 20          # what the post ran
SEEDS = 400                   # what this file runs, once the control passes
BOOT = 20000


def make_store(seed, age_tracks_value):
    """VERBATIM from ragfresh.__main__ -- do not 'improve' it; the point is that it is theirs."""
    rng = random.Random(seed)
    store, tv = [], {}
    for i in range(N):
        v = rng.random() ** 3
        if age_tracks_value:
            age = (1 - v) * rng.expovariate(1 / 40.0) + rng.expovariate(1 / 90.0)
        else:
            age = rng.expovariate(1 / 60.0)
        hits = int(max(0, rng.gauss(v * 40, 8)))
        orphan = rng.random() < 0.06
        it = Item(id=f"c{i}", updated_ts=NOW - age * DAY,
                  last_access_ts=NOW - rng.expovariate(1 / 30.0) * DAY,
                  hits=hits, value=v, source_exists=not orphan, bytes=4096)
        store.append(it)
        tv[it.id] = v if not orphan else 0.0
    return store, tv


def obs_score(it):
    shadow = Item(it.id, it.updated_ts, it.last_access_ts, it.hits, None, it.source_exists, it.bytes)
    return _retention_score(shadow, NOW, 120.0)


def arms(store, tv, seed, second_random_seed=None):
    live = [it for it in store if it.source_exists]
    oracle = sum(sorted(tv.values(), reverse=True)[:BUDGET]) or 1.0
    keep = lambda key: sorted(live, key=key, reverse=True)[:BUDGET]          # noqa: E731
    ret = lambda k: sum(tv[it.id] for it in k) / oracle                      # noqa: E731
    out = {
        "value-only (oracle labels)": ret(keep(lambda it: it.value)),
        "value x freshness (oracle)": ret(keep(lambda it: _retention_score(it, NOW, 120.0))),
        "hits-proxy x freshness": ret(keep(obs_score)),
        "hits-only": ret(keep(lambda it: it.hits)),
        "recency-only": ret(keep(lambda it: it.updated_ts)),
        "random": ret(random.Random(seed).sample(live, BUDGET)),
    }
    if second_random_seed is not None:                                        # the control's 2nd draw
        out["random-B"] = ret(random.Random(second_random_seed).sample(live, BUDGET))
    return out


def _ci(d, rng):
    idx = rng.integers(0, len(d), size=(BOOT, len(d)))
    m = d[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main() -> int:
    # ---- CONTROL FIRST: reproduce the published run, or stop. ------------------------------------
    ctrl = {}
    for s in range(PUBLISHED_SEEDS):
        st, tv = make_store(s, True)
        for k, v in arms(st, tv, s).items():
            ctrl.setdefault(k, []).append(v)
    pub_rec = 100 * float(np.mean(ctrl["recency-only"]))
    pub_rnd = 100 * float(np.mean(ctrl["random"]))
    print("CONTROL -- reproducing the published run (%d seeds, age~value):" % PUBLISHED_SEEDS)
    for k, v in ctrl.items():
        print("   %-28s %5.1f%%" % (k, 100 * float(np.mean(v))))
    assert 60.0 <= pub_rec <= 64.0, (
        "this file does not reproduce the post's recency-only 62%% (got %.1f%%): it is measuring a "
        "different store generator, and nothing below would be about our published number" % pub_rec)
    assert 54.0 <= pub_rnd <= 58.0, "random did not reproduce the post's 56%% (got %.1f%%)" % pub_rnd
    print("   -> reproduces the post (recency %.1f%%, random %.1f%%). Proceeding.\n" % (pub_rec, pub_rnd))

    # ---- the interval, paired by seed --------------------------------------------------------
    rec, rnd_a, rnd_b = [], [], []
    for s in range(SEEDS):
        st, tv = make_store(s, True)
        a = arms(st, tv, s, second_random_seed=s + 10_000)
        rec.append(a["recency-only"]); rnd_a.append(a["random"]); rnd_b.append(a["random-B"])
    rec, rnd_a, rnd_b = np.array(rec), np.array(rnd_a), np.array(rnd_b)
    rng = np.random.default_rng(20260810)

    print("PAIRED over %d seeds (same store per seed):" % SEEDS)
    print("  recency-only  %5.1f%%  (sd %.1f)" % (100 * rec.mean(), 100 * rec.std(ddof=1)))
    print("  random        %5.1f%%  (sd %.1f)" % (100 * rnd_a.mean(), 100 * rnd_a.std(ddof=1)))

    d = rec - rnd_a
    lo, hi = _ci(d, rng)
    se = d.std(ddof=1) / np.sqrt(len(d))
    print("\n  recency MINUS random: %+.2f pp   95%% bootstrap CI [%+.2f, %+.2f]   t=%.1f   wins %d/%d"
          % (100 * d.mean(), 100 * lo, 100 * hi, d.mean() / se if se else float("inf"),
             int((d > 0).sum()), SEEDS))

    dc = rnd_a - rnd_b
    clo, chi = _ci(dc, rng)
    print("  CONTROL random-vs-random: %+.2f pp   95%% CI [%+.2f, %+.2f]  (must straddle 0)"
          % (100 * dc.mean(), 100 * clo, 100 * chi))

    sep = lo > 0
    print("\nMEASURED: at a 50%% keep budget in the realistic regime, recency-only beats random by "
          "%+.1f pp (95%% CI %+.1f..%+.1f)." % (100 * d.mean(), 100 * lo, 100 * hi))
    print("VERDICT: the two means ARE separated -- but the honest report is the paired interval and "
          "\n         the gap's SIZE, not '62 vs 56'. Recency is a weak-but-real baseline here, and it "
          "\n         is weak because this is a one-shot keep decision with no request recurrence, "
          "\n         where age informs only through its correlation with value.")

    assert clo < 0 < chi, ("the CONTROL separates random from itself -- the harness manufactures "
                           "differences and nothing above can be believed")
    assert sep, ("recency-only is NOT separated from random (CI %.2f..%.2f pp) -- the post's 62 vs 56 "
                 "must be restated, not defended" % (100 * lo, 100 * hi))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
