# PR: pluggable `AccessStore` + `Memory.cleanup(policy)` (mem0#5611)

**Status: READY, held locally — NOT opened on mem0.** Open only after the owner approves and kartik signals
the design direction is acceptable. Branch `feat/access-store-cleanup` in the local mem0 clone; patch +
files in this folder.

## What it does
Implements the design we proposed on #5611: first-class, policy-driven pruning of stale / low-value
memories, plus the lightweight per-memory access metadata it needs — **at the SDK layer, zero vector-backend
changes, opt-in (default off, so existing behaviour is unchanged).**

## Directly answers kartik's two open design questions

**(1) Persistence model** (his main blocker — in-memory `hit_count` only survives one process).
The access metadata is tiny (`{memory_id: (hit_count, last_access)}`), so it lives in a small **pluggable
`AccessStore` sidecar**, decoupled from both the 30+ vector backends *and* the process lifetime:
- `InMemoryAccessStore` — zero-config; fine for short-lived agents / dev.
- `SQLiteAccessStore` — zero-infra, file-backed, **survives restart** (WAL + `synchronous=NORMAL` +
  write-behind batching); the natural single-node production default.
- subclass `AccessStore` for Redis / a distributed store (multi-process).
No vector backend changes; persistence is a one-line store choice (`memory.access_store = SQLiteAccessStore(path)`).

**(2) `policy` semantics** (pinned down in `evict_candidates`):
- `lru`  — evict oldest `last_access` first; tie-break by lowest `hit_count`.
- `lfu`  — evict lowest `hit_count` first; tie-break by oldest `last_access`.
- `decay` — evict lowest recency-weighted frequency `hit_count * 2**(-age/half_life)` (7-day half-life);
  balances LRU's "drops rarely-but-critically used" against LFU's "old high-count items never leave".
- `cleanup(policy, max_items=..., max_age=...)` is **explicit and caller-triggered** (never automatic), so
  eviction is predictable and testable. `max_age` is a hard staleness bound regardless of policy.

## Measured (reproducible — the benchmark IS the test, `tests/memory/test_access_store.py`)
SQLite sidecar, 100k memories, 500k hits, Zipf-ish access, string memory-ids:
- **~1.4 µs / recorded hit** (in-memory ~0.5 µs) — i.e. **< 0.2 % of a 1-10 ms vector search**; the access
  write never touches the hot retrieval path beyond a buffered, batched upsert.
- **~4 MB on disk per 100k tracked** memories.
- **counts intact across a process restart** (close + reopen verified).

(Note: this corrects the earlier in-thread estimate — with real string ids it is ~1.4 µs/hit and ~4 MB/100k,
not the ~6.4 µs / ~2 MB figure I cited; the conclusion "persistence is essentially free" is unchanged and
stronger.)

## Files
- `mem0/memory/access_store.py` (+212) — the interface + InMemory + SQLite impls (stdlib only).
- `mem0/memory/main.py` (+42) — opt-in: `self.access_store` (default `None`); `search()`/`get()` record a hit
  when set; new `Memory.cleanup(policy, max_items, max_age)`.
- `tests/memory/test_access_store.py` (+120) — functional tests (all policies, restart survival) + benchmark.

## Why it's safe to merge
Default off → no behaviour change for anyone who doesn't set `access_store`. No new deps (stdlib `sqlite3`).
No backend touches. The risky part (the store) is fully unit-tested; the wiring is 3 small opt-in hooks.

## Usage
```python
from mem0 import Memory
from mem0.memory.access_store import SQLiteAccessStore

m = Memory()
m.access_store = SQLiteAccessStore("mem0_access.db")   # opt-in; survives restart
# ... normal add/search/get; hits are recorded automatically ...
m.cleanup(policy="lru", max_items=10_000)              # prune the least-recently-used beyond 10k
m.cleanup(policy="decay", max_age=30*86400)            # or drop anything untouched in 30 days
```
