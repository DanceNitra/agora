# ragfresh — a freshness & decay layer for RAG / vector stores

> Your vector store rots. `ragfresh` decides what to **keep, down-weight, refresh, or prune** —
> ranked by *value × freshness*, not recency — so answers stay current and the bill stops climbing.
> One file, zero dependencies. A sibling of [mnemo](../mnemo).

## The problem (measured in the wild, 2026)
Production RAG isn't "scrape once, embed, forget." Teams report:
- **Cost that climbs on the same data** — one team's vector DB went **$50 → $380 → $2,847/mo** across three months on an unchanged dataset and query mix.
- **Orphaned vectors** — a source doc is deleted but its vectors linger for days, so search returns results pointing at content that no longer exists.
- **Stale answers = real risk** — chunks confidently serving last quarter's pricing or a superseded policy (a compliance problem, not just a quality one).

The fix the field keeps reaching for is *"freshness-aware re-ranking + down-weight or prune stale content."* That is exactly the consolidation/decay core that runs an autonomous research OS over ~5,800 notes — distilled here to a single zero-dependency file.

## What it does
For a batch of vector-store entries, `triage()` returns a per-item plan:

| action | when | what you do |
|---|---|---|
| **KEEP** | fresh and worth its space | nothing |
| **DOWNWEIGHT** | over budget but still useful | multiply its retrieval score by a `<1` staleness factor |
| **REFRESH** | stale but valuable | re-scrape / re-embed (don't silently serve stale) |
| **PRUNE** | orphaned (source gone) or stale + low-value | delete the vector, reclaim the cost |

And `retrieval_weight(item, now)` gives a `0..1` multiplier to fold into your similarity score at query time — so fresh chunks rank above stale ones **without deleting anything** (orphans get `0`).

## Measured, not assumed
`python ragfresh.py` runs a head-to-head on a 1,000-chunk synthetic store with a known true value:

```
FAIR A/B — true business value retained, both keep exactly 500 of 1000:
  ragfresh (value+freshness): 214.5  (96% of oracle)
  recency-only (naive)      : 117.2  (52% of oracle)
  uplift over naive         : +83%
  + orphans auto-deleted: 65, stale flagged for refresh: 85
```

Ranking what to keep by **value × freshness** retains **96% of the maximum achievable value** at a 50% prune budget — **+83% more** than the recency-only cleanup most teams hand-roll — while removing orphans and flagging stale chunks for refresh.

## Design rules (each one measured)
- **Value-ranked + capacity-aware — not recency, not access-frequency.** The payoff from ranking *what to keep* grows super-linearly as the budget tightens; access-frequency alone starves the rarely-read-but-load-bearing chunk. (mnemo retention benchmark.)
- **Run it as a PERIODIC BATCH, not a per-write hook.** Continuous cleanup keeps a store ~8% leaner but pays ~25× more pruning events; once a pruning event has any real overhead, the periodic pass wins on net (Agora Lab `619055`, crossover ≈ 0.07 overhead/event). Schedule it; don't hook it.
- **Orphans on a signal, never a guess.** Stale-but-valuable is **refreshed**, not dropped.
- **Advisory + reversible.** `triage()` returns a plan; your code applies it. No silent deletes.

## Use it
```python
from ragfresh import Item, triage, retrieval_weight
import time

items = [Item(id=v.id, updated_ts=v.scraped_at, last_access_ts=v.last_hit,
              hits=v.hit_count, value=v.relevance, source_exists=v.doc_alive, bytes=v.size)
         for v in my_vector_store.scan()]

plan = triage(items, now=time.time(), stale_days=90, keep_budget=200_000)
for vid, (action, reason) in plan["decisions"].items():
    if action == "PRUNE":     my_vector_store.delete(vid)
    elif action == "REFRESH": reembed_queue.add(vid)
print(plan["report"])   # counts, pruned_fraction, reclaimed_bytes, orphans_removed, stale_refreshed

# query time: rank fresh over stale without deleting
score = cosine(q, v) * retrieval_weight(item, now=time.time())
```
Works with any store (Pinecone, pgvector, Weaviate, Qdrant, …) — `ragfresh` only decides; you apply.

## Status
v0: the core decision engine + the measured benchmark. Next: an MCP server (like `mnemo_mcp.py`) and thin store adapters. Open-core — the core stays free.
