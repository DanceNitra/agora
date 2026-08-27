"""A format string that exists in exactly one place identifies every record carrying it.

King Aldric's forecasts were banked under the endpoint's default author, because
`/brain/predict-record` never threaded `by` into `record_prediction`. Three of his calls sat in a
242-record ledger labelled `claude`, indistinguishable from the /loop path's own forecasts -- and
`claude` legitimately writes there, on themes drawn from the same board vocabulary, so no amount of
theme-and-metric matching settles it. Circumstantial evidence was enough for one record (the endpoint
had echoed its id back in the session) and not for the other two.

What settled it was the organ's own prose. `organs/king.py` builds its reason from a fixed template:

    "Poisson null, rate14=%d, lambda=%s vs threshold %s; confidence IS the model's P(%s)"

That string is written at ONE place in the entire codebase, and exactly 3 of the 242 records carry
it -- the one already confirmed his and the two in question. The other 35 `claude` records read like
prose a person wrote ("Local inference is in a strong growth phase...", "MCP is in hypergrowth..."),
a different kind of text entirely. A generated format is a signature: it cannot be produced by any
path that does not run that line.

This file pins the evidence rather than the conclusion, so the same reasoning is available the next
time a record's author is in doubt: if the template stops being unique, or stops being what the organ
writes, the inference it supported is no longer sound and should not be repeated.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
KING = REPO / "agora-game-server" / "organs" / "king.py"
LEDGER = REPO / "server" / ".predictions.json"

#: The generated reason, as a pattern over what it produces rather than over the format string.
TEMPLATE = re.compile(
    r"Poisson null, rate14=\d+, lambda=[\d.]+ vs threshold [\d.]+; confidence IS the model")


def _records() -> list:
    if not LEDGER.exists():
        return []
    d = json.loads(LEDGER.read_text(encoding="utf-8"))
    return d if isinstance(d, list) else (d.get("items") or [])


def test_the_template_is_written_in_exactly_one_place():
    """THE LOAD-BEARING CLAIM. If a second site starts emitting it, the string stops identifying a
    writer and every attribution drawn from it becomes unsound."""
    src = KING.read_text(encoding="utf-8", errors="replace")
    assert src.count("Poisson null, rate14=") == 1, (
        "the reason template now appears %d times in king.py alone" % src.count("Poisson null, rate14="))
    hits = []
    for p in (REPO / "server" / "agora").rglob("*.py"):
        if "Poisson null, rate14=" in p.read_text(encoding="utf-8", errors="replace"):
            hits.append(p.name)
    for p in (REPO / "agora-game-server" / "organs").glob("*.py"):
        if p != KING and "Poisson null, rate14=" in p.read_text(encoding="utf-8", errors="replace"):
            hits.append(p.name)
    assert not hits, "the template is no longer unique to king.py; also in %s" % hits


def test_the_organ_still_writes_it():
    """THE FIXTURE CONTROL. A unique string nothing emits identifies nothing."""
    src = KING.read_text(encoding="utf-8", errors="replace")
    assert "confidence IS the model's" in src, (
        "king.py no longer builds this reason, so the signature is stale and cannot support an "
        "attribution made from it")


def test_every_record_carrying_it_is_attributed_to_the_organ():
    """The repair this evidence supported, pinned. Records written by that line are King Aldric's."""
    recs = _records()
    if not recs:
        pytest.skip("no prediction ledger on this machine")
    carrying = [r for r in recs if TEMPLATE.search(str(r.get("why") or ""))]
    assert carrying, ("no record carries the organ template -- the ledger may have rotated past them; "
                      "re-measure before trusting the attribution reasoning in this file")
    wrong = [(r.get("id"), r.get("by")) for r in carrying if r.get("by") != "King Aldric"]
    assert not wrong, (
        "records written by king.py:772 are attributed to somebody else: %s -- the endpoint may have "
        "stopped threading `by` again" % wrong)


def test_the_other_authors_write_a_different_kind_of_reason():
    """THE FALSIFICATION CONTROL. If `claude` started emitting the same shape, the signature would no
    longer separate them and this file would be asserting on a coincidence."""
    recs = _records()
    if not recs:
        pytest.skip("no prediction ledger on this machine")
    others = [r for r in recs if r.get("by") not in ("King Aldric", None)
              and not TEMPLATE.search(str(r.get("why") or ""))]
    assert len(others) >= 10, (
        "only %d records by other authors lack the template; too few to show the signature actually "
        "discriminates" % len(others))
