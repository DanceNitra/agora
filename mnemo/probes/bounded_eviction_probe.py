"""Verify mnemo's opt-in bounded-capacity eviction: it (1) bounds the ACTIVE set to `capacity`, and
(2) its value-PROTECTED tier retains a rare-but-critical high-value memory that pure-recency (LRU)
evicts under a flood — the core reason mnemo uses the two-tier design (value-protected + recency-aged)
validated as universal in Lab 29992a. We do NOT re-derive the full 3-regime universality here (that
needs the lab's carefully constructed workloads — value-inflating poison, value-agnostic locality);
this probe confirms correctness + the protected-tier win that LRU cannot get. Synthetic clock so
wall-clock decay separates items in a sub-second test. Deterministic, no embedder.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import mnemo as _mnemo_mod
from mnemo import Mnemo

DAY = 86400.0
_CLK = [1_000_000.0]
_mnemo_mod.time.time = lambda: _CLK[0]
def tick(days=1.0): _CLK[0] += days * DAY

def active(m):
    return [r for r in m.items if r.get("status") == "active"]

def run():
    ok = True

    # 1. CAPACITY BOUND: insert far past capacity -> active set stays exactly at capacity.
    m = Mnemo(path=None, capacity=20)
    for i in range(100):
        m.remember(f"item {i}", tags=[f"i{i}"], value=1.0); tick()
    n_active = len(active(m))
    c1 = n_active == 20
    print(f"  [{'OK' if c1 else 'FAIL'}] capacity bound: {n_active} active (want 20)"); ok &= c1

    # 2. legacy default is UNBOUNDED (capacity=None): no eviction, byte-identical behavior.
    m2 = Mnemo(path=None)   # no capacity
    for i in range(50):
        m2.remember(f"x {i}", tags=[f"x{i}"], value=1.0); tick()
    c2 = len(active(m2)) == 50
    print(f"  [{'OK' if c2 else 'FAIL'}] default unbounded: {len(active(m2))} active (want 50)"); ok &= c2

    # 3. PROTECTED TIER vs LRU on a rare-critical item: one old high-value fact, then a low-value flood.
    #    pure-recency (LRU) evicts the old critical fact; two-tier's protected tier keeps it.
    def rare_critical(two_tier):
        m = Mnemo(path=None, capacity=20)
        m.two_tier_keep = two_tier; m.protect_frac = 0.30 if two_tier else 0.0
        m.remember("critical fact", tags=["CRIT"], value=50.0); tick(30)
        for t in range(200):
            m.remember(f"junk {t}", tags=[f"j{t}"], value=1.0); tick()
        return "CRIT" in {r["tags"][0] for r in active(m)}
    lru_keeps = rare_critical(two_tier=False)
    tt_keeps = rare_critical(two_tier=True)
    c3 = (not lru_keeps) and tt_keeps
    print(f"  [{'OK' if c3 else 'FAIL'}] rare-critical: LRU keeps={lru_keeps} (want False), "
          f"two-tier keeps={tt_keeps} (want True) -> protected tier saves what LRU evicts"); ok &= c3

    print(f"\nBOUNDED EVICTION: {'ALL PASS' if ok else 'FAIL'} "
          f"(bounds capacity; protected tier retains rare-critical vs LRU; full 3-regime universality "
          f"established in Lab 29992a, not re-derived here)")
    return ok

if __name__ == "__main__":
    run()
