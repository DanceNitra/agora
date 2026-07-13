"""erasure_auditor_probe.py — demo: the erasure auditor catches data that survives the fan-out after a delete.

Scenario: a subject requests erasure. The app naively deletes only its PRIMARY memory store and calls it done —
but the same data still lives in the app's vector index (embedding not purged), a retrieval log, and an
embedding cache. The auditor adversarially re-checks each store and reports erasure as INCOMPLETE, naming the
leaking stores (and, for the vector index, recovering the value by NN-inversion — the check DSAR tools skip).
Then we wire the stores to actually purge and the auditor verifies erasure.

Run: python mnemo/probes/erasure_auditor_probe.py   (cloud-free; needs Ollama nomic-embed-text for the vector probe)
Part of Agora / mnemo (MIT).
"""
import os
import sys
import json
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mnemo import Mnemo  # noqa: E402
from erasure_auditor import (ErasureAuditor, TextStoreProbe, VectorIndexProbe, KVCacheProbe)  # noqa: E402

OLLAMA = "http://localhost:11434/api/embeddings"


def embed(text):
    body = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    return list(json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"])


CANDIDATES = ["type-1 diabetes", "epilepsy", "HIV positive", "bipolar disorder", "breast cancer",
              "schizophrenia", "hepatitis C", "multiple sclerosis", "clinical depression", "lupus"]


def build(subject, value, wire_all_stores):
    """Set up the store + fan-out copies, run the app's erasure (naive OR wired), return the auditor + stores."""
    store = Mnemo(path=None)
    fact = f"{subject}'s medical condition is {value}."
    store.remember(fact, key=f"{subject}::cond", object=value, source={"doc": subject})

    vindex = VectorIndexProbe("app-vector-index", embed)
    vindex.add(subject, fact)
    retrieval_log = [f"[query] condition of {subject} -> {fact}"]     # a text store the app forgets to purge
    embed_cache = {f"emb::{subject}::cond": fact}                     # an embedding-API response cache

    # ---- the app's erasure ----
    store.forget_subject(subject, request_id=f"dsar-{subject}")       # primary store: always done
    if wire_all_stores:                                              # a diligent app also purges the fan-out
        vindex.purge(subject)
        retrieval_log[:] = [l for l in retrieval_log if subject not in l]
        embed_cache.clear()

    auditor = (ErasureAuditor()
               .register(TextStoreProbe("primary-store", lambda: [r["text"] for r in store.items if r.get("status") == "active"]))
               .register(vindex)
               .register(TextStoreProbe("retrieval-log", lambda: list(retrieval_log)))
               .register(KVCacheProbe("embedding-cache", lambda: dict(embed_cache))))
    return auditor


def show(title, report):
    print(title)
    for r in report["results"]:
        mark = "LEAK" if r["recoverable"] else " ok "
        extra = f"  recovered={r['recovered']}" if r["recovered"] else ""
        print(f"    [{mark}] {r['store']:<18} ({r['kind']}, {r['method']}){extra}")
    print(f"  -> erasure_verified = {report['erasure_verified']}   leaking = {report['leaking_stores']}\n")


def main():
    subj, val = "alice-42", "type-1 diabetes"
    print("=== ERASURE AUDITOR: does the data stay deleted across the fan-out? ===\n")

    rA = build(subj, val, wire_all_stores=False).audit(subj, [val], candidates=CANDIDATES,
                                                        template="{subject}'s medical condition is {value}.")
    show("Scenario A — app deleted ONLY its primary store (the common default):", rA)

    rB = build(subj, val, wire_all_stores=True).audit(subj, [val], candidates=CANDIDATES,
                                                      template="{subject}'s medical condition is {value}.")
    show("Scenario B — app also purged the vector index, log, and cache:", rB)

    passed = (rA["erasure_verified"] is False
              and set(rA["leaking_stores"]) == {"app-vector-index", "retrieval-log", "embedding-cache"}
              and rB["erasure_verified"] is True)
    if passed:
        print("VERDICT: PASS — the auditor catches the data surviving in the vector index (by NN-inversion,")
        print("  the check DSAR platforms skip), the retrieval log, and the cache — and reports erasure INCOMPLETE")
        print("  instead of a false 'deleted'. Once the app purges them, it verifies erasure. This is the runnable")
        print("  'content still reconstructible?' auditor; honest by construction, prior-art-credited, not a claim.")
    else:
        print("VERDICT: FAIL — auditor did not behave as specified.")
        print("  A:", rA["leaking_stores"], "| B verified:", rB["erasure_verified"])


if __name__ == "__main__":
    main()
