"""Crucible silent-failure receipt: do 2026 soft RAG-freshness blends quietly return STALE values on
back-dated / out-of-order writes — a case the published papers never test?

This is NOT a new method and NOT "our gate beats theirs." The FIX is 40-year-old textbook (valid-time vs
transaction-time; Snodgrass & Ahn, "A Taxonomy of Time in Databases," ACM SIGMOD 1985; SQL:2011
application_time vs system_time; Kimball SCD Type-2). The contribution is only the runnable receipt that the
*published* soft-blend freshness scorers (all arXiv preprints, 2025-26) silently carry the bug, because
their temporal channel keys on CREATION/INGEST time, and their own benchmarks are monotonic-in-arrival
(they never run an out-of-order write).

To de-confound (we vary ONE thing): we hold the SOFT BLEND mechanism fixed and change only the TEMPORAL
FIELD it reads — creation-time (as published) vs valid-time (the bitemporal fix). Blend is the verbatim
weighted sum from the SmartVector framework (Xu, "Self-Aware Vector Embeddings for Retrieval-Augmented
Generation," arXiv:2604.20598):
    score = 0.35*cos + 0.25*temporal + 0.25*confidence + 0.15*relational ,  temporal = 0.5^(age/H)
'age' is measured from creation-time in the published version, from valid-time in the fixed version.

Regimes:
  monotonic   : the value that became true later was also ingested later (creation order = valid order).
  back_dated  : the CURRENT-correct value was ingested EARLIER; a STALE value is back-filled / arrives LATER
                (out-of-order). Realistic for late corrections, replays, merged revisions. (Even the
                deterministic max-serial last-write-wins of Reddy & Challaram, arXiv:2606.01435, keys on
                serial/arrival order, so it is blind to this case too.)

Scope (honest): only the SOFT-BLEND SCORING subfamily inherits this. The temporal-KG / validity-interval
camp (TimeQA; "When Facts Expire," CIKM 2025; production "valid from-to" layers) already keys on valid-time
and is NOT affected (a given production system must be checked to confirm it stores valid-time, not ingest).
Falsifier: if the verbatim creation-time blend does NOT drop on back_dated, the receipt is wrong.

Run: python research/probes/soft_freshness_backdated.py   (numpy + local Ollama nomic-embed-text). Agora/mnemo MIT."""
import json, urllib.request, numpy as np

OLLAMA = "http://localhost:11434/api/embed"
MODEL = "nomic-embed-text"
W_SIM, W_TEMP, W_CONF, W_REL = 0.35, 0.25, 0.25, 0.15        # arXiv:2604.20598 weights, verbatim

FACTS = [
    ("the billing API", "authentication method", "OAuth2", "API keys"),
    ("the staging database", "host", "db-staging-01", "db-staging-07"),
    ("the deploy script", "default branch", "master", "main"),
    ("the pricing tier Pro", "monthly price", "29 dollars", "39 dollars"),
    ("the cache layer", "eviction policy", "LRU", "two-tier value-protected"),
    ("the auth service", "session timeout", "30 minutes", "15 minutes"),
    ("the report job", "schedule", "every night at 2am", "every 6 hours"),
    ("project Atlas", "tech lead", "Maria", "Daniel"),
    ("the API rate limit", "value", "100 requests per minute", "300 requests per minute"),
    ("the model endpoint", "default model", "gpt-4", "claude-opus"),
    ("the backup retention", "window", "7 days", "30 days"),
    ("the frontend framework", "version", "React 17", "React 19"),
    ("the data warehouse", "region", "us-east-1", "eu-west-1"),
    ("the password policy", "minimum length", "8 characters", "12 characters"),
    ("the support queue", "owner team", "Team Falcon", "Team Otter"),
    ("the feature flag rollout", "percentage", "10 percent", "50 percent"),
    ("the encryption standard", "algorithm", "AES-128", "AES-256"),
    ("the onboarding flow", "number of steps", "5 steps", "3 steps"),
    ("the CI pipeline", "test runner", "Jest", "Vitest"),
    ("the storage bucket", "access level", "private", "public-read"),
    ("the metric dashboard", "refresh interval", "60 seconds", "10 seconds"),
    ("the license", "type", "MIT", "Apache-2.0"),
    ("the queue broker", "technology", "RabbitMQ", "Kafka"),
    ("the admin override code", "value", "4471", "9920"),
]


def batch_embed(texts, batch=64):
    out = []
    for i in range(0, len(texts), batch):
        body = json.dumps({"model": MODEL, "input": texts[i:i+batch]}).encode()
        req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
        out += json.loads(urllib.request.urlopen(req, timeout=120).read())["embeddings"]
    return [np.array(v, dtype=float) for v in out]


