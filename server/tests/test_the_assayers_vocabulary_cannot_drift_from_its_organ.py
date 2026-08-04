"""The reader's vocabulary for the Folklore Assayer must stay tied to the organ's own declaration.

`repair_ledger._DECISIVE` copies each organ's outcome words by hand, on purpose: the module is read
by the reporting path and importing every organ into it would be a dependency knot. The cost of
copying is drift. A verdict added to `folklore.py` and not added here does not raise anything -- it
reads as inconclusive, and the organ's owner is then reported to the owner as producing nothing.
That is the failure this whole registry exists for, and it has already hit Wren, Orin, Elara and
Kael. These tests turn the copy into something that fails when the original moves.

`.folklore.json` had no entry at all until 2026-08-04, so its single HARMFUL ruling read as
inconclusive.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agora.execution import folklore  # noqa: E402
from agora.execution import repair_ledger as rl  # noqa: E402

STORE = ".folklore.json"


def test_the_decisive_words_are_the_organs_own_forecastable_verdicts():
    """Not 'a sensible set' -- literally what the assayer declares it can rule."""
    assert set(rl._DECISIVE[STORE]) == {v.lower() for v in folklore.FORECASTABLE}, (
        "the reader's vocabulary has drifted from folklore.FORECASTABLE; a verdict the assayer can "
        "reach that is missing here reads as inconclusive and erases the ruling")


def test_the_honest_cell_is_not_counted_as_a_ruling():
    """folklore.py: 'A VERDICT THAT CANNOT SAY I DO NOT KNOW IS DECORATION.'"""
    assert folklore.INCONCLUSIVE.lower() in rl._INCONCLUSIVE[STORE]
    assert folklore.INCONCLUSIVE.lower() not in rl._DECISIVE[STORE], (
        "counting INCONCLUSIVE as decisive makes the organ unable to score below 100%, at which "
        "point the number measures nothing")


def test_every_verdict_the_organ_can_write_is_classified_somewhere():
    """The coverage assertion. An unclassified verdict is invisible, not an error."""
    known = set(rl._DECISIVE[STORE]) | set(rl._INCONCLUSIVE[STORE]) | set(rl._INCONCLUSIVE_ANY)
    unclassified = sorted(v for v in folklore.VERDICTS if v.lower() not in known)
    assert unclassified == [], (
        f"{unclassified} can be written by the assayer and match nothing the reader knows")


@pytest.mark.parametrize("verdict", [v for v in folklore.FORECASTABLE])
def test_a_real_ruling_reads_as_decisive(verdict):
    """The positive control, one per verdict, so no single word carries the suite."""
    rec = {"id": "x", "verdict": verdict, "status": "resolved", "by": "king"}
    assert rl._is_decisive(rec, STORE), f"a {verdict} ruling still reads as no ruling at all"


def test_the_honest_cell_reads_as_undecided():
    rec = {"id": "x", "verdict": folklore.INCONCLUSIVE, "status": "resolved", "by": "king"}
    assert not rl._is_decisive(rec, STORE)


def test_the_negative_control_an_unruled_record_is_not_talked_into_counting():
    """Without this, a vocabulary that matched everything would pass every test above."""
    for rec in ({"id": "x", "status": "open", "by": "king"},
                {"id": "x", "status": "pending", "by": "king"},
                {"id": "x", "verdict": "", "status": "queued", "by": "king"}):
        assert not rl._is_decisive(rec, STORE), f"{rec} reached no verdict but reads as decisive"


def test_the_other_reader_has_the_same_vocabulary():
    """There are TWO independent classifiers for the same ledger and fixing one leaves the other
    blind. `probes/swarm_health.py` carries its own per-ledger spec; on 2026-08-04 it listed three
    of the four forecastable verdicts, having never been updated when HARMFUL was added."""
    import re

    gate = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "probes", "swarm_health.py")
    if not os.path.exists(gate):
        pytest.skip("swarm_health.py not present")
    src = open(gate, encoding="utf-8", errors="replace").read()
    block = re.search(r'"\.folklore\.json": dict\((.*?)\n    \),', src, re.S)
    assert block, "the folklore spec is gone from swarm_health.py"
    words = re.search(r"decisive=\(([^)]*)\)", block.group(1))
    got = {t.strip().strip("\"'").lower() for t in words.group(1).split(",") if t.strip()}
    assert got == {v.lower() for v in folklore.FORECASTABLE}, (
        f"swarm_health.py's folklore vocabulary is {sorted(got)} but the organ declares "
        f"{sorted(v.lower() for v in folklore.FORECASTABLE)}; the difference vanishes from the "
        f"agent's row rather than failing")


def test_the_live_store_is_actually_read_now():
    """The registry can be right in the abstract and still miss the file it is pointed at."""
    import json

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "server", ".folklore.json")
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), ".folklore.json")
    if not os.path.exists(path):
        pytest.skip("no local folklore ledger")
    recs = json.load(open(path, encoding="utf-8"))
    recs = recs if isinstance(recs, list) else (recs.get("records") or recs.get("items") or [])
    ruled = [r for r in recs if isinstance(r, dict) and r.get("verdict")
             and r["verdict"].upper() != folklore.INCONCLUSIVE]
    if not ruled:
        pytest.skip("the assayer has not ruled on anything yet")
    assert all(rl._is_decisive(r, STORE) for r in ruled), (
        "a ruling sitting in the live ledger right now still reads as inconclusive")
