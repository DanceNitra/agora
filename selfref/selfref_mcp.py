#!/usr/bin/env python3
"""
selfref MCP server — expose the self-reference governor to ANY MCP-compatible agent.

Wraps the zero-dependency `selfref` engine as a Model Context Protocol stdio server, so a
Claude Code / Claude Desktop / Cursor / custom agent (or a training/CI guard) can ask, before it
retrains on synthetic data or trusts its own memory loop: am I about to COLLAPSE (lose diversity)
or LOCK (permanently confirm a bias)? Stateless: pass your settings in, get a verdict back.

selfref.py stays dependency-free; only THIS file needs the MCP SDK:  pip install "mcp[cli]"

Run (stdio):   python -m selfref.selfref_mcp
or register it in an MCP client (see selfref/README.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import the local zero-dep engine whether launched as `python -m selfref.selfref_mcp` or directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from selfref import (collapse_risk as _collapse, min_external_anchor as _minanchor,  # noqa: E402
                     lock_fraction as _lockfrac, lock_risk as _lockrisk, audit as _audit)

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    sys.stderr.write("selfref MCP server needs the MCP SDK: pip install \"mcp[cli]\"\n")
    raise

mcp = FastMCP("selfref")


@mcp.tool()
def collapse_risk(external_fraction: float, generations: int = 120, samples_per_gen: int = 20,
                  trials: int = 200) -> dict:
    """Recursive-self-training COLLAPSE risk at a given external/real-data fraction (0..1). Returns
    {collapse_rate, mean_final_diversity, verdict}. Use before retraining a model on its own/synthetic
    outputs, or before letting an agent's memory feed itself: too little real data and diversity
    drains to zero (curse of recursion). ~5% real is the measured knee, >=20% is clean."""
    return _collapse(external_fraction, generations=generations, samples_per_gen=samples_per_gen,
                     trials=trials)


@mcp.tool()
def min_external_anchor(max_collapse_rate: float = 0.05) -> dict:
    """The smallest real/external-data fraction whose collapse rate stays under max_collapse_rate —
    i.e. 'how much human/real data must I keep mixing in to stay safe?' Returns the fraction + scan."""
    return _minanchor(max_collapse_rate=max_collapse_rate)


@mcp.tool()
def lock_risk(self_trust_p: float) -> dict:
    """Permanent self-confirmation LOCK risk for a self-trust exponent p (how fast the system trusts
    its own prior vs new evidence). Returns {locked_bias_fraction, verdict}. p<=1 washes bias out;
    p>1 locks a fixed fraction forever (p=1.5 -> 18%, p=2 -> 50%, p=3 -> 81%). Field test for p>1:
    inject a known bias, keep feeding unbiased data — if it does NOT decay, you're locked."""
    return _lockrisk(self_trust_p)


@mcp.tool()
def lock_fraction(self_trust_p: float) -> float:
    """Just the number: the fraction of an initial bias permanently locked in at self-trust exponent
    p (analytic, exact). 0.0 means safe (p<=1)."""
    return _lockfrac(self_trust_p)


@mcp.tool()
def audit(external_fraction: float, self_trust_p: float = 1.0) -> dict:
    """Both laws in one call: the data-mix collapse risk AND the self-trust lock risk, with a combined
    SAFE / WATCH / COLLAPSE / LOCK verdict and the concrete fix. The one-shot self-reference check."""
    return _audit(external_fraction, self_trust_p)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
