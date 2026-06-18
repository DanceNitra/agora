# Dialectic made measured: "an RCT is always strictly better than a quasi-experimental DiD."
# It is the gold standard for INTERNAL validity (no confounding bias), but it pays in VARIANCE when it
# is small. A large confounded observational/DiD estimate trades a fixed bias for tiny variance. So the
# better design is a bias-variance question: MSE_rct = var (unbiased) vs MSE_obs = bias^2 + var_obs.
# A clean small RCT can be STRICTLY WORSE (higher MSE) than a big mildly-confounded study. Find the
# crossover RCT size. Source: simulation.
import numpy as np
rng = np.random.default_rng(0)

TAU, SIGMA, N_OBS, TRIALS = 2.0, 1.0, 5000, 4000     # true effect, noise, big observational panel size

def mse_rct(n):
    # randomized: unbiased difference in means, n/2 treated + n/2 control
    est = []
    for _ in range(TRIALS):
        nt = n // 2
        t = rng.normal(TAU, SIGMA, nt); c = rng.normal(0.0, SIGMA, n - nt)
        est.append(t.mean() - c.mean())
    e = np.array(est); return float(np.mean((e - TAU) ** 2))

def mse_obs(bias):
    # large observational/DiD panel: low variance (big n) but a FIXED confounding/parallel-trends bias
    est = []
    for _ in range(TRIALS):
        t = rng.normal(TAU + bias, SIGMA, N_OBS); c = rng.normal(0.0, SIGMA, N_OBS)
        est.append(t.mean() - c.mean())
    e = np.array(est); return float(np.mean((e - TAU) ** 2))

print(f"True effect tau={TAU}. Observational panel n={N_OBS} (low variance, fixed bias).\n")
for bias in [0.05, 0.15, 0.30]:
    mo = mse_obs(bias)
    print(f"--- confounding bias = {bias} (obs MSE = {mo:.4f}) ---")
    print(f"  {'RCT size n':>10}{'RCT MSE':>12}{'winner (lower MSE)':>22}")
    cross = None
    for n in [40, 100, 200, 500, 1000, 2000]:
        mr = mse_rct(n)
        win = "RCT" if mr < mo else "observational"
        if win == "RCT" and cross is None: cross = n
        print(f"  {n:>10}{mr:>12.4f}{win:>22}")
    print(f"  => RCT becomes the better design only above n ~ {cross}\n" if cross else
          f"  => observational wins at every RCT size tested (bias too small to matter)\n")
print("=> An RCT is strictly better ONLY when it is large enough that its sampling variance falls below")
print("   the observational design's squared bias. A clean small trial loses to a big mildly-confounded")
print("   one. 'Always run the RCT' is wrong; the right rule is bias^2 vs variance at YOUR sample size.")
