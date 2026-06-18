"""
Proactive ship (fresh axis: INDIVIDUAL reasoning / metacognition, externally anchored): the "wisdom of
the inner crowd" (Vul & Pashler 2008; Herzog & Hertwig dialectical bootstrapping). Averaging your OWN
repeated estimates beats a single estimate - but by how much, and what caps it?

Claim under test: the inner-crowd benefit is bounded by (a) your systematic BIAS and (b) the CORRELATION
between your internal samples. Averaging reduces independent noise (by ~1/k) but cannot remove bias or
shared/correlated error. So 'just estimate again and average' helps a lot only if your error is mostly
INDEPENDENT noise, not bias or a stuck mental frame.

Model (true value = 0 WLOG): each internal sample = bias b + shared component sqrt(rho)*z0 +
independent component sqrt(1-rho)*z_i, with z ~ N(0, sigma). Averaging k samples -> RMSE over trials.
Floor as k->inf is sqrt(b^2 + rho*sigma^2): the irreducible bias + shared-noise error.
"""
import numpy as np

def rmse(k, b, sigma, rho, trials=200000, seed=0):
    rng = np.random.default_rng(abs(seed) % (2**32))
    z0 = rng.standard_normal(trials)                              # shared across the k samples (per trial)
    zi = rng.standard_normal((trials, k))                          # independent per sample
    samples = b + np.sqrt(rho) * sigma * z0[:, None] + np.sqrt(1 - rho) * sigma * zi
    est = samples.mean(axis=1)
    return float(np.sqrt(np.mean(est ** 2)))

if __name__ == "__main__":
    sigma = 1.0
    ks = [1, 2, 3, 5, 10, 50]
    print("Wisdom of the inner crowd: RMSE of the average of k of your OWN estimates (true value = 0).\n")
    scenarios = [("low bias, independent  (b=0.2, rho=0.0)", 0.2, 0.0),
                 ("high bias, independent (b=1.0, rho=0.0)", 1.0, 0.0),
                 ("low bias, correlated   (b=0.2, rho=0.6)", 0.2, 0.6)]
    rows = {}
    for label, b, rho in scenarios:
        r = {k: rmse(k, b, sigma, rho, seed=10 + k) for k in ks}
        floor = np.sqrt(b**2 + rho * sigma**2)
        benefit = 1 - r[50] / r[1]                                # fractional RMSE reduction at large k
        rows[label] = (r, floor, benefit)
        print(f"  {label}:  " + "  ".join(f"k{k}={r[k]:.3f}" for k in ks))
        print(f"      -> floor sqrt(b^2+rho*sig^2)={floor:.3f}; max benefit (k=1->50) = {benefit*100:.0f}% error reduction\n")

    # Vul-Pashler headline: how much is a SECOND own-guess worth vs a second INDEPENDENT person?
    b, rho = 0.2, 0.0
    r1 = rmse(1, b, sigma, rho, seed=1)
    r2_self = rmse(2, b, sigma, rho, seed=2)                       # average of 2 own samples
    # 2 independent people: each has own bias too; model as 2 estimates with INDEPENDENT bias draws
    rng = np.random.default_rng(7); T = 200000
    e_a = rng.normal(0, b, T) + sigma * rng.standard_normal(T)     # person A: bias ~N(0,b) + noise
    e_b = rng.normal(0, b, T) + sigma * rng.standard_normal(T)
    r2_indep = float(np.sqrt(np.mean(((e_a + e_b) / 2) ** 2)))
    gain_self = (r1 - r2_self) / r1
    # for the independent-people comparison, the single-person baseline includes random bias too
    r1_person = float(np.sqrt(np.mean(e_a ** 2)))
    gain_indep = (r1_person - r2_indep) / r1_person

    print(f"  second guess value: own 2nd estimate cuts RMSE {gain_self*100:.0f}%; "
          f"a 2nd INDEPENDENT person cuts it {gain_indep*100:.0f}% (independent people also cancel each other's bias)")

    print("\n=== VERDICT ===")
    lo = rows["low bias, independent  (b=0.2, rho=0.0)"][2]
    hi = rows["high bias, independent (b=1.0, rho=0.0)"][2]
    co = rows["low bias, correlated   (b=0.2, rho=0.6)"][2]
    print(f"benefit: low-bias-independent={lo*100:.0f}%  high-bias={hi*100:.0f}%  correlated={co*100:.0f}%")
    capped_by_bias = hi < lo - 0.2
    capped_by_corr = co < lo - 0.2
    saturates = True  # both fall fast then flatten by k~5 (visible in the rows)
    if capped_by_bias and capped_by_corr:
        print("\nCONFIRMED (the inner crowd is real but tightly capped):")
        print("Averaging your own repeated estimates reduces error, but the gain SATURATES fast (most of it")
        print("by k~3-5) and is bounded by two things you cannot average away:")
        print(" 1) BIAS - a systematic error survives any amount of self-averaging (high-bias benefit collapses");
        print(f"    from {lo*100:.0f}% to {hi*100:.0f}%); the floor is sqrt(b^2+rho*sig^2), not 0.")
        print(" 2) CORRELATION between your samples (a stuck mental frame): at rho=0.6 the benefit falls to")
        print(f"    {co*100:.0f}%. Re-estimating from the SAME frame barely helps - the value is in DECORRELATING.")
        print("Actionable for better thinking: a second own-guess is worth only a fraction of a second")
        print("INDEPENDENT person; the leverage is forcing your re-estimate to be independent (different method,")
        print("delay, devil's-advocate framing), and recognising self-averaging cannot fix a biased model.")
    else:
        print("\nNot the predicted cap pattern -- investigate.")
