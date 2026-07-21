#!/usr/bin/env python3
"""
aiaudit MCP server — run the full AI reliability audit from ANY MCP-compatible agent.

So a Claude / Cursor / custom agent can audit an AI system (its own, or a customer's) in one call:
pass a spec describing the parts you have, get back a PASS/WARN/FAIL report across every failure mode
(noise A/B, gamed metric, model collapse, agent herding, biased causal claim, rotting RAG) + the fixes.

aiaudit is pure Python over the toolkit cores; only THIS file needs the MCP SDK: pip install "mcp[cli]"
Run (stdio):  python -m aiaudit.aiaudit_mcp
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aiaudit import audit as _audit, format_report as _format   # noqa: E402

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    sys.stderr.write("aiaudit MCP server needs the MCP SDK: pip install \"mcp[cli]\"\n")
    raise

mcp = FastMCP("aiaudit")


@mcp.tool()
def ai_audit(spec: dict) -> dict:
    """Run the full AI reliability audit. `spec` is a dict with any of these OPTIONAL keys (each runs
    its check only if present):
      ab_test     {conv_a,n_a,conv_b,n_b}        - is a reported lift real or noise? (nullcheck)
      metric      {gameability,n_metrics}        - is an optimized proxy/KPI gamed? (goodhart)
      training_mix{external_fraction,self_trust_p}- model collapse / lock risk? (selfref)
      multi_agent {peers_seen,own_weight,discount}- will an ensemble herd? (herdcheck)
      causal      {controls:{name:role}}         - is a causal number identified? (idcheck)
      rag_store   {items:[{id,updated_ts,value,source_exists}]} - is the vector store rotting? (ragfresh)
      memory      {items:[{text,value,links}]}   - agent-memory health (inspeximus)
    Returns {overall PASS/WARN/FAIL, health_score, dimensions[], fixes[]}."""
    return _audit(spec)


@mcp.tool()
def ai_audit_report(spec: dict) -> str:
    """Same as ai_audit but returns the human-readable report text (verdict per dimension + fixes)."""
    return _format(_audit(spec))


def main():
    mcp.run()


if __name__ == "__main__":
    main()
