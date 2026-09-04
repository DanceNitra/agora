"""The seminar's per-agent recall hint must be the agent's ROLE, not its NAME.

Regression cover for a silent-degradation bug: `_brain_ecosystem_tick` selected only
(npc_id, npc_name) from dungeon_npcs, so `n.get("role")` in seminar._run_group_seminar_inner was
always None and every agent fell back to querying the shared memory store by its own NAME. That
fallback looked like success (a round still ran, contributions still appeared) while the gate it
was supposed to feed had stopped discriminating.

The first test runs the PRODUCTION SQL against a real sqlite database, so dropping `role` from the
SELECT makes the column genuinely absent from the row — it does not assert on the spelling of a
query string.
"""
from __future__ import annotations

import asyncio
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

NPCS = [
    ("00000000-0000-0000-0000-000000000001", "Shadow Kael", "adventurer"),
    ("00000000-0000-0000-0000-000000000006", "Artificer Rooke", "artificer"),
]


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    async def fetchall(self):
        return self._rows


class _FakeDB:
    """Async shim over a real in-memory sqlite3 connection.

    The production SQL string is executed verbatim, so a SELECT that omits `role` yields a row that
    genuinely has no `role` key — which is what makes this test go red on a revert.
    """

    def __init__(self, con: sqlite3.Connection):
        self.con = con

    async def execute(self, sql, params=()):
        return _FakeCursor(self.con.execute(sql, params).fetchall())

    async def commit(self):
        self.con.commit()


@pytest.fixture
def npc_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute(
        "CREATE TABLE dungeon_npcs (npc_id TEXT PRIMARY KEY, npc_name TEXT NOT NULL, "
        "role TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active')")
    con.executemany(
        "INSERT INTO dungeon_npcs (npc_id, npc_name, role, status) VALUES (?, ?, ?, 'active')",
        NPCS)
    con.commit()
    yield con
    con.close()


async def test_tick_hands_the_seminar_rows_that_carry_role(npc_db, monkeypatch):
    """End to end: the tick's own query must deliver `role` into run_group_seminar's npc rows."""
    import types

    from agora import main as agora_main
    from agora.execution import seminar

    captured: list[list[dict]] = []

    def _fake_seminar(npcs, vault):
        captured.append(npcs)
        return {"topic": "t", "contributors": [], "passed": [], "contribution": None,
                "role_missing": []}

    monkeypatch.setattr(seminar, "run_group_seminar", _fake_seminar)
    # ENABLE THE ORGAN UNDER TEST. Since 2026-09-04 the tick reads AGORA_SEMINAR and the seminar is
    # off by default, because it was the brain's largest spender. This test is about WHAT the tick
    # hands the seminar when it runs, so it asks for the organ rather than asserting the default.
    # Setting the input, not accepting the outcome: without this the run produces no rows at all and
    # the assertion below reports "the seminar never ran", which is a true statement about the
    # configuration and says nothing about the SELECT this file exists to guard.
    monkeypatch.setenv("AGORA_SEMINAR", "1")

    # Force the seminar branch by swapping the module attribute the tick reads, not the global
    # `random` module (which every other test in the process shares).
    monkeypatch.setattr(agora_main, "random",
                        types.SimpleNamespace(random=lambda: 0.0, choice=lambda seq: seq[0]))

    app = types.SimpleNamespace(state=types.SimpleNamespace(
        db=_FakeDB(npc_db), agent_os=object(), tick_count=20, event_bus=None))

    await agora_main._brain_ecosystem_tick(app)
    # The tick fires the seminar via asyncio.create_task + asyncio.to_thread. Drain the tasks it
    # spawned instead of polling a wall clock: a sleep budget is a timing gate that a loaded runner
    # can trip for reasons that have nothing to do with the behaviour under test.
    spawned = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if spawned:
        await asyncio.wait(spawned, timeout=60)

    assert captured, "the seminar never ran"
    rows = {r["npc_name"]: r for r in captured[0]}
    for _npc_id, name, role in NPCS:
        assert "role" in rows[name], f"the tick's SELECT dropped `role` for {name}"
        assert rows[name]["role"] == role
        assert rows[name]["role"] != name


