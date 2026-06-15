#!/usr/bin/env python3
"""
ragfresh MCP server — expose the RAG freshness/decay layer to ANY MCP-compatible agent.

Wraps the zero-dependency `ragfresh` engine as a Model Context Protocol stdio server, so a
Claude Code / Claude Desktop / Cursor / custom agent (or a maintenance cron) can decide what to
KEEP / DOWNWEIGHT / REFRESH / PRUNE in a RAG / vector store — ranked by value × freshness, not
recency — and get a query-time staleness weight. ragfresh is stateless: you pass the store's item
metadata in, it returns a plan; your code applies it. No silent deletes.

ragfresh.py stays dependency-free; only THIS file needs the MCP SDK:  pip install "mcp[cli]"

Run (stdio):   python -m ragfresh.ragfresh_mcp
or register it in an MCP client (see ragfresh/README.md).

An `item` is a JSON object:
    {"id": "c1", "updated_ts": 1.7e9, "last_access_ts": 1.7e9, "hits": 12,
     "value": 0.8, "source_exists": true, "bytes": 4096}
Only `id` and `updated_ts` are required; the rest default. Timestamps are epoch seconds.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Import the local zero-dep engine whether launched as `python -m ragfresh.ragfresh_mcp` or directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ragfresh import Item, triage as _triage, retrieval_weight as _retweight  # noqa: E402

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    sys.stderr.write("ragfresh MCP server needs the MCP SDK: pip install \"mcp[cli]\"\n")
    raise

mcp = FastMCP("ragfresh")

_FIELDS = ("id", "updated_ts", "last_access_ts", "hits", "value", "source_exists", "bytes")


def _to_item(d: dict) -> Item:
    """Build an Item from a JSON object, ignoring unknown keys and filling sane defaults."""
    kw = {k: d[k] for k in _FIELDS if k in d}
    return Item(id=str(kw.get("id", "")), updated_ts=float(kw.get("updated_ts", 0.0)),
                last_access_ts=float(kw.get("last_access_ts", 0.0) or 0.0),
                hits=int(kw.get("hits", 0) or 0),
                value=(None if kw.get("value") is None else float(kw["value"])),
                source_exists=bool(kw.get("source_exists", True)),
                bytes=int(kw.get("bytes", 0) or 0))


@mcp.tool()
def triage(items: list[dict], now: float | None = None, stale_days: float = 90.0,
           half_life_days: float = 120.0, keep_budget: int | None = None,
           refresh_min_value: float = 0.5) -> dict:
    """Decide, for a batch of vector-store entries, what to KEEP / DOWNWEIGHT / REFRESH / PRUNE.
    Run this as a PERIODIC BATCH (a scheduled 'dream' pass), not a per-write hook — continuous
    cleanup pays ~25x more pruning events for ~8% leaner storage (measured). Orphans (source_exists
    false) are PRUNEd; stale-but-valuable is REFRESHed (re-embed), not dropped; under a keep_budget
    the weakest-by-value surplus is DOWNWEIGHTed (or PRUNEd if its retention score is very low).
    Returns {'decisions': {id: [action, reason]}, 'report': {counts, pruned_fraction,
    reclaimed_bytes, orphans_removed, stale_refreshed}}. Advisory only — your code applies the plan."""
    now = time.time() if now is None else float(now)
    res = _triage([_to_item(d) for d in items], now=now, stale_days=stale_days,
                  half_life_days=half_life_days, keep_budget=keep_budget,
                  refresh_min_value=refresh_min_value)
    # JSON-friendly: tuples -> lists
    res["decisions"] = {k: list(v) for k, v in res["decisions"].items()}
    return res


@mcp.tool()
def retrieval_weight(item: dict, now: float | None = None, half_life_days: float = 120.0) -> float:
    """Query-time multiplier in [0,1] to fold into a chunk's similarity score so fresh content ranks
    above stale WITHOUT deleting anything (an orphan whose source is gone returns 0.0). Multiply your
    cosine/similarity by this before ranking."""
    now = time.time() if now is None else float(now)
    return _retweight(_to_item(item), now=now, half_life_days=half_life_days)


@mcp.tool()
def prune_ids(items: list[dict], now: float | None = None, stale_days: float = 90.0,
              keep_budget: int | None = None) -> dict:
    """Convenience: return just the actionable id lists — {'prune': [...], 'refresh': [...]} — for a
    maintenance job to delete / re-embed directly. Same engine as triage()."""
    res = triage(items, now=now, stale_days=stale_days, keep_budget=keep_budget)
    pr, rf = [], []
    for vid, (action, _reason) in res["decisions"].items():
        if action == "PRUNE":
            pr.append(vid)
        elif action == "REFRESH":
            rf.append(vid)
    return {"prune": pr, "refresh": rf, "report": res["report"]}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
