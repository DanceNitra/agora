"""A research direction we paid to choose must be answerable afterwards.

`frontier-seed` is 39.7% of all metered brain spend, 3.47M tokens over 794 calls. Until today a
seed row was {target, kind, ts}: it recorded the choice and nothing about what followed, so the
question "what did that buy" had no field to read. These tests cover the loop that closes it.

The negative cases are the point. A ledger that accepts an outcome for any key will fill with
verdicts attached to nothing and still look healthy, which is the same shape as a guard that
reports SAFE because it never saw its target.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Point the module at a temp ledger, so no test can touch the real one."""
    from agora.execution import frontier as F
    p = tmp_path / ".frontier.json"
    monkeypatch.setattr(F, "_STORE", p)
    return F, p


def test_a_seed_returns_an_id_and_carries_an_empty_outcome(store):
    F, p = store
    sid = F.record_seeded("Physics <-> Linguistics", "hole")
    assert sid, "record_seeded returned nothing, so nothing can ever be written back against it"
    rows = json.loads(p.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["id"] == sid
    assert rows[0]["outcome"] is None, "a fresh pick must be open, not silently counted as answered"


def test_an_outcome_lands_on_the_pick_it_names(store):
    F, _ = store
    a = F.record_seeded("Physics <-> Linguistics", "hole")
    b = F.record_seeded("Finance <-> Psychology", "hole")
    r = F.record_outcome(b, "contribution", "produced one grounded claim")
    assert r["written"] is True
    assert r["id"] == b

    cov = F.outcome_coverage()
    assert cov["seeds"] == 2
    assert cov["closed"] == 1, "the outcome landed on more or fewer picks than the one it named"
    assert cov["coverage_pct"] == 50.0
    # AND IT LANDED ON THE RIGHT ONE. Counting alone would pass if both rows were written.
    rows = json.loads(_store_text(F))
    by = {x["id"]: x for x in rows}
    assert by[b]["outcome"] == "contribution"
    assert by[a]["outcome"] is None


def test_an_unknown_id_is_refused_rather_than_appended(store):
    F, p = store
    F.record_seeded("Physics <-> Linguistics", "hole")
    before = json.loads(p.read_text(encoding="utf-8"))

    r = F.record_outcome("deadbeef00", "contribution")
    assert r["written"] is False
    assert "no seed carries id" in r["why"]

    after = json.loads(p.read_text(encoding="utf-8"))
    assert after == before, ("the ledger grew a row for an id it never issued. A store that accepts "
                             "any key fills with outcomes attached to nothing and still reports "
                             "healthy coverage.")


def test_coverage_is_zero_before_anything_is_answered(store):
    """THE CONTROL. If coverage cannot report 0, a later 50% means nothing."""
    F, _ = store
    F.record_seeded("A <-> B", "hole")
    F.record_seeded("C <-> D", "thin_domain")
    cov = F.outcome_coverage()
    assert cov["seeds"] == 2
    assert cov["closed"] == 0
    assert cov["coverage_pct"] == 0.0
    assert cov["outcomes"] == []


def test_a_revision_keeps_the_first_verdict(store):
    """A later optimistic answer must not erase an earlier honest one."""
    F, _ = store
    sid = F.record_seeded("A <-> B", "hole")
    F.record_outcome(sid, "nothing", "no bridge was findable")
    r = F.record_outcome(sid, "contribution", "revisited a week later")
    assert r["written"] is True
    assert r["revisions"] == 1
    rows = json.loads(_store_text(F))
    assert rows[0]["outcome"] == "contribution"
    assert rows[0]["outcome_first"] == "nothing", "the first verdict was overwritten and lost"


def test_an_empty_outcome_is_refused(store):
    F, _ = store
    sid = F.record_seeded("A <-> B", "hole")
    assert F.record_outcome(sid, "")["written"] is False
    assert F.record_outcome("", "contribution")["written"] is False
    assert F.outcome_coverage()["closed"] == 0


def _store_text(F):
    return F._STORE.read_text(encoding="utf-8")
