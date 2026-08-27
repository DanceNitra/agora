"""The six grounding detectors must give ONE answer per citation form.

On 2026-07-31 this repo held six independent answers to "does this text carry a citation", disagreeing
on 8 of 9 forms. The two author-year regexes were mirror images: `quality_gate._CITES` required the name
INSIDE the parentheses, `finding_diversity._CITE` required it OUTSIDE. Measured over the 4,000 most
recent discoveries, the vault door passed 2,514 (62.9%) and turned away 1,127 (28.2%) that were carrying
a real narrative citation -- "Cameron et al. (2022)", "Lemos (2010)". Silently: a rejection leaves no
trace, so nobody could see it.

These tests pin every consumer to one table. They exist because the fix is not "the regexes agree today"
-- it is "they cannot drift apart again without a red test".
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agora.execution import grounding                              # noqa: E402
from agora.execution.finding_diversity import _source              # noqa: E402
from agora.execution.quality_gate import _real_grounding           # noqa: E402

#: (form, text, is_cited, is_measured, is_internal_ref). The table the whole repo now agrees on.
FORMS = [
    ("parenthetical author-year", "Shown in (Smith, 2024).",              True,  False, False),
    ("narrative author-year",     "As Smith (2024) showed.",              True,  False, False),
    ("narrative et al.",          "Holds, Breznau et al. (2022).",        True,  False, False),
    ("parenthetical et al.",      "Holds (Breznau et al., 2022).",        True,  False, False),
    ("two authors",               "Per Dame & Thaddeus (2003) the arm.",  True,  False, False),
    ("doi",                       "Confirmed doi:10.1234/abc.",           True,  False, False),
    ("arxiv",                     "See arXiv:2404.12967.",                True,  False, False),
    ("url",                       "See https://example.org/paper",        True,  False, False),
    ("vault link",                "Extends [[a vault note]].",            False, False, True),
    ("bare et al., no year",      "As Smith et al. showed.",              False, False, False),
    ("measured/verdict",          "MEASURED: 0.42 VERDICT: FAILED",       False, True,  False),
    ("lab receipt",               "settled by lab a1b2c3.",               False, True,  False),
    ("bare prose",                "The mechanism generalises.",           False, False, False),
]


@pytest.mark.parametrize("form,text,cited,measured,internal", FORMS)
def test_the_primitives_match_the_table(form, text, cited, measured, internal):
    assert grounding.is_cited(text) is cited, form
    assert grounding.is_measured(text) is measured, form
    assert grounding.is_internal_ref(text) is internal, form


@pytest.mark.parametrize("form,text,cited,measured,internal", FORMS)
def test_the_vault_door_agrees_with_the_primitives(form, text, cited, measured, internal):
    """quality_gate is the door into the owner's vault: external citation OR our own measurement.
    An internal [[vault note]] is NOT external evidence and must not open it."""
    assert _real_grounding(text) is (cited or measured), form


@pytest.mark.parametrize("form,text,cited,measured,internal", FORMS)
def test_the_source_extractor_agrees_with_the_detector(form, text, cited, measured, internal):
    """finding_diversity extracts the source STRING for concentration metrics. It must find a source
    exactly when the shared detector says one is there -- these were the two mirror-image regexes."""
    assert (_source(text) is not None) is cited, form


def test_both_author_year_orders_are_accepted():
    """THE regression. `Smith (2024)` and `(Smith, 2024)` are both standard and each detector used to
    reject the other's form. 28.2% of 4,000 discoveries died on this."""
    assert _real_grounding("As Smith (2024) showed.")
    assert _real_grounding("Shown in (Smith, 2024).")
    assert _source("As Smith (2024) showed.")
    assert _source("Shown in (Smith, 2024).")


def test_an_internal_link_is_checkable_but_not_external_evidence():
    """The one place the consumers legitimately differ. Flattening this would let a note citing another
    note pass as grounded research."""
    t = "Extends [[a vault note]]."
    assert grounding.is_grounded(t) is False
    assert grounding.is_grounded(t, allow_internal=True) is True


def test_a_bare_et_al_with_no_year_is_not_a_source():
    """seminar._SOURCE_RE used to match this. There is nothing to look up, so it cannot be a checkable
    source. Tightening, and deliberate."""
    assert grounding.is_grounded("As Smith et al. showed.", allow_internal=True) is False


def test_no_second_definition_has_reappeared():
    """THE FALSIFICATION CONTROL, and the only test here that can catch the defect COMING BACK rather
    than being present. Six detectors drifted apart over months precisely because each new one looked
    reasonable in isolation. Any module that compiles its own author-year regex is a seventh."""
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[1] / "agora"
    own = re.compile(r"""re\.compile\([^)]*(?:\\\(|\()\s*\[A-Z\]""")
    offenders = []
    for p in root.rglob("*.py"):
        if p.name == "grounding.py":
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        for m in own.finditer(txt):
            line = txt[:m.start()].count("\n") + 1
            offenders.append("%s:%d" % (p.relative_to(root), line))
    assert not offenders, (
        "a private author-year citation regex reappeared outside grounding.py: %s. "
        "Delegate to agora.execution.grounding instead -- six of these drifted apart once already."
        % offenders)
