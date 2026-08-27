"""A negative verdict requires that something was actually looked at.

The Map-maker's bridge test compares the span rate of a JOINT corpus (papers returned for a query
about both domains) against a NULL corpus (papers about each domain alone). Its sample-size floor was
applied only to the null, on the reasoning that the null carries the negative evidence.

That is half the requirement. It asks whether we know the ambient rate; it never asks whether we
looked at the pair at all. With an empty joint corpus every span test is vacuously false and control
falls through to `NO BRIDGE` -- a verdict that reads as a structural finding while meaning only "the
query returned no papers".

Measured 2026-07-31 on a live note that had already landed as a discovery with a lab id attached:

    VERDICT: no honest bridge (NO BRIDGE)
    MEASURED: joint-query span rate 0/0 (n/a) vs single-domain null 0/4 (0.000)

`0/0`. Nothing was examined. Cashing that as a finding is the failure the repo's own rule names --
never cash an "I could not find" as novelty -- and it is the same shape as a guard that reports safe
on input it never received.

These cases replay the shipped decision on synthetic counts, so the boundary is pinned without
needing a live literature search.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "agora-game-server"))

import organs.cartographer as C  # noqa: E402

MIN_PAPERS = 3


def verdict(n_joint: int, n_null: int, joint_spans: int, null_spans: int) -> str:
    """The shipped decision, replayed. Mirrors the branch order in the Lab script exactly."""
    rate_j = (joint_spans / n_joint) if n_joint else 0.0
    rate_n = (null_spans / n_null) if n_null else 0.0
    if n_null < MIN_PAPERS:
        return "INCONCLUSIVE"
    if n_joint == 0:
        return "INCONCLUSIVE"
    if null_spans and rate_n >= rate_j:
        return "ALREADY BRIDGED"
    if joint_spans and rate_j > rate_n:
        return "BRIDGE"
    return "NO BRIDGE"


@pytest.mark.parametrize("counts,expected,why", [
    ((0, 4, 0, 0), "INCONCLUSIVE", "the live note: empty joint corpus, nothing examined"),
    ((0, 9, 0, 1), "INCONCLUSIVE", "empty joint even with plenty of null"),
    ((6, 2, 0, 0), "INCONCLUSIVE", "null below the sample-size floor"),
    ((6, 6, 0, 0), "NO BRIDGE", "six joint papers examined, none spans -- a REAL negative"),
    ((6, 6, 3, 0), "BRIDGE", "joint spans beat an ambient rate of zero"),
    ((6, 6, 1, 4), "ALREADY BRIDGED", "ambient rate at or above the joint rate"),
])
def test_the_verdict_boundary(counts, expected, why):
    assert verdict(*counts) == expected, why


def test_an_empty_joint_corpus_can_never_be_a_negative_finding():
    """The claim in one line: no amount of null evidence licenses NO BRIDGE if nothing was examined."""
    for n_null in (3, 10, 50):
        for null_spans in range(0, min(n_null, 4)):
            assert verdict(0, n_null, 0, null_spans) == "INCONCLUSIVE", (
                "NO BRIDGE issued with an empty joint corpus (null %d/%d)" % (null_spans, n_null))


def test_a_real_negative_still_gets_through():
    """The control. A guard widened until nothing can be negative would pass everything above and
    silently remove the organ's ability to say no -- which is the whole point of this organ."""
    assert verdict(6, 6, 0, 0) == "NO BRIDGE"
    assert verdict(20, 20, 0, 0) == "NO BRIDGE"


def test_the_guard_is_in_the_shipped_script():
    """Pins this file to the code it replays: the branch must exist, and BEFORE the span tests."""
    src = next(v for v in vars(C).values()
               if isinstance(v, str) and "joint-query span rate" in v)
    assert "elif nj == 0:" in src, "the empty-joint guard is gone from the Lab script"
    assert src.index("elif nj == 0:") < src.index("elif ns and rate_n"), (
        "the guard sits after the span tests, so an empty corpus reaches them first")
