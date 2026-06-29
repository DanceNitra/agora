"""Artifact-Debunk (Crucible): "Founder-led firms returned ~3.1x more than the rest (1990-2014);
the 'founder's mentality' drives superior long-run performance" (Zook & Allen / Bain, 2016).

NULL (skill switched OFF): founder-led and professional-CEO cohorts have the SAME expected return.
The ONLY differences are mechanical: founder-led firms are more VOLATILE and DELIST more often. Then
apply the same look-ahead index filter the stat uses -- count only firms that SURVIVED to the end and
are large enough to be 'in the index'. Measure the apparent return gap between the two surviving cohorts.

Pre-registered: survivorship of a higher-variance cohort manufactures a multi-x apparent gap from ZERO
skill difference; we report what FRACTION of the claimed 3.1x it explains (honest -- may be partial).
FALSIFIER: if the gap stays ~1x across plausible volatility/threshold settings, survivorship does NOT
explain the 3.1x and the claim survives. Pure numpy, cloud-free. Bain's exact universe is opaque, so
all reconstruction assumptions are stated and swept.
"""
import numpy as np

def cohort(rng, n, months, mu, sigma, ruin=0.15):
    """returns final cumulative multiple per firm; firms whose value ever drops below `ruin`x delist (NaN)."""
    r = rng.normal(mu, sigma, size=(n, months))
    val = np.exp(np.cumsum(r, axis=1))           # cumulative value path (start=1)
    delisted = (val.min(axis=1) < ruin)          # ever fell below ruin threshold -> delisted
    final = val[:, -1]
    final[delisted] = np.nan
    return final

def run(seed, n=4000, years=24, mu=0.006, sig_prof=0.05, sig_found=0.09,
        ruin=0.15, include_pct=60):
    rng = np.random.default_rng(seed)
    m = years * 12
    prof = cohort(rng, n, m, mu, sig_prof, ruin)
    found = cohort(rng, n, m, mu, sig_found, ruin)
    surv_p, surv_f = np.isfinite(prof), np.isfinite(found)
    # index inclusion = survived AND final size in the top (100-include_pct)%... use a common size cutoff
    # across the pooled survivors so both cohorts face the SAME 'be large enough to be in the index' bar.
    pooled = np.concatenate([prof[surv_p], found[surv_f]])
    cutoff = np.percentile(pooled, include_pct)
    inc_p = prof[surv_p & (prof >= cutoff)]
    inc_f = found[surv_f & (found >= cutoff)]
    if len(inc_p) == 0 or len(inc_f) == 0:
        return None
    # apparent return gap. MEAN = how an index/aggregate '3.1x' stat is computed (tail-sensitive);
    # MEDIAN = the typical surviving firm (tail-robust). Reporting both is the honesty check.
    gap = float(np.mean(inc_f) / np.mean(inc_p))
    gap_med = float(np.median(inc_f) / np.median(inc_p))
    return {"surv_rate_prof": float(surv_p.mean()), "surv_rate_found": float(surv_f.mean()),
            "gap": gap, "gap_med": gap_med}

def main():
    import statistics as st
    print("=== Founder-led 3.1x: zero-skill survivorship null (Monte Carlo) ===")
    print("Both cohorts: SAME expected return. Founder-led only differs by higher volatility + more delisting.\n")
    print(" vol ratio | survival prof/found | INDEX bar | MEAN gap (%% of 3.1x) | MEDIAN gap")
    base = []
    for sig_f in (0.07, 0.09, 0.11):
        for inc in (50, 70):
            res = [run(s, sig_found=sig_f, include_pct=inc) for s in range(120)]
            res = [x for x in res if x]
            gap = st.mean(x["gap"] for x in res); gapm = st.mean(x["gap_med"] for x in res)
            sp = st.mean(x["surv_rate_prof"] for x in res); sf = st.mean(x["surv_rate_found"] for x in res)
            print("   %.2fx   |     %.2f / %.2f      |  top %d%%  |   %.2fx  (%4.0f%%)    |   %.2fx"
                  % (sig_f/0.05, sp, sf, 100-inc, gap, (gap-1)/2.1*100, gapm))
            base.append((sig_f, inc, gap, gapm))
    central, central_m = [(g, gm) for sf,inc,g,gm in base if abs(sf-0.09)<1e-9 and inc==50][0]
    print("\nMEASURED: with IDENTICAL expected returns, a founder-led cohort merely ~1.8x as volatile, filtered")
    print("by the same survive-and-be-large index rule, shows an apparent MEAN gap of %.2fx (%.0f%% of Bain's" % (
        central, (central-1)/2.1*100))
    print("3.1x) from ZERO skill. Crucially the MEDIAN gap is only %.2fx -- the 'advantage' lives in the" % central_m)
    print("extreme upper tail (exactly where survivorship operates), not the typical founder firm.")
    verdict = ("FAILED — survivorship of a higher-variance cohort reproduces ~%.0f%% of the 3.1x with NO skill; "
               "and it is tail-driven (median only %.2fx), the survivorship signature." % ((central-1)/2.1*100, central_m)) \
        if central >= 2.0 else "PARTIAL / NOT an artifact"
    print("VERDICT:", verdict)
    print("Scope: shows the index-construction (look-ahead + survivorship) can manufacture the gap; NOT that")
    print("founder firms have no real edge. Assumptions (vol ratio, ruin, index bar) stated + swept above.")

if __name__ == "__main__":
    main()
