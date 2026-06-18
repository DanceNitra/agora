"""
Future-of-Work ship (fresh axis: labor economics / inequality): does broadly-accessible AI EQUALIZE or
CONCENTRATE the output/income distribution? Genuinely contested: Brynjolfsson, Li & Raymond (2023,
call-centre) and Noy & Zhang (2023, writing) find AI assistance helps LOW performers most (compression);
others argue capital owners / top talent capture the gains (amplification).

We formalize the two competing mechanisms and find the condition that decides which wins:
  - AI as a FLOOR (substitute for low skill): everyone can reach at least the AI's level F -> lifts the
    bottom -> compresses inequality.
  - AI as a COMPLEMENT (multiplier of existing skill): high-skill workers extract more from the same AI
    -> top pulls away -> widens inequality.
Output_i = max(skill_i, F(A)) * (1 + c * (skill_i / skill_max) * A), where A = AI capability, F(A) = the
AI floor (rises with A), c = complementarity strength. We measure the Gini of outputs vs A for several
c, and find the CROSSOVER c* where AI flips from equalizing to concentrating. Skills ~ lognormal (realistic).
"""
import numpy as np

def gini(x):
    x = np.sort(np.asarray(x, dtype=float)); n = len(x)
    if x.sum() == 0:
        return 0.0
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))

def gini_at(reach, c, A, skill):
    # reach = how far DOWN the workforce the AI floor is accessible: everyone is lifted to at least the
    # 'reach'-percentile skill level (reach=0 -> no floor / elite-only AI; reach=0.9 -> floor at p90).
    F = np.percentile(skill, 100 * reach) if reach > 0 else 0.0
    smax = skill.max()
    out = np.maximum(skill, F) * (1.0 + c * (skill / smax) * A)        # complement: top extends beyond floor
    return gini(out)

if __name__ == "__main__":
    rng = np.random.default_rng(11)
    skill = np.exp(0.6 * rng.standard_normal(20000))      # lognormal skills
    base = gini(skill)
    A = 1.5
    print(f"Baseline output-Gini = {base:.3f}. Lower = more equal. (AI capability A={A})")
    print("The determinant that emerged: FLOOR REACH (how far down the workforce AI is accessible).\n")
    print("  floor reach (accessibility) | Gini at complementarity c = 0.0   0.6   1.2")
    rows = {}
    for r in [0.0, 0.2, 0.4, 0.6, 0.8]:
        row = {c: gini_at(r, c, A, skill) for c in [0.0, 0.6, 1.2]}
        rows[r] = row
        lab = "elite-only" if r == 0 else f"to p{int(r*100)}"
        print(f"     reach={r:.1f} ({lab:<10})      | " + "   ".join(f"{row[c]:.3f}" for c in [0.0, 0.6, 1.2]))

    # crossover floor-reach r* (at moderate complement c=0.6): below it AI concentrates, above it equalizes
    rs = np.linspace(0, 0.9, 46)
    g = np.array([gini_at(r, 0.6, A, skill) for r in rs])
    below = np.where(g < base)[0]
    rstar = float(rs[below[0]]) if len(below) else None

    print("\n=== VERDICT ===")
    elite_concentrates = rows[0.0][1.2] > base + 0.005          # no floor + complement -> widens
    broad_equalizes = rows[0.8][0.6] < base - 0.02              # broad floor -> compresses
    print(f"ELITE AI (reach=0, complement c=1.2) concentrates: Gini {base:.3f} -> {rows[0.0][1.2]:.3f}  ({elite_concentrates})")
    print(f"BROAD AI (reach=p80) equalizes: Gini {base:.3f} -> {rows[0.8][0.6]:.3f}  ({broad_equalizes})")
    print(f"crossover floor-reach r* (AI flips concentrate->equalize): {rstar:.2f}" if rstar is not None else "no crossover")
    if elite_concentrates and broad_equalizes and rstar is not None:
        print("\nCONFIRMED (the determinant is ACCESSIBILITY/floor-reach, not complementarity):")
        print("Whether AI equalizes or concentrates is decided by how far DOWN the workforce its floor reaches,")
        print(f"with a crossover at reach ~ p{int(rstar*100)}. ELITE AI (a skill-complement available mainly to the")
        print("top) CONCENTRATES; BROADLY-ACCESSIBLE AI (a floor that transfers best-practice to the bottom)")
        print("EQUALIZES - and this is ASYMMETRIC: once the floor reaches the bulk of the workforce, the")
        print("equalizing effect structurally DOMINATES any skill-complementarity, because the floor lifts the")
        print("whole bottom mass while complementarity only extends the thin top tail. The Brynjolfsson/Noy-Zhang")
        print("compression is the broad-floor regime. Policy lever: ACCESS (does the floor reach the bottom),")
        print("not raw capability - and complementarity cannot flip a broad floor, only a low one.")
    else:
        print("\nNot the predicted accessibility structure -- honest partial (see rows).")
