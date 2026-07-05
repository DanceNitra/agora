"""Two REAL gates on the recovery verdict: does set-coherence close mnemo's forged-source residual -- and where
do the two gates SHARE a blind spot? (No modelled gate; both are computed.)

Follow-up to gate_ensemble_recovery.py, whose gate 2 was modelled (so its exact 1-rho shape was partly
by-construction). Here BOTH gates are real, and we measure the ACTUAL failure-correlation between them as a
function of attack sophistication -- the non-by-construction result.

  Gate 1 = mnemo PROVENANCE (Mnemo._is_corroborated): a contested value 'recovers' iff it has >=2 distinct
           corroborating sources. Its residual (storm/verify): a forged 2-source attack clears the bar -> it
           lets the poison recover. Provenance counts sources; it never reads whether the witnesses are ABOUT
           the claim.
  Gate 2 = SET-COHERENCE (computed, zero-dependency lexical): a value 'recovers' iff each corroborating witness
           is actually coherent with the claim (min witness<->claim token-Jaccard >= threshold). A lazy forgery
           uses unrelated filler witnesses (low coherence -> caught); a sophisticated forgery writes witnesses
           that are ON-TOPIC (high coherence -> missed).

The sharp, testable question the #1466 collaboration raised (credit: Marat Sultanov / TAT-7): two independent
gates agreeing on RECOVERY is worth their DECORRELATION -- so how decorrelated are provenance and coherence,
really? Answer, measured here: it DEPENDS ON THE ATTACK. Against a lazy (incoherent-witness) forgery the two are
orthogonal -- coherence catches exactly what provenance misses, so AND-agreement closes the residual. Against a
sophisticated (coherent-witness) forgery they SHARE the blind spot 'plausible-looking evidence' -- both pass it,
AND-agreement closes nothing. So a coherence gate does not *close* the forged-source residual; it RAISES THE
FORGER'S BAR from '2 distinct source strings' to '2 distinct source strings + on-topic witness text'.

FINDINGS (self-check asserts the core):
  - provenance alone false-allows the forged attack at EVERY coherence level (~1.0): it can't see witness content.
  - AND-agreement false-allow RISES with forgery coherence: ~0 for an incoherent forgery (coherence catches it)
    up to ~1.0 for a fully coherent forgery (both gates blind) -- the measured decorrelation collapses as the
    attacker invests in coherent witnesses.
  - honest cost: coherence also false-withholds some genuine recoveries (real witnesses that happen to phrase
    the confirmation differently) -- reported alongside.

FALSIFIER: if AND-agreement false-allow were flat across forgery coherence (coherence caught coherent and
incoherent forgeries equally, OR neither), 'coherence adds a decorrelated signal' would be false. It is not flat.

Deterministic (fixed seed; needs numpy). MIT. Part of Agora / mnemo.
Run:  python mnemo/probes/gate_ensemble_coherence.py
"""
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from mnemo import Mnemo

SEED = 11
N = 1500                 # episodes per (arm, coherence level)
COH_THR = 0.18           # gate-2 threshold: min witness<->claim token-Jaccard to count as coherent corroboration
CLAIM_LEN = 10           # tokens per claim
VOCAB = [f"t{i}" for i in range(400)]


def _toks(rng, base, overlap, n=CLAIM_LEN):
    """A witness token set: `overlap` fraction drawn from the claim's tokens `base`, the rest random vocab.
    Per-witness overlap is jittered around the target so coherence varies continuously (a real forgery's
    witnesses are not all equally on-topic) -- this makes the AND-agreement curve a smooth S, not a step."""
    base = list(base)
    overlap = float(np.clip(rng.normal(overlap, 0.15), 0.0, 1.0))
    k_on = int(round(overlap * n))
    on = list(rng.choice(base, size=min(k_on, len(base)), replace=False)) if k_on else []
    off = list(rng.choice(VOCAB, size=n - len(on), replace=False))
    return set(on + off)


def _jacc(a, b):
    return len(a & b) / len(a | b) if (a or b) else 0.0


