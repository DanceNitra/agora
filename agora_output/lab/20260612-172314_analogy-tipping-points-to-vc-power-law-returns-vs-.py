"""
Analogy forge + test: 'Tipping Points / criticality' -> 'Venture Capital returns'.

STRUCTURAL CLAIM (not surface): VC portfolio returns are extremely concentrated (a few deals make
the fund) because outcomes are driven by a MULTIPLICATIVE / preferential-growth process with a
heavy tail — the same skeleton as tipping-point dynamics (small differences compound past a
threshold into runaway winners) — NOT by Gaussian differences in 'skill'. If true, a minimal
multiplicative model reproduces the empirically known concentration; a Gaussian-skill model cannot.

Empirical anchors (well documented for early-stage VC):
  - return distribution is power-law / extremely right-skewed,
  - roughly the top ~5% of deals produce ~ the majority (~60%) of returns,
  - most deals return < 1x (losses dominate by count).

MODEL A (tipping/multiplicative): each deal's multiple = exp(sum of T i.i.d. shocks) — geometric
Brownian outcome with occasional 'breakout' (a heavy-tail jump when a latent score crosses a
threshold). MODEL B (Gaussian skill): each deal's multiple = max(0, 1 + N(mu, sigma)).

Measured: Pareto tail index, top-5% share of total return, fraction of deals < 1x, top-1 deal share.
VERDICT:
  ANALOGY HOLDS  -- Model A reproduces power-law concentration (top-5% share >= ~50%, heavy tail,
                    majority of deals < 1x) while Model B (Gaussian skill) does NOT.
  NO MAPPING     -- both behave alike, or A fails to concentrate.
"""
import numpy as np

rng = np.random.default_rng(20260612)
N = 20000          # deals
T = 12             # compounding rounds (financing stages)


def concentration(mult):
    mult = np.sort(mult)[::-1]
    tot = mult.sum()
    top5 = mult[:max(1, N // 20)].sum() / tot
    top1deal = mult[0] / tot
    frac_loss = np.mean(mult < 1.0)
    # Pareto/Hill tail index on the top 5%
    tail = mult[mult > np.quantile(mult, 0.95)]
    xmin = tail.min()
    alpha = 1 + len(tail) / np.sum(np.log(tail / xmin)) if len(tail) > 5 else float("nan")
    return top5, top1deal, frac_loss, alpha


# ---- Model A: tipping / multiplicative with threshold breakout ----
shocks = rng.normal(-0.05, 0.5, (N, T))          # slightly negative drift: most deals fade
latent = shocks.sum(axis=1)
breakout = latent > np.quantile(latent, 0.92)    # top ~8% cross the tipping threshold...
boost = np.where(breakout, rng.normal(2.5, 1.0, N), 0.0)   # ...and compound into runaway winners
multA = np.exp(latent + boost)
multA = np.clip(multA, 0, None)

# ---- Model B: Gaussian skill (additive, no compounding/threshold) ----
multB = np.maximum(0.0, 1 + rng.normal(0.6, 1.2, N))

print("=== Analogy test: Tipping Points -> VC returns ===")
for name, m in [("A tipping/multiplicative", multA), ("B Gaussian skill", multB)]:
    top5, top1, loss, alpha = concentration(m)
    print(f"\n[{name}]")
    print(f"  top-5% of deals share of total return : {top5*100:5.1f}%   (empirical VC ~60%)")
    print(f"  single best deal share                : {top1*100:5.1f}%")
    print(f"  fraction of deals returning < 1x      : {loss*100:5.1f}%   (empirical: most)")
    print(f"  Pareto tail index alpha (lower=heavier): {alpha:.2f}")

t5A, _, lossA, aA = concentration(multA)
t5B, _, lossB, aB = concentration(multB)
print("\n=== Verdict ===")
holds = (t5A >= 0.50 and lossA >= 0.5 and aA < 3.0) and (t5B < 0.40)
if holds:
    print("ANALOGY HOLDS (structural): a multiplicative/threshold 'tipping' mechanism reproduces VC's")
    print(f"power-law concentration (top-5% = {t5A*100:.0f}% of returns, {lossA*100:.0f}% of deals <1x,")
    print(f"tail alpha={aA:.2f}) — while a Gaussian-skill model does NOT (top-5% only {t5B*100:.0f}%).")
    print("VC return skew is a tipping-point signature, not a spread of skill.")
else:
    print(f"NO CLEAN MAPPING at these params (A top5={t5A*100:.0f}% lossA={lossA*100:.0f}% aA={aA:.2f};")
    print(f"B top5={t5B*100:.0f}%).")
