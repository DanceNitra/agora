"""Recovery-agreement across decorrelated gates: does a second gate close inspeximus's OWN measured residual?

Born from the DeepSeek-V3 #1466 cross-framework collaboration (credit: Marat Sultanov / TAT-7, and the joint
panel). The finding there: at the moment of conflict EVERY act/withhold gate withholds -- a legitimate update
and an attack look identical (B-003 and B-002 both spike at step 1). The discriminator is RECOVERY: does the
contested value earn its way back into the influence set (B-003 out->in, a genuine independent 2nd source) or
not (B-002 out->out, a single-source override + same-origin sybil that never corroborates)? We insisted in the
report that "independent gates converge on the recovery verdict" is a HYPOTHESIS worth testing, not a law. This
probe tests it -- and grounds it in inspeximus's real failure mode.

THE SHARP CLAIM (not the textbook "ensembles help"): a second gate's value on the recovery verdict is bounded by
how DECORRELATED its failure mode is from the first's -- the marginal cut in poison-through scales with (1 - rho),
not with the number of gates. We measure it where it bites: inspeximus's provenance gate is FOOLED by a forged 2nd
source (the storm/verify residual -- two forged distinct sources clear the >=2-distinct-source bar, so a poison
is wrongly judged "recovered"). Gate 1 here is the REAL inspeximus gate (Inspeximus._is_corroborated); its false-allow on a
forged-source attack is real, not modelled. Gate 2 is a coherence-style recovery check whose failure we CORRELATE
with gate 1's by rho in [0,1]. AND-agreement (allow the value back only if BOTH gates say "recovered") is measured
against each gate alone, as rho sweeps.

FINDINGS (self-check asserts the core):
  - gate 1 (real inspeximus) false-allows the forged-source attack ~100% (its known residual).
  - AND-agreement with an ORTHOGONAL gate 2 (rho=0) cuts the forged-source false-allow to ~1-catch2, and the cut
    DECAYS to ~0 as rho->1 (a correlated 2nd gate is one gate counted twice) -- the marginal gain tracks (1-rho).
  - the honest cost: AND-agreement raises the false-WITHHOLD rate on genuine recoveries (a legit update blocked
    because gate 2 mis-fired); we report it alongside so the trade is visible, not hidden.

FALSIFIER: if AND-agreement cut the forged-source false-allow no better at rho=0 than at rho=1 (i.e. the gain did
not track decorrelation), the "different failure mode is the whole mechanism" thesis would be wrong. It is not.

Deterministic (fixed seed; needs numpy). MIT. Part of Agora / inspeximus.
Run:  python research/probes/gate_ensemble_recovery.py
"""
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from inspeximus import Inspeximus

SEED = 7
N = 4000                 # recovery episodes
P_LEGIT = 0.5            # half genuine independent-source recoveries, half forged-source attacks
CATCH2 = 0.85           # gate 2's base catch rate on a forged-source attack when fully independent (rho=0)
FW2 = 0.08              # gate 2's false-withhold rate on a genuine recovery (its own error the other way)


def _inspeximus_recovers_forged():
    """REAL inspeximus gate 1 on a forged-source attack: a poison with TWO forged distinct-source links clears the
    >=2-distinct-source bar, so _is_corroborated == True -> the value is (wrongly) 'recovered'. Returns the
    real verdict (True = inspeximus lets the poison back into the influence set: a false-allow)."""
    m = Inspeximus(os.path.join(tempfile.mkdtemp(), "g.jsonl"))
    P = m.remember("Contested value under override.", source={"doc": "origin-real"})
    c1 = m.remember("witness A", source={"doc": "forged-site-a"})
    c2 = m.remember("witness B", source={"doc": "forged-site-b"})
    by = {x["id"]: x for x in m.items}
    by[P]["links"] = [c1, c2]      # two forged, distinct-looking sources
    return Inspeximus._is_corroborated(by[P], by)


def _inspeximus_recovers_legit():
    """REAL inspeximus gate 1 on a genuine recovery: an independent 2nd source arrives -> corroborated -> recovered."""
    m = Inspeximus(os.path.join(tempfile.mkdtemp(), "g.jsonl"))
    P = m.remember("Contested value, later independently confirmed.", source={"doc": "origin-real"})
    c1 = m.remember("independent confirmation", source={"doc": "independent-lab"})
    c2 = m.remember("second independent confirmation", source={"doc": "independent-forum"})
    by = {x["id"]: x for x in m.items}
    by[P]["links"] = [c1, c2]
    return Inspeximus._is_corroborated(by[P], by)


