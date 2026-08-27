"""ONE definition means one ANSWER, and it was still two -- on plurals.

`methods.board_priority_terms` carries a docstring saying it is THE one definition, written after the
brain and the dungeon were found deriving the board's vocabulary separately and disagreeing. That was
fixed at the level of WHICH WORDS. It was not fixed at the level of WORD FORM: this function returned
exact tokens while the dungeon's `_theme_words` lightly stems (`w.rstrip("s")`).

Measured 2026-08-08 on the live board, same text, same moment:

    "LLM agents with o"   brain -> NONE          dungeon -> {"agent"}

`agent` is the commonest word in our domain, and the disagreement runs in the EXCLUDING direction:
the brain filed on-mission work as off-board. That is the expensive direction -- it does not add
noise you would notice, it withholds real work silently.

Found while triaging the Claude inbox WITH this function, one step before six tasks would have been
skipped on its verdict. An instrument has to be checked before its readings are acted on.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))

from agora.execution.methods import board_priority_terms  # noqa: E402

#: The dungeon's matcher, verbatim from `mcp_server._theme_words`. Copied deliberately: this test
#: exists to prove the two IMPLEMENTATIONS agree, so it must hold the other one to compare against.
#: `mcp_server` cannot be imported (it is __main__ and starts a server), so the copy is checked
#: against the live source by `test_the_dungeon_matcher_still_looks_like_this`.
def dungeon_theme_words(text: str) -> set:
    def stem(w):
        return w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith(("ss", "us", "is")) else w
    return {stem(w) for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) > 3}


BOARD = "prioritize agent memory, poison resistance, erasure, supersession and correction"

PROBES = [
    "LLM agents with o",          # the measured case
    "agent memories are stale",
    "poison attacks on retrieval",
    "erasures and reverts",
    "memory operations benchmark",
    "a study of corrections",
    "Reeb orbits on contact manifolds",      # genuinely off-mission -- must stay off in BOTH
]


@pytest.mark.parametrize("probe", PROBES)
def test_the_two_gates_reach_the_same_verdict(probe):
    board = board_priority_terms(BOARD)
    brain = bool(board_priority_terms(probe) & board)
    dungeon = bool(dungeon_theme_words(probe) & board)
    assert brain == dungeon, (
        "%r: brain says %s, dungeon says %s -- one definition, two answers" % (probe, brain, dungeon))


def test_the_plural_case_is_actually_on_mission():
    """CONTROL. The agreement above could be satisfied by BOTH gates saying no. Pin the direction:
    'LLM agents' is on-mission and both must admit it."""
    board = board_priority_terms(BOARD)
    assert board_priority_terms("LLM agents with o") & board
    assert dungeon_theme_words("LLM agents with o") & board


def test_off_mission_still_gets_refused():
    """The other control: stemming must not turn the gate into a pass-through."""
    board = board_priority_terms(BOARD)
    assert not (board_priority_terms("Reeb orbits on contact manifolds") & board)


def test_a_refusal_sentence_contributes_no_priority_words():
    """The older guarantee must survive the change -- the owner's REFUSALS are not a whitelist."""
    terms = board_priority_terms(
        "Prioritize agent memory. Deprioritize generic meta-science and politics.")
    assert "agent" in terms and "memory" in terms
    assert "politic" not in terms and "science" not in terms


def test_our_own_product_name_survives_the_stem():
    """`rstrip("s")` turned "inspeximus" into "inspeximu" -- the one term the board most needs to
    match, mangled by the matcher, on BOTH sides but at different times, so they never met."""
    from agora.execution.methods import light_stem
    for unchanged in ("inspeximus", "class", "analysis", "bias", "process"):
        assert light_stem(unchanged) == unchanged, "%r was stemmed" % unchanged
    for a, b in (("agents", "agent"), ("operations", "operation"), ("compounds", "compound"),
                 ("competitors", "competitor")):
        assert light_stem(a) == b
    assert "inspeximus" in board_priority_terms("prioritize inspeximus and agent memory")


def test_the_dungeon_matcher_still_looks_like_this():
    """THE CONTROL FOR THE COPY ABOVE. If `_theme_words` changes shape, the comparison in this file
    stops testing the real pair and silently starts testing itself."""
    src = (SERVER.parent / "agora-game-server" / "mcp_server.py").read_text(
        encoding="utf-8", errors="replace")
    # THE WHOLE FUNCTION, not a fixed window. This read 500 characters until 2026-08-27, when the
    # docstring grew a note about -ies and pushed `w.endswith(...)` out to offset 935. The assertion
    # then failed while the code it guards was correct, which is the same defect in the safe
    # direction: a check that cannot see its target. A bigger constant would only postpone it.
    i = src.index("def _light_stem(")
    j = src.find(chr(10) + "def ", i + 1)
    body = src[i:j if j > 0 else len(src)]
    assert 'w.endswith(("ss", "us", "is"))' in body, "the dungeon's stem drifted from the brain's"
    assert "len(w) > 4" in body
    assert 'rstrip("s")' not in src[src.index("def _theme_words("):][:400], "crude stem is back"
