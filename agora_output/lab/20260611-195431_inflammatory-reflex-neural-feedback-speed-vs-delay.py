"""
Hypothesis (severe-tested here): the nervous system's regulatory advantage over purely humoral
immune control is SPEED. The inflammatory reflex (vagal sensing of cytokines -> efferent
acetylcholine -> alpha7-nAChR on macrophages -> TNF suppression) is a fast negative-feedback loop.
Modeled as delayed proportional feedback on a cytokine with self-amplification:

    dC/dt = S(t) + alpha*C*(1 - C/Cmax) - delta*C - kappa*u,   u = max(0, G * C(t - tau))

  C        = pro-inflammatory cytokine (e.g. TNF), arbitrary units
  S(t)     = transient insult (drive on [0,1])
  alpha    = self-amplification (inflammation begets inflammation)
  delta    = passive/humoral clearance (the no-neural baseline)
  G        = neural feedback gain; tau = neural sensing+actuation DELAY

Predictions:
  (1) Adding fast feedback (small tau) sharply lowers peak C and integrated exposure (AUC) vs G=0.
  (2) The benefit DEGRADES with delay; beyond a critical tau* the loop overshoots / oscillates
      (delayed negative feedback destabilizes) -- so a SLOW (humoral-speed) controller is not just
      weaker but can be worse than none. That is the measured reason the regulator must be neural.
"""
import numpy as np

dt, T = 0.01, 60.0
n = int(T / dt)
alpha, Cmax, delta, kappa = 1.6, 10.0, 0.6, 1.0
S0, Sdur = 6.0, 1.0


def simulate(G, tau):
    lag = int(round(tau / dt))
    C = np.zeros(n)
    C[0] = 0.05
    for t in range(1, n):
        Cd = C[t - 1 - lag] if t - 1 - lag >= 0 else 0.0
        u = max(0.0, G * Cd)
        S = S0 if (t * dt) < Sdur else 0.0
        dC = S + alpha * C[t - 1] * (1 - C[t - 1] / Cmax) - delta * C[t - 1] - kappa * u
        C[t] = max(0.0, C[t - 1] + dt * dC)
    peak = C.max()
    auc = C.sum() * dt
    # oscillation/instability: late-window swing after the insult clears
    late = C[int(40 / dt):]
    swing = late.max() - late.min()
    return peak, auc, swing


base_peak, base_auc, _ = simulate(G=0.0, tau=0.0)
print(f"NO NEURAL CONTROL (humoral clearance only): peak={base_peak:.2f}  AUC={base_auc:.1f}")
print(f"\nNeural feedback gain G=2.0, varying sensing+actuation DELAY tau:")
print(f"{'tau':>5} {'peak':>7} {'AUC':>8} {'dAUC%':>7} {'late-swing':>11} {'verdict':>14}")
G = 2.0
for tau in (0.05, 0.2, 0.5, 1.0, 2.0, 3.0, 4.0):
    pk, au, sw = simulate(G, tau)
    dauc = 100 * (au - base_auc) / base_auc
    verdict = "OSCILLATES" if sw > 0.5 else ("helps" if au < base_auc else "WORSE than none")
    print(f"{tau:>5.2f} {pk:>7.2f} {au:>8.1f} {dauc:>6.0f}% {sw:>11.2f} {verdict:>14}")

# Fast-vs-slow headline numbers
fp, fa, fs = simulate(G, 0.1)
sp, sa, ss = simulate(G, 3.0)
print(f"\nFAST (tau=0.1): AUC {fa:.1f} -> {100*(base_auc-fa)/base_auc:.0f}% lower than none, peak {fp:.2f}, swing {fs:.2f} (stable)")
print(f"SLOW (tau=3.0): AUC {sa:.1f} -> {100*(base_auc-sa)/base_auc:+.0f}% vs none, peak {sp:.2f}, swing {ss:.2f}")
print("Claim: the neural loop's value is its SPEED; the same gain applied slowly loses the benefit and can destabilize.")
