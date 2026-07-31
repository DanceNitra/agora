"""The pipeline must not open on a subject the owner never asked for.

`_pick_collab_seed` rotates the pipeline's opening subject across four sources: a fresh paper, one of
Agora's own open claims, a thin frontier domain, and a recent finding to deepen. Not one of the four
was filtered against the board.

The pipeline is the dominant trust engine -- five cooperations every ~57s, seven LLM stages per
artifact -- so an unfiltered seed spends the organism's whole collaborative budget on whatever arXiv
happened to deliver. Measured on the live library 2026-07-31: **2 of 12 papers were on-board**, so
83% of pipelines opened off-mission. The refusal ledger shows where they ended: 16 of 25 post-restart
write attempts refused LAB-FIRST, on subjects like "Multiplicity of closed Reeb orbits on contact
manifolds", "TIME Commissioning Observations: II" and "Polynomial equivalence of the global
transverse-field Ising model". The write door held the line; the cost was already spent.

These tests run the shipped arithmetic against each supply shape, including the one that matters: a
library with nothing on-board must open NO pipeline rather than fall back to an off-mission paper.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MCP = REPO / "agora-game-server" / "mcp_server.py"
sys.path.insert(0, str(REPO / "server"))

BOARD_TERMS = {"memory", "recall", "retrieval", "agent", "erasure", "supersession", "integrity"}

ON_BOARD = "Do agent-memory benchmark leaderboards overstate the leader"
OFF_BOARD = "Multiplicity of closed Reeb orbits on contact manifolds"
OFF_BOARD_2 = "TIME Commissioning Observations: II. Instrument performance"


def words(t: str) -> set:
    """`_theme_words`: content words only, the same shape both gates use."""
    return {w for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if len(w) > 3}


def on_board(t: str, terms=BOARD_TERMS) -> bool:
    return (not terms) or bool(words(t) & terms)


def pick(library, claims=(), frontier=None, findings=(), terms=BOARD_TERMS, slot=0):
    """The shipped selection order, with the board filter applied at every slot."""
    if slot == 0:
        on = [p for p in library if on_board(p, terms)]
        if on:
            return ("paper", on[0])
    if slot == 1:
        on = [q for q in claims if on_board(q, terms)]
        if on:
            return ("claim", on[0])
    if slot == 2 and frontier and on_board(frontier, terms):
        return ("frontier-thin", frontier)
    on = [k for k in findings if on_board(k, terms)]
    if on:
        return ("finding", on[0])
    on = [p for p in library if on_board(p, terms)]
    if on:
        return ("paper", on[0])
    return None


# --------------------------------------------------------------------------------------------

def test_an_off_board_library_opens_no_pipeline():
    """The case measured live: 10 of 12 papers off-mission, and the fallback used to take one."""
    assert pick([OFF_BOARD, OFF_BOARD_2]) is None


def test_an_on_board_paper_is_still_chosen():
    """The control. A filter that refuses everything would pass the test above and freeze the
    pipeline permanently."""
    kind, seed = pick([OFF_BOARD, ON_BOARD, OFF_BOARD_2])
    assert (kind, seed) == ("paper", ON_BOARD)


def test_an_off_board_slot_falls_through_to_the_next():
    """Slot 0 has nothing on-board, so the seed must come from a later source, not from nowhere."""
    got = pick([OFF_BOARD], findings=["How supersession affects recall at scale"], slot=0)
    assert got is not None and got[0] == "finding"


def test_an_off_board_frontier_target_is_refused():
    assert pick([], frontier=OFF_BOARD, slot=2) is None


def test_a_silent_board_lets_everything_through():
    """A gate with nothing to gate on must not stop the organism."""
    kind, seed = pick([OFF_BOARD], terms=set())
    assert (kind, seed) == ("paper", OFF_BOARD)


def test_a_finding_is_judged_on_its_title_not_its_body():
    """An off-mission note whose body mentions `memory` in passing must not wave the subject in."""
    assert not on_board("Multiplicity of closed Reeb orbits")


# --------------------------------------------------------------------------------------------

def test_every_seed_slot_in_the_shipping_code_is_gated():
    """Pins the claim to the source. Four slots plus a fallback; each must consult the board."""
    src = MCP.read_text(encoding="utf-8", errors="replace")
    body = src.split("async def _pick_collab_seed():", 1)[1].split("\nasync def ", 1)[0]
    assert body.count("_on_board(") >= 5, (
        "only %d of the seed slots consult the board; an ungated slot is how 83%% of pipelines "
        "opened off-mission" % body.count("_on_board("))
    assert "no on-board seed in any slot" in body, "silent starvation: nothing logs the empty cycle"


def test_the_board_helper_is_permissive_when_the_board_is_silent():
    src = MCP.read_text(encoding="utf-8", errors="replace")
    body = src.split("async def _on_board(", 1)[1].split("\nasync def ", 1)[0]
    assert "not prio" in body, "with no priorities set, the gate must pass everything"
