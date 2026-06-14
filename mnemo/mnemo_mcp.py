#!/usr/bin/env python3
"""
mnemo MCP server — expose Agora's memory layer to ANY MCP-compatible agent.

This wraps the zero-dependency `mnemo.Mnemo` store as a Model Context Protocol stdio server, so a
Claude Code / Claude Desktop / Cursor / custom agent can use mnemo as its long-term memory: it can
`remember` facts, `recall` them value-ranked (relevance × accrued value, not just recency), run the
`consolidate` "dream" pass under a keep-budget, surface `contradictions`, and read value rollups.

mnemo.py stays dependency-free; only THIS file needs the MCP SDK:  pip install "mcp[cli]"

Run (stdio):
    MNEMO_PATH=./agent_memory.json python -m mnemo.mnemo_mcp
or register it in an MCP client (see mnemo/README.md for a .mcp.json / claude_desktop_config.json
snippet).

Config (environment):
    MNEMO_PATH        where to persist memory (JSON). Default: ./mnemo_memory.json
    MNEMO_EMBED_URL   optional OpenAI-compatible /embeddings endpoint for SEMANTIC recall
    MNEMO_EMBED_MODEL embedding model id (default: text-embedding-3-small)
    MNEMO_EMBED_KEY   bearer key for that endpoint
  With no embedder configured, mnemo uses its lexical-overlap fallback — it runs anywhere, today.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

# Import the local zero-dep store whether launched as `python -m mnemo.mnemo_mcp` or `python mnemo_mcp.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mnemo import Mnemo  # noqa: E402

try:
    from mcp.server.fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    sys.stderr.write("mnemo MCP server needs the MCP SDK: pip install \"mcp[cli]\"\n")
    raise


def _make_embedder():
    """Optional OpenAI-compatible embedder (zero extra deps — urllib). Returns None if unconfigured."""
    url = os.environ.get("MNEMO_EMBED_URL", "").strip()
    if not url:
        return None
    model = os.environ.get("MNEMO_EMBED_MODEL", "text-embedding-3-small").strip()
    key = os.environ.get("MNEMO_EMBED_KEY", "").strip()

    def embed(text: str):
        body = json.dumps({"model": model, "input": text}).encode()
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())["data"][0]["embedding"]

    return embed


_PATH = os.environ.get("MNEMO_PATH", "mnemo_memory.json")
_MEM = Mnemo(_PATH, embed=_make_embedder())

mcp = FastMCP("mnemo")


@mcp.tool()
def remember(text: str, tags: list[str] | None = None, value: float = 1.0,
             mtype: str | None = None) -> dict:
    """Store a memory (append-only; raw text is never edited afterward). `tags` group memories into
    cohorts; `value` (>=1) is its importance — higher-value memories outrank merely-similar ones at
    recall, and recall itself nudges value up. `mtype` ∈ {episodic, semantic, procedural} sets the
    decay prior — episodic (events) fades fast, semantic (durable facts) slow, procedural (rules /
    preferences) barely; pass it when you know the kind, else it's inferred. Returns the new id."""
    mid = _MEM.remember(text, tags=tags or [], value=value, mtype=mtype)
    rec = next((r for r in _MEM.items if r["id"] == mid), {})
    return {"id": mid, "stored": text[:120], "tags": tags or [], "value": value,
            "mtype": rec.get("mtype")}


@mcp.tool()
def recall(query: str, k: int = 6) -> list[dict]:
    """Retrieve the top-k memories by RELEVANCE × accrued VALUE (not recency). Use this to load
    relevant prior knowledge before reasoning. Returns text, tags, value, and a relevance score."""
    return _MEM.recall(query, k=k)


@mcp.tool()
def consolidate(keep: int | None = None) -> dict:
    """Run the consolidation 'dream' pass over ALL memories: flag universal-matcher 'hub' notes, link
    near-duplicates, and (if `keep` is given) supersede the lowest-value surplus. Includes the
    STATE-TOGGLE guard — a high-similarity pair that is a polarity clash (a preference flip) is
    superseded, not merged, so recall returns the new state. ADDS a derived layer only; never edits
    or deletes raw memories. Returns a report (active / hubs_flagged / linked_pairs / toggled / ...)."""
    return _MEM.consolidate(keep=keep)


@mcp.tool()
def consolidate_clusters(threshold: int = 15) -> dict:
    """Cluster-TRIGGERED consolidation: consolidate a semantic cluster only once it has grown past
    `threshold` members — not a global blanket. Avoids prematurely consolidating sparse topics (raw
    episodes stay the best representation) and unbounded growth in dense ones. Cheap to call often
    (a no-op until a cluster is ripe). Returns clusters_total / clusters_fired / linked_pairs / ..."""
    return _MEM.consolidate_clusters(threshold=threshold)


@mcp.tool()
def contradictions() -> list[dict]:
    """Surface mutually-incompatible memories (related in content, opposite in polarity) for review.
    It FLAGS, never auto-resolves — silent rewrites destroy trust. Returns the conflicting pairs."""
    return _MEM.contradictions()


@mcp.tool()
def value_by_cohort() -> dict:
    """Per-tag value rollup (count / total value / average). Reported at the cohort level on purpose:
    at n-of-1 a single memory's value is noise; the tag/time-block is where the signal is real."""
    return _MEM.value_by_cohort()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
