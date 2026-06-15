#!/usr/bin/env python3
"""
quitkit MCP server — expose the drawdown-exit "when to quit" governor to ANY MCP-compatible agent.

Wraps the zero-dependency `quitkit` engine as a Model Context Protocol stdio server, so a
Claude Code / Claude Desktop / Cursor / custom agent (or a portfolio/effort-allocation loop) can ask,
about a declining effort: have we hit the drawdown stop — cut and reallocate, or keep going? Stateless.

quitkit.py stays dependency-free; only THIS file needs the MCP SDK:  pip install "mcp[cli]"

Run (stdio):   python -m quitkit.quitkit_mcp
or register it in an MCP client (see quitkit/README.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import the local zero-dep engine whether launched as `python -m quitkit.quitkit_mcp` or directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from quitkit import (should_quit as _should_quit, optimal_theta as _optimal_theta,  # noqa: E402
                     compare as _compare)

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    sys.stderr.write("quitkit MCP server needs the MCP SDK: pip install \"mcp[cli]\"\n")
    raise

mcp = FastMCP("quitkit")


@mcp.tool()
def should_quit(history: list[float], theta: float = 0.6, window: int = 25) -> dict:
    """Should you quit the current effort? `history` = your per-period yields so far (newest last):
    1/0 for hit/miss, or any numeric yield (revenue, conversions, findings). QUITs when the recent
    average yield has fallen more than `theta` below its running peak (a drawdown stop; theta=0.6 is
    the measured interior optimum). Returns {quit, recent_rate, peak_rate, drawdown, reason}."""
    return _should_quit(history, theta=theta, window=window)


@mcp.tool()
def optimal_theta() -> dict:
    """The measured drawdown threshold: sweeps theta on the reference depletable-pool model and returns
    the argmax plus the whole curve, showing the INTERIOR optimum (~0.6 — quitting too early or too
    late both lose) and the lift over mining to depletion. Use to justify the default theta."""
    return _optimal_theta()


@mcp.tool()
def compare(theta: float = 0.6) -> dict:
    """Drawdown-exit at `theta` vs mine-to-depletion on the same budget — the headline lift (+~213-239%
    in the reference model). Returns findings/pools for each strategy and the percent lift."""
    return _compare(theta)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
