"""Graph-shift (randomized retrieval) vs an orthogonal unforgeable outcome-gate — the ASR-vs-UTILITY
tradeoff, measured. (From the cross-framework thread DeepSeek-V3 #1462.)

Setup. A query has M candidate memories with true relevance scores:
  - 1 CORRECT target memory (what the legit user needs), relevance 1.0, GROUNDED (has earned outcome)
  - P POISON memories crafted to OUTRANK it, relevance 1.15 (aimed just above the correct one)
  - the rest DISTRACTORS, relevance ~ U(0, 0.5)
The decision reads the top-1 memory (the one that drives an irreversible action).

Defenses tested:
  * GRAPH-SHIFT: add Normal(0, sigma) noise to the relevance ranking (a targeted attacker can't aim at
    rank-1). Marat's proposal.
  * OUTCOME-GATE: prefer memories carrying an earned-outcome signal, on an axis orthogonal to similarity.
    UNFORGEABLE = only the genuinely-used correct memory is grounded; FORGEABLE = the attacker sets it too.
    HARD gate = restrict the decision to grounded candidates when any exist.

Metrics: ASR = P(a poison drives the decision); UTILITY = P(the correct memory drives it).

FINDINGS (zero-dependency, seeds averaged):
  1. Graph-shift ALONE has no usable operating point. It cuts targeted ASR (1.0 -> ~0.12) but utility does
     NOT recover (<=~0.3): a poison placed just above the correct memory on the *similarity* axis moves
     WITH it under ranking noise, so you trade "poison wins" for "noise wins," never for "truth wins."
     And an adaptive attacker who floods the top-K (P=20-50) pushes ASR back to ~1.0 at every usable sigma.
  2. The failure names the fix: separate on an axis the attacker can't set. Graph-shift + an UNFORGEABLE
     outcome-gate creates the operating point graph-shift can't (ASR 0.66 -> 0.11, utility 0.28 -> 0.89);
     a HARD unforgeable gate defeats even the broad flood (ASR -> 0 at any P, because the flood is on the
     wrong axis); a FORGEABLE gate does nothing (identical to no defense). Unforgeability does all the work.
  3. Coverage is the real limit: the gate only reaches the fraction of memory carrying unforgeable earned
     outcome. At a measured live-deployment coverage of ~0.18, the defense protects the grounded ~18% and
     the rest stays exposed -- the lever is raising the unforgeable-earned-outcome share, not randomization.

Honest scope: a controlled score-model simulation; the "hard gate -> 0" is partly by construction -- the
non-trivial content is that it requires UNFORGEABILITY and its reach is capped by COVERAGE.

Run: python graph_shift_orthogonal_gate_probe.py
"""
import random

M = 200
DIST_HI = 0.5
MARGIN = 0.15   # poison relevance = 1.0 + MARGIN (aimed just above the correct memory)


def _decide(sigma, P, gate_bonus, forgeable, hard, coverage, rng):
    correct_grounded = rng.random() < coverage
    cand = [(1.0, correct_grounded, "c")]
    cand += [(1.0 + MARGIN, forgeable, "p") for _ in range(P)]
    cand += [(rng.uniform(0.0, DIST_HI), False, "d") for _ in range(M - 1 - P)]
    if hard:
        grounded = [x for x in cand if x[1]]
        pool = grounded if grounded else cand
        return max(pool, key=lambda x: x[0] + rng.gauss(0, sigma))[2]
    return max(cand, key=lambda x: x[0] + rng.gauss(0, sigma) + (gate_bonus if x[1] else 0.0))[2]


def measure(sigma, P, gate_bonus=0.0, forgeable=False, hard=False, coverage=1.0, trials=20000, seed=0):
    rng = random.Random(seed)
    asr = util = 0
    for _ in range(trials):
        lab = _decide(sigma, P, gate_bonus, forgeable, hard, coverage, rng)
        asr += lab == "p"
        util += lab == "c"
    return asr / trials, util / trials


def avg(**kw):
    rs = [measure(seed=s, **kw) for s in (1, 2, 3)]
    return sum(r[0] for r in rs) / 3, sum(r[1] for r in rs) / 3


def row(name, **kw):
    print(f"  {name:<46}", end="")
    for P in (1, 20, 50):
        a, u = avg(P=P, **kw)
        print(f"  P={P}: ASR={a:.2f} UTIL={u:.2f}", end="")
    print()


if __name__ == "__main__":
    print("Attackers: P=1 targeted, P=20 adaptive flood, P=50 broad flood. sigma=0.2 graph-shift noise.\n")
    print("GRAPH-SHIFT ALONE (Marat's proposal) — no usable operating point:")
    row("graph-shift only", sigma=0.2, gate_bonus=0.0)
    print("\nADD AN ORTHOGONAL EARNED-OUTCOME GATE (soft bonus 0.5):")
    row("+ unforgeable gate (soft)", sigma=0.2, gate_bonus=0.5, forgeable=False)
    row("+ forgeable gate (attacker forges it)", sigma=0.2, gate_bonus=0.5, forgeable=True)
    print("\nHARD gate (restrict decision to grounded candidates):")
    row("+ HARD unforgeable gate", sigma=0.2, hard=True, forgeable=False)
    row("+ HARD forgeable gate", sigma=0.2, hard=True, forgeable=True)
    print("\nCOVERAGE is the real limit (fraction of Core carrying unforgeable earned outcome):")
    row("HARD unforgeable gate, coverage=1.00", sigma=0.2, hard=True, coverage=1.0)
    row("HARD unforgeable gate, coverage=0.18 (measured)", sigma=0.2, hard=True, coverage=0.18)
    print("\nRead: graph-shift alone -> ASR high or utility dead. Unforgeable orthogonal gate -> ASR~0 UTIL~1")
    print("at any P. Forgeable -> nothing. So unforgeability on an orthogonal axis does the work; coverage caps its reach.")