def sent(s, r, o): return f"{s} {r}: {o}"
def cos(a, b): return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def run_regime(regime, text2vec, qvecs, mu):
    n = len(FACTS)
    recs = []
    for i, (s, r, o_old, o_new) in enumerate(FACTS):
        # valid-time: new value became true later (vt=1) than old (vt=0).
        if regime == "monotonic":   # creation order == valid order
            ct_new, ct_old = 1.0, 0.0
        else:                        # back_dated: the STALE value is back-filled / arrives LATER
            ct_new, ct_old = 0.0, 1.0
        recs.append({"fi": i, "subj": s, "text": sent(s, r, o_old), "correct": False, "vt": 0.0, "ct": ct_old})
        recs.append({"fi": i, "subj": s, "text": sent(s, r, o_new), "correct": True,  "vt": 1.0, "ct": ct_new})
    for x in recs:
        x["vec"] = text2vec[x["text"]] - mu
        x["conf"] = 0.8
    Q = [v - mu for v in qvecs]
    METHODS = ("cosine", "soft_blend[creation-time]", "soft_blend[valid-time]")
    res = {m: {"recall": 0, "fresh": 0} for m in METHODS}
    for i in range(n):
        q = Q[i]; subj = FACTS[i][0]
        def sc_cos(x): return cos(q, x["vec"])
        def sc_soft(x, field):                      # SAME blend; only the temporal field differs
            temporal = 0.5 ** (1.0 - x[field])      # field='ct' (as published) or 'vt' (bitemporal fix)
            rel = 1.0 if x["subj"] == subj else 0.0
            return W_SIM*cos(q, x["vec"]) + W_TEMP*temporal + W_CONF*x["conf"] + W_REL*rel
        picks = {"cosine": max(recs, key=sc_cos),
                 "soft_blend[creation-time]": max(recs, key=lambda x: sc_soft(x, "ct")),
                 "soft_blend[valid-time]":   max(recs, key=lambda x: sc_soft(x, "vt"))}
        for m, top in picks.items():
            if top["fi"] == i:
                res[m]["recall"] += 1
                if top["correct"]:
                    res[m]["fresh"] += 1
    return res, n


def main():
    all_texts = []
    for (s, r, o_old, o_new) in FACTS:
        all_texts += [sent(s, r, o_old), sent(s, r, o_new)]
    queries = [f"What is the {r} of {s}?" for (s, r, _o, _n) in FACTS]
    rvecs = batch_embed(all_texts); qvecs = batch_embed(queries)
    mu = np.vstack(rvecs + qvecs).mean(axis=0)
    text2vec = {t: v for t, v in zip(all_texts, rvecs)}

    print("=== Do 2026 soft RAG-freshness blends silently fail back-dated writes? (n=%d facts) ===" % len(FACTS))
    print("    Same verbatim SmartVector blend (arXiv:2604.20598); only the TEMPORAL FIELD differs.")
    print("    fresh|recall = of recalled, %% returning the CURRENT (valid-now) value.\n")
    out = {}
    for regime in ("monotonic", "back_dated"):
        res, n = run_regime(regime, text2vec, qvecs, mu)
        out[regime] = res
        print(f"[{regime}]")
        print(f"    {'method':<28}{'recall':>9}{'fresh|recall':>14}")
        for m in ("cosine", "soft_blend[creation-time]", "soft_blend[valid-time]"):
            rc = res[m]["recall"]; fr = res[m]["fresh"]
            print(f"    {m:<28}{rc/n:>9.0%}{(fr/rc if rc else 0):>14.0%}")
        print()
    ct_mono = out["monotonic"]["soft_blend[creation-time]"]["fresh"]
    ct_back = out["back_dated"]["soft_blend[creation-time]"]["fresh"]
    vt_back = out["back_dated"]["soft_blend[valid-time]"]["fresh"]
    print("RECEIPT: the verbatim creation-time blend fixes the cosine blind spot on monotonic data "
          f"({ct_mono}/{len(FACTS)} fresh) but returns the STALE value on back-dated writes "
          f"({ct_back}/{len(FACTS)} fresh). Switching only its temporal field to valid-time restores it "
          f"({vt_back}/{len(FACTS)}). The fix is the 1985 bitemporal distinction (Snodgrass & Ahn, SIGMOD 1985; "
          "SQL:2011 application_time); the receipt is that published 2025-26 freshness blends (SmartVector / Xu "
          "2604.20598; Grofsky, 'Freshness and the Limits of Heuristic Trend Detection in Temporal RAG' "
          "2509.19376) key on creation/ingest time and never test the out-of-order case (the deterministic max-serial "
          "method, Reddy & Challaram 2606.01435, keys on serial/arrival order too). Scope: soft-blend scoring subfamily only — validity-interval "
          "temporal-KG methods already use valid-time. n=24 synthetic — illustrative, not a benchmark.")


if __name__ == "__main__":
    main()
