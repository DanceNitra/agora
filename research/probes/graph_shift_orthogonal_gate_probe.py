"""Graph-shift (randomized retrieval) vs an unforgeable earned-outcome gate — a MEASURED reality-check,
not a new idea. (From the cross-framework thread DeepSeek-V3 #1462.)

WHAT THIS IS (honest framing). Both mechanisms here are textbook; this probe only measures where they
land on a realistic retrieval model, plus one number from our own deployment.
  - "Graph-shift" = randomized retrieval = a MOVING-TARGET DEFENSE (Sengupta et al. 2019); randomized
    defenses degrade under adaptive attackers is the adaptive-attack canon (Carlini & Wagner 2017;
    Athalye-Carlini-Wagner "Obfuscated Gradients" 2018; Tramer et al. 2020); the utility cost of
    randomized/DP defenses vs poisoning is known (Ma et al. 2019).
  - "Separate poison from truth on an axis the attacker can't set (an UNFORGEABLE signal)" is
    Kerckhoffs / Saltzer-Schroeder and the sybilproof-reputation impossibility (Cheng & Friedman 2005;
    Douceur 2002); unforgeable provenance = attestation (RATS RFC 9334, SLSA). Our own prior result is
    the same ("content memory defenses are forgeable; only unforgeable system write-history holds").
Our contribution is ONLY the measurement: the forgeable-vs-unforgeable ablation, and the coverage number.

MODEL (fair: few serious rivals, DISTRIBUTIONAL adversary, top-K read — not argmax over a huge field).
A query has: 1 CORRECT memory (relevance 1.0, GROUNDED = carries earned outcome), P POISON (relevance
~ Normal(1.10, 0.12), aimed near the correct one), and R=15 distractors ~ U(0, 0.6). Graph-shift adds
Normal(0, sigma) to the ranking; the system reads the TOP-K=5 and the action is driven by the top entry
(after an optional HARD outcome-gate that restricts the top-K to grounded entries when any are present).
UNFORGEABLE = only the correct memory is grounded; FORGEABLE = poison forges grounding too.
ASR = P(a poison drives the action); UTILITY = P(the correct memory drives it).

MEASURED (seeds averaged):
  graph-shift only          : targeted P=1 ASR 0.61 / util 0.36 ; flood P=10 ASR 0.97 -> insufficient.
  + HARD unforgeable gate    : targeted P=1 ASR 0.01 / util 0.99 (strong for the TARGETED case), but it
                               DEGRADES under a flood (P=10 ASR ~0.72): if the correct memory doesn't
                               survive into the top-K, there is nothing grounded to prefer. NOT a hard block.
  + HARD forgeable gate      : does nothing (identical to no defense) -> unforgeability is load-bearing.
  coverage: the gate only reaches the fraction of Core carrying unforgeable earned outcome; at our measured
            live-deployment coverage ~0.18, most of Core stays exposed.

HONEST TAKEAWAY: randomized retrieval alone doesn't stop poisoning (textbook MTD + adaptive attacks);
an unforgeable earned-outcome gate strongly helps the TARGETED case and its work comes entirely from
UNFORGEABILITY (a forgeable copy does nothing) — but it is not a hard block under flooding and its reach
is capped by how much memory carries the unforgeable signal (~18% in our deployment). A controlled
simulation; the load-bearing claims (unforgeability does the work; coverage caps reach) are model-robust,
the exact ASR/utility magnitudes are model-dependent.

Run: python graph_shift_orthogonal_gate_probe.py
"""
import random

R_DISTRACTORS = 15
K = 5


def _act(sigma, P, hard, forgeable, coverage, rng):
    correct_grounded = rng.random() < coverage
    cand = [(1.0, correct_grounded, "c")]
    cand += [(rng.gauss(1.10, 0.12), forgeable, "p") for _ in range(P)]
    cand += [(rng.uniform(0.0, 0.6), False, "d") for _ in range(R_DISTRACTORS)]
    topk = sorted(cand, key=lambda x: -(x[0] + rng.gauss(0, sigma)))[:K]
    if hard:
        grounded = [x for x in topk if x[1]]
        return (grounded if grounded else topk)[0][2]
    return topk[0][2]


def measure(sigma, P, hard=False, forgeable=False, coverage=1.0, trials=40000, seed=0):
    rng = random.Random(seed)
    asr = util = 0
    for _ in range(trials):
        lab = _act(sigma, P, hard, forgeable, coverage, rng)
        asr += lab == "p"
        util += lab == "c"
    return asr / trials, util / trials


def avg(**kw):
    rs = [measure(seed=s, **kw) for s in (1, 2, 3)]
    return sum(r[0] for r in rs) / 3, sum(r[1] for r in rs) / 3


def show(name, **kw):
    print(f"  {name:<38}", end="")
    for P in (1, 10, 30):
        a, u = avg(P=P, **kw)
        print(f"   P={P:>2}: ASR={a:.2f} UTIL={u:.2f}", end="")
    print()


if __name__ == "__main__":
    print("Fair model (R=15 rivals, distributional poison, top-K=5 read). sigma=0.2 graph-shift.")
    print("P=1 targeted, P=10/30 flood.\n")
    show("graph-shift only", sigma=0.2)
    show("+ HARD unforgeable outcome-gate", sigma=0.2, hard=True, forgeable=False)
    show("+ HARD forgeable gate", sigma=0.2, hard=True, forgeable=True)
    print("\nCoverage caps reach (HARD unforgeable gate, P=10):")
    for cov in (1.0, 0.18):
        a, u = avg(sigma=0.2, P=10, hard=True, coverage=cov)
        print(f"  coverage={cov:<4}  ASR={a:.2f} UTIL={u:.2f}")
    print("\nRead: graph-shift alone insufficient (textbook MTD + adaptive attacks). Unforgeable gate strongly")
    print("helps the TARGETED case, degrades under flood, and does nothing if forgeable -> unforgeability is")
    print("the load-bearing part; coverage (~18% of our Core) caps its reach. Measurement, not a new principle.")
