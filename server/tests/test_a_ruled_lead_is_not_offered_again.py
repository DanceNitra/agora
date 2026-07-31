"""A selector must not hand out work that has already been done.

A scout lead ruled a FIT keeps `status: open` by design -- the owner's approval gate owns it from
there, and closing it would hide it from the gated pipeline. But the box endpoint offered every
`open` lead, so a ruled one came back on the next cycle and the one after.

Measured 2026-07-31: Shadow Kael re-ruled fmind-ai/fgentic#333 on four consecutive cycles, each with
a fresh Lab run, and every resulting contribution was refused at the vault door as a duplicate of the
one before. Four cycles of real compute producing nothing that could land, while two other unruled
leads sat in the same box untouched.

This is the third instance of one shape today. `pick_untested_bridges` re-offered its oldest eight
charts to a caller allowed to refuse them, forever. `belief-challenge-target` returned a single head
and wedged the challenge sweep for 42 days. A selector that cannot advance past work already done is
not a queue, it is a loop.

The fix separates the two questions the record was answering with one field: `verdict` is what the
Scout decided, `status` is where the gated pipeline stands. The box offers leads with no verdict, and
REPORTS how many ruled-but-open leads it is holding rather than dropping them silently.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "server"))

from agora.api import agent_os_api as A  # noqa: E402


def endpoint_src() -> str:
    return inspect.getsource(A.brain_scout_box)


def test_the_box_filters_on_the_verdict_not_only_the_status():
    src = endpoint_src()
    assert 'not x.get("verdict")' in src, (
        "the box still offers leads the Scout has already ruled, so the same lead returns every "
        "cycle and every contribution built from it is refused as a duplicate")


def test_a_ruled_lead_is_still_open_for_the_owner():
    """The guard against over-correcting: a fit MUST stay `open`. Closing it would hide it from the
    gated pipeline, which is the only thing that can act on it."""
    from agora.execution import scout as S
    src = inspect.getsource(S.box_rule)
    assert '"status"' not in src.split("def box_rule", 1)[1].split("return", 1)[0] or \
           "x[\"status\"]" not in src, "box_rule must not touch status"


def test_the_holding_count_is_reported():
    """Silent filtering is how a lead disappears. The endpoint must say what it is holding back."""
    assert "ruled_open" in endpoint_src(), (
        "the box drops ruled leads from its answer without saying how many -- a filtered lead and a "
        "lead that was never found look identical from outside")


def test_the_filter_is_by_verdict_alone():
    """`status` is the pipeline's field; using it here would re-conflate the two facts that were
    just separated."""
    src = endpoint_src()
    body = src.split("unruled = ", 1)[1].split("\n", 1)[0]
    assert 'x.get("status") == "open"' in body and 'not x.get("verdict")' in body, (
        "the selector's condition changed shape: %s" % body.strip())


def test_the_live_box_would_advance():
    """On the real store: at least one lead with no verdict must remain offerable, or the Scout has
    nothing to walk to and this fix would trade a loop for a stall."""
    import json
    p = REPO / "server" / ".scout_box.json"
    if not p.exists():
        import pytest
        pytest.skip("no scout box on this machine")
    items = json.loads(p.read_text(encoding="utf-8"))
    items = items if isinstance(items, list) else (items.get("items") or [])
    open_ = [x for x in items if isinstance(x, dict) and x.get("status") == "open"]
    if not open_:
        import pytest
        pytest.skip("no open leads right now")
    unruled = [x for x in open_ if not x.get("verdict")]
    assert unruled, ("every open lead already carries a verdict, so the Scout would stall rather "
                     "than loop -- the box needs a fresh scan, not a different selector")
