"""The write path was storing the preamble and deleting the evidence.

An organ note is structured -- CLAIM, SOURCE, MODEL, MEASURED, TOLERANCE, VERDICT, INDEPENDENCE,
Falsifier -- and runs 1,500 to 3,000 characters, with the verdict and the falsifier at the END. The
contribution path capped content at 500, a size from when a contribution was one sentence of flavour
text. So every long note was stored down to its opening paragraph.

Measured 2026-07-31:

* every one of the last 40 discoveries sat at EXACTLY 500 characters;
* 0 of those 40 stated a falsifier, against 984 of the 10,437 lifetime rows (9.4%) that do;
* Dame Elara's note ended mid-word -- "...a NUMBER disputed between a note and its own".

That read as a swarm-wide contract gap -- "four of the eight organs never write a falsifier" -- and
it was a substring operation. Elara's organ, Voss's and Orin's were all writing one and having it cut
off before anyone could see it.

THREE numbers governed one limit: the dungeon posted `content[:600]`, its own `_CONTRIB_CAP` said
500, and the brain stored `content[:500]`. The smallest silently won, one layer below where anyone
looking at the dungeon would check. Raising one alone changes nothing, so this pins them together.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MCP = REPO / "agora-game-server" / "mcp_server.py"
sys.path.insert(0, str(REPO / "server"))


def dungeon_cap() -> int:
    tree = ast.parse(MCP.read_text(encoding="utf-8", errors="replace"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and "_CONTRIB_CAP" in {
                t.id for t in node.targets if isinstance(t, ast.Name)}:
            return int(ast.literal_eval(node.value))
    raise AssertionError("_CONTRIB_CAP is no longer a module-level literal")


def brain_cap() -> int:
    from agora.agent_os.agent_os import _CONTRIB_MAX_CHARS
    return int(_CONTRIB_MAX_CHARS)


def test_the_two_caps_agree():
    """The failure is silent on both sides: the poster never learns it was cut, the store never
    reports it. Only equality makes the budget the dungeon computes against real."""
    assert dungeon_cap() == brain_cap(), (
        "dungeon caps at %d and the brain stores %d -- the smaller one wins silently"
        % (dungeon_cap(), brain_cap()))


def test_the_cap_clears_a_real_organ_note():
    """Not a round number pulled from the air: the largest organ note measured is ~3,000 chars, and
    the falsifier sits in its last fifth."""
    assert brain_cap() >= 6000, (
        "cap %d leaves no headroom above the ~3,000-character notes the organs already write; the "
        "falsifier lives at the end and is the first thing a tight cap deletes" % brain_cap())


def test_nothing_on_the_write_path_still_hardcodes_a_smaller_limit():
    """The defect was a THIRD number nobody reconciled. Any bare `content[:NNN]` on the post is one
    again -- the constant has to be the only place the limit is stated."""
    src = MCP.read_text(encoding="utf-8", errors="replace")
    post = src.split('"/api/v1/agent-os/brain/collective"', 1)[1][:400]
    bare = re.findall(r"content\[:(\d+)\]", post)
    assert not bare, "the contribute POST hardcodes %s instead of using _CONTRIB_CAP" % bare
    assert "content[:_CONTRIB_CAP]" in post, "the POST no longer budgets against the shared constant"


def test_the_store_uses_the_constant_not_a_literal():
    import inspect
    from agora.agent_os import agent_os as A
    src = inspect.getsource(A.AgentOS._contribute_to_collective)
    assert "content[:_CONTRIB_MAX_CHARS]" in src, (
        "the INSERT hardcodes a length again; that literal is what deleted every falsifier")
    assert "content[:500]" not in src


def test_the_history_still_shows_the_truncation():
    """The control. These assertions must not be able to pass because the defect never existed --
    the stored rows still carry it, and if that stops being true the fixture has drifted."""
    import sqlite3
    db = REPO / "server" / "agora.db"
    if not db.exists():
        import pytest
        pytest.skip("no local database")
    con = sqlite3.connect("file:%s?mode=ro" % db.as_posix(), uri=True)
    rows = con.execute("SELECT length(content) FROM collective_knowledge "
                       "WHERE knowledge_type='discovery' AND content IS NOT NULL "
                       "ORDER BY created_at DESC LIMIT 40").fetchall()
    con.close()
    if not rows:
        import pytest
        pytest.skip("no discoveries recorded")
    at_cap = sum(1 for (n,) in rows if n == 500)
    assert at_cap >= len(rows) // 2, (
        "only %d of the last %d discoveries sit at exactly 500 chars; the truncation this file "
        "documents is no longer visible in the data" % (at_cap, len(rows)))
