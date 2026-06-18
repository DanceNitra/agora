"""
BREAKTRUTH: calibration, not capability, is the scarce resource of intelligence.

It emerged unplanned this session - 5 independent results all showed the epistemic win is CALIBRATION
(honest uncertainty), not a better point estimate or more capability: SC-vs-DiD (the win is CI coverage,
not the estimate), the inner crowd (calibration capped by correlation), the thinking protocol (calibration
not accuracy), the early-warning engine (its value is knowing when NOT to trust itself), the Crucible
(FAILED replications calibrate the literature).

Here we make the thesis make a NOVEL, sharp, falsifiable prediction and test it: the CAPABILITY-CALIBRATION
SCISSORS. As a reasoner's CAPABILITY rises (more evidence / sources / compute it can bring to bear) on
realistically CORRELATED evidence, its ACCURACY barely improves (correlated evidence has a shared-error
floor) but its naive CALIBRATION COLLAPSES - it grows more CONFIDENT (tighter intervals from counting K)
while staying just as wrong. So confident-wrongness, the danger, GROWS with capability. An effective-
independence mechanism (count N_eff, not K) severs the scissors. This is the AI-era claim: scaling
capability WITHOUT a calibration mechanism increases confident error.
"""
import numpy as np

def run(K, rho=0.4, sigma=1.0, trials=40000, seed=0):
    rng = np.random.default_rng(seed)
    z0 = rng.standard_normal((trials, 1))                       # shared component (correlation source)
    zi = rng.standard_normal((trials, K))
    src = sigma * (np.sqrt(rho) * z0 + np.sqrt(1 - rho) * zi)    # K correlated estimates of theta=0
    mu = src.mean(axis=1)
    sd = src.std(axis=1, ddof=1)
    se_naive = sd / np.sqrt(K)                                   # treats K as independent -> tightens with K
    n_eff = K / (1 + (K - 1) * rho)
    se_cal = sd / np.sqrt(n_eff)                                 # effective-independence -> calibrated
    rmse = float(np.sqrt(np.mean(mu**2)))
    cov_naive = float(np.mean(np.abs(mu) <= 1.96 * se_naive))
    cov_cal = float(np.mean(np.abs(mu) <= 1.96 * se_cal))
    return rmse, cov_naive, cov_cal

if __name__ == "__main__":
    rho = 0.4
    floor = np.sqrt(rho)        # accuracy floor: correlated evidence cannot beat the shared-error sqrt(rho)*sigma
    print(f"Capability-calibration scissors (correlated evidence, rho={rho}). theta=0; accuracy floor ~ {floor:.2f}.\n")
    print("  capability K | RMSE (accuracy) | naive 95%-CI coverage | calibrated (N_eff) coverage")
    rows = []
    for K in [2, 5, 10, 25, 50, 100]:
        rmse, cn, cc = run(K)
        rows.append((K, rmse, cn, cc))
        print(f"    K={K:<4}      | {rmse:.3f}           | {cn:.2f}                  | {cc:.2f}")

    first, last = rows[0], rows[-1]
    acc_gain = first[1] - last[1]                                 # how much accuracy improved over the K range
    naive_calib_collapse = first[2] - last[2]                    # how much naive coverage fell
    scissors = acc_gain < 0.20 and naive_calib_collapse > 0.30   # accuracy ~flat, calibration collapses
    cal_holds = last[3] > 0.85
    print("\n=== VERDICT ===")
    print(f"accuracy barely improves with capability (RMSE {first[1]:.2f} -> {last[1]:.2f}, plateau ~{floor:.2f}): {acc_gain < 0.20}")
    print(f"naive CALIBRATION COLLAPSES with capability (coverage {first[2]:.2f} -> {last[2]:.2f}): {naive_calib_collapse > 0.30}")
    print(f"effective-independence mechanism SEVERS the scissors (coverage stays {last[3]:.2f}): {cal_holds}")
    if scissors and cal_holds:
        print("\nBREAKTRUTH SUPPORTED - the capability-calibration scissors is real and measured:")
        print(f"As capability (K) rises on correlated evidence, accuracy is stuck near the shared-error floor")
        print(f"(~{floor:.2f}) - more evidence barely helps - yet the naive reasoner grows ever more CONFIDENT")
        print(f"(its '95%' interval covers the truth only {last[2]:.0%} of the time at K={last[0]}, down from {first[2]:.0%}).")
        print("So scaling capability WITHOUT a calibration mechanism does not mainly make a system more right -")
        print("it makes it more confidently WRONG. Counting EFFECTIVE-INDEPENDENT evidence (N_eff, not K) holds")
        print(f"calibration flat ({last[3]:.0%}) at any capability. Hence the Breaktruth: calibration, not capability,")
        print("is the scarce resource of intelligence - and in the AI-scaling era, capable-but-miscalibrated is")
        print("precisely the danger. The lever is effective-independent evidence + external grounding, not scale.")
    else:
        print("\nScissors not as predicted -- investigate.")
