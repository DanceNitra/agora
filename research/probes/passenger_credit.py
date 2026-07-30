"""PASSENGER CREDIT — does retrieval-conditioned credit() promote a provably NON-CAUSAL memory
into inspeximus's durable / influence tier?

Lead e5d955 (Rocchi, "Does Memory Credit Travel?", SSRN 10.2139/ssrn.7160321, 2026-07-27) measures,
on ALFWorld: of 169 joint successes a retrieval-conditioned ledger would credit to the candidate
memory, only 10 are marginal helps (5.9% precision); 159 are "passenger credit".

That precision number is near-definitional once the bank-only success rate is high, so this probe does
NOT try to re-derive it. It asks the consequential question on OUR OWN substrate:

    inspeximus's credit(ids, outcome) credits EVERY RECALLED id on success.
    good/bad then feed (a) recall ranking, (b) the influence gate, (c) episodic->semantic graduation.
    The code's own comment claims that bar is "EARNED ... set only by credit() resolving real work,
    not self-assertable".

    HYPOTHESIS: a memory that is never causal for any episode can EARN that bar by riding along in
    the recalled set, so "earned" does not mean "caused".

FALSIFIER: if the passenger does NOT pass the influence gate and does NOT graduate after T
successful episodes, the hypothesis is dead.

Controls (must pass, or the measurement is void):
  C1 never-recalled passenger  -> MUST score 0 (a passenger that is never retrieved cannot earn).
  C2 genuinely causal memory   -> MUST score 1 (if credit does not promote a real earner, the
                                  instrument is broken and arm A proves nothing).
Denominators are printed explicitly.  Zero-dependency lexical mode = deterministic, no GPU, no cloud.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "inspeximus_pypi"))
from inspeximus.core import Inspeximus  # noqa: E402

# Each topic gets a DISTINCTIVE subject word so the causal memory is reliably retrievable for its
# own query.  (A first draft used "service 0..29", which differ only by a digit: the causal memory
# reached the top-K in 2/30 episodes and control C2 failed, voiding the run.  The discriminating
# token has to be real, or the probe measures retrieval failure instead of credit.)
SUBJECTS = [
    "billing", "authentication", "search", "checkout", "inventory", "notification",
    "recommendation", "analytics", "scheduler", "gateway", "identity", "pricing",
    "shipping", "catalogue", "messaging", "telemetry", "archival", "translation",
    "moderation", "provisioning",
]
N_TOPICS = len(SUBJECTS)
K = 3

QUERY = "how do I roll back the {s} service"
CAUSAL = "{s} rollback: drain connections then flip the traffic weight"
# Shares the PROCEDURE vocabulary with every query, carries no subject -> co-recalls, never causal.
PASSENGER_NEAR = "roll back the service: general standing note on rollback and traffic"
# Control C1: shares nothing with the queries -> never recalled.
PASSENGER_FAR = "banana bread requires ripe fruit and a warm oven overnight"


def _ollama_embed(text):
    """Local nomic-embed-text, so the result is not an artifact of lexical token overlap."""
    import urllib.request
    body = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
    req = urllib.request.Request("http://localhost:11434/api/embeddings", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["embedding"]


EMBED = None  # set to _ollama_embed for the semantic arm


def build(passenger_text, require_warrant):
    path = os.path.join(tempfile.mkdtemp(), "store.json")
    m = Inspeximus(path, embed=EMBED)
    m.credit_requires_warrant = require_warrant
    causal_ids = {}
    for j, s in enumerate(SUBJECTS):
        r = m.remember(CAUSAL.format(s=s), tags=["runbook"])
        causal_ids[j] = r["id"] if isinstance(r, dict) else r
    p = m.remember(passenger_text, tags=["runbook"])
    passenger_id = p["id"] if isinstance(p, dict) else p
    return m, causal_ids, passenger_id


def run_arm(name, passenger_text, require_warrant, warrant):
    m, causal_ids, pid = build(passenger_text, require_warrant)
    episodes = successes = credit_calls = credits_issued = credits_to_passenger = 0
    passenger_recalled = 0

    credited_causal = []
    for j, s in enumerate(SUBJECTS):
        episodes += 1
        hits = m.recall(QUERY.format(s=s), k=K)
        ids = [h["id"] for h in hits]
        if pid in ids:
            passenger_recalled += 1
        # Deterministic ground truth: the episode succeeds iff its causal memory was retrieved.
        if causal_ids[j] not in ids:
            continue
        successes += 1
        # This is the DOCUMENTED usage: credit the recalled set on a real outcome.
        m.credit(ids, True, warrant=warrant)
        credit_calls += 1
        credits_issued += len(ids)
        credited_causal.append((j, s))
        if pid in ids:
            credits_to_passenger += 1

    by_id = {r["id"]: r for r in m.items}
    p = by_id[pid]
    # Behavioural check, not a private-method call: does the influence-only read path return it?
    infl_hits = m.recall(PASSENGER_NEAR, k=10, influence_only=True, reinforce=False)
    in_influence = pid in [h["id"] for h in infl_hits]
    # C2: a genuinely causal memory that WAS credited must also earn the bar. (Checking an
    # arbitrary causal memory instead of a credited one is what broke the first run: an uncredited
    # memory legitimately fails the gate, which is the gate working, not the instrument working.)
    causal_in_influence = None
    if credited_causal:
        j, s = credited_causal[0]
        infl_causal = m.recall(CAUSAL.format(s=s), k=10, influence_only=True, reinforce=False)
        causal_in_influence = causal_ids[j] in [h["id"] for h in infl_causal]

    return {
        "arm": name,
        "require_warrant": require_warrant,
        "warrant_passed": warrant,
        "episodes": episodes,
        "successes": successes,
        "credit_calls": credit_calls,
        "credits_issued": credits_issued,
        "credits_to_passenger": credits_to_passenger,
        "passenger_recalled_in": passenger_recalled,
        # marginal helps for the passenger, by construction of the success rule:
        "passenger_marginal_helps": 0,
        "passenger_good": float(p.get("good", 0) or 0),
        "passenger_good_warranted": float(p.get("good_warranted", 0) or 0),
        "passenger_bad": float(p.get("bad", 0) or 0),
        "passenger_value": round(float(p.get("value", 0) or 0), 2),
        "passenger_mtype": p.get("mtype"),
        "passenger_graduated": bool((p.get("meta") or {}).get("graduated_from_episodic")),
        "passenger_in_influence_set": in_influence,
        "causal_in_influence_set": causal_in_influence,
    }


def main():
    global EMBED
    if "--embed" in sys.argv:
        EMBED = _ollama_embed
        print("MODE: semantic (local nomic-embed-text)")
    else:
        print("MODE: lexical (zero-dependency default)")
    arms = [
        run_arm("A_passenger_corecalls", PASSENGER_NEAR, False, None),
        run_arm("C1_control_never_recalled", PASSENGER_FAR, False, None),
        run_arm("D_warrant_gate_on", PASSENGER_NEAR, True, "resolved-ticket-4471"),
    ]
    for a in arms:
        print(json.dumps(a, ensure_ascii=False))

    A = arms[0]
    C1 = arms[1]
    D = arms[2]

    print("\n--- CONTROLS ---")
    c1_ok = (C1["passenger_good"] == 0 and not C1["passenger_in_influence_set"])
    c2_ok = A["causal_in_influence_set"]
    print(f"C1 never-recalled passenger scores 0                : {'PASS' if c1_ok else 'FAIL'} "
          f"(good={C1['passenger_good']}, influence={C1['passenger_in_influence_set']})")
    print(f"C2 genuinely causal memory IS promoted (instrument) : {'PASS' if c2_ok else 'FAIL'}")

    print("\n--- PRIMARY ENDPOINT ---")
    print(f"denominator: {A['episodes']} episodes, {A['successes']} successes, "
          f"{A['credits_issued']} individual credits issued across {A['credit_calls']} credit() calls")
    print(f"passenger was in the recalled set {A['passenger_recalled_in']}/{A['episodes']} times, "
          f"received {A['credits_to_passenger']} good credits, "
          f"and caused {A['passenger_marginal_helps']} successes")
    print(f"passenger passes influence gate (warrant OFF): {A['passenger_in_influence_set']}")
    print(f"passenger passes influence gate (warrant ON) : {D['passenger_in_influence_set']} "
          f"(good_warranted={D['passenger_good_warranted']})")

    if not (c1_ok and c2_ok):
        print("\nRESULT: VOID — a control failed, the arms prove nothing.")
    elif A["passenger_in_influence_set"]:
        print("\nRESULT: HYPOTHESIS SUPPORTED — a provably non-causal memory earned the bar.")
    else:
        print("\nRESULT: FALSIFIED — passenger did not earn the bar.")


if __name__ == "__main__":
    main()