def _provenance_recovers(n_distinct_sources):
    """REAL mnemo gate 1: build a record with n distinct-source corroborating links, return _is_corroborated."""
    m = Mnemo(os.path.join(tempfile.mkdtemp(), "g.jsonl"))
    P = m.remember("contested value", source={"doc": "origin"})
    links = [m.remember(f"w{i}", source={"doc": f"src-{i}"}) for i in range(n_distinct_sources)]
    by = {x["id"]: x for x in m.items}
    by[P]["links"] = links
    return Mnemo._is_corroborated(by[P], by)


def main():
    rng = np.random.default_rng(SEED)
    print("=== Two REAL gates on recovery: provenance vs set-coherence, vs forgery sophistication (#1466/TAT-7) ===\n")

    # gate 1 is REAL mnemo and deterministic on the source count: a 2-distinct-source forgery recovers (residual).
    prov_forged = _provenance_recovers(2)     # True -> false-allow
    prov_legit = _provenance_recovers(2)      # True -> correct
    print(f"gate 1 (REAL mnemo provenance): 2-source forgery recovers -> {prov_forged} (residual); "
          f"genuine 2-source recovery -> {prov_legit}\n")

    # LEGIT episodes: witnesses genuinely on-topic (coherence high). Measure gate-2 false-withhold once.
    fw = 0
    for _ in range(N):
        claim = set(rng.choice(VOCAB, size=CLAIM_LEN, replace=False))
        ws = [_toks(rng, claim, overlap=rng.uniform(0.5, 0.8)) for _ in range(2)]
        coh = min(_jacc(claim, w) for w in ws)
        if coh < COH_THR:                     # coherence wrongly blocks a genuine recovery
            fw += 1
    fw_rate = fw / N

    print(" forgery witness coherence | provenance FALSE-ALLOW | coherence catches | AND-agreement FALSE-ALLOW")
    fa_curve = {}
    for ov in (0.0, 0.1, 0.2, 0.35, 0.6):
        prov_fa = coh_pass = 0
        for _ in range(N):
            claim = set(rng.choice(VOCAB, size=CLAIM_LEN, replace=False))
            ws = [_toks(rng, claim, overlap=ov) for _ in range(2)]     # forged witnesses at this coherence level
            coh = min(_jacc(claim, w) for w in ws)
            prov_fa += 1 if prov_forged else 0                          # provenance always allows the 2-source forgery
            if coh >= COH_THR:                                          # gate 2 FAILS to catch (passes it)
                coh_pass += 1
        prov_rate = prov_fa / N
        coh_catch = 1.0 - coh_pass / N
        and_fa = coh_pass / N                                           # both allow == provenance(1.0) AND coherence-pass
        fa_curve[ov] = and_fa
        print(f"        overlap={ov:<4}        |        {prov_rate:5.3f}         |      {coh_catch:5.3f}      |"
              f"        {and_fa:5.3f}")

    print(f"\n  legit-recovery FALSE-WITHHOLD from the coherence gate: {fw_rate:.3f} (its honest utility cost)")

    # --- self-check (the falsifier) ---
    assert prov_forged is True, "gate 1 must be the real mnemo gate with the forged-source residual"
    assert fa_curve[0.0] < 0.2, "against an INCOHERENT forgery, coherence must catch it -> AND-agreement closes it"
    assert fa_curve[0.6] > fa_curve[0.0] + 0.4, "AND-agreement false-allow must RISE with forgery coherence (shared blind spot)"

    print("\nVERDICT: both gates are real. Provenance alone lets the 2-source forgery recover at every coherence")
    print("level (~1.0) -- it counts sources, never reads witness content. Set-coherence catches the forgery ONLY")
    print("when its witnesses are incoherent, so AND-agreement false-allow rises from ~%.2f (lazy, off-topic filler)"
          % fa_curve[0.0])
    print("to ~%.2f (witnesses crafted on-topic), where the two gates SHARE the blind spot 'plausible evidence'."
          % fa_curve[0.6])
    print("So the #1466 recovery-agreement is REAL but ATTACK-RELATIVE: a coherence gate does not CLOSE the forged-")
    print("source residual -- it raises the forger's bar from '2 distinct sources' to '2 distinct sources + on-topic")
    print("witnesses', at a %.1f%% false-withhold cost. Decorrelation is not a constant the defender sets; the" % (fw_rate * 100))
    print("adversary controls it. Credit: co-arose with Marat Sultanov / TAT-7 in deepseek-ai/DeepSeek-V3#1466.")


if __name__ == "__main__":
    main()