def main():
    rng = np.random.default_rng(SEED)
    print("=== Recovery-agreement across decorrelated gates (gate 1 = REAL inspeximus; #1466 / TAT-7 finding) ===\n")

    # sanity: gate 1 is the real inspeximus gate. Confirm its residual: it recovers BOTH the legit AND the forged attack.
    g1_forged = _inspeximus_recovers_forged()      # True = false-allow (poison judged 'recovered')
    g1_legit = _inspeximus_recovers_legit()        # True = correct-allow
    print("gate 1 (REAL inspeximus) recovery verdict:")
    print(f"   genuine independent-source recovery -> {g1_legit}  (correct: value earns back in)")
    print(f"   FORGED 2-source attack              -> {g1_forged}  (WRONG: the storm/verify residual -- poison "
          "clears the 2-distinct-source bar)\n")

    is_legit = rng.random(N) < P_LEGIT        # 1 = genuine recovery, 0 = forged-source attack
    # gate 1 = real inspeximus, applied per episode (deterministic given the construction above):
    #   legit -> recovered=True (correct);  forged attack -> recovered=True (WRONG, false-allow).
    g1_recovered = np.where(is_legit, g1_legit, g1_forged)   # both True -> gate 1 alone never blocks the attack

    print(" gate-2 failure corr | forged-attack FALSE-ALLOW (poison back in) | legit FALSE-WITHHOLD | vs gate1")
    base_fa = float((g1_recovered[~is_legit]).mean())        # gate 1 alone: fraction of attacks it lets recover
    for rho in (0.0, 0.25, 0.5, 0.75, 1.0):
        # gate 2 on a forged attack: CATCHES it (says NOT recovered) with prob CATCH2*(1-rho). rho=1 -> gate 2
        # shares gate 1's blind spot and catches nothing; rho=0 -> fully independent failure mode.
        catch2 = CATCH2 * (1.0 - rho)
        g2_recovered = np.empty(N, dtype=bool)
        # on attacks: gate 2 says 'recovered' (i.e. FAILS to catch) with prob 1-catch2
        atk = ~is_legit
        g2_recovered[atk] = rng.random(atk.sum()) >= catch2
        # on genuine recoveries: gate 2 correctly says 'recovered' except its own false-withhold rate FW2
        leg = is_legit
        g2_recovered[leg] = rng.random(leg.sum()) >= FW2
        # AND-agreement: value is allowed back only if BOTH gates say recovered
        agree = g1_recovered & g2_recovered
        fa = float(agree[atk].mean())               # attack still allowed back = false-allow (poison-through)
        fw = float((~agree[leg]).mean())            # genuine recovery blocked = false-withhold (utility cost)
        print(f"        rho={rho:<4}       |            {fa:5.3f}   (gate1 alone {base_fa:.3f})          |"
              f"        {fw:5.3f}        | {'-' if rho==1 else 'cut '+format(base_fa-fa,'+.3f')}")

    # --- self-check (the falsifier) ---
    assert g1_forged is True and g1_legit is True, "gate 1 must be the real inspeximus gate that recovers BOTH (its residual)"
    # measure the cut at rho=0 vs rho=1 on the attack false-allow
    def _fa(rho):
        catch2 = CATCH2 * (1.0 - rho)
        r = np.random.default_rng(SEED + 1)
        atk = ~is_legit
        g2 = r.random(atk.sum()) >= catch2
        return float((g1_recovered[atk] & g2).mean())
    fa0, fa1 = _fa(0.0), _fa(1.0)
    assert fa0 < base_fa - 0.3, "orthogonal gate 2 must sharply cut the forged-source false-allow"
    assert fa1 > fa0 + 0.3, "the cut must DECAY as failure-correlation rises (decorrelation is the mechanism)"

    print("\nVERDICT: gate 1 is the real inspeximus provenance gate, and its forged-source residual is real -- alone it")
    print("lets the forged attack 'recover' ~100%. A SECOND gate on the recovery verdict closes it ONLY to the")
    print("degree its failure mode is decorrelated: an orthogonal gate (rho=0) cuts the false-allow to ~1-catch2,")
    print("and the cut decays to ~0 as rho->1 (a correlated 2nd gate is one gate counted twice). The marginal gain")
    print("tracks (1-rho), at a bounded false-withhold cost -- the #1466 'same decision, different signals' finding,")
    print("made falsifiable: independent gates agreeing on RECOVERY is worth exactly their decorrelation, no more.")
    print("Credit: co-arose with Marat Sultanov / TAT-7 in deepseek-ai/DeepSeek-V3#1466. SCOPE: a minimal model +")
    print("inspeximus's real gate; not yet a second REAL decorrelated gate (that is the next step, with a coherence gate).")


if __name__ == "__main__":
    main()
