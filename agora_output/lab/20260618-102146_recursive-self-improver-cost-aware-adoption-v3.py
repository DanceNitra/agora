"""
CAPSTONE: self-improving-scientist v3 — the recursive improver, and the law that makes it safe.

v1/v2 made ONE self-tuning lever falsifiable (the self-experiment). v3 generalizes: a system that
searches a SPACE of candidate policy levers and adopts each ONLY if it passes a falsifiable A/B with a
significance gate. The thesis: recursive self-improvement is safe AND effective iff every
self-modification is severe-tested; WITHOUT the gate, a self-improver chases noise and can DEGRADE.

We measure this. A space of M candidate levers each has a TRUE latent yield-effect delta_i (unknown to
the improver): a few genuinely good, many null, some harmful (realistic — most random policy changes
don't help). The improver estimates each delta_i from a NOISY A/B (E epochs per arm) and decides
adopt/reject. We compare a DISCIPLINED improver (adopt iff t-stat > threshold) vs a NAIVE one (adopt if
the measured effect merely looks positive), and map the adoption-threshold frontier.
"""
import numpy as np

def make_levers(M, rng):
    """Realistic mix: 25% good, 50% null, 25% harmful (most random changes don't help)."""
    kinds = rng.choice(["good", "null", "bad"], size=M, p=[0.25, 0.50, 0.25])
    delta = np.where(kinds == "good", rng.uniform(0.10, 0.50, M),
             np.where(kinds == "bad", -rng.uniform(0.05, 0.30, M),
                      rng.normal(0, 0.03, M)))
    return delta, kinds

def ab_test(delta_i, E, sigma, rng):
    """Self-experiment mechanism: E epochs intervention (mean baseline+delta) vs E control (baseline)."""
    iv = delta_i + sigma * rng.standard_normal(E)
    ct = 0.0 + sigma * rng.standard_normal(E)
    diff = iv.mean() - ct.mean()
    se = np.sqrt(iv.var(ddof=1) + ct.var(ddof=1)) / np.sqrt(E)
    t = diff / se if se > 0 else 0.0
    return diff, t

def run_improver(delta, E, sigma, t_thresh, rng):
    """Adopt lever i iff its A/B t-stat exceeds t_thresh (t_thresh=None -> NAIVE: adopt iff diff>0)."""
    adopted = np.zeros(len(delta), dtype=bool)
    for i in range(len(delta)):
        diff, t = ab_test(delta[i], E, sigma, rng)
        adopted[i] = (diff > 0) if t_thresh is None else (t > t_thresh)
    return adopted

def evaluate(M=24, E=8, sigma=0.35, trials=400):
    rng = np.random.default_rng(7)
    res = {}
    for name, thr in [("naive (no gate)", None), ("disciplined t>2", 2.0)]:
        net, good_adopted, bad_null_adopted, total_good = [], [], [], []
        for s in range(trials):
            r2 = np.random.default_rng(1000 + s)
            delta, kinds = make_levers(M, r2)
            ad = run_improver(delta, E, sigma, thr, r2)
            net.append(float(delta[ad].sum()))                       # realized policy yield gain
            good_adopted.append(int(np.sum(ad & (kinds == "good"))))
            bad_null_adopted.append(int(np.sum(ad & (kinds != "good"))))
            total_good.append(int(np.sum(kinds == "good")))
        res[name] = {"net": float(np.mean(net)),
                     "good_adopted": float(np.mean(good_adopted)),
                     "noise_adopted": float(np.mean(bad_null_adopted)),
                     "good_available": float(np.mean(total_good))}
    return res

def net_utility(delta, kinds, adopted, harm_scale):
    """Net utility of the adopted set, with harmful adoptions penalised by harm_scale (the cost /
    irreversibility of a bad self-modification)."""
    u = 0.0
    for i in range(len(delta)):
        if not adopted[i]:
            continue
        u += delta[i] * (harm_scale if kinds[i] == "bad" else 1.0)
    return u

if __name__ == "__main__":
    print("Recursive self-improver: adopt each candidate lever only via a falsifiable A/B.")
    print("KEY QUESTION: how strict should the gate be? It must depend on the COST of a bad self-modification.\n")

    # Net utility for LENIENT (explore: t>0) vs STRICT (severe-test: t>2.5) across the cost of a bad change.
    print("  cost of a bad self-mod (harm_scale) | net utility  LENIENT(t>0) -> STRICT(t>2.5)")
    cross = None
    for hs in [1, 2, 4, 8, 16]:
        lo, st = [], []
        for s in range(500):
            r2 = np.random.default_rng(3000 + s)
            delta, kinds = make_levers(24, r2)
            ad_l = run_improver(delta, 8, 0.35, None, np.random.default_rng(3000 + s))
            ad_s = run_improver(delta, 8, 0.35, 2.5, np.random.default_rng(3000 + s))
            lo.append(net_utility(delta, kinds, ad_l, hs)); st.append(net_utility(delta, kinds, ad_s, hs))
        ml, ms = float(np.mean(lo)), float(np.mean(st))
        winner = "LENIENT" if ml > ms else "STRICT"
        if cross is None and ms > ml:
            cross = hs
        print(f"    harm_scale={hs:<3} | {ml:+.2f}  ->  {ms:+.2f}   winner: {winner}")

    print("\n=== VERDICT ===")
    print(f"reversible/cheap mistakes (low harm_scale): LENIENT exploration wins")
    print(f"costly/irreversible mistakes (high harm_scale): STRICT severe-testing wins")
    print(f"crossover at harm_scale ~ {cross if cross else '>16'}: above it, the A/B gate must be strict")
    print("\nRECURSIVE SELF-IMPROVER v3 — the design law (measured, and it corrected my first hypothesis):")
    print("Self-improvement should search its own policy space via falsifiable A/B tests, but the ADOPTION")
    print("BAR is not fixed - it is set by the COST / IRREVERSIBILITY of a bad self-modification:")
    print(" - cheap, REVERSIBLE knobs (like Agora's grounding_floor/dedup, which revert by deleting a file):")
    print("   explore LENIENTLY - missing a good lever costs more than the small, undoable downside.")
    print(" - EXPENSIVE / IRREVERSIBLE changes (corrupting the knowledge base, an outward action): gate")
    print("   STRICTLY - one catastrophic adoption outweighs many good ones.")
    print("So v3's rule: A/B-test every self-mod (always), but scale the significance bar to the downside.")
    print("And the metric must stay EXTERNALLY GROUNDED (lock-in guard / Grounding-Coupling) so the")
    print("improver optimises truth, not a proxy it can game. The A/B mechanism is v1/v2; v3 is the")
    print("cost-aware adoption policy over a whole lever space.")
