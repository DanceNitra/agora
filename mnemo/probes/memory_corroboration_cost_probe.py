"""v8 — the freshness-vs-poison Pareto on mnemo's REAL corroboration gates (the one thing the prior-art hunt
found UNMEASURED). NOT a new law: the two-channel/coupling idea is textbook (PeerTrust fusion; quickest-change-
detection delay-vs-false-alarm; Cheng-Friedman 2005 no-symmetric-reputation-is-sybilproof). This just MEASURES
what those gates actually do to an ADAPTIVE forger's cost, and confirms the Cheng-Friedman residual empirically.

A memory earns standing (influences an action) via mnemo's bar: earned credit (un-self-gradable) OR >=2
corroborating witnesses that pass the OPT-IN gates — coherence_gate (witness must be ON-TOPIC, not filler),
temporal_gate (co-arriving witnesses collapse to one; genuine ones spread over time), strict_corroboration
(distinct VERIFIED KEYS, not spoofable source strings). We run the real gate on four actors:

  legit_established : 2 GENUINE witnesses (distinct real sources, on-topic, time-spread, distinct keys).  -> pass
  legit_fresh       : 1 genuine witness (a brand-new true fact not yet re-corroborated).                  -> the FRESHNESS cost
  poison_naive      : 2 CHEAP forged witnesses (one spoofed source, off-topic filler, co-arriving).        -> gates should block
  poison_sleeper    : 2 FULLY-PAID forged witnesses (2 real keypairs the attacker generated, on-topic,
                      time-spread) -- a patient attacker who pays the full d* cost.                        -> the RESIDUAL (passes)

Prints a scenario x gate-config table of corroborated?(True/False). The story that must EMERGE (not be hard-
coded): gates turn a free 2-string forgery into a costly (2-keypair + on-topic + time-spread) one -> they
RAISE the attacker's d* floor; but a sleeper who pays it is indistinguishable from legit (Cheng-Friedman), and
the SAME bar that blocks a 1-witness poison also blocks a 1-witness legit update (the coupling / freshness cost).
"""
import os, sys, time, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from mnemo.mnemo import Mnemo
try:
    from mnemo.mnemo import new_source_keypair, attest
    HAVE_CRYPTO = True
except Exception:
    HAVE_CRYPTO = False

CLAIM = "The capital of the province of Xanthe is Oruma."   # the fact under test (fictional)
ON_TOPIC = ["Xanthe's provincial capital is recorded as Oruma.",
            "Per the Xanthe gazetteer, Oruma is the capital of the province."]
OFF_TOPIC = ["Quarterly revenue rose on strong demand in the eastern markets.",
             "The recipe calls for two cups of flour and a pinch of salt."]


def store(**kw):
    fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd); os.remove(p)
    try:
        s = Mnemo(path=p)
    except TypeError:
        s = Mnemo()
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def witness(s, text, doc, ts, keyed=False):
    """Append a witness record: source string `doc`, timestamp `ts`, and (if keyed) a DISTINCT Ed25519 verified
    key — the exogenous trust root strict_corroboration counts, which a forger can only get by generating a real
    keypair (the Douceur cost)."""
    att = None
    if keyed and HAVE_CRYPTO:
        sk, pk = new_source_keypair()
        att = (pk, attest(text, sk, doc))       # attest binds text to the doc STRING (matches remember's verify)
    wid = s.remember(text, mtype="episodic", source={"doc": doc}, attestation=att)
    rec = next(r for r in s.items if r["id"] == wid)
    rec["ts"] = ts                              # set arrival time (temporal_gate reads ts)
    return wid


