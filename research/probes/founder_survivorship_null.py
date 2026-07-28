"""Founder-led firms' '3.1x edge' -- how much a zero-skill survivorship null reproduces.

Public probe for the Crucible null-result "Founder-led firms' 3.1x edge: mostly survivorship"
(dancenitra.github.io/agora/public/posts/founder-led-survivorship-null.html).

CLAIM under test (Zook & Allen, *The Founder's Mentality*, Bain/HBR Press 2016): founder-led firms returned
~3.1x more than the rest (1990-2014), presented as evidence a "founder's mentality" drives superior long-run
performance.

NULL (skill switched OFF): the founder-led and professional-CEO cohorts have the SAME expected return. The
ONLY differences are mechanical -- the founder cohort is more VOLATILE and DELISTS more often. Then apply the
same look-ahead index filter the statistic uses: count only firms that SURVIVED to the end AND are large
enough to be "in the index". Measure the apparent MEAN and MEDIAN return gap between the two surviving cohorts.

HONEST SCOPE + the load-bearing assumption: the fraction of 3.1x reproduced is DENSITY-DEPENDENT on the
volatility ratio, which is stated and swept (1.4x -> 26%, 1.8x -> 76%, 2.2x -> 179%). The 1.8x central case
assumes founder firms are ~1.8x as volatile (~31%/yr vs ~17%/yr) -- an assumption, not a measured input;
Bain's exact universe is opaque. This shows the index CONSTRUCTION (survivorship + look-ahead inclusion of a
higher-variance cohort) CAN manufacture most of the gap with zero skill, and that the surviving advantage is
tail-driven (mean >> median) -- the survivorship signature. It does NOT prove founder firms have no real edge;
controlled studies (e.g. Fahlenbrach 2009, JFQA) report founder-CEO abnormal returns that survive some
controls, which a survivorship null does not address. Survivorship bias in performance samples is textbook
(Brown, Goetzmann, Ibbotson & Ross 1992, "Survivorship Bias in Performance Studies", Rev. Financial Studies).

Deterministic (fixed seeds; needs numpy):  python founder_survivorship_null.py
MIT-licensed. Part of Agora / inspeximus (https://github.com/DanceNitra/inspeximus).
"""
import statistics as st
import numpy as np

N = 4000
YEARS = 24            # 1990-2014
MU = 0.006            # SAME monthly expected log-return for both cohorts (zero skill difference)
SIG_PROF = 0.05       # professional-CEO monthly volatility (~17%/yr)
RUIN = 0.15           # a firm whose value ever falls below 0.15x delists
SEEDS = 120


def cohort(rng, n, months, sigma):
    r = rng.normal(MU, sigma, size=(n, months))
    val = np.exp(np.cumsum(r, axis=1))
    final = val[:, -1].copy()
    final[val.min(axis=1) < RUIN] = np.nan            # ever below ruin -> delisted
    return final


def run(seed, sig_found, include_pct):
    rng = np.random.default_rng(seed)
    m = YEARS * 12
    prof = cohort(rng, N, m, SIG_PROF)
    found = cohort(rng, N, m, sig_found)
    sp, sf = np.isfinite(prof), np.isfinite(found)
    pooled = np.concatenate([prof[sp], found[sf]])
    cutoff = np.percentile(pooled, include_pct)       # same "be large enough" bar for both cohorts
    inc_p, inc_f = prof[sp & (prof >= cutoff)], found[sf & (found >= cutoff)]
    if len(inc_p) == 0 or len(inc_f) == 0:
        return None
    return {"sp": float(sp.mean()), "sf": float(sf.mean()),
            "gap": float(np.mean(inc_f) / np.mean(inc_p)),
            "gap_med": float(np.median(inc_f) / np.median(inc_p))}


def main():
    print("=== Founder-led 3.1x: zero-skill survivorship null (Monte Carlo, %d seeds) ===" % SEEDS)
    print("Both cohorts have the SAME expected return; the founder cohort only differs by higher volatility\n"
          "+ more delisting. Apparent gap after the same survive-and-be-large index filter:\n")
    print(" vol ratio | survival prof/found | index bar | MEAN gap (%% of 3.1x) | MEDIAN gap")
    rows = {}
    for sig_f in (0.07, 0.09, 0.11):
        for inc in (50, 70):
            res = [x for x in (run(SEEDS * 0 + s, sig_f, inc) for s in range(SEEDS)) if x]
            gap = st.mean(x["gap"] for x in res)
            gapm = st.mean(x["gap_med"] for x in res)
            sp = st.mean(x["sp"] for x in res)
            sf = st.mean(x["sf"] for x in res)
            rows[(sig_f, inc)] = (gap, gapm)
            print("   %.2fx   |     %.2f / %.2f      |  top %d%%  |   %.2fx  (%4.0f%%)    |   %.2fx"
                  % (sig_f / SIG_PROF, sp, sf, 100 - inc, gap, (gap - 1) / 2.1 * 100, gapm))

    gap, gapm = rows[(0.09, 50)]
    print("\nMEASURED (central case, ~1.8x volatility, top-50%% index): with IDENTICAL expected returns, pure")
    print("survivorship + look-ahead inclusion shows an apparent MEAN gap of %.2fx (%.0f%% of Bain's 3.1x) from" % (gap, (gap - 1) / 2.1 * 100))
    print("ZERO skill -- yet the MEDIAN gap is only %.2fx, so the 'advantage' lives in the extreme upper tail" % gapm)
    print("(where survivorship operates), not the typical founder firm. The 1.8x volatility is an ASSUMPTION")
    print("(swept above: 1.4x->26%%, 2.2x->179%%); grounding it against real founder-firm volatility is the open task.")
    print("VERDICT (mechanism):", "FAILED -- index construction of a higher-variance cohort reproduces most of the "
          "3.1x with no skill, tail-driven (median << mean)." if gap >= 2.0 else "PARTIAL.")


if __name__ == "__main__":
    main()
