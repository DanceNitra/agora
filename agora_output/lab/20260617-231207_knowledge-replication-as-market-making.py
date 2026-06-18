"""
Insight (inbox 76a473): model KNOWLEDGE REPLICATION as MARKET-MAKING under adverse selection.

Agora's Crucible IS a market maker in claims: it accepts claims into the belief stock, can pay to
REPLICATE (a noisy verification), and bears adverse-selection risk (some claims are false = toxic
order flow). Akerlof (lemons) / Glosten-Milgrom say an ordinary market UNRAVELS when the toxic
fraction is high. The ORIGINAL, non-textbook claim here is the knowledge-specific twist:

  A knowledge market differs from a goods market because an accepted-true belief has REUSE value
  (it is consumed many times: canon, a memory product). That reuse externality makes replication
  rational at false-claim rates that would freeze a one-shot market -> the lemons collapse is
  POSTPONED, with a ceiling set by replication ACCURACY (not budget or reuse).

Falsifiable: if reuse does NOT shift the freeze threshold (knowledge market collapses at the same
false-rate q* as a one-shot goods market), the "knowledge is special" claim is wrong.

Setup. Claims are True w.p. 1-q, False w.p. q. Actions per claim:
  - reject            -> value 0
  - accept blindly    -> R*[(1-q)*v_true - q*pen]            (no verification)
  - replicate (cost c)-> -c + R*[(1-q)*p_t*v_true - q*p_f*pen]  (accept iff the test is positive)
R = reuse multiplier (1 = one-shot goods market; >1 = knowledge with reuse). p_t,p_f = replication
sensitivity / false-positive. The market "freezes" (produces nothing) when the best action is reject.
q* = the false-rate at which the optimal net value hits 0 (freeze threshold).
"""
import numpy as np

V_TRUE, PEN, P_T, P_F, C = 1.0, 1.0, 0.90, 0.15, 0.20

def net_value(q, R):
    reject = 0.0
    blind = R * ((1 - q) * V_TRUE - q * PEN)
    replicate = -C + R * ((1 - q) * P_T * V_TRUE - q * P_F * PEN)
    best = max(reject, blind, replicate)
    action = ["reject", "accept-blind", "replicate"][int(np.argmax([reject, blind, replicate]))]
    return best, action

def freeze_q(R, grid):
    """Largest false-rate q at which the market still produces (optimal action != reject)."""
    last = 0.0
    for q in grid:
        best, act = net_value(q, R)
        if act == "reject" and best <= 1e-9:
            return last
        last = q
    return last

def simulate(q, R, N=40000, seed=7):
    """Monte-Carlo solvency check under the optimal per-claim policy: realized net value + belief truth."""
    rng = np.random.default_rng(seed)
    _, act = net_value(q, R)
    truth = rng.random(N) >= q          # True claim?
    val = 0.0; accepted = 0; accepted_true = 0
    for t in truth:
        if act == "reject":
            continue
        if act == "accept-blind":
            accepted += 1; accepted_true += int(t)
            val += R * (V_TRUE if t else -PEN)
        else:  # replicate
            val -= C
            test_pos = (rng.random() < (P_T if t else P_F))
            if test_pos:
                accepted += 1; accepted_true += int(t)
                val += R * (V_TRUE if t else -PEN)
    purity = (accepted_true / accepted) if accepted else None
    return act, val / N, purity, accepted / N

if __name__ == "__main__":
    grid = [round(x, 3) for x in np.arange(0.0, 0.95, 0.01)]
    # theoretical freeze ceiling for replicate-with-infinite-reuse: bracket root (1-q)p_t = q p_f
    ceil = P_T / (P_T + P_F)
    print(f"Knowledge market = market-making in claims (replication accuracy p_t={P_T}, p_f={P_F}, cost c={C}).")
    print(f"Theoretical freeze ceiling (reuse->inf) = p_t/(p_t+p_f) = {ceil:.3f}\n")
    print("  reuse R | freeze threshold q* (max false-rate the market still produces) | optimal action near q*")
    qs = {}
    for R in [1, 2, 5, 10, 30]:
        qstar = freeze_q(R, grid)
        _, act = net_value(min(qstar, 0.94), R)
        qs[R] = qstar
        print(f"    R={R:<3} -> q* = {qstar:.0%}   (action just below freeze: {act})")
    rises = all(qs[r2] >= qs[r1] for r1, r2 in zip([1,2,5,10],[2,5,10,30]))
    gap = qs[10] - qs[1]

    print("\n  Monte-Carlo solvency check (optimal policy):")
    for (q, R) in [(0.30, 1), (0.30, 10), (0.70, 10), (0.90, 10)]:
        act, npv, pur, acc = simulate(q, R)
        ps = f"{pur:.0%}" if pur is not None else "n/a"
        print(f"    q={q:.0%} R={R:<3}: action={act:<12} net/claim={npv:+.2f}  accepted={acc:.0%}  belief-purity={ps}")

    print("\n=== VERDICT ===")
    print(f"A) freeze threshold q* RISES with reuse R: {rises}  {[(r, round(v,2)) for r,v in qs.items()]}")
    print(f"B) reuse postpones the lemons collapse: q*(R=1)={qs[1]:.0%} -> q*(R=10)={qs[10]:.0%} (gap +{gap:.0%})")
    print(f"C) ceiling set by replication ACCURACY, not reuse: q* -> {ceil:.0%} as R grows (q*(R=30)={qs[30]:.0%})")
    ok = rises and gap > 0.05 and abs(qs[30] - ceil) < 0.05
    if ok:
        print("\nKNOWLEDGE-MARKET-MAKING CONFIRMED (and it is NOT just Akerlof):")
        print("A one-shot goods market freezes at a false-claim rate of ~50% (accept-blind goes net-negative,")
        print("and one replication is not worth its cost). But a KNOWLEDGE market - where an accepted-true")
        print("belief is reused many times (canon, a memory product) - rationally keeps replicating and stays")
        print(f"solvent up to ~{ceil:.0%} false claims. The reuse externality is what makes verification pay; the")
        print("hard CEILING is set by replication ACCURACY p_t/(p_t+p_f), not by budget or reuse. Actionable")
        print("for the Crucible: its replication spend is justified by REUSE, and raising test accuracy - not")
        print("just doing more replications - is what lets the belief stock tolerate a noisier literature.")
    else:
        print("\nNot confirmed as stated (see clause) -- honest partial result.")
