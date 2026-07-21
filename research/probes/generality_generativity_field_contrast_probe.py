"""
[SUPERSEDED 2026-07-08] The ML/CS field result below did NOT survive a pre-registered domain-neutral
robustness test: swapping Semantic Scholar's CS-trained influentialCitationCount for a classifier-free
build-on proxy erased the ML effect (partial +0.11..+0.14 -> -0.02). The apparent generality->build-on
effect is metric-specific, not a robust field property. Use generality_generativity_metric_dependence_probe.py
instead. This file is kept for provenance of the earlier (S2-metric-only) analysis.

Does an idea's GENERALITY predict its GENERATIVITY (getting genuinely built upon),
at birth, on real data -- and is the answer the same across fields?

Frontier question (Agora): is idea generativity predictable at generation time, or purely
path-dependent? The literature conflates "generativity" with raw citation count. We separate
them using Semantic Scholar's `influentialCitationCount` -- S2's classifier flag for citations
that genuinely BUILD ON a paper (vs merely mention it). Generativity := influential (build-on)
citations. Popularity := raw citation count.

Intrinsic-at-birth signal := content GENERALITY, rated 0-10 from the ABSTRACT ALONE (reference-
blind, so non-circular) by LLM judges: 0 = a narrow single-purpose result tied to one
dataset/task/disease; 10 = a broad general-purpose method/framework reusable across problems.

The decisive test is the PARTIAL rank correlation of generality with build-on CONTROLLING FOR
raw popularity -- i.e. does generality predict genuine build-on BEYOND merely getting cited?
(The raw generality->influential correlation is inflated by popularity and misleads; use the
partial. This distinction cost the authors three false "wins" before they trusted the partial.)

RESULT (this dataset: 347 ML/CS + 414 Medicine papers, 2015-17, min 5 citations):

  ML/CS field   -- partial(generality, build-on | popularity) EXCLUDES 0 for every rater:
                   deepseek +0.11, kimi +0.14 (95% CIs above 0). Generality predicts GENUINE
                   build-on beyond popularity.
  MEDICINE field -- partial ~ 0 for FOUR independent raters (deepseek, Claude, kimi, GLM-5.2:
                   -0.05..-0.03). Generality here buys raw citations/attention but NOT build-on.

So generativity-predictability-from-generality is FIELD-DEPENDENT: in a methods field general
ideas get genuinely reused; in a clinical field "generality" buys attention, not generativity.
Robust across 4 LLM raters (so not a rater artifact) and controls popularity (so not a raw-
correlation artifact). Honest scope: ML-vs-Medicine specifically; magnitudes are small (~0.13);
to claim "methods vs clinical" broadly, add a second field of each type.

Data: data/generality_generativity_ratings.jsonl -- one row per paper with field, the raw and
influential citation counts, and each LLM rater's 0-10 generality score. (No titles/abstracts/PII;
just integers.) The LLM rating step is non-deterministic, so the ratings are shipped; this script
recomputes every statistic from them with zero dependencies.

Run: python generality_generativity_field_contrast_probe.py
"""
import json
import math
import os
import random


def load():
    path = os.path.join(os.path.dirname(__file__), "data", "generality_generativity_ratings.jsonl")
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def rankdata(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def _pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((x - mb) ** 2 for x in b))
    return num / (da * db) if da > 0 and db > 0 else 0.0


def spearman(a, b):
    return _pearson(rankdata(a), rankdata(b))


def _resid(y, x):
    # residual of y on x (both mean-centered rank vectors)
    b = sum(x[i] * y[i] for i in range(len(x))) / sum(v * v for v in x)
    return [y[i] - b * x[i] for i in range(len(y))]


def partial_spearman(g, inf, raw):
    """rank-partial correlation of g with inf, controlling for raw."""
    rg, ri, rr = rankdata(g), rankdata(inf), rankdata(raw)
    mg, mi, mr = sum(rg) / len(rg), sum(ri) / len(ri), sum(rr) / len(rr)
    rg = [v - mg for v in rg]
    ri = [v - mi for v in ri]
    rr = [v - mr for v in rr]
    return _pearson(_resid(rg, rr), _resid(ri, rr))


def bootstrap_partial_ci(g, inf, raw, iters=3000, seed=5):
    rng = random.Random(seed)
    n = len(g)
    vals = []
    for _ in range(iters):
        idx = [rng.randrange(n) for _ in range(n)]
        vals.append(partial_spearman([g[i] for i in idx], [inf[i] for i in idx], [raw[i] for i in idx]))
    vals.sort()
    lo = vals[int(0.025 * iters)]
    hi = vals[int(0.975 * iters)]
    return lo, hi


def analyze(rows, field, rater):
    sel = [r for r in rows if r["field"] == field and rater in r["gen"]]
    g = [r["gen"][rater] for r in sel]
    inf = [r["influential"] for r in sel]
    raw = [r["raw"] for r in sel]
    raw_rho = spearman(g, inf)
    pop_rho = spearman(g, raw)
    part = partial_spearman(g, inf, raw)
    lo, hi = bootstrap_partial_ci(g, inf, raw)
    return len(sel), raw_rho, pop_rho, part, lo, hi


if __name__ == "__main__":
    rows = load()
    print("generality -> generativity (build-on), by field and rater")
    print("  raw = Spearman(gen, influential) ; pop = Spearman(gen, raw citations)")
    print("  PARTIAL = gen vs build-on CONTROLLING popularity  (the decisive 'beyond attention' test)\n")
    for field, label in (("ML", "ML / CS  "), ("MED", "MEDICINE ")):
        raters = sorted({k for r in rows if r["field"] == field for k in r["gen"]})
        for rater in raters:
            n, raw_rho, pop_rho, part, lo, hi = analyze(rows, field, rater)
            excl = "excludes 0" if (lo > 0 or hi < 0) else "straddles 0"
            print(f"  {label} {rater:9} n={n:3}  raw={raw_rho:+.3f}  pop={pop_rho:+.3f}  "
                  f"PARTIAL={part:+.3f} CI[{lo:+.3f},{hi:+.3f}] {excl}")
        print()
    print("Verdict: ML partial excludes 0 (build-on-specific signal); Medicine partial straddles 0")
    print("across all raters -> generality predicts genuine generativity in a methods field, not a clinical one.")