async def test_role_not_name_reaches_agent_can_contribute(monkeypatch):
    """A row carrying a role must query memory by that ROLE, never by the agent's name.

    This is the CONTRACT test, and it is deliberately honest about which of its assertions bite.
    The two `hints` assertions are satisfied by the OLD `role = n.get("role") or name` too, because
    these rows happen to carry a role — they pin the contract, they do not detect a regression.
    Revert detection is carried per hunk: the SELECT hunk by
    test_tick_hands_the_seminar_rows_that_carry_role (a row that lacks the column entirely), and
    the seminar.py hunk by test_missing_role_is_reported_not_silently_swallowed (a blank role,
    which the old truthiness check passed straight through as a whitespace hint).
    """
    from agora.execution import inspeximus_bridge, seminar

    hints: list[str] = []

    def _fake_can_contribute(role_hint, topic, min_rel=0.22):
        hints.append(role_hint)
        return False, ""

    monkeypatch.setattr(inspeximus_bridge, "agent_can_contribute", _fake_can_contribute)
    monkeypatch.setattr(seminar, "pick_topic", lambda vault: {"id": "x", "headline": "calibration"})
    monkeypatch.setattr(seminar, "log_round", lambda *a, **k: None)
    monkeypatch.setattr(seminar, "_record_attempt", lambda *a, **k: None)

    npcs = [{"npc_id": i, "npc_name": n, "role": r} for i, n, r in NPCS]
    res = seminar._run_group_seminar_inner(npcs, "/vault")

    assert hints == ["adventurer", "artificer"]
    assert "Shadow Kael" not in hints and "Artificer Rooke" not in hints
    assert res["role_missing"] == []


async def test_missing_role_is_reported_not_silently_swallowed(monkeypatch, capsys):
    """Without a role the round still runs, but the degradation is loud and machine-readable."""
    from agora.execution import inspeximus_bridge, seminar

    hints: list[str] = []

    def _fake_can_contribute(role_hint, topic, min_rel=0.22):
        hints.append(role_hint)
        return False, ""

    monkeypatch.setattr(inspeximus_bridge, "agent_can_contribute", _fake_can_contribute)
    monkeypatch.setattr(seminar, "pick_topic", lambda vault: {"id": "x", "headline": "calibration"})
    monkeypatch.setattr(seminar, "log_round", lambda *a, **k: None)
    monkeypatch.setattr(seminar, "_record_attempt", lambda *a, **k: None)
    monkeypatch.setattr(seminar, "_ROLE_WARNED", set())

    npcs = [{"npc_id": "1", "npc_name": "Shadow Kael"},              # role absent
            {"npc_id": "2", "npc_name": "Sage Mira", "role": "  "}]  # role blank
    res = seminar._run_group_seminar_inner(npcs, "/vault")

    assert res["role_missing"] == ["Shadow Kael", "Sage Mira"]
    assert hints == ["Shadow Kael", "Sage Mira"]                     # the fallback still works
    out = capsys.readouterr().out
    assert "DEGRADED" in out and "Shadow Kael" in out and "Sage Mira" in out

    # ...and it warns once per agent, not once per round (a round fires every 20 ticks).
    seminar._run_group_seminar_inner(npcs, "/vault")
    assert "DEGRADED" not in capsys.readouterr().out


@pytest.mark.asyncio
async def test_the_seminar_stays_off_unless_it_is_asked_for(npc_db, monkeypatch):
    """The default-off decision needs cover, because the organ it guards is the biggest spender.

    On 2026-09-04 the seminar was switched off by default: 66% of the brain's metered calls, 3,514
    contributions, none cited downstream. Nothing tested that. A change that flipped the default
    back would have passed every test in this repository, including the one above, which only ever
    ran because it now asks for the organ explicitly.

    So this asserts the pair. The absence half is worthless without the presence half: a tick that
    never runs a seminar under ANY setting would satisfy "off by default" and mean nothing.
    """
    import types

    from agora import main as agora_main
    from agora.execution import seminar

    captured = []
    monkeypatch.setattr(seminar, "run_group_seminar",
                        lambda *a, **k: captured.append(a) or {"ok": True})
    monkeypatch.setattr(agora_main, "random",
                        types.SimpleNamespace(random=lambda: 0.0, choice=lambda seq: seq[0]))

    async def tick_once():
        app = types.SimpleNamespace(state=types.SimpleNamespace(
            db=_FakeDB(npc_db), agent_os=object(), tick_count=20, event_bus=None))
        await agora_main._brain_ecosystem_tick(app)
        spawned = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if spawned:
            await asyncio.wait(spawned, timeout=60)

    monkeypatch.delenv("AGORA_SEMINAR", raising=False)
    await tick_once()
    assert not captured, ("the seminar ran with AGORA_SEMINAR unset. It is the brain's largest "
                          "spender and it is meant to be opt-in.")

    # THE CONTROL. Without this, a tick broken so that it never seminars at all would pass.
    monkeypatch.setenv("AGORA_SEMINAR", "1")
    await tick_once()
    assert captured, ("the seminar did not run with AGORA_SEMINAR=1 either, so the assertion above "
                      "measured a dead tick rather than the default")

