"""Does a paper's content-GENERALITY predict how much it gets genuinely BUILT UPON — and
does that apparent effect survive changing how "built upon" is measured?

Honest cautionary tale (a construct-validity check on citation-impact metrics). We hypothesised
that content-generality (rated 0-10 reference-blind from the ABSTRACT ALONE by LLM judges; 0 =
narrow single-purpose, 10 = broad reusable method) predicts GENUINE build-on — operationalised as
Semantic Scholar's `influentialCitationCount` (a classifier flag for citations that build on a
paper, Valenzuela, Escarcega-Ha & Etzioni 2015) — BEYOND raw-citation popularity.

The decisive statistic is the rank-PARTIAL correlation of generality with build-on CONTROLLING
FOR raw citation count (does generality predict build-on beyond merely getting cited?). The raw
correlation is inflated by popularity and misleads — use the partial.

RESULT on real Semantic Scholar data (2015-17, min 5-8 citations; 345 ML/CS + 413 Medicine papers,
same papers rated by deepseek-v4-flash and kimi-k2.7-code):

1. WITH S2's influential-citation metric, a SMALL apparent effect in ML/CS:
     partial(generality, S2-influential | raw) = +0.11 (deepseek) / +0.14 (kimi), 95% CI excludes 0.
     Medicine: ~0. (Small magnitudes — a weak-to-modest effect, not a strong law.)

2. PRE-REGISTERED domain-neutral swap — replace S2's CS-trained classifier with a classifier-FREE
   build-on proxy, FOCUSED-CITER = # of citing papers whose OWN reference list is short (<= field
   median), i.e. genuine users not survey-listers (field-normalized, no classifier). The ML effect
   DISAPPEARS: partial(generality, focused-citer | raw) = -0.02 / -0.03, CI straddles 0.

3. POSITIVE CONTROL (does focused-citer even have the POWER to detect a ~0.13 build-on correlate?):
     partial(focused-citer, S2-influential | raw) = +0.17 (ML) — yes, it captures build-on structure
     beyond popularity at a magnitude ABOVE the effect we were testing for. So the null in (2) is NOT
     mere proxy noise; the generality signal simply does not transfer to an equally-powered,
     classifier-free build-on measure.

CONCLUSION (honestly scoped): the generality->build-on effect is METRIC-SPECIFIC /
operationalization-dependent — it lives in Semantic Scholar's influential-citation operationalization
and does not survive a classifier-free proxy that is demonstrably powered to see build-on. This is
CONSISTENT WITH (but not proof of) the influential-citation classifier's CS home-field advantage
(the classifier was trained on ~465 ACL/CS citations). Limits: magnitudes are small; ONE classifier-
free proxy (not two); two fields (ML/CS, Medicine). The lesson is a standard construct-validity check,
not a new method: if swapping your influential-citation detector erases a result, the result was
measurement-specific.

Data: data/generality_generativity_rescue_data.json — per paper: field, raw citations, S2 influential
count, focused-citer count, and each LLM rater's 0-10 generality. (Integers only; no PII.) Zero deps.

Run: python generality_generativity_metric_dependence_probe.py
"""
import json
import math
import os
import random


def load():
    p = os.path.join(os.path.dirname(__file__), "data", "generality_generativity_rescue_data.json")
    return json.load(open(p, encoding="utf-8"))


def rankdata(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1.0
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
    b = sum(x[i] * y[i] for i in range(len(x))) / (sum(v * v for v in x) or 1.0)
    return [y[i] - b * x[i] for i in range(len(y))]


def partial(a, o, ctrl):
    """rank-partial correlation of a with o, controlling for ctrl."""
    ra, ro, rc = rankdata(a), rankdata(o), rankdata(ctrl)
    ma, mo, mc = sum(ra) / len(ra), sum(ro) / len(ro), sum(rc) / len(rc)
    ra = [v - ma for v in ra]
    ro = [v - mo for v in ro]
    rc = [v - mc for v in rc]
    return _pearson(_resid(ra, rc), _resid(ro, rc))


def boot_ci(a, o, ctrl, seed=5, B=3000):
    rng = random.Random(seed)
    n = len(a)
    vals = []
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        vals.append(partial([a[i] for i in idx], [o[i] for i in idx], [ctrl[i] for i in idx]))
    vals.sort()
    return vals[int(0.025 * B)], vals[int(0.975 * B)]


def cols(rows, rater):
    g = [r["gen"][rater] for r in rows if rater in r["gen"]]
    s2 = [r["s2i"] for r in rows if rater in r["gen"]]
    fo = [r["_focused"] for r in rows if rater in r["gen"]]
    rw = [r["raw"] for r in rows if rater in r["gen"]]
    return g, s2, fo, rw


if __name__ == "__main__":
    d = load()
    print("generality -> build-on: is the apparent effect robust to how 'build-on' is measured?\n")
    for field, label in (("ML", "ML / CS "), ("MED", "MEDICINE")):
        rows = d[field]
        print(f"--- {label} (n={len(rows)}) ---")
        raters = sorted({k for r in rows for k in r["gen"]})
        # positive control uses any rater's rows for the raw/s2/focused columns (rater-independent)
        _, s2c, foc, rwc = cols(rows, raters[0])
        pc = partial(foc, s2c, rwc)
        print(f"  positive control  partial(focused-citer, S2-influential | raw) = {pc:+.3f}"
              f"   (>0 => focused-citer has power to see build-on beyond popularity)")
        for rater in raters:
            g, s2, fo, rw = cols(rows, rater)
            p_s2 = partial(g, s2, rw); l2, h2 = boot_ci(g, s2, rw)
            p_fo = partial(g, fo, rw); lf, hf = boot_ci(g, fo, rw)
            e2 = "excl 0" if (l2 > 0 or h2 < 0) else "straddles 0"
            ef = "excl 0" if (lf > 0 or hf < 0) else "straddles 0"
            print(f"  {rater:9}: gen->S2-influential partial={p_s2:+.3f} CI[{l2:+.3f},{h2:+.3f}] {e2}"
                  f"  |  gen->FOCUSED(classifier-free) partial={p_fo:+.3f} CI[{lf:+.3f},{hf:+.3f}] {ef}")
        print()
    print("Read: ML gen->S2-influential excludes 0 (small effect); gen->focused-citer straddles 0 while")
    print("focused-citer has power (positive control > 0). => the effect is metric-specific, not robust")
    print("across build-on operationalizations. Construct-validity cautionary tale, not a proven artifact.")
