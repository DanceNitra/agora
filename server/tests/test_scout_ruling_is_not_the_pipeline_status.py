"""A ruling and a pipeline stage are two different facts, and one field was carrying both.

`status` on a scout-box record tracks the GATED pipeline -- open -> drafted -> posted -- and a real
fit must stay `open` until the owner approves, because nothing goes outward unapproved. `verdict`
records what Shadow Kael DECIDED, which is finished work the moment he decides it.

They were one field, and that made his ledger incoherent. A `no_fit` was marked and counted as a
decisive outcome. A FIT -- strictly more work, measured against the board, the vault and the
thread's reachability, and grounded by a Lab run -- was left `open` and scored as nothing.

Measured 2026-07-31: 9 box records in the window, every one `open`, and the acceptance gate reported
Shadow Kael with 0 decisive outcomes on the same cycle his contribution LANDED as a grounded
discovery with lab 015ef4. The instrument credited him for finding nothing and not for finding
something.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agora.execution import scout as S  # noqa: E402

URL = "https://github.com/acme/widget/issues/7"


@pytest.fixture()
def box(tmp_path, monkeypatch):
    p = tmp_path / "box.json"
    p.write_text(json.dumps([{"url": URL, "repo": "acme/widget", "issue_number": 7,
                              "kind": "contribute", "status": "open",
                              "found_ts": time.time()}]), encoding="utf-8")
    monkeypatch.setattr(S, "_BOX", p)
    return p


def only(p) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))[0]


def test_a_ruling_does_not_close_the_lead(box):
    """The whole point: the owner's approval gate must still see an OPEN lead."""
    assert S.box_rule(URL, "drafted") is True
    r = only(box)
    assert r["verdict"] == "drafted"
    assert r["status"] == "open", "the ruling closed a lead the owner has not approved"
    assert r["ruled_ts"] > 0


def test_the_ruling_names_its_author(box):
    S.box_rule(URL, "drafted")
    assert only(box)["by"], "an unattributed ruling cannot be credited to anyone"


def test_marking_still_closes_a_lead(box):
    """The control. box_rule must not have become the only way to touch a record."""
    assert S.box_mark(URL, "no_fit") is True
    r = only(box)
    assert r["status"] == "no_fit"
    assert r["closed_ts"] > 0


def test_a_ruling_and_a_close_do_not_overwrite_each_other(box):
    S.box_rule(URL, "drafted")
    S.box_mark(URL, "posted")
    r = only(box)
    assert r["verdict"] == "drafted", "closing the lead erased what the Scout decided"
    assert r["status"] == "posted"


def test_an_empty_verdict_is_refused(box):
    assert S.box_rule(URL, "") is False
    assert "verdict" not in only(box)


def test_an_unknown_url_changes_nothing(box):
    assert S.box_rule("https://example.com/nope", "drafted") is False
    assert "verdict" not in only(box)


def test_the_gate_reads_the_field_this_writes():
    """Pins the two sides together. The gate already lists `verdict` and treats `drafted` as
    decisive; if either list stops matching, a ruling becomes invisible again."""
    src = (Path(__file__).resolve().parents[2] / "probes" / "swarm_health.py"
           ).read_text(encoding="utf-8", errors="replace")
    # Cut at the NEXT ledger key, not at the first "),": that one sits inside verdict_fields and
    # truncated the block to its first line, so the assertions below were reading almost nothing.
    block = src.split('".scout_box.json": dict(', 1)[1].split('\n    ".', 1)[0]
    assert '"verdict"' in block, "the gate no longer reads the verdict field"
    assert '"drafted"' in block, "the gate no longer treats a fit ruling as decisive"
    assert '"ruled_ts"' in block, "the gate reads no timestamp for when the Scout ruled"
