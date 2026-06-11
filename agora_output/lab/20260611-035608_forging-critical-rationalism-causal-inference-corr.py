import numpy as np
rng = np.random.default_rng(23)

# Critical Rationalism -> Causal Inference.
# Popper: a theory is corroborated (not proven) by SURVIVING severe falsification attempts.
# Map: a causal estimate is corroborated by surviving independent falsification tests
# (placebo-in-time, placebo-in-space, leave-one-out, pre-trend...). Claim: among estimates
# that survive k of N tests, the false-discovery rate (fraction actually spurious) FALLS as k
# rises - corroboration is real, not rhetoric. Falsifier: if FDR is flat in k, the analogy dies.

N_TESTS = 5
N = 40000
PRIOR_TRUE = 0.30                 # 30% of candidate causal claims are genuinely non-null
# a falsification test PASSES (fails to refute) a true effect with high prob, a spurious one
# with a lower prob (tests are imperfect: some power, some false-pass)
PASS_IF_TRUE = 0.85              # power-ish: true effects usually survive a placebo test
PASS_IF_SPURIOUS = 0.45         # spurious effects survive a single weak test ~half the time

truth = rng.random(N) < PRIOR_TRUE
p = np.where(truth, PASS_IF_TRUE, PASS_IF_SPURIOUS)
survived = (rng.random((N, N_TESTS)) < p[:, None]).sum(axis=1)   # how many of N tests each passed

print("Critical Rationalism -> Causal Inference: false-discovery rate vs tests survived")
print(f"(prior true {PRIOR_TRUE:.0%}, pass|true {PASS_IF_TRUE}, pass|spurious {PASS_IF_SPURIOUS}, "
      f"{N_TESTS} tests, N={N})\n")
print(f"{'survived k/5':>12} {'count':>7} {'FDR (still spurious)':>22}")
for k in range(N_TESTS + 1):
    mask = survived == k
    c = mask.sum()
    fdr = (mask & ~truth).sum() / c if c else float('nan')
    print(f"{k:>12} {c:>7} {fdr:>21.1%}")

# headline: FDR among those surviving ALL tests vs surviving none
all_mask = survived == N_TESTS
fdr_all = (all_mask & ~truth).sum() / all_mask.sum()
print(f"\nFDR after surviving ALL {N_TESTS} tests: {fdr_all:.1%} "
      f"(vs base rate {1-PRIOR_TRUE:.0%} spurious)")
print("Reading: if FDR falls monotonically with tests survived, corroboration-by-severe-testing")
print("is REAL in causal inference (Popper maps); if flat, surviving tests means nothing.")
