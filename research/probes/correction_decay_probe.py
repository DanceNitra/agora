"""Correction-decay probe — marintkael's experiment (r/RAG echo-post comment, 2026-07-09).

His words: "inject the correction, then drip N restatements of the old value at growing
distance, and watch the correction decay. The failure you are catching is recency of
mention beating recency of truth. A store that reconciles silently at read time hides the
one field that would have settled it."

We build exactly that. Two stores, same event stream:
  1. state old value   2. CORRECT to new value   3. drip N restatements of the OLD value
For each N in a sweep, query "what is the current value?" and score whether the CORRECTED
(new) value is still returned.

  ARM A — SET / LOG store, silent read-time reconciliation (the bug he names):
    append every utterance, recall top-k by similarity, answer = MAJORITY value among
    the top-k. No validity field. As OLD restatements pile up they dominate top-k ->
    "recency/frequency of mention" wins and the correction decays.
  ARM B — VALIDITY-INTERVAL store (inspeximus keyed supersession, valid_from/superseded-by):
    the OLD value is superseded on correction and HIDDEN from recall; a later restatement
    is retired stale-on-arrival by echo_guard. Resolves by the ledger, not by whichever
    value was mentioned most/last.

Deterministic, local embedder (nomic-embed-text), no LLM judge -> anyone can re-run it.
Output: the correction-survival curve vs N for both stores.

CAVEAT (verified 2026-07-10): the ARM-A majority-vote read below produces a clean 1.00 -> 0.00
CLIFF at N=1, but that is an artifact of the counting rule (at N=1 the store holds 2 old + 1 new,
so majority trivially flips). A REAL read-time reconciler behaves differently: running the same
experiment against live mem0 (native OpenAI, its own LLM memory-manager) gives a PARTIAL, NOISY
decay -- correction survival ~0.88 (N=0) -> ~0.50 (N=1) -> ~0.38 (N=2) -> ~0.50 (N=4), n=8 -- not a
total collapse (mem0's ADD/UPDATE/DELETE manager sometimes merges the duplicates, so it is
non-monotonic). The validity-interval store holds at 1.00 in BOTH the toy read and the live-mem0
run. So treat arm A here as an UPPER BOUND / illustration of the mechanism, not the deployed rate.
"""
import sys, os, json, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus

ENTS = ["payment region", "auth method", "cache backend", "deploy branch", "log level",
        "queue driver", "storage class", "cdn provider", "retry policy", "session ttl"]
OLD = ["frankfurt", "oauth", "redis", "main", "debug", "kafka", "cold", "fastly", "linear", "30m"]
NEW = ["ohio", "apikey", "memcached", "release", "warn", "sqs", "hot", "cloudflare", "exp", "10m"]
N_SWEEP = [0, 1, 2, 3, 4, 6, 8]
K = 5

def embed(texts):
    body = json.dumps({"model": "nomic-embed-text", "input": texts}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/embed", data=body,
        headers={"Content-Type": "application/json"}), timeout=120).read())
    return r["embeddings"]

def value_in(text, old, new):
    t = text.lower()
    return "new" if new in t else ("old" if old in t else None)

def arm_A_answer(m, ent, old, new, read="majority"):
    """SET/LOG store, silent read-time reconciliation over top-k by similarity.
    Two honest read rules (both are ways a store 'reconciles at read time' with no validity field):
      majority = frequency of mention wins; recency = most-recent mention wins."""
    hits = m.recall(f"what is the current {ent}?", k=K, include_superseded=True)
    if read == "recency":
        best = None
        for h in hits:                                   # hits carry ts; pick the newest value-bearing one
            v = value_in(h["text"], old, new)
            if v and (best is None or h.get("ts", 0) > best[1]):
                best = (v, h.get("ts", 0))
        return best[0] if best else None
    votes = {"old": 0, "new": 0}
    for h in hits:
        v = value_in(h["text"], old, new)
        if v:
            votes[v] += 1
    if votes["new"] == votes["old"] == 0:
        return None
    return "new" if votes["new"] >= votes["old"] else "old"   # ties -> favor the correction (generous to arm A)

def arm_B_answer(m, ent, old, new):
    """VALIDITY-INTERVAL store: recall hides superseded; answer = value of top active hit."""
    hits = m.recall(f"what is the current {ent}?", k=K)
    for h in hits:
        v = value_in(h["text"], old, new)
        if v:
            return v
    return None

def run():
    curveA_maj, curveA_rec, curveB = {}, {}, {}
    for N in N_SWEEP:
        okAm = okAr = okB = tot = 0
        for i, ent in enumerate(ENTS):
            old, new = OLD[i], NEW[i]
            # ARM A — plain append log, no supersession
            a = Inspeximus(path=None, embed=embed)
            a.remember(f"the {ent} is {old}.")
            a.remember(f"correction: the {ent} is now {new}.")
            for _ in range(N):
                a.remember(f"the {ent} is {old}.")            # drip old-value restatements
            # ARM B — keyed supersession + echo guard (validity intervals)
            b = Inspeximus(path=None, embed=embed)
            b.echo_guard = True
            key = f"{ent}::v"
            b.remember(f"the {ent} is {old}.", key=key, object=old)
            b.remember(f"correction: the {ent} is now {new}.", key=key, object=new)
            for _ in range(N):
                b.remember(f"the {ent} is {old}.", key=key, object=old)
            okAm += 1 if arm_A_answer(a, ent, old, new, "majority") == "new" else 0
            okAr += 1 if arm_A_answer(a, ent, old, new, "recency") == "new" else 0
            okB += 1 if arm_B_answer(b, ent, old, new) == "new" else 0
            tot += 1
        curveA_maj[N] = round(okAm / tot, 3)
        curveA_rec[N] = round(okAr / tot, 3)
        curveB[N] = round(okB / tot, 3)
        print(f"  N={N:>2}  set/log[freq]={curveA_maj[N]:.2f}  set/log[recency]={curveA_rec[N]:.2f}  "
              f"validity-interval={curveB[N]:.2f}")
    out = {"metric": "correction-survival-rate (fraction where the CORRECTED value is still returned)",
           "n_entities": len(ENTS), "top_k": K, "n_restatements_sweep": N_SWEEP,
           "set_log_store_frequency_read": curveA_maj, "set_log_store_recency_read": curveA_rec,
           "validity_interval_store": curveB,
           "credit": "experiment suggested by marintkael, r/RAG echo-post comment 2026-07-09",
           "note": "deterministic, local nomic-embed-text, retrieval-level; arm A ties favor the correction (generous)"}
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "correction_decay_probe_result.json"), "w"), indent=2)
    print("\n" + json.dumps({k: out[k] for k in ("set_log_store_frequency_read",
          "set_log_store_recency_read", "validity_interval_store")}, indent=2))
    return out

if __name__ == "__main__":
    run()
