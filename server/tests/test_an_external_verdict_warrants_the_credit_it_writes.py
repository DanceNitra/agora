"""A credit that came from OUTSIDE must say so, or the guard against self-grading has no input.

`credit_requires_warrant` is the MINJA defence: an agent must not be able to credit its own recalled
poison as a success and promote it into the influence set. It counts `good_warranted`, which
`credit(..., warrant=X)` raises only when X is exogenous to the record.

Measured 2026-08-09 across this deployment's 220,213 records:

    good              470   0.2134%
    bad               506   0.2298%
    good_warranted      0   0.0000%

So the credit loop was LIVE and every good credit in it was unwarranted. Not because our verdicts are
self-graded — a resolved forecast and a Lab run are as external as we have — but because
`credit_outcome()` had no `warrant` parameter and neither caller could name its artifact. The sixth
instance of one class: the mechanism works given its input, and nothing delivered the input.

These tests pin the INPUT ARRIVING, at both ends: the library really does count our token as
exogenous (a format that collided with the record's own source would silently earn nothing), and our
callers really do pass one. The unwarranted half is not decoration — without it a rubber stamp that
warranted everything would pass just as well, and that is the failure mode worth more than the fix.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPO = Path(r"C:\Users\Danculus\inspeximus-repo")

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
Inspeximus = pytest.importorskip("inspeximus").Inspeximus


def _store(tmp_path):
    return Inspeximus(path=str(tmp_path / "s.json"), embed=None)


def _rec(s, rid):
    """The library exposes records as `.items`; `get()` is the MCP tool name, not the API."""
    return next((r for r in s.items if r.get("id") == rid), {})


# ------------------------------------------------------ the library end: does our token count as exogenous?
def test_a_lab_warrant_on_a_sourced_record_earns_warranted_good(tmp_path):
    """Our records carry source={'doc': ...}. `_warrant_is_exogenous` REFUSES a warrant equal to the
    record's own source, so the token format is load-bearing, not cosmetic."""
    s = _store(tmp_path)
    rid = s.remember("volatility drag is not a free lunch", source={"doc": "crucible/claim-17"})
    s.credit([rid], "good", warrant="lab:9f2c1a")
    rec = _rec(s, rid)
    assert float(rec.get("good", 0)) > 0
    assert float(rec.get("good_warranted", 0)) > 0, "an external Lab run must earn warranted good"


def test_a_prediction_warrant_also_counts(tmp_path):
    s = _store(tmp_path)
    rid = s.remember("agent adoption will rise this quarter", source={"doc": "brain/theme-x"})
    s.credit([rid], "good", warrant="prediction:8a3f1b2c")
    assert float(_rec(s, rid).get("good_warranted", 0)) > 0


def test_an_unwarranted_credit_raises_good_but_never_warranted_good(tmp_path):
    """THE CONTROL. This is the self-graded path (our dungeon quality gate). If this ever earned
    warranted good, `credit_requires_warrant` would be a rubber stamp and the whole field meaningless."""
    s = _store(tmp_path)
    rid = s.remember("an agent grading its own output", source={"doc": "dungeon/thief"})
    s.credit([rid], "good")
    rec = _rec(s, rid)
    assert float(rec.get("good", 0)) > 0, "credit must still register"
    assert float(rec.get("good_warranted", 0) or 0) == 0, "a self-grade must earn NO warranted good"


def test_a_warrant_naming_the_records_own_source_is_not_exogenous(tmp_path):
    """The spoof closest to home: warrant yourself with your own provenance."""
    s = _store(tmp_path)
    rid = s.remember("self-vouching claim", source={"doc": "crucible/claim-17"})
    s.credit([rid], "good", warrant="crucible/claim-17")
    assert float(_rec(s, rid).get("good_warranted", 0) or 0) == 0


# --------------------------------------------------------------- our end: do the callers actually pass one?
class _Spy:
    def __init__(self):
        self.kwargs = None

    def recall(self, q, k=5):
        return [{"id": "m1", "relevance": 0.9}]

    def credit(self, ids, outcome, weight=1.0, warrant=None):
        self.kwargs = {"ids": ids, "outcome": outcome, "warrant": warrant}
        return {"updated": ids}


def _bridge(monkeypatch, spy):
    sys.path.insert(0, str(ROOT / "server"))
    from agora.execution import inspeximus_bridge as br
    monkeypatch.setattr(br, "_inspeximus", lambda: spy)
    return br


def test_credit_outcome_forwards_the_warrant(monkeypatch):
    spy = _Spy()
    br = _bridge(monkeypatch, spy)
    br.credit_outcome("some theme", good=True, warrant="lab:abc123")
    assert spy.kwargs["warrant"] == "lab:abc123", "the bridge dropped the warrant on the floor"


def test_credit_outcome_defaults_to_no_warrant(monkeypatch):
    """Absent an artifact the default must stay None — silently inventing one would be the forgery."""
    spy = _Spy()
    br = _bridge(monkeypatch, spy)
    br.credit_outcome("some theme", good=True)
    assert spy.kwargs["warrant"] is None


def _replication_warrant(monkeypatch, tmp_path, lab_id):
    """Run the REAL replication.record() path and report the warrant it emitted (None if it never
    credited). Re-deriving the f-string here instead would test my arithmetic, not the code."""
    sys.path.insert(0, str(ROOT / "server"))
    from agora.execution import replication as rp
    from agora.execution import inspeximus_bridge as br

    seen = {}
    monkeypatch.setattr(br, "credit_outcome",
                        lambda subject, good, warrant=None, **kw: seen.update(warrant=warrant))
    monkeypatch.setattr(rp, "_save", lambda items: None)
    monkeypatch.setattr(rp, "_load", lambda: [])
    rp.record(claim="a testable claim about drag", source="arxiv:1234.5678",
              outcome="REPRODUCED", lab_id=lab_id, note="n", by="Rooke")
    return seen.get("warrant", "NEVER_CREDITED")


def test_a_replication_with_a_lab_run_warrants_with_it(monkeypatch, tmp_path):
    assert _replication_warrant(monkeypatch, tmp_path, "9f2c1a") == "lab:9f2c1a"


def test_a_replication_without_a_lab_id_is_not_warranted(monkeypatch, tmp_path):
    """The severe-test rule enforced at the warrant: no runnable artifact, nothing to vouch with.
    The paired half of the test above — together they show the lab_id is what decides, not the call."""
    assert _replication_warrant(monkeypatch, tmp_path, "") is None
