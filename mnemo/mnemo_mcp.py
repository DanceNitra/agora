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
def remember(text: str, tags: list[str] | None = None, value: float = 1.0) -> dict:
    """Store a memory (append-only; raw text is never edited afterward). `tags` group memories into
    cohorts; `value` (>=1) is its importance — higher-value memories outrank merely-similar ones at
    recall, and recall itself nudges value up. Returns the new memory id."""
    mid = _MEM.remember(text, tags=tags or [], value=value)
    return {"id": mid, "stored": text[:120], "tags": tags or [], "value": value}


@mcp.tool()
def recall(query: str, k: int = 6) -> list[dict]:
    """Retrieve the top-k memories by RELEVANCE × accrued VALUE (not recency). Use this to load
    relevant prior knowledge before reasoning. Returns text, tags, value, and a relevance score."""
    return _MEM.recall(query, k=k)


@mcp.tool()
def consolidate(keep: int | None = None) -> dict:
    """Run the consolidation 'dream' pass: link near-duplicate memories and, if `keep` is given,
    mark the lowest-value surplus beyond that budget as superseded. ADDS a derived layer only — it
    never edits or deletes raw memories. Returns a report (active / linked_pairs / staled / total)."""
    return _MEM.consolidate(keep=keep)


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
