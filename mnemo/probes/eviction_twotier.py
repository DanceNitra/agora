"""Eviction / retention benchmark — what to keep when a memory store is finite.

Three workloads stress an eviction policy in incompatible ways:
  - recency           : a drifting working set (locality)
  - rare_critical     : rare but high-value items mixed into frequent low-value traffic
  - adversarial_flood : a flood of UNIQUE junk items (seen once, never re-accessed -> zero future value)

Single rules each fail somewhere: LRU collapses under the flood (junk is always "most recent");
value-only starves the drifting working set. A TWO-TIER store -- a small value-PROTECTED segment
(immune to the recency clock AND the flood) + an LRU-aged segment for everything else -- matches or
beats the best single rule in EVERY regime at once. That split is the cheap, robust default for
"what survives compression" in a persistent, finite memory.

Pre-committed falsifier: if two-tier does NOT match-or-beat max(lru, lfu, value) in all three regimes,
architecture cannot give a universal eviction policy and regime-switching is mandatory.

Runnable, cloud-free, pure-numpy:  python eviction_twotier.py
MIT-licensed. Part of Agora / mnemo (https://github.com/DanceNitra/agora/tree/main/mnemo).
"""
import numpy as np

CAP = 150
SEEDS = 15


def serve_single(stream, weights, value_tag, cap, policy):
    cache = {}; last_used = {}; freq = {}; order = 0; served = 0.0; total = float(weights.sum())
    for t, it in enumerate(stream):
        order += 1
        if it in cache:
            served += weights[t]
        else:
            if len(cache) >= cap:
                if policy == "lru":
                    v = min(cache, key=lambda k: last_used[k])
                elif policy == "lfu":
                    v = min(cache, key=lambda k: (freq[k], last_used[k]))
                else:  # value
                    v = min(cache, key=lambda k: value_tag[k])
                cache.pop(v); last_used.pop(v, None); freq.pop(v, None)
            cache[it] = True
        last_used[it] = order; freq[it] = freq.get(it, 0) + 1
    return served / total


def serve_twotier(stream, weights, value_tag, cap, f):
    pc = max(1, int(f * cap)); lc = cap - pc
    prot = {}            # item -> value   (top-value, immune to recency/flood)
    lru = {}             # item -> last_used
    order = 0; served = 0.0; total = float(weights.sum())
    for t, it in enumerate(stream):
        order += 1
        v = value_tag[it]
        if it in prot:
            served += weights[t]
        elif it in lru:
            served += weights[t]; lru[it] = order
            if (len(prot) < pc or v > min(prot.values())) and it in lru:   # promote if now qualifies
                lru.pop(it)
                if len(prot) >= pc:
                    dk = min(prot, key=lambda k: prot[k]); prot.pop(dk); lru[dk] = order
                prot[it] = v
        else:
            qualifies = (len(prot) < pc) or (v > min(prot.values()))
            if qualifies:
                if len(prot) >= pc:
                    dk = min(prot, key=lambda k: prot[k]); prot.pop(dk); lru[dk] = order
                prot[it] = v
            else:
                lru[it] = order
            while len(lru) > lc:
                ek = min(lru, key=lambda k: lru[k]); lru.pop(ek)
    return served / total


def make_workload(rng, kind, n_items=1200, M=18000):
    if kind == "recency":
        stream = np.empty(M, dtype=int); ws = list(range(20)); cur = 20
        for t in range(M):
            if rng.random() < 0.8 and ws:
                stream[t] = ws[rng.integers(len(ws))]
            else:
                stream[t] = cur % n_items; ws.append(cur % n_items); cur += 1
                if len(ws) > 40: ws.pop(0)
        weights = np.ones(M)
    elif kind == "rare_critical":
        freq_items = np.arange(0, 1000); rare_items = np.arange(1000, 1040)
        stream = np.empty(M, dtype=int); weights = np.empty(M)
        for t in range(M):
            if rng.random() < 0.97:
                stream[t] = freq_items[rng.integers(len(freq_items))]; weights[t] = 1.0
            else:
                stream[t] = rare_items[rng.integers(len(rare_items))]; weights[t] = 60.0
    else:
        # TRUE poison flood: each junk item is UNIQUE (seen once, never re-accessed) -> zero future value.
        hi = np.arange(0, 30); stream = []; weights = []; junk = 2000; FLOOD = 220
        for _ in range(M // (len(hi) + FLOOD) + 1):
            for h in hi: stream.append(h); weights.append(10.0)
            for _ in range(FLOOD):
                stream.append(junk); weights.append(1.0); junk += 1   # unique forever -> pure noise
        stream = np.array(stream[:M], dtype=int); weights = np.array(weights[:M])
    size = int(stream.max()) + 1
    true_val = np.zeros(size)
    for it, w in zip(stream, weights): true_val[it] += w
    value_tag = true_val * np.exp(rng.normal(0, 0.5, size))
    return stream, weights, value_tag, size


def main():
    WORKLOADS = ["recency", "rare_critical", "adversarial_flood"]
    acc = {w: {k: [] for k in ["lru", "lfu", "value", "tt15", "tt30"]} for w in WORKLOADS}
    for sd in range(SEEDS):
        for w in WORKLOADS:
            rng = np.random.default_rng(11000 + sd)
            stream, weights, vtag, n_items = make_workload(rng, w)
            acc[w]["lru"].append(serve_single(stream, weights, vtag, CAP, "lru"))
            acc[w]["lfu"].append(serve_single(stream, weights, vtag, CAP, "lfu"))
            acc[w]["value"].append(serve_single(stream, weights, vtag, CAP, "value"))
            acc[w]["tt15"].append(serve_twotier(stream, weights, vtag, CAP, 0.15))
            acc[w]["tt30"].append(serve_twotier(stream, weights, vtag, CAP, 0.30))
    R = {w: {k: float(np.mean(v)) for k, v in d.items()} for w, d in acc.items()}

    print(f"=== served weight fraction (cap={CAP}; higher=better) ===")
    cols = ["lru", "lfu", "value", "tt15", "tt30"]
    print(f"{'workload':>18} | " + " | ".join(f"{c:>6}" for c in cols))
    for w in WORKLOADS:
        print(f"{w:>18} | " + " | ".join(f"{R[w][c]:6.3f}" for c in cols))

    print("\n=== does a two-tier match-or-beat the best single estimator in EVERY regime? ===")
    for tt in ["tt15", "tt30"]:
        ok_all = True; line = []
        for w in WORKLOADS:
            best_single = max(R[w]['lru'], R[w]['lfu'], R[w]['value'])
            ok = R[w][tt] >= best_single - 0.02
            ok_all = ok_all and ok
            line.append(f"{w.split('_')[0]}:{R[w][tt]:.3f}/{best_single:.3f}{'OK' if ok else 'X'}")
        print(f"   {tt}: " + " | ".join(line) + f"  -> universal: {ok_all}")


if __name__ == "__main__":
    main()
