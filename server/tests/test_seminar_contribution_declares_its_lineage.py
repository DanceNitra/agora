"""A synthesis must declare what it was synthesised FROM, or the retraction lever has nothing to walk.

Measured on the live shared store 2026-07-31, all 3,228 records:

    derived_from coverage : 0.0000%
    taint        coverage : 0.0000%
    source       coverage : 0.0000%

Every one of those three is a field a retraction resolves on. `slash(scope='source')` -- the DEFAULT
scope, and the operation we describe as the accountability moat -- selects records whose canonical
source intersects the caught source. With `source` at 0.00%, it matched NOTHING on our own deployment.
It returned successfully every time; it simply had no targets. The library was fine. The writer never
filled in the fields.

The cause was two dropped values, both already in hand at the call site. `agent_can_contribute()`
recalled the memories an agent reads to decide it can speak, returned their text, and threw away their
ids. `remember_contribution()` then wrote the synthesis as a fresh primary observation with no parents
and no source. So a Contribution built entirely out of a poisoned memory kept full standing after that
memory was retracted, and nothing in the system could say otherwise.

This is rule 12 in its purest form: a check that never sees its target reports SAFE.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "server"))

Inspeximus = pytest.importorskip("inspeximus").Inspeximus

from agora.execution import inspeximus_bridge as B  # noqa: E402


@pytest.fixture()
def store(monkeypatch):
    st = Inspeximus(path=str(Path(tempfile.mkdtemp()) / "s.json"), embed=None)
    monkeypatch.setattr(B, "_store", st)
    return st


def _two_parents(st):
    a = st.remember("agent memory retrieval degrades when the index is stale",
                    source={"doc": "agent:Sage Mira"})
    b = st.remember("retrieval staleness compounds across consolidation rounds",
                    source={"doc": "agent:High Priest Orin"})
    return a, b


def test_the_recall_actually_finds_the_parents(store):
    """THE CONTROL. Every assertion below is vacuous if the recall returns nothing -- an empty lineage
    and a correctly-declared lineage look identical when there was nothing to declare."""
    _two_parents(store)
    can, ctx, ids = B.agent_can_contribute("Knowledge Curator", "agent memory retrieval staleness")
    assert can and ctx, "the fixture's recall found nothing, so this file tests an empty case"
    assert len(ids) >= 2, "expected the recall to surface both parents, got %d" % len(ids)


def test_can_contribute_returns_the_ids_it_read(store):
    a, b = _two_parents(store)
    _, _, ids = B.agent_can_contribute("Knowledge Curator", "agent memory retrieval staleness")
    assert set(ids) <= {a, b} and ids, "the recalled ids are not the records that were recalled"


def test_a_contribution_carries_declared_lineage_and_a_source(store):
    a, b = _two_parents(store)
    _, _, ids = B.agent_can_contribute("Knowledge Curator", "agent memory retrieval staleness")
    B.remember_contribution("Stale indexes dominate retrieval error", "measured, lab 4b4fbf",
                            tags=["topic"], derived_from=ids, source_doc="seminar:r1")
    rec = [r for r in store.items if "contribution" in (r.get("tags") or [])][0]
    assert rec.get("derived_from"), "the synthesis declares no parents"
    assert rec.get("taint"), "no inherited taint, so a source-scoped retraction cannot reach it"
    assert (rec.get("source") or {}).get("doc") == "seminar:r1"


def test_retracting_a_parent_source_forfeits_the_contribution(store):
    """The whole point. Before the fix this forfeited 0 records."""
    a, b = _two_parents(store)
    _, _, ids = B.agent_can_contribute("Knowledge Curator", "agent memory retrieval staleness")
    B.remember_contribution("Stale indexes dominate retrieval error", "measured, lab 4b4fbf",
                            tags=["topic"], derived_from=ids, source_doc="seminar:r1")
    rec = [r for r in store.items if "contribution" in (r.get("tags") or [])][0]
    store.credit(rec["id"], True, weight=5.0)
    res = store.slash([a], scope="source")
    assert res["slashed"] >= 2, (
        "retracting a parent source forfeited %d records; the contribution built from it survived"
        % res["slashed"])
    after = {r["id"]: r for r in store.items}[rec["id"]]
    assert (after.get("meta") or {}).get("slashed"), "the derived contribution kept its standing"
    assert after["good"] == 0.0


def test_a_contribution_is_not_truncated_at_500_chars(store):
    """The third copy of the 500-char cut found today. A claim severed before its falsifier cannot be
    tested, and 0 of the last 40 discoveries stated one while 984 of 10,437 lifetime did."""
    long_claim = ("Stale indexes dominate retrieval error. " * 30).strip()
    B.remember_contribution(long_claim, "FALSIFIER: fails if staleness explains under 20% of error",
                            tags=["topic"], source_doc="seminar:r2")
    rec = [r for r in store.items if "contribution" in (r.get("tags") or [])][0]
    assert len(rec["text"]) > 500, "still cut at %d chars" % len(rec["text"])
    assert "FALSIFIER" in rec["text"], "the falsifier was cut off the end of the claim"


def test_a_vault_only_contributor_declares_no_false_lineage(store):
    """The backstop path reads vault notes, which are not inspeximus records. Naming them as parents
    would fabricate edges to ids that do not exist -- worse than declaring nothing."""
    can, ctx, ids = B.agent_can_contribute("Curator", "a topic no memory covers at all")
    assert ids == [], "returned parent ids for a path that read no inspeximus records"
