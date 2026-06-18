
import numpy as np
rng = np.random.default_rng(13)
# Regression to the mean: a manager targets the WORST performers for a (null, zero-effect) program,
# then measures their improvement. Each person's score = stable skill theta + transient luck. Selecting
# on a noisy period-1 score picks the unlucky; period-2 they bounce back -> the null program looks
# effective. How big is this spurious effect, as a function of measurement reliability?
N = 50000
theta = rng.standard_normal(N)                       # stable skill (sd 1)
def spurious(reliability):
    # reliability r = var(skill)/var(score); noise sd from r
    noise_sd = np.sqrt((1-reliability)/reliability)
    s1 = theta + rng.standard_normal(N)*noise_sd
    s2 = theta + rng.standard_normal(N)*noise_sd      # period 2, NO real effect
    cut = np.percentile(s1, 10)                       # bottom 10% targeted
    sel = s1 <= cut
    return float(s2[sel].mean() - s1[sel].mean())     # apparent 'improvement' (true effect = 0)
print("Targeting bottom 10% for a ZERO-effect program; apparent improvement is pure regression to the mean:")
print(" reliability   spurious 'improvement' (SD units)")
for r in [0.9, 0.7, 0.5, 0.3]:
    print(f"   {r:.1f}         {spurious(r):+.2f}")
print("True program effect = 0. The entire measured 'improvement' is RTM; it grows as measurement gets noisier.")
