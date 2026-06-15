#!/usr/bin/env python3
"""
herdcheck MCP server — expose the multi-agent herding auditor to ANY MCP-compatible agent.

Wraps the zero-dependency `herdcheck` engine as a Model Context Protocol stdio server, so a
Claude Code / Claude Desktop / Cursor / custom orchestrator can ask, before wiring up a multi-agent
system or ensemble: will this crowd stay wiser than its best member, or will it herd into the
popularity trap? And what's the fix?

herdcheck.py stays dependency-free; only THIS file needs the MCP SDK:  pip install "mcp[cli]"

Run (stdio):   python -m herdcheck.herdcheck_mcp
or register it in an MCP client (see herdcheck/README.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from herdcheck import (ensemble_accuracy as _ens, herding_threshold as _kc,  # noqa: E402
                       audit as _audit)

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    sys.stderr.write("herdcheck MCP server needs the MCP SDK: pip install \"mcp[cli]\"\n")
    raise

mcp = FastMCP("herdcheck")


@mcp.tool()
def ensemble_accuracy(peers_seen: int, own_weight: float = 1.0, p: float = 0.60,
                      discount: float = 1.0, n_agents: int = 401) -> float:
    """Collective accuracy of a social-learning crowd: each agent has a private signal correct with
    prob `p`, observes `peers_seen` peers' actions (each weighted by `discount`, own signal by
    `own_weight`), and acts. peers_seen=0 = fully independent (the wisdom ceiling). Returns P(majority
    correct). Watch it collapse toward single-member competence as peers_seen rises past own_weight+1."""
    return _ens(peers_seen, own_weight, p=p, discount=discount, n_agents=n_agents)


@mcp.tool()
def herding_threshold(own_weight: float = 1.0) -> int:
    """k_c = own_weight + 1: the number of observed peers at which collective wisdom STARTS to degrade.
    Cap how many peer verdicts an agent ingests below this, or raise own_weight to push it up."""
    return _kc(own_weight)


@mcp.tool()
def audit(peers_seen: int, own_weight: float = 1.0, discount: float = 1.0, p: float = 0.60) -> dict:
    """Audit a multi-agent / ensemble config: compares its collective accuracy to the independent
    wisdom ceiling and to a single member. Returns INDEPENDENT WISDOM / DEGRADED / HERDED + the fix
    (cap peers, raise own_weight, discount peer signals, or share evidence not verdicts)."""
    return _audit(peers_seen, own_weight, discount=discount, p=p)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
