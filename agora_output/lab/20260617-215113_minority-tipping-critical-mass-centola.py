"""
Direct test of the MINORITY-TIPPING prediction (Centola-style critical mass) — task #21.

The prior real-data test showed collective attention sits in the critical/tippable regime. This tests
the PREDICTION itself: does a COMMITTED minority of fraction f (zealots, Centola-style numbers not
amplified weight) flip a majority that holds the incumbent/correct convention, and is there a SHARP
critical mass f_c (a tipping point), as critical-mass theory predicts — rather than minority influence
rising smoothly/linearly with f?

Falsifiable: critical-mass theory => P(minority wins) vs f is a SHARP threshold (sigmoid with a narrow
window); the null (no tipping) => influence proportional to f, no threshold. We also predict f_c RISES
with external grounding h (a better-grounded majority resists a larger committed minority), per Agora's
Grounding-Coupling Law.

Real-world anchor: measured critical masses in real human/agent systems are ~10-30% (Centola et al.
2018 Science: ~25% committed minority flips a naming convention; Xie et al. 2011: ~9.8% in the naming
game). Our model's f_c should land in this empirical band for a coordinated collective.

Model (mean-field Glauber): N agents, opinions s in {-1,+1}. Incumbent/correct convention = +1; the
persuadable majority starts at +1. A fraction f are COMMITTED to -1 (never change), entering the mean
field with weight 1 each (numbers, not amplification). Persuadable agents feel H = J*M + h (M =
opinion mean over ALL agents incl. committed; h = private-evidence field toward +1). The +1 consensus
is metastable; as f rises it loses stability at a spinodal f_c and the collective abruptly flips to -1.
"""
import numpy as np

def flips(f, J, T, h, N, steps, seed):
    """Start persuadable agents at +1; return True if the collective consensus flips to the
    committed minority's view (-1) at steady state."""
    rng = np.random.default_rng(abs(seed) % (2**32))
    k = int(round(N * f))                      # committed -1 agents (zealots)
    nreg = N - k
    if nreg <= 0:
        return True
    s = np.ones(nreg)                          # persuadable majority holds the incumbent +1
    for _ in range(steps):
        M = (s.sum() + k * (-1.0)) / N         # committed enter with weight 1 (Centola-style numbers)
        H = J * M + h
        p_up = 1.0 / (1.0 + np.exp(-2.0 * H / T))
        s = np.where(rng.random(nreg) < p_up, 1.0, -1.0)
    return s.mean() < 0.0

def p_flip(f, J, T, h, N=2000, steps=400, trials=12):
    return np.mean([flips(f, J, T, h, N, steps, seed=4000 + i) for i in range(trials)])

def critical_mass(J, T, h, fgrid):
    """f_c = smallest committed fraction with P(flip) >= 0.5; also return the transition width."""
    ps = [(f, p_flip(f, J, T, h)) for f in fgrid]
    fc = next((f for f, p in ps if p >= 0.5), None)
    # transition window: f span where P goes 0.1 -> 0.9
    f10 = next((f for f, p in ps if p >= 0.1), None)
    f90 = next((f for f, p in ps if p >= 0.9), None)
    width = (f90 - f10) if (f10 is not None and f90 is not None) else None
    return fc, width, ps

if __name__ == "__main__":
    T, J = 1.0, 2.0
    fgrid = [round(x, 3) for x in np.arange(0.0, 0.52, 0.02)]
    print(f"Committed-minority tipping (coupled collective, J={J}, T={T}). Majority starts at incumbent +1.\n")

    # (1) is there a SHARP critical mass (vs smooth/linear)?  measure f_c and the transition width.
    print("  P(collective flips to the committed minority) vs committed fraction f  [grounding h=0.10]")
    fc, width, ps = critical_mass(J, T, 0.10, fgrid)
    for f, p in ps:
        if 0.0 < f < 0.45 and (abs(p - round(p)) > 0.01 or 0.04 <= f <= 0.36):
            bar = "#" * int(round(p * 20))
            print(f"    f={f:.2f}  P={p:.2f}  {bar}")
    print(f"\n  critical mass f_c = {fc:.0%}   transition width (P:0.1->0.9) = {width if width is None else f'{width:.0%}'}")
    sharp = (width is not None and width <= 0.12)         # narrow window => sharp threshold, not linear
    # linear-null comparison: a no-tipping model would need f~0.5 to flip and rise ~linearly
    linear_null = (fc is not None and fc >= 0.45)

    # (2) does f_c RISE with external grounding h?  (Grounding-Coupling)
    print("\n  external grounding h | critical mass f_c (committed minority needed to flip)")
    fcs = {}
    for h in [0.0, 0.05, 0.15, 0.30]:
        fc_h, _, _ = critical_mass(J, T, h, fgrid)
        fcs[h] = fc_h
        print(f"    h={h:<5} -> f_c = {fc_h:.0%}" if fc_h is not None else f"    h={h:<5} -> no flip up to 50%")
    hv = [(h, fc) for h, fc in sorted(fcs.items()) if fc is not None]
    grounding_raises = len(hv) >= 3 and all(hv[i][1] <= hv[i + 1][1] for i in range(len(hv) - 1))

    # (3) real-world anchor: does f_c land in the empirically observed critical-mass band (~10-30%)?
    band = [fc for fc in fcs.values() if fc is not None and 0.05 <= fc <= 0.35]
    in_empirical_band = len(band) >= 2

    print("\n=== VERDICT ===")
    print(f"A) minority tipping is a SHARP critical mass (narrow window, not linear): {sharp and not linear_null}")
    print(f"   f_c at h=0.10 = {fc:.0%}, transition width = {width:.0%}")
    print(f"B) f_c RISES with external grounding h (Grounding-Coupling): {grounding_raises}  {[f'{h}:{(v if v is None else round(v,2))}' for h,v in sorted(fcs.items())]}")
    print(f"C) f_c lands in the empirically observed critical-mass band ~10-30% (Centola 25%, Xie 10%): {in_empirical_band}")
    ok = sharp and not linear_null and grounding_raises and in_empirical_band
    if ok:
        print("\nMINORITY-TIPPING PREDICTION CONFIRMED (and consistent with real measured critical masses):")
        print("A committed minority flips the majority at a SHARP critical mass (tipping point), not")
        print("gradually. f_c rises with external grounding -- real evidence is what lets a majority resist")
        print("a committed minority -- exactly the Grounding-Coupling Law. And the measured f_c falls in the")
        print("~10-30% band measured in real human/agent experiments (Centola 25%, Xie 10%). The model's")
        print("minority-tipping prediction is not just internally sharp; it matches the real-world threshold.")
    else:
        print("\nNot fully confirmed under this test -- honest partial result (see failed clause).")
