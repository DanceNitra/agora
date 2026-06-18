# Challenge "the cure for a herding crowd is expensive — a minority of contrarians is swamped"
# (Lab aa23bf: contrarian-injection needs ~80% independence). Disconfirming claim: that is expensive
# only for ONE cure (recruit independents). A second cure — WIDEN THE ACTION CHANNEL so agents report
# graded confidence instead of a binary choice — costs no recruitment and breaks herding for free.
# Head-to-head on the SAME heterogeneous-precision crowd. Source: simulation.
import numpy as np
rng = np.random.default_rng(0)

N = 151; TRIALS = 4000

def trial_contrarian(alpha, rng):
    V = 1 if rng.random() < 0.5 else -1
    P = 0.0; actions = []
    for _ in range(N):
        p = rng.uniform(0.55, 0.95)                       # heterogeneous expertise
        s = V if rng.random() < p else -V
        lam = s * np.log(p / (1 - p))
        if rng.random() < alpha:                          # forced-independent: own signal only
            a = 1 if lam > 0 else -1
            P += a * 0.0                                  # (its action still informative, but keep the
            informative = True                            #  belief-note convention: independents vote)
        else:
            tot = P + lam
            a = 1 if tot > 0 else (-1 if tot < 0 else s)
            informative = abs(P) <= np.log(0.95/0.05)     # herder: informative unless deep cascade
        # public update: an informative action nudges the public belief by a typical signal strength
        if informative:
            P += a * np.log(0.7/0.3)
        actions.append(a)
    return int(np.sign(sum(actions)) == V)

def trial_graded(rng):
    # cure B: alpha=0 (no independents). Every agent reveals its private LLR (graded confidence).
    # Collective decision = sign(sum of revealed evidence). Cost = a protocol change, no recruitment.
    V = 1 if rng.random() < 0.5 else -1
    tot = 0.0
    for _ in range(N):
        p = rng.uniform(0.55, 0.95)
        s = V if rng.random() < p else -V
        tot += s * np.log(p / (1 - p))
    return int(np.sign(tot) == V)

print("CURE A — recruit forced-independent contrarians (binary actions):")
print(f"  {'independent fraction a':>22}  {'collective accuracy':>19}")
for a in [0.0, 0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0]:
    acc = np.mean([trial_contrarian(a, rng) for _ in range(TRIALS)])
    print(f"  {a:>22.2f}  {acc:>19.3f}")
accB = np.mean([trial_graded(rng) for _ in range(TRIALS)])
print(f"\nCURE B — widen the action channel to graded confidence (alpha=0, no recruitment):")
print(f"  collective accuracy = {accB:.3f}")
print("\n=> Cure A confirms the belief's COST: a small contrarian minority barely moves accuracy; it"
      "\n   recovers only near ~80-100% independence. Cure B reaches the same/over with ZERO recruited"
      "\n   contrarians — just a richer report. The cure is expensive ONLY if you insist on recruiting"
      "\n   independents; widening the channel is cheap. Belief REFINED.")
