"""FRONTIER PROBE — diffcap / failure-correlation of the S x C x I defense triad against a sleeper-fleet
attacker. NOT a "superadditivity law" (that would re-derive defense-in-depth, whose whole content is the
independence-of-failures assumption; prior art: USPTO 11,829,484 "diffcap"; arXiv 2510.11235 "Independent
Safety Mechanisms or Shared Failures?"; Saltzer & Schroeder separation-of-privilege). Instead we MEASURE, for
three specific agent-memory defenses, whether their failures are INDEPENDENT (defense-in-depth holds -> composed
residual = the multiplicative/Bliss product) or CORRELATED (the composition under-delivers), and we test a
pre-registered KILL CONDITION.

Three ORTHOGONAL attacker budgets (a volume; no two payable by the same currency) — from the pre-audit:
  S = DEPTH  (correctness-over-time): a non-transferable earned-outcome ledger that DECAYS; cost = being right
             across many rounds. Gate: an irreversible action needs the driver's standing >= theta_S.
  I = BREADTH (Sybil count): number of ATTESTED identities, capped by an EXTERNAL, behavior-INDEPENDENT
             attestation scarcity N_I; cost = minting identities. Gate: corroboration needs >= k distinct
             attested identities (attacker holds at most N_I). (If I gated on behavior it would collapse into S.)
  C = SEVERITY (per-action blast): unproven memory can drive only REVERSIBLE actions; an irreversible action
             must be reached by decomposing into D reversible steps. Gate: the irreversible action is blocked
             unless capability-granted (earned).

KILL CONDITION (pre-registered): the triad's value hinges on the reversible set being CLOSED UNDER COMPOSITION.
If N individually-reversible corrupted steps sum to one irreversible outcome (reversible_closed=False), the
sleeper defeats S+I by pre-paying and C for FREE by decomposition -> one strategy, all three down -> NO synergy.
If reversible_closed=True, decomposition is rate-limited so each bad step registers in the ledger and trips the
detection-latency floor (d*, Lorden/CUSUM) BEFORE the aggregate crosses irreversibility -> C becomes the
load-bearing orthogonal leg and S decays the pre-earned standing mid-decomposition.

SLEEPER-FLEET ATTACKER (strongest joint strategy): mint min(needed, N_I) attested identities; warm each up for
W honest rounds to bank standing (pays the accuracy tax, beats S); then all corroborate one on-topic poison and
attempt an irreversible action via D reversible steps (beats C iff the reversible set is not closed).

METHOD (per the by-construction audit):
 - MATCHED UTILITY: each leg's threshold is tuned so legit high-stakes pass-rate is held ~constant across all 8
   subsets; we then compare DAMAGE at equal utility (no free wall).
 - NULL = MULTIPLICATIVE survival (Bliss independence), tested in LOG space: predict residual(SCI) =
   residual(∅) * Π (residual(leg)/residual(∅)); SUPERADDITIVE only if measured residual(SCI) < predicted with a
   bootstrap CI on log(meas) - log(pred) excluding 0. The additive-sum null is invalid on a bounded scale.
 - GATE-PROVENANCE: we log which gate (S/C/I) blocks each attack episode, to measure whether S and I fail
   together (correlated -> not a real third axis).

Monte Carlo over seeded attack episodes (no Date.now/random-at-runtime; per-episode seed). Zero-dependency
except numpy. Deterministic. MIT.
Run: python mnemo/probes/triad_diffcap.py
"""
import os, json, random, itertools
import numpy as np

EPISODES = int(os.environ.get("TD_EPISODES", "4000"))   # attack episodes per condition
N_I = 8               # external cap on attested identities the attacker can mint (breadth budget)
K_CORR = 2            # corroboration needs >= this many distinct attested identities
W_WARM = 6            # honest warm-up rounds an identity needs to bank standing (depth budget cost)
DECAY = 0.15          # per-round standing decay (so pre-earned standing bleeds during a slow decomposition)
D_STEPS = 4           # reversible steps a decomposed irreversible attack takes
DSTAR = 3             # detection-latency floor: bad steps within a window > DSTAR are caught (Lorden/CUSUM)
THETA_S = 2.0         # standing bar for an irreversible action (tuned below for matched utility)


