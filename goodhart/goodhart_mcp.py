#!/usr/bin/env python3
"""
goodhart MCP server — expose the proxy-gameability auditor to ANY MCP-compatible agent.

Wraps the zero-dependency `goodhart` engine as a Model Context Protocol stdio server, so a
Claude Code / Claude Desktop / Cursor / custom agent (or an eval/RLHF/KPI assistant) can ask, before
trusting an optimized metric: how gameable is this proxy, has it stopped measuring the goal (reward
hacking), and how many independent metrics would fix it?

goodhart.py stays dependency-free; only THIS file needs the MCP SDK:  pip install "mcp[cli]"

Run (stdio):   python -m goodhart.goodhart_mcp
or register it in an MCP client (see goodhart/README.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goodhart import (fidelity as _fidelity, metrics_needed as _metrics,  # noqa: E402
                      audit as _audit)

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    sys.stderr.write("goodhart MCP server needs the MCP SDK: pip install \"mcp[cli]\"\n")
    raise

mcp = FastMCP("goodhart")


@mcp.tool()
def fidelity(gameability: float, n_metrics: int = 1) -> dict:
    """How well does an optimized proxy still select the truly-good? `gameability` = how corruptible
    the proxy is (0 = pure signal, higher = more exploitable). Returns the proxy-goal correlation and
    the precision (of items the proxy selects as top-10%, the fraction truly top-10% by the real goal).
    Reproduces the measured Goodhart decay: precision 80% (gameability 0) -> 19% (gameability 4)."""
    return _fidelity(gameability, n_metrics=n_metrics)


@mcp.tool()
def metrics_needed(gameability: float, target_precision: float = 0.7) -> dict:
    """How many INDEPENDENT proxy metrics to combine so the proxy still selects the good at >=
    target_precision (independent gameable noise averages out — harder to game N than 1). Returns the
    smallest sufficient count + the curve; if even many metrics fall short, advises changing the metric."""
    return _metrics(gameability, target_precision=target_precision)


@mcp.tool()
def audit(gameability: float, n_metrics: int = 1, target_precision: float = 0.7) -> dict:
    """Verdict for a metric setup: SAFE / DEGRADED / GAMED at this gameability and number of metrics,
    plus the recommended number of independent metrics. Use before trusting a reward model, eval
    benchmark, or KPI you've been optimizing — to catch reward hacking / metric drift."""
    return _audit(gameability, n_metrics, target_precision=target_precision)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
