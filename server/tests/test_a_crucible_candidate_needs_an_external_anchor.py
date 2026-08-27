"""The Crucible replicates EXTERNAL claims, so a candidate must name something outside us.

What happened. A frontier-seeded quest carries `research_source='frontier:<organ>'` -- a LABEL,
deliberately not a fetchable URL. `_file_ship_review` printed that label into the task as
`SOURCE: frontier:flywheel` and filed the lead as a Crucible candidate, which instructs Claude to
replicate the claim and record REPRODUCED/FAILED. But there was no claim: the research text under
those leads asserted studies that do not exist, e.g. "increasing interlinking in the Wikipedia
Corpus by 10% ... retention improved by 12%, recall decreased by 3%", which returns nothing on any
search. Measured 2026-08-04 on the live queue: 19 of 21 pending Crucible candidates carried
`frontier:flywheel`, and the only two carrying a real anchor (an arXiv URL and a DOI) were the only
two real ones.

Why the existing guards could not catch it. `is_refusal` catches a research step that found nothing
and said so. These are the opposite failure: a confident INVENTION, fluent and specific, which
`is_refusal` correctly passes. `_lead_saturated` catches repetition, and these were varied enough to
slip it. So the discriminator has to be the anchor itself, which is why it is asserted here.

The fixture is the real queue's two shapes, and the controls exist so this file cannot pass
vacuously: a guard that accepted everything would still "pass" a test that only fed it good input,
and a guard that rejected everything would still "pass" one that only fed it bad input.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agora.dungeon_os.agent_worker import _EXTERNAL_ANCHOR  # noqa: E402

# Verbatim from the live queue on 2026-08-04.
REAL_ANCHORS = [
    "paper:http://arxiv.org/abs/1604.05490v1",
    "paper:https://doi.org/10.1103/physreve.91.042122",
]
ORGAN_LABELS = [
    "frontier:flywheel",
    "frontier:contradiction",
    "frontier:frontier",
]


@pytest.mark.parametrize("src", REAL_ANCHORS)
def test_a_real_external_anchor_is_accepted(src):
    assert _EXTERNAL_ANCHOR.search(src), (
        f"{src!r} names a paper outside this organisation; refusing it would send every genuine "
        f"replication candidate down the dossier path and empty the Crucible")


@pytest.mark.parametrize("src", ORGAN_LABELS)
def test_our_own_organ_label_is_not_a_source(src):
    assert not _EXTERNAL_ANCHOR.search(src), (
        f"{src!r} is provenance, not a citation. Accepting it is what filed 19 of 21 Crucible "
        f"candidates asking Claude to replicate claims that were never made")


@pytest.mark.parametrize("src", ["", "doi", "n/a", "C:/Users/x/notes/finding.md", "findings_path"])
def test_nothing_else_sneaks_through_as_an_anchor(src):
    assert not _EXTERNAL_ANCHOR.search(src), (
        f"{src!r} is not fetchable, so nobody can check the claim it is supposed to support")


def test_the_control_a_bare_doi_still_counts():
    """A DOI without a URL around it is still an external anchor; requiring `http` would reject it."""
    assert _EXTERNAL_ANCHOR.search("10.1038/nrg2825")


def test_the_control_this_fixture_still_separates_the_two_populations():
    """The point of the guard is DISCRIMINATION, not a verdict on either population alone.

    If a future edit made the pattern accept everything or reject everything, every test above could
    still be made to pass by adjusting inputs. This one fails in both directions."""
    accepted = [s for s in REAL_ANCHORS + ORGAN_LABELS if _EXTERNAL_ANCHOR.search(s)]
    assert accepted == REAL_ANCHORS, (
        f"the guard no longer separates real anchors from organ labels; it accepted {accepted}")


def test_the_guard_is_actually_wired_into_the_crucible_door():
    """A correct pattern that nothing calls would leave the defect live and this suite green."""
    import inspect

    from agora.dungeon_os.agent_worker import CorporationWorker

    src = inspect.getsource(CorporationWorker._file_ship_review)
    assert "_EXTERNAL_ANCHOR" in src, (
        "the anchor requirement is not applied on the path that files Crucible candidates")
    assert "_file_research_dossier" in src, (
        "an unanchored lead must be re-routed to the dossier door, not silently dropped -- the "
        "research behind it is still worth judging, it just is not a replication target")
    assert re.search(r"if not _EXTERNAL_ANCHOR\.search\(src\)", src), (
        "the check must gate on the ABSENCE of an anchor; an inverted test would file exactly the "
        "wrong population")