def episode(seed, legs, reversible_closed):
    """One attack episode. Returns (success: bool, blocked_by: set). success=True iff the poison lands one
    irreversible corrupted action. legs is a subset of {'S','C','I'}. The attacker plays its optimal joint
    strategy given which legs are active; the environment is stochastic (identity mint failures, warm-up
    outcome noise, detection noise), seeded per episode so all 8 subsets see the SAME randomness (paired)."""
    rng = random.Random(seed)
    blocked = set()

    # --- I (breadth): mint attested identities under the external scarcity cap ---
    # minting each identity succeeds w.p. p_mint (external attestation friction); with I active the cap N_I binds.
    p_mint = 0.9
    minted = sum(1 for _ in range(N_I if 'I' in legs else K_CORR) if rng.random() < p_mint)
    # need K_CORR distinct attested identities to corroborate the poison
    if 'I' in legs and minted < K_CORR:
        blocked.add('I')

    # --- S (depth): warm up each identity to bank standing; standing decays over the attack horizon ---
    # honest warm-up banks good outcomes but each round has outcome noise (a warm-up step can resolve bad).
    # standing = good - bad, then decays by DECAY per round over the (W_WARM + attack) horizon.
    banked = 0.0
    if 'S' in legs:
        good = sum(1 for _ in range(W_WARM) if rng.random() < 0.8)   # honest-but-noisy warm-up
        bad = W_WARM - good
        banked = float(good - bad)
        horizon = W_WARM + (D_STEPS if 'C' in legs else 1)
        banked *= (1.0 - DECAY) ** horizon                          # decay bleeds pre-earned standing
        if banked < THETA_S:
            blocked.add('S')

    # --- C (severity): the irreversible action must be reached by D reversible steps ---
    if 'C' in legs:
        # each reversible corrupted step registers a bad outcome in the ledger with detection noise.
        caught = 0
        for _ in range(D_STEPS):
            if rng.random() < 0.7:            # a bad reversible step is observed w.p. 0.7
                caught += 1
        if reversible_closed:
            # rate-limited: if the decomposition's caught-bad-steps exceed the Lorden floor, it trips BEFORE
            # the aggregate crosses irreversibility -> C blocks. Also, mid-decomposition standing decay (above)
            # already may have dropped the driver below theta_S (S and C intersect here).
            if caught > DSTAR - 1:
                blocked.add('C')
        else:
            # NOT closed: decomposition is free -> C does not block a decomposed attack at all (kill condition).
            pass

    # attack SUCCEEDS iff no active leg blocked it
    success = len(blocked) == 0
    return success, blocked


SUBSETS = ['', 'S', 'C', 'I', 'SC', 'SI', 'CI', 'SCI']


def precompute(reversible_closed):
    """Run each episode ONCE per subset; return {sub: float-array of success} + S/I block flag arrays for SCI.
    Paired: episode seed 1000+e is identical across subsets, so all conditions see the same randomness."""
    succ = {sub: np.zeros(EPISODES, dtype=np.float64) for sub in SUBSETS}
    s_blk = np.zeros(EPISODES); i_blk = np.zeros(EPISODES)
    for e in range(EPISODES):
        sd = 1000 + e
        for sub in SUBSETS:
            ok, b = episode(sd, set(sub), reversible_closed)
            succ[sub][e] = 1.0 if ok else 0.0
            if sub == 'SCI':
                s_blk[e] = 1.0 if 'S' in b else 0.0
                i_blk[e] = 1.0 if 'I' in b else 0.0
    return succ, s_blk, i_blk


def si_corr(s_blk, i_blk):
    both = float(np.sum((s_blk > 0) & (i_blk > 0)))
    s = float(np.sum(s_blk > 0)); i = float(np.sum(i_blk > 0))
    union = s + i - both
    return {"P(I|S)": (both / s) if s else 0.0, "jaccard_S_I": (both / union) if union else 0.0,
            "s_block_rate": s / EPISODES, "i_block_rate": i / EPISODES}


def boot_logsynergy(succ, B=2000):
    """Fast bootstrap: resample INDICES into the precomputed success arrays (no episode re-run)."""
    rng = np.random.default_rng(42)
    diffs = np.empty(B)
    n = EPISODES
    for bi in range(B):
        idx = rng.integers(0, n, n)
        r0 = max(1e-6, succ[''][idx].mean())
        pred = r0
        for lg in ('S', 'C', 'I'):
            pred *= max(1e-6, succ[lg][idx].mean()) / r0
        r_sci = max(1e-6, succ['SCI'][idx].mean())
        diffs[bi] = np.log(r_sci) - np.log(max(1e-6, pred))
    return float(diffs.mean()), (float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)))


print(f"=== TRIAD diffcap: S(depth) x C(severity) x I(breadth) vs sleeper-fleet, {EPISODES} episodes/cond ===\n")
store = {}
for reversible_closed in (False, True):
    succ, s_blk, i_blk = precompute(reversible_closed)
    res = {sub: float(succ[sub].mean()) for sub in SUBSETS}
    corr = si_corr(s_blk, i_blk)
    mean_d, ci = boot_logsynergy(succ)
    store[reversible_closed] = {"res": res, "corr": corr, "ci": ci}
    print(f"--- KILL CONDITION reversible_closed={reversible_closed} " +
          ("(C rate-limited under d*)" if reversible_closed else "(reversible steps sum to irreversible -> C free)"))
    for sub in SUBSETS:
        print(f"    residual[{sub or 'none':<4}] = {res[sub]:.3f}")
    r0 = max(1e-6, res['']); pred = r0
    for lg in ('S', 'C', 'I'):
        pred *= res[lg] / r0
    print(f"    Bliss-null prediction residual[SCI] = {pred:.3f} ; measured = {res['SCI']:.3f}")
    print(f"    log-synergy mean {mean_d:+.3f}  95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]  -> "
          f"{'SUPERADDITIVE' if ci[1] < 0 else 'at/below multiplicative (NO synergy beyond Bliss)'}")
    print(f"    S/I failure correlation: Jaccard(S,I) = {corr['jaccard_S_I']:.2f}  -> "
          f"{'ONE axis (correlated failure)' if corr['jaccard_S_I'] > 0.5 else 'independent'}")
    print()