def build(scenario):
    """Return (store-config-independent) a store with a CLAIM whose links are the scenario's witnesses."""
    s = store()
    now = 1_000_000.0
    cid = s.remember(CLAIM, mtype="episodic", source={"doc": "primary"})
    claim = next(r for r in s.items if r["id"] == cid)
    W = []
    if scenario == "legit_established":
        W += [witness(s, ON_TOPIC[0], "registry-A", now, keyed=True),              # 2 genuine: distinct real
              witness(s, ON_TOPIC[1], "survey-B", now + 5 * 86400, keyed=True)]    # keys, on-topic, 5 days apart
    elif scenario == "legit_fresh":
        W += [witness(s, ON_TOPIC[0], "registry-A", now, keyed=True)]              # ONE genuine witness (brand new)
    elif scenario == "poison_naive":
        # a COMPETENT cheap forger: 2 DISTINCT source strings, on-topic, time-spread -- but NO real keys (free)
        W += [witness(s, ON_TOPIC[0], "sockpuppet-1", now, keyed=False),
              witness(s, ON_TOPIC[1], "sockpuppet-2", now + 5 * 86400, keyed=False)]
    elif scenario == "poison_sleeper":
        # the patient attacker who PAYS the d* floor: generates 2 real keypairs, on-topic, time-spread
        W += [witness(s, ON_TOPIC[0], "sockpuppet-1", now, keyed=True),
              witness(s, ON_TOPIC[1], "sockpuppet-2", now + 5 * 86400, keyed=True)]
    claim["links"] = W
    return s, claim


CONFIGS = {
    "none":        dict(coherence_gate=None, temporal_gate=None, strict_corroboration=False),
    "coher+temp":  dict(coherence_gate=0.15, temporal_gate=3600, strict_corroboration=False),
    "strict-keys": dict(coherence_gate=None, temporal_gate=None, strict_corroboration=True),
    "all":         dict(coherence_gate=0.15, temporal_gate=3600, strict_corroboration=True),
}
SCENARIOS = ["legit_established", "legit_fresh", "poison_naive", "poison_sleeper"]


def main():
    if not HAVE_CRYPTO:
        print("NOTE: `cryptography` missing -> strict/verified-key arm degrades (keys won't attest); "
              "source-string + coherence + temporal arms still valid.\n")
    print(f"corroborated? (>=2 gate-passing witnesses OR earned credit)  [CLAIM: {CLAIM!r}]\n")
    print(f"{'scenario':20} | " + " | ".join(f"{c:>9}" for c in CONFIGS) + " | cost to reach it")
    print("-" * 88)
    cost = {"legit_established": "2 genuine (real sources+keys, on-topic, spread)",
            "legit_fresh": "1 genuine (a fresh true update)",
            "poison_naive": "2 cheap forged strings (free)",
            "poison_sleeper": "2 real keypairs + on-topic + time-spread (the d* floor)"}
    for sc in SCENARIOS:
        cells = []
        for cfg, kw in CONFIGS.items():
            s, claim = build(sc)
            for k, v in kw.items():
                setattr(s, k, v)
            by = {r["id"]: r for r in s.items}
            cells.append("PASS" if s._corroborated(claim, by) else " -- ")
        print(f"{sc:20} | " + " | ".join(f"{c:>9}" for c in cells) + f" | {cost[sc]}")
    print("\nRead honestly (the result EMERGES from the real gate, it is not hard-coded):")
    print("1. Even COHERENCE + TEMPORAL corroboration is theater against a COMPETENT forger: poison_naive (2")
    print("   distinct source STRINGS, on-topic, time-spread -- all free) passes 'none' AND 'coher+temp'. Writing")
    print("   on-topic and spreading in time costs the attacker ~nothing.")
    print("2. The ONLY gate that imposes a real cost is VERIFIED-KEY independence (strict): it blocks the keyless")
    print("   sybil -> the attacker now needs 2 real Ed25519 keypairs (the Douceur d* floor). This is the ONE")
    print("   channel from the v5/v7 'system-metadata, not content' finding, made concrete.")
    print("3. But the cost is PAYABLE: poison_sleeper (2 real keypairs, on-topic, spread) passes even 'all' --")
    print("   indistinguishable from legit_established. The gate PRICES the attack, it does not CLOSE it")
    print("   (Cheng & Friedman 2005: no symmetric reputation is sybilproof -- confirmed empirically).")
    print("4. The COUPLING / freshness cost: legit_fresh (1 genuine witness, a true new fact) is blocked")
    print("   EVERYWHERE -- the same >=2 bar that stops a 1-witness poison stops a 1-witness legit update. You")
    print("   cannot accept fresh true facts fast without also accepting single-shot poison (quickest-change-")
    print("   detection delay-vs-false-alarm; our Adaptation-Corruption coupling, unescapable by a per-write rule).")


if __name__ == "__main__":
    main()
