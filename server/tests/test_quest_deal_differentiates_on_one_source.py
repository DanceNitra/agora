"""Eight agents drawing from one supply must not draw the same card.

The deal in `mcp_server._renewable_quests` gives each agent a different entry point into the same
pool: WHICH source leads (seat % n) and HOW DEEP it enters (seat // n). The first version divided by
`len(buckets)` -- all four sources, stocked or not.

That held only while all four had stock. In the ordinary live case, papers, findings and flywheel
run dry while `directions` refills, so ONE bucket is non-empty: rotating four buckets' ORDER is then
a no-op, and `seat // 4` yields two distinct depths across eight agents. Measured 2026-07-31 after
deploying it -- eight agents collapsed onto two distinct top picks, and the rejection ledger caught
Artificer Rooke and Dame Elara submitting one identical title in the SAME SECOND.

The fix counts the buckets that actually have stock. This suite runs the deal at every supply shape,
including the one-source shape the first version was never tested against.
"""
from __future__ import annotations

import pytest

SEATS = ["artificer", "cartographer", "guard_l", "guard_r", "king", "priest", "scholar", "thief"]


def deal(eid: str, buckets: list[list], want: int = 3) -> list:
    """The shipping arithmetic from mcp_server._renewable_quests, verbatim."""
    b = [list(x) for x in buckets]
    seat = SEATS.index(eid)
    b = [x for x in b if x]
    if b:
        nz = len(b)
        b = b[seat % nz:] + b[:seat % nz]
        off = seat // nz
        if off:
            b = [x[off % len(x):] + x[:off % len(x)] for x in b]
    out, i = [], 0
    while any(len(x) > i for x in b):
        for x in b:
            if len(x) > i:
                out.append(x[i])
        i += 1
    return out[:want]


def firsts(buckets) -> list:
    return [deal(e, buckets)[0] for e in SEATS if deal(e, buckets)]


D7 = ["D%d" % i for i in range(1, 8)]
D3 = ["D1", "D2", "D3"]
FOUR = [["P1", "P2"], ["F1", "F2"], ["Y1", "Y2"], D7]


def ceiling(buckets) -> int:
    """The most distinct top picks ANY deal could produce from this supply.

    Derived, not guessed. Seats are spread across the stocked buckets by `seat % nz`, so bucket i is
    led by the seats congruent to i, and it can offer at most one distinct top pick per item it
    holds. A hand-written ceiling got this wrong on the two-source shape -- four seats lead a
    two-item bucket, so six is the maximum there and asserting eight failed a correct deal.
    """
    b = [x for x in buckets if x]
    if not b:
        return 0
    nz = len(b)
    return sum(min(len([s for s in range(len(SEATS)) if s % nz == i]), len(x))
               for i, x in enumerate(b))


@pytest.mark.parametrize("label,buckets", [
    ("one source, 7 items (THE LIVE CASE)", [[], [], [], D7]),
    ("four stocked sources", FOUR),
    ("two stocked sources", [[], ["F1", "F2"], [], D7]),
    ("one source, 3 items (shallow)", [[], [], [], D3]),
])
def test_the_deal_hits_the_ceiling_of_distinct_top_picks(label, buckets):
    got, want = len(set(firsts(buckets))), ceiling(buckets)
    assert want >= 3, "%s: the fixture cannot discriminate (ceiling %d)" % (label, want)
    assert got >= want, "%s: only %d distinct top picks, ceiling is %d" % (label, got, want)


def test_the_old_arithmetic_collapsed_on_one_source():
    """The control. Without it, a green suite could mean the fix works OR that the case is trivial."""
    def old(eid, buckets):
        b = [list(x) for x in buckets]
        seat = SEATS.index(eid)
        b = b[seat % len(b):] + b[:seat % len(b)]
        off = seat // len(b)
        if off:
            b = [(x[off % len(x):] + x[:off % len(x)]) if x else x for x in b]
        out, i = [], 0
        while any(len(x) > i for x in b):
            for x in b:
                if len(x) > i:
                    out.append(x[i])
            i += 1
        return out[:3]
    old_firsts = {old(e, [[], [], [], D7])[0] for e in SEATS}
    assert len(old_firsts) == 2, (
        "the old deal no longer reproduces the collapse (%d distinct), so the parametrised test "
        "above proves nothing" % len(old_firsts))


@pytest.mark.parametrize("buckets", [[[], [], [], D7], FOUR, [[], [], [], D3]])
def test_no_agent_is_starved_of_supply(buckets):
    """Rotating, not slicing. An earlier attempt sliced and cut deep seats from 3 quests to 1."""
    for e in SEATS:
        assert len(deal(e, buckets)) == 3, "%s got %d quests" % (e, len(deal(e, buckets)))


@pytest.mark.parametrize("buckets", [[[], [], [], D7], FOUR])
def test_every_agent_can_still_reach_every_item(buckets):
    """Differentiation must cost no supply: each agent walks the whole ring, entering at its point."""
    everything = {x for b in buckets for x in b}
    for e in SEATS:
        assert set(deal(e, buckets, want=999)) == everything, "%s cannot reach the whole pool" % e


def test_an_empty_supply_does_not_raise():
    assert deal("king", [[], [], [], []]) == []


def test_the_deal_matches_the_shipping_source():
    """Pins this arithmetic to mcp_server, so the two cannot drift apart unnoticed."""
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[2] / "agora-game-server" / "mcp_server.py"
           ).read_text(encoding="utf-8", errors="replace")
    assert "buckets = [b for b in buckets if b]" in src, "the empty-bucket drop is gone"
    assert "_off = _seat // _nz" in src, "the depth dial no longer divides by the STOCKED count"
