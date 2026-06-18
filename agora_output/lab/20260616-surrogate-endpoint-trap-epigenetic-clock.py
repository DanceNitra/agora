# Severe test for the second-brain challenge: the vault's "Epigenetic Clocks" note claims the clock
# is "a CAUSAL component of aging - a primary driver, not a consequence", and that since interventions
# that slow aging also slow the clock, slowing the clock is the target. Test the surrogate-endpoint
# logic: if the clock S is correlated with the true outcome Y only via a hidden cause C (plus its own
# variation), does an intervention that improves the MEASURED clock actually improve lifespan?
import numpy as np

rng = np.random.default_rng(42)
N = 200000
C = rng.normal(0, 1, N)                         # hidden true driver (rate of aging / damage)
Y = -(1.2 * C + rng.normal(0, 0.6, N))          # true outcome: higher = longer life (so -C is good)
S = 0.9 * C + rng.normal(0, 0.5, N)             # epigenetic clock: tracks C + its own variation

r_SY = float(np.corrcoef(S, Y)[0, 1])
print(f"Clock looks like a great biomarker: corr(clock S, lifespan Y) = {r_SY:.2f}\n")

delta = 1.0  # same measured improvement in the clock under each intervention
# (i) CAUSAL intervention: actually reduce the driver C by delta/0.9 so the clock drops by `delta`.
C_causal = C - delta / 0.9
Y_causal = -(1.2 * C_causal + rng.normal(0, 0.6, N))
S_causal = 0.9 * C_causal + (S - 0.9 * C)       # clock improves because C improved
# (ii) SURROGATE-TARGETING: make the clock read `delta` younger WITHOUT touching C (act on S's own
#      component) - "cosmetically" reset methylation / target the clock itself.
S_surr = S - delta
Y_surr = Y                                       # C untouched -> true outcome unchanged

print(f"{'intervention':<28}{'mean clock change':>18}{'mean lifespan change':>22}")
print(f"{'(i) target the CAUSE C':<28}{np.mean(S_causal-S):>18.2f}{np.mean(Y_causal-Y):>22.2f}")
print(f"{'(ii) target the CLOCK only':<28}{np.mean(S_surr-S):>18.2f}{np.mean(Y_surr-Y):>22.2f}")

# how much of the clock-lifespan association is non-causal (mediated by S's own variation, not C)?
frac_noncausal = 1 - (0.9**2 * np.var(C)) / np.var(S)
print(f"\nShare of the clock's variance that is NOT the causal driver C: {frac_noncausal:.0%}")
print("VERDICT: same -1.0 clock improvement -> lifespan moves ~"
      f"{np.mean(Y_causal-Y):.2f} if you fix the CAUSE, but ~{np.mean(Y_surr-Y):.2f} if you only move "
      "the CLOCK. A clock with r=0.86 to mortality is a predictor, not proof it is the lever - "
      "'slow the clock' is a surrogate-endpoint bet, not an established causal target.")
