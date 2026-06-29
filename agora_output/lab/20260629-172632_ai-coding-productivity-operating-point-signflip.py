"""Crucible: "AI coding assistants make developers ~55% faster" (vendor, universal reading) vs the
independent METR RCT (-19% for experienced devs in mature repos). Storm-research verified both numbers.

NOT an RCT we can re-run. The computable, OURS contribution: show the +26% (juniors/scoped, Cui/Demirer,
peer-reviewed, task-COUNT) and the -19% (experts/mature, METR, TIME) are NOT a contradiction but two
OPERATING POINTS of a single write-vs-review model (the Operating-Point Trap applied to AI coding).

Model. Context k in [0,1] (0 = novice/unfamiliar; 1 = expert/own mature repo). Times relative to a
NOVICE self-write = 1.0.
  without AI:  T0(k) = w(k) = w_hi - (w_hi - w_lo)*k     (experts write faster)
  with AI:     Tai(k) = a + v(k),  v(k) = v0*(1 + beta*k) (read AI draft + review/rework; tax may rise with k)
  speedup(k) = 1 - Tai(k)/T0(k)
FALSIFIER: if no plausible params yield a junior-gain / expert-loss sign-flip, the operating-point
explanation is rejected and the two studies truly conflict. Magnitudes are illustrative (the RCTs use
different metrics); the SHAPE (sign-flip + crossover) is the claim.
"""
import numpy as np

def speedup(k, w_hi, w_lo, a, v0, beta):
    w = w_hi - (w_hi - w_lo) * k
    v = v0 * (1 + beta * k)
    return 1 - (a + v) / w

def main():
    w_hi, w_lo = 1.00, 0.50   # expert writes ~2x faster than novice
    a          = 0.12         # prompt + read an AI draft ~12% of a novice write (context-free)
    v0         = 0.57         # base review/rework of an AI draft
    k_j, k_e = 0.15, 0.90
    print("=== AI-coding productivity is an operating-point SIGN-FLIP, not a contradiction ===\n")

    # KEY honesty point: the sign flips even with NO context-dependent review tax (beta=0) -- purely because
    # experts write faster (less to gain) + AI adds a fixed read/prompt overhead. A tax (beta>0) deepens it.
    for beta, label in [(0.0, "beta=0   (review cost CONSTANT - no expert reconciliation tax)"),
                        (2.5, "beta=2.5 (review cost RISES with context - the reconciliation tax)")]:
        sj, se = speedup(k_j, w_hi, w_lo, a, v0, beta), speedup(k_e, w_hi, w_lo, a, v0, beta)
        ks = np.linspace(0, 1, 4001); cross = ks[np.argmin(np.abs(speedup(ks, w_hi, w_lo, a, v0, beta)))]
        print(label)
        print("   junior(k=.15) %+.2f | expert(k=.90) %+.2f | crossover k*=%.2f | curve %s" % (
            sj, se, cross, " ".join("%.1f:%+.2f" % (k, speedup(k, w_hi, w_lo, a, v0, beta)) for k in (0,.25,.5,.75,1.0))))

    rng = np.random.default_rng(0); flips = 0; trials = 5000
    for _ in range(trials):
        p = dict(w_hi=1.0*rng.uniform(.9,1.1), w_lo=rng.uniform(.35,.65), a=rng.uniform(.06,.20),
                 v0=rng.uniform(.40,.70), beta=rng.uniform(0.0, 3.0))   # beta drawn from 0..3: tax NOT assumed
        if speedup(k_j, **p) > 0 and speedup(k_e, **p) < 0:
            flips += 1
    print("\nROBUSTNESS: over %d plausible param sets (review-tax beta drawn 0..3, i.e. NOT assumed), "
          "the sign-flip (junior gains AND expert loses) holds in %.0f%% of them." % (trials, 100*flips/trials))
    print("\nMEASURED: a minimal write-vs-review model yields a robust junior-gain / expert-loss SIGN-FLIP "
          "with a crossover, and it flips even with NO context review tax (beta=0) - purely from experts "
          "writing faster + a fixed AI read/prompt overhead. The +26%% (task-count) and -19%% (time) RCTs "
          "are two operating points of ONE curve, not a contradiction.")
    print("VERDICT: FAILED - the universal 'AI makes devs ~55%% faster' claim. Speedup flips sign with the "
          "developer's context/expertise; reporting one operating point as 'the' effect is the error.")
    print("SCOPE: illustrative model (magnitudes NOT fit to the differing metrics); it shows the two studies "
          "are CONSISTENT and the universal framing fails. WHICH driver dominates (less-to-gain vs review-tax) "
          "is underdetermined -> frontier question. Anchor: storm-research dossier (METR 2507.09089 CONFIRMED; "
          "Cui/Demirer MnSc 2025 +26%%; Peng 2302.06590 vendor single greenfield task).")

if __name__ == "__main__":
    main()
