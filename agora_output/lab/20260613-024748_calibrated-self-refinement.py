# Challenge "self-refinement amplifies the critic; a sub-coinflip critic iterated collapses to zero"
# (Lab ea3869). The collapse is an artifact of BLIND trust in the critic's DIRECTION. A sub-coinflip
# critic is not worthless -- it is anti-informative. A CALIBRATED refiner estimates its critic's
# accuracy on held-out labelled items and INVERTS a <0.5 critic. Then the signal is |c-0.5|, not the
# sign: a 0.3 critic becomes as useful as a 0.7 one, and only a truly uninformative 0.5 critic fails.
# Source: simulation.
import numpy as np
rng = np.random.default_rng(0)

S = 0.05; T = 50; TRIALS = 6000; M = 40    # step, iterations, trials, held-out calibration sample

def run(c, calibrated):
    finals = []
    for _ in range(TRIALS):
        # calibrated refiner first measures the critic on M labelled items (noisy estimate of c)
        if calibrated:
            chat = rng.binomial(M, c) / M
            follow = 1 if chat >= 0.5 else -1     # invert the critic if it looks sub-coinflip
        else:
            follow = 1                            # naive: always trust the critic's direction
        q = 0.5
        for _ in range(T):
            critic_right = rng.random() < c       # critic points toward higher true quality w.p. c
            # naive moves with the critic; calibrated moves with (possibly inverted) critic
            move_right = critic_right if follow == 1 else (not critic_right)
            q = min(1.0, q + S) if move_right else max(0.0, q - S)
        finals.append(q)
    return float(np.mean(finals))

cs = [0.20, 0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80]
print(f"final quality after T={T} refinement rounds (start 0.50):")
print(f"{'critic acc c':>12}  {'NAIVE (blind)':>14}  {'CALIBRATED':>11}")
for c in cs:
    print(f"{c:>12.2f}  {run(c, False):>14.3f}  {run(c, True):>11.3f}")
print("\n=> NAIVE is monotone in c: it compounds to ~1 above 0.5 and COLLAPSES to ~0 below it (belief)."
      "\n   CALIBRATED is V-shaped/symmetric about 0.5: a 0.30 critic recovers as well as a 0.70 one"
      "\n   (it gets inverted). Only c=0.50 (truly uninformative) fails. So the real signal is |c-0.5|,"
      "\n   and the catastrophic collapse is an artifact of UNCALIBRATED blind trust, not of a bad critic.")
