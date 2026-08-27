"""A refusal that is not recorded cannot be learned from.

The brain refused writes through six gates and kept only counters, never the title. That is why the 19
research directions re-seeded forever: a direction is a QUESTION, the vault holds ANSWERS, and the
findings that would prove a direction exhausted were rejected -- so absent from collective_knowledge
too. The evidence existed only in a dungeon log line. Measured 2026-07-31: 67 write attempts in ten
minutes, 51 refused as "vault already covers this", across 10 distinct titles.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agora.api import agent_os_api as api                            # noqa: E402


def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "_REJECTED_FILE", tmp_path / ".rejected_writes.json")
    api._DIR_COVER_CACHE.update(ts=0, cov={})


def test_a_refusal_is_recorded_with_its_reason(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    api._record_rejection("Sergeant Voss", "Does X hold under Y", "vault already covers this")
    assert api._rejected_titles() == ["Does X hold under Y"]


def test_recording_never_raises(tmp_path, monkeypatch):
    """Losing the ledger must not fail the request that was being refused."""
    monkeypatch.setattr(api, "_REJECTED_FILE", tmp_path / "no" / "such" / "dir" / "x.json")
    api._record_rejection("a", "b", "c")            # must not raise
    assert api._rejected_titles() == []


def test_a_direction_refused_twice_is_withheld(tmp_path, monkeypatch):
    """THE regression. Two refusals on the same ground mark a direction exhausted; one does not, because
    a single refusal can be a near-miss rather than a saturated theme."""
    import asyncio
    _fresh(tmp_path, monkeypatch)
    d = "How should a memory system write-acceptance conservatism scale with n"
    other = "Is there an interior optimal retrieval depth k in memory recall"

    api._record_rejection("Voss", d, "vault already covers this")
    cov = asyncio.run(api._direction_coverage(None, [d, other]))
    assert cov[d] is False, "one refusal must not retire a direction"

    api._DIR_COVER_CACHE.update(ts=0, cov={})
    api._record_rejection("Elara", d, "vault already covers this")
    cov = asyncio.run(api._direction_coverage(None, [d, other]))
    assert cov[d] is True, "two refusals on the same direction must retire it"
    assert cov[other] is False, "an untried direction must stay on offer"
