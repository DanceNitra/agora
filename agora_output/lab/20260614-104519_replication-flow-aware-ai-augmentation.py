
import numpy as np

rng = np.random.default_rng(42)
N = 4000  # tasks per condition

# ---- Flow model (Csikszentmihalyi, operationalized) ----
# Each task has an intrinsic difficulty d and the agent has skill s.
# Flow channel = small |d - s|. Performance is a bell over the gap:
#   too easy (d<<s) -> boredom; too hard (d>>s) -> anxiety; both reduce performance.
# perf(gap) = exp(-(gap/w)^2), gap = d_eff - s, w = flow bandwidth.
# An AI intervention shifts EFFECTIVE difficulty toward the flow band by amount a (scale),
# applied only on ticks where the policy chooses to act (timing).

W = 1.0  # flow bandwidth (skill units)

def perf(gap):
    return np.exp(-(gap / W) ** 2)

# Sample tasks: difficulty varies, skill varies; the raw gap is often OUTSIDE the flow band
s = rng.normal(0.0, 0.6, N)              # agent skill (centered)
d = s + rng.normal(0.0, 1.6, N)          # task difficulty: correlated w/ skill but high variance
raw_gap = d - s                          # disruption signal the system can observe (noisily)

# The system observes the gap with sensor noise (context estimate)
obs_gap = raw_gap + rng.normal(0.0, 0.4, N)

# ---------------------------------------------------------------
# Condition A: NO intervention (baseline) — just live with the gap
gap_A = raw_gap
perf_A = perf(gap_A)

# Condition B: CONTEXT-AWARE policy
#   timing: act only when observed disruption exceeds the flow band (|obs_gap| > W)
#   scale: move effective difficulty toward s, proportional to observed gap (gap-closing),
#          but capped (an intervention can only do so much) and with execution noise.
act_B = np.abs(obs_gap) > W
adjust_B = np.clip(-obs_gap, -2.5, 2.5)               # try to cancel the observed gap
adjust_B = adjust_B + rng.normal(0.0, 0.15, N)        # execution noise
adjust_B = np.where(act_B, adjust_B, 0.0)             # only when timing says act
gap_B = raw_gap + adjust_B
perf_B = perf(gap_B)

# ---------------------------------------------------------------
# Condition C: POORLY-TIMED policy
#   intervenes at random ticks (ignores context) with the right-ish scale.
act_C = rng.random(N) < act_B.mean()                  # same intervention RATE, wrong timing
adjust_C = np.clip(-obs_gap, -2.5, 2.5) + rng.normal(0.0, 0.15, N)
adjust_C = np.where(act_C, adjust_C, 0.0)
gap_C = raw_gap + adjust_C
perf_C = perf(gap_C)

# Condition D: POORLY-SCALED policy
#   right timing (acts when disrupted) but over-scales (2.2x) and adds heavy noise.
act_D = act_B
adjust_D = np.clip(-obs_gap, -2.5, 2.5) * 2.2 + rng.normal(0.0, 0.6, N)
adjust_D = np.where(act_D, adjust_D, 0.0)
gap_D = raw_gap + adjust_D
perf_D = perf(gap_D)

def summ(name, p, g):
    in_flow = np.mean(np.abs(g) <= W)
    print(f"{name:22s} mean_perf={p.mean():.4f}  sd={p.std():.4f}  frac_in_flow={in_flow:.3f}")
    return p.mean()

print("=== Flow-preservation under AI intervention policies (N=%d/condition) ===" % N)
mA = summ("A_no_intervention", perf_A, gap_A)
mB = summ("B_context_aware",   perf_B, gap_B)
mC = summ("C_poorly_timed",    perf_C, gap_C)
mD = summ("D_poorly_scaled",   perf_D, gap_D)

print()
print("Context-aware vs baseline:      delta = %+.4f (%.1f%%)" % (mB-mA, 100*(mB-mA)/mA))
print("Context-aware vs poorly-timed:  delta = %+.4f (%.1f%%)" % (mB-mC, 100*(mB-mC)/mC))
print("Context-aware vs poorly-scaled: delta = %+.4f (%.1f%%)" % (mB-mD, 100*(mB-mD)/mD))
print()
print("CLAIM CHECK:")
print("  context-aware > baseline         :", bool(mB > mA))
print("  context-aware > poorly-timed     :", bool(mB > mC))
print("  context-aware > poorly-scaled    :", bool(mB > mD))
print("  poorly-timed HURTS vs baseline   :", bool(mC < mA), "(delta %+.4f)" % (mC-mA))
print("  poorly-scaled HURTS vs baseline  :", bool(mD < mA), "(delta %+.4f)" % (mD-mA))

# Bootstrap 95% CI on the key contrast (B - A)
B = 2000
idx = rng.integers(0, N, (B, N))
diffs = perf_B[idx].mean(1) - perf_A[idx].mean(1)
lo, hi = np.percentile(diffs, [2.5, 97.5])
print()
print("Bootstrap 95%% CI on (context_aware - baseline): [%+.4f, %+.4f]" % (lo, hi))
