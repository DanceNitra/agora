# ragfresh — a freshness & decay layer for RAG / vector stores

> Your vector store rots. `ragfresh` decides what to **keep, down-weight, refresh, or prune** —
> ranked by **value**, not recency — so answers stay current and the bill stops climbing.
> (Value-aware eviction is the [GreedyDual-Size-Frequency](https://www.usenix.org/legacy/publications/library/proceedings/usits97/full_papers/cao/cao.pdf) cache-eviction family applied to vector stores; freshness is the query-time + lifecycle layer on top.)
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
`python ragfresh.py` runs every obvious keep-policy head-to-head on a 1,000-chunk synthetic store with a known true value (keep 500 of 1000, 20 seeds, % of the keep-best-by-true-value oracle):

```
age ~ value (realistic: fresher content is more valuable)
  value-only (oracle labels)        100%
  value+freshness blend (oracle)     95%
  hits-proxy + freshness (no labels) 91%   <- what you actually get without value labels
  hits-only                          92%
  recency-only                       62%
  random                             56%
  + orphans auto-deleted: ~65, stale flagged for refresh: ~85
```

The honest picture: **value-awareness is the lever** — ranking what to keep by value retains ~100% of the achievable value, vs **62% for a recency-only cleanup** (which falls to ~56% ≈ random when content-age doesn't track value). So a value-aware keep-policy retains roughly **1.5–1.8× as much of the value that matters** as recency-only cleanup (~50–80% more). Two honest caveats the benchmark makes explicit:
- **You usually don't have value labels.** The realistic, observable arm is `hits-proxy` — a decayed hit-count — which still retains **~91%**. So *access-frequency is a strong proxy, not "the wrong signal"* (this is LFU-with-aging / [LFUDA](https://en.wikipedia.org/wiki/Cache_replacement_policies#LFU_with_dynamic_aging)). It tracks value only when popularity correlates with value — usually true, not always.
- **Freshness adds little to *what to keep*** (value-only 100% ≥ value+freshness 95%). Freshness's real job is the **query-time staleness multiplier** (`retrieval_weight`) and flagging **orphans + stale-but-valuable** chunks — not winning the keep-ranking.

## Design rules (each one measured)
- **Value-ranked + capacity-aware — not recency.** Ranking *what to keep* by value retains ~1.5–1.8× more value than a recency-only cleanup; with no value labels a **decayed hit-count is a strong stand-in (~91%)**, so don't discard frequency — age it (LFU-with-aging) so a once-popular dead chunk decays out. (Benchmark above.)
- **Run it as a PERIODIC BATCH, not a per-write hook.** Continuous cleanup buys a small (~8%) retrieval-quality (signal/clutter) edge but pays ~25× more pruning events; once a pruning event has any real overhead, the periodic pass wins on net (a separate runnable lab, `20260615-070150_autophagy-vs-continuous-pruning-overhead-crossover`, analytic crossover ≈ 0.07 overhead/event). Schedule it; don't hook it. (`python ragfresh.py` reproduces the keep-ranking arms above, not this A/B.)
- **Orphans on a signal, never a guess.** Stale-but-valuable is **refreshed**, not dropped.
- **Advisory + reversible.** `triage()` returns a plan; your code applies it. No silent deletes.

## Prior art (this is packaging, not a discovery)
The individual ideas are established; ragfresh's contribution is the integrated zero-dependency tool + the measured comparison.
- **Cost-aware / value-aware eviction:** GreedyDual-Size (Cao & Irani, USENIX 1997); GreedyDual-Size-Frequency (Cherkasova, HP Labs 1998); GreedyDual (Young 2002). ragfresh's value+freshness keep-score is this family applied to vector stores.
- **Frequency without aging pollutes the cache:** the classic LFU cache-pollution problem; the fix is **LFU-Aging / LFUDA** — which is exactly why our hit-count proxy decays.
- **Freshness / staleness for retrieval:** FreshLLMs / FreshQA (Vu et al., 2023, [arXiv:2310.03214](https://arxiv.org/abs/2310.03214)) and the temporal-RAG line — the motivation for `retrieval_weight` and the REFRESH action.

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

## MCP server
`ragfresh_mcp.py` exposes the engine to any MCP client (Claude Code/Desktop, Cursor, a maintenance cron):
- `triage(items, …)` → the full per-item plan + savings report
- `prune_ids(items, …)` → just `{prune: [...], refresh: [...]}` for a job to act on
- `retrieval_weight(item, …)` → the query-time staleness multiplier

```
python -m ragfresh.ragfresh_mcp      # stdio; needs:  pip install "mcp[cli]"
```
ragfresh is **stateless** — pass your store's item metadata in, get a plan back; your code applies it.

## Store adapters
`adapters.py` is the thin bridge from a real store to the engine — `run(adapter, now=...)` does
**scan → triage → apply** (pass `apply=False` for a dry run):
- **`PgVectorAdapter`** (Postgres + pgvector; `pip install "psycopg[binary]"`) — DELETE prunes, UPDATE flags refresh
- **`PineconeAdapter`** (`pip install pinecone`) — `index.delete` prunes, metadata flags refresh/down-weight
- **`MemoryAdapter`** (zero deps) — the runnable reference; `python adapters.py` verifies the full round-trip

Your store just keeps the freshness signals in metadata (`updated_ts`, `last_access_ts`, `hits`, `value`, `source_exists`); field names are configurable. The engine decides; the adapter applies — nothing is deleted that triage didn't mark.

## Status
v0: core decision engine + measured benchmark + MCP server + pgvector/Pinecone adapters. Open-core — the core stays free.
