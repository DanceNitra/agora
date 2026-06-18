"""
Deepen insight 417c87f0 (inbox c06d64): "Under high attentional distraction, even high-involvement
individuals fail central-route argument evaluation." This is the Elaboration Likelihood Model (Petty &
Cacioppo). Falsifier (given): a study showing high-involvement people still do central-route evaluation
under high distraction would refute it.

The deepening turns the verbal claim into a quantitative, falsifiable one. The non-tautological,
EMERGENT quantity is the ARGUMENT-QUALITY EFFECT (AQE) measured through a decision threshold:
  AQE = P(persuaded | strong argument) - P(persuaded | weak argument)
i.e. how much a population's verdict tracks argument QUALITY (= central-route engagement). We ask
whether the high-involvement group's AQE survives distraction (involvement compensates -> ADDITIVE) or
collapses (capacity gates it -> MULTIPLICATIVE). These are two distinct, contrastable models; the human
literature (Petty, Wells & Brock 1976: distraction reduces argument-quality impact regardless of
motivation) is the real-world anchor for which one holds.

Per agent judging an argument of true strength s in {+1 strong, -1 weak}:
  capacity C = 1 - distraction; central weight w_c set by the model below; cue ~ N(0,1) (peripheral,
  uncorrelated with s). Judgment J = w_c*s + (1-w_c)*cue + noise; persuaded iff J > 0.
  MULTIPLICATIVE (gate): w_c = clip(involvement * C, 0, 1)   (can't spend capacity you don't have)
  ADDITIVE (compensate): w_c = clip(0.5*involvement + 0.5*C, 0, 1)  (involvement substitutes for capacity)
"""
import numpy as np

def aqe(distraction, involvement, model, M=20000, sigma=0.6, seed=0):
    rng = np.random.default_rng(abs(seed) % (2**32))
    C = 1.0 - distraction
    if model == "mult":
        w = np.clip(involvement * C, 0, 1)
    else:  # additive
        w = np.clip(0.5 * involvement + 0.5 * C, 0, 1)
    def frac_persuaded(s):
        cue = rng.standard_normal(M)
        J = w * s + (1 - w) * cue + sigma * rng.standard_normal(M)
        return np.mean(J > 0)
    return frac_persuaded(+1.0) - frac_persuaded(-1.0)     # P(persuaded|strong) - P(persuaded|weak)

if __name__ == "__main__":
    LOW, HIGH = 0.4, 0.95
    grid = [0.0, 0.2, 0.4, 0.6, 0.8, 0.95]
    print("Argument-Quality Effect AQE = P(persuaded|strong) - P(persuaded|weak), through a decision threshold.")
    print("High-involvement advantage = AQE(high) - AQE(low). Does distraction erase it?\n")
    print("  distraction | MULT: AQE_low  AQE_high  adv | ADD: AQE_low  AQE_high  adv")
    mult_adv, add_adv = [], []
    for d in grid:
        ml = aqe(d, LOW, "mult", seed=1); mh = aqe(d, HIGH, "mult", seed=2)
        al = aqe(d, LOW, "add", seed=3); ah = aqe(d, HIGH, "add", seed=4)
        mult_adv.append(mh - ml); add_adv.append(ah - al)
        print(f"    {d:.2f}        | {ml:.2f}     {mh:.2f}     {mh-ml:+.2f} | {al:.2f}     {ah:.2f}     {ah-al:+.2f}")

    # Under the MULTIPLICATIVE (gate) model, the high-involvement advantage should COLLAPSE at high
    # distraction (even high-involvement individuals fail). Under ADDITIVE it should persist.
    mult_collapse = mult_adv[0] > 0.1 and mult_adv[-1] < mult_adv[0] * 0.4
    add_persist = add_adv[-1] > add_adv[0] * 0.6
    # high-involvement AQE itself at high distraction (the headline: does it fail?)
    mh_lowdist = aqe(0.0, HIGH, "mult", seed=5); mh_hidist = aqe(0.9, HIGH, "mult", seed=6)
    print("\n=== VERDICT ===")
    print(f"MULT model: high-involvement advantage collapses under distraction: {mult_collapse}  "
          f"(adv {mult_adv[0]:.2f} -> {mult_adv[-1]:.2f})")
    print(f"ADD  model: advantage persists under distraction: {add_persist}  (adv {add_adv[0]:.2f} -> {add_adv[-1]:.2f})")
    print(f"MULT high-involvement AQE: {mh_lowdist:.2f} (no distraction) -> {mh_hidist:.2f} (distraction 0.9)")
    if mult_collapse and add_persist:
        print("\nDEEPENED (the two models make OPPOSITE, falsifiable predictions):")
        print("If attention is a hard CAPACITY budget (multiplicative gate w_c = involvement x capacity), the")
        print(f"high-involvement argument-quality advantage COLLAPSES under distraction ({mult_adv[0]:.2f} -> {mult_adv[-1]:.2f}):")
        print("you cannot spend capacity you do not have, so 'even high-involvement individuals' lose central-")
        print("route sensitivity. The ADDITIVE model (involvement substitutes for capacity) instead PRESERVES")
        print("the advantage. These are distinguishable by experiment; Petty-Wells-Brock (1976) - distraction")
        print("cuts argument-quality impact regardless of motivation - is real-world evidence for the GATE.")
        print("Quantitative deepening: the claim holds iff attention is multiplicative (capacity-gated), not")
        print("additive; the falsifier is a measured high-involvement AQE that survives high distraction.")
    else:
        print("\nModels did not separate as expected -- investigate.")
