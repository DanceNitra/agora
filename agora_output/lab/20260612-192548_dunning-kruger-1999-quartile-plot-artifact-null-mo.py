"""
Replication: Dunning & Kruger (1999) — "the unskilled systematically overestimate their ability
(a metacognitive deficit): the bottom quartile overestimates most (~+46 pct points), the top
slightly underestimates (~-13)."

THE CANONICAL EVIDENCE: the quartile plot — group by actual test performance, plot mean
self-estimated percentile per quartile. Bottom quartile: actual ~12th pct, self-estimate ~58th.

THE TEST (the Nuhfer 2016/Gignac & Zajenkowski 2020 critique, made fully computational): does the
plot — INCLUDING its famous asymmetry — arise from a null model with NO metacognitive deficit?
Null ingredients, each individually uncontroversial:
  1. true skill T ~ N(0,1); measured performance P = T + noise (tests are noisy),
  2. self-estimates are ABSOLUTE percentile guesses with a UNIFORM better-than-average offset
     (everyone, skilled or not, thinks they're ~65th percentile on average — a separate, global
     bias) and imperfect-but-skill-INDEPENDENT self-knowledge:
        S_pct = clip( 50 + OFFSET + SHRINK*(T_pct - 50) + noise , 1, 99 )
By construction the self-assessment ERROR DISTRIBUTION is the same at every skill level — there is
no "incompetents are blind to their incompetence" mechanism. If the canonical numbers reproduce,
the plot cannot evidence the deficit; only the artifact (regression to the mean + selection on a
noisy measure) plus a uniform global bias.

Calibration discipline: OFFSET is set from DK's own reported GRAND MEAN self-estimate (~66th pct),
not tuned to the quartile gaps. SHRINK/noise set for a realistic self-insight correlation (~0.3-0.5,
the literature's range). The quartile gaps are then PREDICTIONS, not fits.
"""
import numpy as np

rng = np.random.default_rng(20260612)
N = 400000

OFFSET = 16.0        # grand-mean self-estimate ~66th pct (DK's own tables) — global, uniform
SHRINK = 0.35        # self-insight slope (corr(self,perf) lands ~0.3-0.45, literature range)
SELF_NOISE = 14.0    # pct-point noise on self-estimates (same for everyone)


def run(reliability: float):
    T = rng.standard_normal(N)
    noise_p = np.sqrt(max(1 / reliability**2 - 1, 1e-9))
    P = T + noise_p * rng.standard_normal(N)
    Tpct = 100 * (np.argsort(np.argsort(T)) + 0.5) / N
    Ppct = 100 * (np.argsort(np.argsort(P)) + 0.5) / N
    S = 50 + OFFSET + SHRINK * (Tpct - 50) + SELF_NOISE * rng.standard_normal(N)
    S = np.clip(S, 1, 99)
    q = np.digitize(Ppct, [25, 50, 75])
    rows = []
    for k in range(4):
        m = q == k
        rows.append((Ppct[m].mean(), S[m].mean()))
    r_self_perf = np.corrcoef(S, Ppct)[0, 1]
    return rows, S.mean(), r_self_perf


print("=== Null model: ZERO metacognitive deficit (identical self-error at every skill level) ===")
print("(self-estimates are absolute percentile guesses with a uniform better-than-average bias)\n")
for rel, label in [(0.85, "high-reliability test"), (0.60, "typical psych test"), (0.45, "noisy quiz (DK-style)")]:
    rows, smean, r = run(rel)
    print(f"[{label}: corr(T,P)~{rel} | grand-mean self-est {smean:.0f}th pct | corr(self,perf)={r:.2f}]")
    names = ["bottom", "2nd", "3rd", "top"]
    for nm, (p, s) in zip(names, rows):
        print(f"  {nm:>6}: actual {p:5.1f} | self {s:5.1f} | gap {s-p:+6.1f}")
    print()

rows, smean, r = run(0.45)
gb, gt = rows[0][1] - rows[0][0], rows[3][1] - rows[3][0]
print("=== Verdict (DK 1999 reported: bottom ~+46, top ~-13; grand mean ~66th pct) ===")
if gb > 35 and -22 < gt < 0:
    print(f"FAILED (the canonical inference): a null with NO deficit reproduces the famous plot AND its")
    print(f"asymmetry — bottom {gb:+.0f} (DK: ~+46), top {gt:+.0f} (DK: ~-13) — from just (1) regression to")
    print(f"the mean on a noisy measure and (2) a UNIFORM better-than-average bias shared by everyone.")
    print(f"The asymmetry that made 'incompetents are blind' famous is the uniform offset, not a")
    print(f"skill-dependent blindness. The plot cannot detect a metacognitive deficit even if one exists;")
    print(f"only skill-conditional error variance could — and that requires a different design (e.g.")
    print(f"Gignac-Zajenkowski's continuous moderation test, which finds little to none).")
    print(f"Operating-Point note: the artifact GROWS as test reliability falls — largest exactly in the")
    print(f"quick-quiz settings where the effect is usually demonstrated.")
else:
    print(f"The null does NOT reproduce DK's numbers (bottom {gb:+.1f}, top {gt:+.1f} vs +46/-13) —")
    print(f"the canonical inference survives this artifact model. REPRODUCED-as-evidence.")
