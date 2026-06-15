#!/usr/bin/env python3
"""
idcheck MCP server — expose the identification / bad-control auditor to ANY MCP-compatible agent.

Wraps the zero-dependency `idcheck` engine as a Model Context Protocol stdio server, so a
Claude Code / Claude Desktop / Cursor / custom agent (or an analytics/diligence assistant) can check,
before trusting a causal or attribution number: is this identified, or are the controls injecting bias?

idcheck.py stays dependency-free; only THIS file needs the MCP SDK:  pip install "mcp[cli]"

Run (stdio):   python -m idcheck.idcheck_mcp
or register it in an MCP client (see idcheck/README.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from idcheck import (audit as _audit, identification_score as _score,  # noqa: E402
                     collider_bias as _collider, good_and_bad_controls as _table)

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    sys.stderr.write("idcheck MCP server needs the MCP SDK: pip install \"mcp[cli]\"\n")
    raise

mcp = FastMCP("idcheck")


@mcp.tool()
def audit(controls: dict) -> dict:
    """Audit the variables you condition on in a regression/attribution model. `controls` = {name:
    role}, role one of: confounder, proxy_confounder, outcome_predictor (good, INCLUDE) | collider,
    mediator, descendant_outcome, instrument (bad, DROP) | unrelated. Returns the keep/DROP verdict
    per control, an overall identification verdict, and a 0..1 score. A control is a claim about the
    graph — you state the role, idcheck applies the back-door rules. More controls is NOT safer."""
    return _audit(controls)


@mcp.tool()
def identification_score(controls: dict) -> float:
    """0..1: are the variables you condition on admissible? 1.0 = all good controls + a confounder
    covered; any bad control conditioned on drops it sharply (bad controls actively inject bias)."""
    return _score(controls)


@mcp.tool()
def collider_bias(beta: float = 0.5, n: int = 20000) -> dict:
    """The measured proof at your own true effect `beta`: X->Y with collider C=X+Y+noise. Returns the
    naive Y~X estimate (recovers beta), the estimate after 'controlling for' the collider (corrupted),
    and the bias that adjusting injected. Demonstrates that a more-controlled model can be more wrong."""
    return _collider(beta, n=n)


@mcp.tool()
def good_and_bad_controls() -> dict:
    """Reference table: each causal role -> INCLUDE / DROP / OPTIONAL + the reason. Classify your
    candidate controls against this, then call audit()."""
    return _table()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
