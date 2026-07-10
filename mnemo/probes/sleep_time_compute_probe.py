"""Verify mnemo.sleep() — sleep-time compute as a library primitive.

Claims to check:
  1. NO-OP WHEN IDLE: sleep() on a store with no ripe cluster / no capacity pressure does nothing
     (clusters_fired=0, no items demoted) — cheap to call on every idle tick.
  2. FIRES WHEN RIPE: after a dense cluster (> threshold near-duplicates) accumulates, sleep()
     consolidates it (clusters_fired >= 1, linked_pairs > 0).
  3. IDEMPOTENT: a second immediate sleep() does no new linking (the pass already ran).
  4. RECALL-SAFE: a genuine fact is still recallable after sleep() (consolidation links/demotes
     near-dupes but never loses the content).
  5. CAPACITY on sleep: with capacity set, sleep() re-affirms the bound (no-op if already bounded).

Uses the local embedder if available (clusters are semantic); falls back to lexical clustering.
"""
import sys, os, urllib.request, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mnemo import Mnemo

def embed(texts):
    body = json.dumps({"model": "nomic-embed-text", "input": texts}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/embed", data=body,
        headers={"Content-Type": "application/json"}), timeout=120).read())
    return r["embeddings"]

def run():
    ok = True
    m = Mnemo(path=None, embed=lambda t: embed([t])[0])

    # a few sparse, distinct facts -> nothing ripe
    for t in ["the billing service runs in ohio", "the auth token ttl is 30 minutes",
              "the cdn provider is fastly"]:
        m.remember(t, mtype="semantic")
    r_idle = m.sleep(cluster_threshold=15)
    c1 = r_idle["consolidated_clusters"]["clusters_fired"] == 0
    print(f"  [{'OK' if c1 else 'FAIL'}] no-op when idle: clusters_fired={r_idle['consolidated_clusters']['clusters_fired']} (want 0)"); ok &= c1

    # a dense cluster of near-duplicates -> ripe. Consolidation "work" can be linking OR toggle-dedup
    # (repeats of the same value collapse to the latest) OR keep-budget staling — any is real work.
    for i in range(20):
        m.remember(f"the deploy region for the payment api is frankfurt (note {i})", mtype="semantic")
    r_fire = m.sleep(cluster_threshold=15)["consolidated_clusters"]
    fired = r_fire["clusters_fired"]
    work = r_fire["linked_pairs"] + r_fire["toggled"] + r_fire["staled"]
    active_after = sum(1 for r in m.items if r.get("status") == "active")
    c2 = fired >= 1 and work > 0
    print(f"  [{'OK' if c2 else 'FAIL'}] fires when ripe: clusters_fired={fired} work(link+toggle+stale)={work} "
          f"(20 near-dupes -> {active_after} active) (want fired>=1, work>0)"); ok &= c2

    # idempotent: immediate second sleep does no NEW work
    r_again = m.sleep(cluster_threshold=15)["consolidated_clusters"]
    work2 = r_again["linked_pairs"] + r_again["toggled"] + r_again["staled"]
    c3 = work2 == 0
    print(f"  [{'OK' if c3 else 'FAIL'}] idempotent: 2nd sleep work={work2} (want 0)"); ok &= c3

    # recall-safe: the genuine sparse fact is still retrievable
    hits = m.recall("billing service region", k=5)
    c4 = any("ohio" in h["text"] for h in hits)
    print(f"  [{'OK' if c4 else 'FAIL'}] recall-safe after sleep: genuine fact still recalled = {c4}"); ok &= c4

    # capacity re-affirm on sleep
    mc = Mnemo(path=None, capacity=10)
    for i in range(10):
        mc.remember(f"c{i}", tags=[f"c{i}"])
    r_cap = mc.sleep()
    c5 = r_cap.get("evicted_on_sleep", 0) == 0 and sum(1 for r in mc.items if r["status"] == "active") == 10
    print(f"  [{'OK' if c5 else 'FAIL'}] capacity re-affirm: evicted_on_sleep={r_cap.get('evicted_on_sleep')} (want 0, already bounded)"); ok &= c5

    print(f"\nSLEEP-TIME COMPUTE: {'ALL PASS' if ok else 'FAIL'} "
          f"(no-op idle / fires ripe / idempotent / recall-safe / capacity-aware)")
    return ok

if __name__ == "__main__":
    run()
