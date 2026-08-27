""""Does this claim say what would kill it?" must be one question, asked of the concept.

The press arm refuses a source note that states no falsifier -- correctly, under the raised bar. It
asked with a literal substring test for `"falsifier"`, while the Theory Engine writes
`falsification control: ...`, and "falsifier" is not a substring of "falsification". A note that DID
state its falsifier was refused for not stating one.

Measured 2026-07-31: of the last 40 discoveries, 40 carried a Lab id and 1 was seen to carry a
falsifier. That read as a swarm-wide contract gap -- four of the eight organs never write one -- and
part of it was this detector.

The bar stays a NAMED TEST. A bare "falsifiable" is a claim ABOUT the claim, and letting it through
would empty the gate whose whole job is to demand the test. `falsifiable` cannot match, by
construction: it contains neither "falsifier" nor "falsification".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "server"))

from agora.execution.grounding import has_falsifier  # noqa: E402

#: Wordings taken from live notes, not invented.
STATES_A_FALSIFIER = [
    "- falsification control: shuffle the labels; the signature must vanish",
    "Falsifier, fixed in the lab script before it computed anything: below a 0.50 restatement rate "
    "the model is false and every pair must be adjudicated on its merits",
    "Falsifier: recall must not fall below 0.40 at n=200",
    "This claim is wrong if the null reproduces it",
    "A rerun would refute the claim if the delta vanishes",
    "The finding is refuted if the effect does not survive Bonferroni",
    "We pre-registered a falsifier threshold of 0.30",
    "Falsification test - the control must not reproduce the signature",
]

STATES_NONE = [
    "The result is falsifiable in principle",          # an adjective, not a test
    "This is a falsifiable hypothesis",
    "MEASURED: recall 0.59 VERDICT: HOLDS",            # a measurement is not a kill test
    "VERDICT: no honest bridge (NO BRIDGE)",
    "We ran the lab and it agreed with the claim",
    "",
]


@pytest.mark.parametrize("text", STATES_A_FALSIFIER)
def test_a_stated_falsifier_is_recognised(text):
    assert has_falsifier(text), "refused a note that names its own kill test: %r" % text[:70]


@pytest.mark.parametrize("text", STATES_NONE)
def test_an_assertion_is_not_a_falsifier(text):
    assert not has_falsifier(text), (
        "accepted a claim that never says what would kill it: %r" % text[:70])


def test_the_two_live_wordings_that_motivated_this():
    """The exact pair the old substring test split: one passed, one did not, and both are falsifiers."""
    theory = "- falsification control: shuffle the labels; the signature must vanish"
    desk = "Falsifier, fixed in the lab script before it computed anything: below 0.50 it is false"
    assert has_falsifier(theory) and has_falsifier(desk)
    # the control: the OLD test really did split them, so this suite is not passing vacuously
    old = lambda t: "falsifier" in t.lower()
    assert not old(theory) and old(desk), (
        "the old substring test no longer splits these, so the defect this file records has "
        "changed shape -- re-measure before trusting it")


def test_the_press_arm_uses_the_shared_definition_and_fails_closed():
    src = (REPO / "agora-game-server" / "organs" / "scholar.py").read_text(encoding="utf-8",
                                                                          errors="replace")
    assert "_has_falsifier(note)" in src, "the press arm no longer asks the shared question"
    assert "has_falsifier" in src, "the shared definition is not loaded"
    body = src.split("def _has_falsifier(", 1)[1].split("\ndef ", 1)[0]
    assert "else False" in body, (
        "the press arm must fail CLOSED: if the shared definition cannot be loaded, publishing a "
        "claim whose falsifier nobody checked is worse than publishing nothing")
