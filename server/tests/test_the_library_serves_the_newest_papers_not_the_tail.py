"""The swarm's only external anchor was served as an insertion-order tail.

`/brain/library` returned `_load()[-12:]`. That is not the newest twelve and not the most relevant
twelve -- it is whichever twelve happen to sit at the end of the file. Measured 2026-08-08: NINE of
the twelve were a stale 2026-07-03 block (image synthesis, closed Reeb orbits, a transverse-field
Ising model) while the store held 205 papers and 161 on-mission ones sat queued unread.

That mattered because the dungeon's `b_paper` bucket reads this endpoint and takes the first six, and
papers are the ONLY source in `_renewable_quests` that is not our own canon fed back to us. The board
gate then passed 1 of those 6, against 8 of 8 for our own findings -- so the swarm's diet was
self-referential by plumbing, not by policy. The supply was never missing; it was unreachable.

Newest-first, and deep enough for the caller to rank.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))

from agora.api import agent_os_api as api  # noqa: E402


class _FakeLoad:
    """A store whose INSERTION order disagrees with its timestamp order -- which is the whole
    defect. A fixture already sorted by ts could not tell the two implementations apart."""

    rows = [
        {"title": "oldest but written last", "ts": 100.0},
        {"title": "newest", "ts": 900.0},
        {"title": "middle", "ts": 500.0},
        {"title": "no timestamp at all", "ts": None},
    ]


@pytest.fixture()
def patched(monkeypatch):
    import agora.execution.library as lib
    monkeypatch.setattr(lib, "_load", lambda: list(_FakeLoad.rows), raising=True)
    monkeypatch.setattr(lib, "format_library", lambda: "report", raising=True)
    return lib


@pytest.mark.asyncio
async def test_papers_are_newest_first(patched):
    out = await api.brain_library()
    got = [p["title"] for p in out["papers"]]
    assert got[:3] == ["newest", "middle", "oldest but written last"], got
    assert "no timestamp at all" in got, "a missing ts must sort last, never be dropped"


@pytest.mark.asyncio
async def test_the_fixture_would_have_fooled_the_old_code(patched):
    """CONTROL. The tail of this store is NOT its newest rows, so a passing test above cannot be
    explained by the fixture happening to already be in order."""
    tail = [r["title"] for r in _FakeLoad.rows][-2:]
    assert tail != ["middle", "newest"], "fixture no longer reproduces insertion != recency"
    out = await api.brain_library()
    assert [p["title"] for p in out["papers"]][:2] != tail


@pytest.mark.asyncio
async def test_depth_is_requestable_and_bounded(patched):
    assert len((await api.brain_library(n=2))["papers"]) == 2
    assert len((await api.brain_library(n=0))["papers"]) == 1      # clamped up, never empty
    assert len((await api.brain_library(n=99999))["papers"]) == len(_FakeLoad.rows)
