"""A refill that fails must leave the tank where it was.

`/brain/directions` re-synthesises research directions from recent findings and stores them in the
module-global `_DIRECTIONS`. It assigned unconditionally, so ONE failed LLM call replaced the stored
directions with nothing -- and `current_directions` serves `frontier + _DIRECTIONS["directions"]`,
so the harvested half of the swarm's research supply vanished until some later call happened to
succeed.

Measured 2026-07-31 during an account-wide Ollama Cloud outage ("you have reached your weekly usage
limit" -- 429 on cheap, main and reasoning alike): the harvest returned 0 themes and 0 directions
from 14 real findings. The stored half was empty and 19 durable frontier directions were carrying
the whole swarm on their own.

The failure mode is exactly the one a research organism cannot afford: the outage that stops you
refilling also empties what you had.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agora.api import agent_os_api as A  # noqa: E402


class _Cur:
    def __init__(self, rows): self._rows = rows
    async def fetchall(self): return self._rows


class _DB:
    def __init__(self, rows): self._rows = rows
    async def execute(self, *_a, **_k): return _Cur(self._rows)


class _Req:
    def __init__(self, rows):
        self.app = type("App", (), {"state": type("S", (), {"db": _DB(rows)})()})()


FINDINGS = [{"content": "MEASURED: recall falls 12%% past 4k records (lab a1b2c3)"} for _ in range(3)]
STORED = {"directions": [{"title": "an existing direction", "why": "it was harvested earlier"}],
          "themes": ["memory integrity"], "ts": 1.0}
FRESH = {"directions": [{"title": "a newly harvested direction", "why": "new"}],
         "themes": ["freshly harvested"], "insight": "something"}


@pytest.fixture()
def restore():
    before = A._DIRECTIONS
    yield
    A._DIRECTIONS = before


async def _call(monkeypatch, harvest_result, stored):
    A._DIRECTIONS = dict(stored)

    async def _fake(_findings):
        return harvest_result

    monkeypatch.setattr("agora.execution.harvest.synthesize_directions", _fake)
    return await A.brain_directions(_Req(FINDINGS))


@pytest.mark.asyncio
async def test_an_empty_harvest_does_not_erase_the_store(monkeypatch, restore):
    out = await _call(monkeypatch, {"directions": [], "themes": [], "insight": ""}, STORED)
    assert A._DIRECTIONS["directions"] == STORED["directions"], "the failed refill emptied the tank"
    assert out.get("harvest_empty") is True
    assert out.get("kept_previous") == 1


@pytest.mark.asyncio
async def test_the_outage_is_reported_not_hidden(monkeypatch, restore):
    """Silent starvation is the thing this repo keeps finding. The caller must be able to see it."""
    out = await _call(monkeypatch, {"directions": [], "themes": [], "insight": ""}, STORED)
    assert "kept" in (out.get("note") or "").lower()


@pytest.mark.asyncio
async def test_a_real_harvest_still_replaces_the_store(monkeypatch, restore):
    """The control. A guard that never lets anything through would pass the test above and freeze
    the supply forever."""
    out = await _call(monkeypatch, FRESH, STORED)
    assert A._DIRECTIONS["directions"] == FRESH["directions"], "a good harvest failed to land"
    assert not out.get("harvest_empty")


@pytest.mark.asyncio
async def test_themes_alone_are_enough_to_count_as_a_harvest(monkeypatch, restore):
    """A cycle can legitimately surface themes without a new direction; that is not a failure."""
    await _call(monkeypatch, {"directions": [], "themes": ["a real theme"], "insight": "x"}, STORED)
    assert A._DIRECTIONS["themes"] == ["a real theme"]


@pytest.mark.asyncio
async def test_an_empty_harvest_onto_an_empty_store_reports_zero(monkeypatch, restore):
    out = await _call(monkeypatch, {"directions": [], "themes": []}, {"directions": [], "themes": []})
    assert out.get("kept_previous") == 0
    assert out.get("harvest_empty") is True
