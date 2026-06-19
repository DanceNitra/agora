"""
CRUCIBLE replication — "Emergent abilities of LLMs are genuine sharp capability transitions"
============================================================================================
Claim (Wei et al. 2022, 'Emergent Abilities of Large Language Models'): certain abilities appear
SUDDENLY and unpredictably above a scale threshold — a sharp, discontinuous jump.
Counter (Schaeffer, Miranda & Koyejo 2023, 'Are Emergent Abilities a Mirage?', NeurIPS): the sharpness
is largely an artifact of using a DISCONTINUOUS / nonlinear metric (e.g. exact-match over a multi-token
answer); under a smooth metric the same underlying skill improves gradually.

Minimal computational test (NO real LLMs, NO private data): posit a SMOOTH per-token skill that rises
gradually with scale,  p(s) = sigmoid((s - s0)/w).  A task needs L tokens ALL correct (exact match), so
task accuracy = p(s)**L. We ask: does a genuine capability DISCONTINUITY have to exist to reproduce the
canonical sharp 'emergence' curve, or does a smooth p(s) under exact-match already produce it?

Verdict rule:
  REPRODUCED (emergence is real/sharp)  if the exact-match jump CANNOT be explained by the smooth metric;
  FAILED (strong claim)                 if a SMOOTH p(s) under exact-match reproduces the sharp jump AND a
                                        smooth metric (per-token accuracy) on the SAME runs shows no jump.
"""
import numpy as np

rng = np.random.default_rng(0)


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


# smooth underlying per-token skill vs scale s (e.g. log-compute), rising GRADUALLY (no discontinuity)
s = np.linspace(-6, 6, 240)
s0, w = 0.0, 1.6
p = sigmoid((s - s0) / w)           # smooth per-token correctness probability


def transition_width(curve, x):
    """scale-range over which a 0..1 curve goes from 0.1 to 0.9 (small = sharp jump)."""
    lo = np.interp(0.1, curve, x)
    hi = np.interp(0.9, curve, x)
    return float(hi - lo)


# per-token (smooth) metric vs exact-match (nonlinear) metric for several answer lengths L
print("=== Apparent 'emergence' is set by the metric, not a capability jump ===")
print("underlying skill p(s) is the SAME smooth sigmoid in every row.\n")
w_smooth = transition_width(p, s)
print(f"  per-token accuracy (smooth metric):           transition width = {w_smooth:.2f} scale units (gradual)")
rows = []
for L in (1, 5, 20, 50, 100):
    acc = p ** L                    # exact-match over L tokens
    acc_n = acc / acc.max()         # normalize to [0,1] for width (it saturates at p_max**L)
    wL = transition_width(acc_n, s)
    # threshold scale where exact-match passes 0.5 of its own max -> the apparent 'emergence point'
    thr = float(np.interp(0.5, acc_n, s))
    rows.append((L, wL, thr))
    print(f"  exact-match, answer length L={L:>3}: transition width = {wL:5.2f}  | apparent onset at s={thr:+.2f}")

sharp = rows[-1][1]
ratio = w_smooth / sharp if sharp > 0 else float("inf")
print(f"\nMEASURED: same smooth skill -> per-token transition width {w_smooth:.2f} vs exact-match (L=100) "
      f"width {sharp:.2f}; the exact-match curve is {ratio:.1f}x sharper PURELY from the metric. "
      f"The 'emergence onset' also shifts right as L grows ({rows[0][2]:+.2f} -> {rows[-1][2]:+.2f}) with NO "
      f"change in the underlying skill.")

# control: is a genuine discontinuity REQUIRED? Show a truly smooth metric never jumps no matter how we
# look at it, while exact-match jumps for large L. If a discontinuity were required, the smooth metric
# would also have to jump. It doesn't.
big_jump_exact = sharp < 0.5 * w_smooth
no_jump_smooth = w_smooth > 2.0
print()
if big_jump_exact and no_jump_smooth:
    print("VERDICT: FAILED (strong claim). The canonical SHARP emergence curve is reproduced by a SMOOTH, "
          "continuous per-token skill measured with a nonlinear exact-match metric — no capability "
          "discontinuity is needed. Schaeffer et al.'s 'mirage' result REPRODUCES; the strong claim that "
          "emergent abilities are genuine sharp capability transitions is NOT supported by sharpness alone. "
          "(Scope: this shows sharpness is metric-dependent; it does not prove NO ability is ever genuinely "
          "emergent — it removes sharp benchmark curves as evidence for discontinuity.)")
else:
    print("VERDICT: REPRODUCED — the sharp jump survives a smooth metric, i.e. a genuine discontinuity.")
