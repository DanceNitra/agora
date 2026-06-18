"""
CAPSTONE: the Science-of-Better-Thinking protocol, tested end-to-end (not asserted).

Every rule below is a measured result from this session; the unifying principle (the retrospective's
through-line) is: good reasoning = maximize the EFFECTIVE-INDEPENDENT evidence and resist the forces
that collapse it (correlation, herding, bias, internal-coherence-as-confidence).

We don't summarize the rules - we BUILD a reasoner that follows them and MEASURE its accuracy +
CALIBRATION against a naive reasoner, across an adversarial environment of correlated / herded /
biased sources. The claim: the protocol's advantage GROWS with the adversarial structure, and its
biggest win is honest CALIBRATION (the naive reasoner is overconfident because it treats correlated
sources as independent evidence).

Environment: estimate a true value theta (=0). K=12 sources grouped into G independent LINEAGES (echo
chambers / shared-origin sources). Within a lineage, estimates are near-copies (herded, correlated);
across lineages, independent. Some lineages carry a systematic BIAS. Effective independent evidence =
G, not K. The reasoner observes each source's estimate AND its lineage tag (provenance - realistic:
you usually know which sources are independent).

  NAIVE reasoner   : mean of all K; confidence from K (treats every source as independent evidence).
  PROTOCOL reasoner: one vote per LINEAGE (effective-independence); robust aggregate (median of lineage
                     means, resists biased lineages); confidence from G (calibrated to real independence).
"""
import numpy as np

def trial(G, K=12, sigma_lin=1.0, within=0.08, frac_biased=0.34, bias_mag=1.6, directional=False, seed=0):
    rng = np.random.default_rng(abs(seed) % (2**32))
    # assign K sources to G lineages (roughly even)
    lin_of = np.array([i % G for i in range(K)])
    # each lineage: an independent draw around theta=0, plus maybe a systematic bias
    biased = rng.random(G) < frac_biased
    sign = np.ones(G) if directional else rng.choice([-1, 1], G)   # directional = a one-way false consensus
    lin_center = sigma_lin * rng.standard_normal(G) + biased * (bias_mag * sign)
    est = np.array([lin_center[lin_of[i]] + within * rng.standard_normal() for i in range(K)])

    # NAIVE: all K independent
    naive_mu = est.mean()
    naive_se = est.std(ddof=1) / np.sqrt(K)

    # PROTOCOL: one vote per lineage (effective independence) + robust + calibrated confidence
    lin_means = np.array([est[lin_of == g].mean() for g in range(G)])
    proto_mu = np.median(lin_means)                      # robust to biased lineages
    proto_se = lin_means.std(ddof=1) / np.sqrt(G) if G > 1 else lin_means.std() + 0.5
    return naive_mu, naive_se, proto_mu, proto_se

def evaluate(G, trials=4000, **kw):
    nmu, nse, pmu, pse = [], [], [], []
    for s in range(trials):
        a, b, c, d = trial(G, seed=s, **kw)
        nmu.append(a); nse.append(b); pmu.append(c); pse.append(d)
    nmu, nse, pmu, pse = map(np.array, (nmu, nse, pmu, pse))
    def cover(mu, se):                                   # 95% CI coverage of the truth (theta=0)
        return float(np.mean(np.abs(mu) <= 1.96 * se))
    return {"G": G,
            "naive_rmse": float(np.sqrt(np.mean(nmu**2))), "proto_rmse": float(np.sqrt(np.mean(pmu**2))),
            "naive_cover": cover(nmu, nse), "proto_cover": cover(pmu, pse)}

if __name__ == "__main__":
    print("Better-Thinking protocol vs naive reasoner. K=12 sources; G independent lineages (echo chambers).")
    print("Truth theta=0. Lower RMSE = more accurate; 95% CI coverage near 0.95 = well-calibrated.\n")
    print("  G (independent lineages) | RMSE naive -> protocol | 95%-CI coverage naive -> protocol")
    rows = [evaluate(G) for G in [12, 8, 4, 2]]
    for r in rows:
        herd = {12: "none", 8: "mild", 4: "strong", 2: "severe"}[r["G"]]
        print(f"    G={r['G']:<2} (herding {herd:<6})    | {r['naive_rmse']:.3f} -> {r['proto_rmse']:.3f}"
              f"          | {r['naive_cover']:.2f} -> {r['proto_cover']:.2f}")

    sev = rows[-1]  # G=2, severe herding
    indep = rows[0]  # G=12, fully independent
    calib_better = sev["proto_cover"] - sev["naive_cover"] > 0.3
    grows = (sev["naive_cover"] < indep["naive_cover"] - 0.2)   # naive miscalibration WORSENS with herding

    # The honest LIMIT: a MAJORITY directional herd (most lineages biased one way) defeats ANY aggregation
    # -> truth needs EXTERNAL GROUNDING, not cleverer averaging (the Grounding-Coupling Law).
    maj = evaluate(4, directional=True, frac_biased=0.8, bias_mag=1.6)
    maj_both_fail = maj["naive_rmse"] > 0.8 and maj["proto_rmse"] > 0.8

    print("\n=== VERDICT ===")
    print(f"protocol CALIBRATION beats naive, and the gap GROWS with herding: {calib_better and grows}")
    print(f"  coverage at severe herding: naive {sev['naive_cover']:.2f} vs protocol {sev['proto_cover']:.2f}")
    print(f"  (point-RMSE is comparable: {sev['naive_rmse']:.2f} vs {sev['proto_rmse']:.2f} - calibration, not accuracy, is the win)")
    print(f"HONEST LIMIT - majority directional herd (80% lineages biased one way): BOTH fail on accuracy: {maj_both_fail}")
    print(f"  RMSE naive {maj['naive_rmse']:.2f}, protocol {maj['proto_rmse']:.2f} -> no aggregation recovers truth")
    if calib_better and grows:
        print("\nPROTOCOL VALIDATED (end-to-end, measured) - and its limit mapped:")
        print("Weighting by EFFECTIVE INDEPENDENCE (one vote per independent lineage) + a ROBUST aggregate +")
        print("confidence set by the number of INDEPENDENT sources delivers a decisive CALIBRATION win: under")
        print(f"heavy herding the naive reasoner is wildly OVERCONFIDENT (95% CI covers truth only {sev['naive_cover']:.0%}) while")
        print(f"the protocol stays calibrated ({sev['proto_cover']:.0%}), and the gap GROWS with the herding. Point accuracy is")
        print("COMPARABLE (the win is honest uncertainty, not a better estimate - the same lesson as SC-vs-DiD")
        print("and the inner crowd this session). The HONEST LIMIT: against a MAJORITY directional herd, NO")
        print("aggregation rule recovers truth (both fail) - that requires EXTERNAL GROUNDING, exactly the")
        print("Grounding-Coupling Law. Master rule: count INDEPENDENT evidence not sources; never read")
        print("confidence off mere agreement; and when the herd is the majority, only an external anchor saves you.")
    else:
        print("\nCalibration advantage not as predicted -- investigate.")