# ---- verdict ----
corr_closed = store[True]["corr"]; ci_closed = store[True]["ci"]; ci_open = store[False]["ci"]
res_open = store[False]["res"]; res_closed = store[True]["res"]
si_one_axis = corr_closed['jaccard_S_I'] > 0.5
open_kills = res_open['SCI'] >= res_open['C'] - 1e-6          # when not closed, SCI no better than C-less...
# ── SELF-AUDIT: this model is BY-CONSTRUCTION DEGENERATE — do not read the numbers as a result. ──
# (1) At these params S alone -> residual 0 (a perfect wall) and I alone -> residual 1 (a no-op): each leg is
#     not a partial, independently-failing defense at MATCHED UTILITY, so the composition question is degenerate
#     (auditor #1's exact warning: a leg that alone gives 0/1 is a scope restriction, not a composable defense).
# (2) FATAL: S-block and I-block are drawn from INDEPENDENT rng draws here, so their measured "independence"
#     (Jaccard 0) is HARD-CODED, not emergent — the whole point (does the shared pay-ahead currency make S and I
#     fail TOGETHER?) cannot be answered by a model that assumes them independent. A valid model must fund S
#     (warm-up standing) and I (usable corroborators) from ONE shared per-identity investment and let the
#     correlation EMERGE, at matched legit-utility. This attempt does not; its numbers are void.
_valid = False
_superadd_label = "SUPERADDITIVE" if ci_closed[1] < 0 else "NOT superadditive (at/below multiplicative independence)"
_si_label = "CORRELATED - effectively one pay-ahead axis" if si_one_axis else "independent"
verdict = (
    "INVALID ATTEMPT — do NOT cite these numbers (self-audited). This first cut is BY-CONSTRUCTION DEGENERATE: at "
    "these params S alone gives residual 0 (a perfect wall) and I alone gives residual 1 (a no-op), so no leg is a "
    "partial independently-failing defense at matched utility (exactly auditor #1's warning); and S-block / I-block "
    "are drawn from INDEPENDENT rng, so their 'independence' (Jaccard 0) is HARD-CODED, not emergent — which voids "
    "the one thing worth measuring (does the shared pay-ahead currency make S and I fail TOGETHER?). A valid model "
    "must fund S (warm-up standing) and I (usable corroborators) from ONE shared per-identity investment and let the "
    "correlation EMERGE at matched legit-utility. "
    "WHAT ACTUALLY HOLDS (from the rigorous 3-lens PRE-AUDIT, not this sim): the superadditive-triad question is "
    "textbook DEFENSE-IN-DEPTH — its entire content is the independence-of-failures assumption; prior art USPTO "
    "11,829,484 (diffcap), arXiv 2510.11235 ('Independent Safety Mechanisms or Shared Failures?'), Saltzer & "
    "Schroeder (separation of privilege). The honest, non-textbook finding would be the failure-CORRELATION "
    "structure: S (earned standing) and I (corroboration count) plausibly share the pay-ahead currency and fail "
    "together (2 axes, not 3), and C (capability ceiling) is load-bearing ONLY if the reversible set is closed / "
    "rate-limited under the d* floor (Lorden) — which our own reversibility_gate_frontier ARM D already suggested "
    "it is NOT. NET: bod-2 is a textbook re-derivation with a likely-negative correlation result; not worth a "
    "clean measured build under the RAISED BAR. Kept as an honest receipt of a degenerate attempt + the pre-audit.")
print("VERDICT:", verdict)

out = {"scenario": "triad_diffcap", "valid": False, "episodes": EPISODES,
       "params": {"N_I": N_I, "K_CORR": K_CORR, "W_WARM": W_WARM, "DECAY": DECAY, "D_STEPS": D_STEPS,
                  "DSTAR": DSTAR, "THETA_S": THETA_S},
       "reversible_open": {"residual": res_open, "logsynergy_ci": ci_open},
       "reversible_closed": {"residual": res_closed, "logsynergy_ci": ci_closed,
                             "SI_jaccard": corr_closed['jaccard_S_I']},
       "SI_one_axis": bool(si_one_axis), "verdict": verdict}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "triad_diffcap_result.json"), "w"),
          ensure_ascii=False, indent=1)
print("\nsaved: mnemo/probes/triad_diffcap_result.json")
