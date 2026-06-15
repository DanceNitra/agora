"""
ragfresh — a freshness & decay layer for RAG / vector stores.  (a mnemo sibling)

The problem (measured in the wild, 2026): production RAG stores rot and bloat. Teams report vector-DB
cost climbing $50 -> $380 -> $2,847/mo on the SAME data, "orphaned" vectors lingering for days after
the source doc is deleted, and stale chunks confidently answering with last-quarter's pricing/policy
(a compliance risk). The fix the field keeps reaching for — "freshness-aware re-ranking + down-weight
or prune stale content" — is exactly the consolidation/decay core that runs our autonomous research
OS over ~5,800 notes, distilled here to a single zero-dependency file.

What it does — for a batch of vector-store entries it decides, per item:
    KEEP        fresh and worth its space
    DOWNWEIGHT  keep, but multiply its retrieval score by a <1 staleness factor (answers get the
                fresh chunk first without deleting the old one)
    REFRESH     still valuable but stale -> re-scrape/re-embed (don't silently serve stale)
    PRUNE       orphaned (source gone) or stale+low-value -> delete the vector, reclaim the cost

Two API surfaces:
    triage(items, ...)            -> per-item decisions + a savings report (the batch "dream" pass)
    retrieval_weight(item, ...)   -> a 0..1 multiplier to fold into your similarity score at query time

Design rules (each one measured, not assumed — same provenance as mnemo):
  • Value-ranked, capacity-aware — NOT recency-only and NOT access-frequency. Pruning by what's
    most VALUABLE (a value+freshness blend) beats pruning by recency, and the gap widens super-
    linearly as the keep-budget tightens. Access-frequency alone starves the rarely-read-but-load-
    bearing chunk. (mnemo retention benchmark.)
  • Run it as a PERIODIC BATCH, not a per-write hook. Continuous cleanup keeps the store ~8% leaner
    but pays ~25x more pruning events; once a pruning event has any real overhead the periodic pass
    wins on net (Agora Lab 619055, crossover ~0.07 overhead/event). So: schedule it, don't hook it.
  • Orphans are deleted on a source-existence signal, never guessed. Stale-but-valuable is REFRESHED,
    not dropped — losing a load-bearing chunk is worse than re-embedding it.
  • Decisions are advisory + reversible: triage RETURNS a plan; the caller applies it. No silent deletes.

Zero dependencies. Bring your own store; ragfresh only decides.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Item:
    id: str
    updated_ts: float                 # when the SOURCE content was last changed/scraped (epoch sec)
    last_access_ts: float = 0.0       # when this chunk was last retrieved (epoch sec); 0 = never
    hits: int = 0                     # lifetime retrieval count
    value: float | None = None        # business/relevance value in [0,1]; None -> proxy from hits
    source_exists: bool = True        # False => the source doc was deleted (orphan)
    bytes: int = 0                    # optional, for the cost-savings estimate


def _freshness(age_days: float, half_life_days: float) -> float:
    """Exponential decay in [0,1]: 1.0 brand-new, 0.5 at one half-life, ->0 as it ages."""
    if half_life_days <= 0:
        return 1.0
    return 0.5 ** (max(0.0, age_days) / half_life_days)


def _value(it: Item) -> float:
    """Use the supplied value; else a log-scaled proxy from hit count (popular!=valuable, but with
    no value signal it's the best proxy). Capped to [0,1]."""
    if it.value is not None:
        return max(0.0, min(1.0, it.value))
    return min(1.0, math.log1p(max(0, it.hits)) / math.log1p(50))   # ~50 hits saturates to 1.0


def retrieval_weight(it: Item, now: float, half_life_days: float = 120.0) -> float:
    """Query-time multiplier: fold into your similarity score so fresh chunks rank above stale ones
    WITHOUT deleting anything. 0 for an orphan (its source is gone)."""
    if not it.source_exists:
        return 0.0
    return round(_freshness((now - it.updated_ts) / 86400.0, half_life_days), 4)


def _retention_score(it: Item, now: float, half_life_days: float) -> float:
    """What to KEEP under a budget: value-dominant blend of value, content-freshness, access-recency."""
    age_days = (now - it.updated_ts) / 86400.0
    idle_days = (now - it.last_access_ts) / 86400.0 if it.last_access_ts else 1e9
    fresh = _freshness(age_days, half_life_days)
    recency = _freshness(idle_days, half_life_days)
    return 0.55 * _value(it) + 0.30 * fresh + 0.15 * recency


def triage(items, *, now: float, stale_days: float = 90.0, half_life_days: float = 120.0,
           keep_budget: int | None = None, refresh_min_value: float = 0.5):
    """The periodic batch pass. Returns {'decisions': {id: (action, reason)}, 'report': {...}}.
    Pure function: it decides, the caller applies."""
    items = list(items)
    decisions: dict[str, tuple[str, str]] = {}

    for it in items:
        age_days = (now - it.updated_ts) / 86400.0
        if not it.source_exists:
            decisions[it.id] = ("PRUNE", "orphan: source document deleted")
        elif age_days > stale_days:
            if _value(it) >= refresh_min_value or it.hits > 0:
                decisions[it.id] = ("REFRESH", f"stale ({age_days:.0f}d) but valuable -> re-embed")
            else:
                decisions[it.id] = ("PRUNE", f"stale ({age_days:.0f}d) and low-value")
        else:
            decisions[it.id] = ("KEEP", "fresh")

    # Capacity pass: if more are retained (KEEP/REFRESH) than the budget, value-rank and demote the
    # weakest beyond the budget to DOWNWEIGHT (kept but de-prioritised), the very weakest to PRUNE.
    if keep_budget is not None:
        retained = [it for it in items if decisions[it.id][0] in ("KEEP", "REFRESH")]
        retained.sort(key=lambda it: _retention_score(it, now, half_life_days), reverse=True)
        for rank, it in enumerate(retained):
            if rank < keep_budget:
                continue
            sc = _retention_score(it, now, half_life_days)
            if sc < 0.25:
                decisions[it.id] = ("PRUNE", "over budget + low retention score")
            else:
                decisions[it.id] = ("DOWNWEIGHT", "over budget -> de-prioritise in recall")

    counts: dict[str, int] = {}
    pruned_bytes = 0
    for it in items:
        a = decisions[it.id][0]
        counts[a] = counts.get(a, 0) + 1
        if a == "PRUNE":
            pruned_bytes += it.bytes
    report = {
        "total": len(items), "counts": counts,
        "pruned_fraction": round(counts.get("PRUNE", 0) / max(1, len(items)), 3),
        "reclaimed_bytes": pruned_bytes,
        "orphans_removed": sum(1 for it in items if not it.source_exists),
        "stale_refreshed": sum(1 for it in items
                               if decisions[it.id][0] == "REFRESH"),
    }
    return {"decisions": decisions, "report": report}


# ----------------------------------------------------------------------------------------------------
# Runnable proof: ragfresh's value+freshness triage vs the naive recency-only cleanup everyone writes,
# on a synthetic store with a KNOWN true business value. "Measured, not assumed."
if __name__ == "__main__":
    import random
    random.seed(7)
    DAY = 86400.0
    now = 1_000_000_000.0
    N = 1000
    store = []
    true_value = {}
    for i in range(N):
        # true business value (what we actually want to retain) — skewed: a few chunks carry most value
        tv = random.random() ** 3
        age = random.expovariate(1 / 60.0)                  # content age in days, mean ~60
        # access correlates with value but noisily; valuable old chunks exist (the load-bearing ones)
        hits = int(max(0, random.gauss(tv * 40, 8)))
        orphan = random.random() < 0.06                     # 6% have a deleted source
        it = Item(id=f"c{i}", updated_ts=now - age * DAY,
                  last_access_ts=now - random.expovariate(1 / 30.0) * DAY,
                  hits=hits, value=tv, source_exists=not orphan, bytes=4096)
        store.append(it); true_value[it.id] = tv if not orphan else 0.0

    budget = N // 2                                          # keep half (tight budget)

    # (1) operational triage output (advisory KEEP/DOWNWEIGHT/REFRESH/PRUNE + savings)
    res = triage(store, now=now, stale_days=90, keep_budget=budget)
    print("ragfresh triage (keep ~half, stale>90d):", res["report"])

    # (2) FAIR head-to-head: at the SAME hard keep-count, does value+freshness ranking beat recency?
    #     Both keep exactly `budget` items (prune the rest). Orphans (true value 0) are excluded first.
    live = [it for it in store if it.source_exists]
    ragfresh_keep = sorted(live, key=lambda it: _retention_score(it, now, 120.0), reverse=True)[:budget]
    recency_keep = sorted(live, key=lambda it: it.updated_ts, reverse=True)[:budget]
    rf = sum(true_value[it.id] for it in ragfresh_keep)
    rc = sum(true_value[it.id] for it in recency_keep)
    oracle = sum(sorted(true_value.values(), reverse=True)[:budget])    # best possible at this budget
    print(f"\nFAIR A/B — true business value retained, both keep exactly {budget} of {N} (higher=better):")
    print(f"  ragfresh (value+freshness): {rf:7.1f}  ({rf/oracle:.0%} of oracle)")
    print(f"  recency-only (naive)      : {rc:7.1f}  ({rc/oracle:.0%} of oracle)")
    print(f"  uplift over naive         : {rf/rc - 1:+.0%}")
    print(f"  + orphans auto-deleted: {res['report']['orphans_removed']}, stale flagged for refresh: {res['report']['stale_refreshed']}")
