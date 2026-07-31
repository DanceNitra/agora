"""A search that ends against its own bracket has not measured anything.

The cascade-window instrument bisects for the mean degree at which global cascades stop. Its bracket
was a fixed [4.0, 9.0], calibrated at phi=0.18 where z_c is 5.76. The window MOVES with the
threshold: at phi=0.10 the analytic z_c is 13.66, outside the bracket entirely.

Run at phi=0.10 it reported:

    MEASURED cascade_window_upper = 8.9805
    SE = 0.0000
    runs = [8.98, 8.98, 8.98, 8.98, 8.98]

8.98 is the bracket's upper bound. Five identical answers and SE exactly zero are the signature of a
boundary, not of a measurement -- and a -34% "bias" against the canonical value would have been
reported as a FAILED verdict about somebody's claim. That is an instrument error wearing a verdict's
clothes, which this organ's contract explicitly forbids.

Two things follow, and both are tested here. The bracket must be derived from phi rather than fixed;
vulnerable degrees run to 1/phi, so the window cannot sit far above that. And when a run still ends
against either edge, it must report `SE = -1` -- this file's existing convention for "the instrument
could not resolve the quantity" -- instead of returning the edge as if it were an answer.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "agora-game-server"))

from organs.artificer import _LTM_CODE, _inst_ltm  # noqa: E402


def analytic_zc(phi: float) -> float:
    def pois(k, z):
        return math.exp(-z + k * math.log(z) - math.lgamma(k + 1)) if z > 0 else (1.0 if k == 0 else 0.0)
    def g(z):
        return sum(k * (k - 1) * pois(k, z) for k in range(0, int(1.0 / phi) + 1)) - z
    lo, hi = 1.5, 60.0
    for _ in range(300):
        mid = (lo + hi) / 2
        if g(lo) * g(mid) <= 0: hi = mid
        else: lo = mid
    return (lo + hi) / 2


def test_the_window_really_does_move_with_phi():
    """The premise. If z_c were phi-independent a fixed bracket would be fine and this file moot."""
    assert abs(analytic_zc(0.18) - 5.7647) < 0.01
    assert abs(analytic_zc(0.10) - 13.6593) < 0.01
    assert analytic_zc(0.10) > 9.0, "the old fixed bracket [4, 9] would not contain it"


def test_the_bracket_is_derived_from_phi():
    assert "_LO, _HI = " in _LTM_CODE, "the bracket is no longer named"
    assert "3.0 / PHI" in _LTM_CODE, (
        "the upper bracket is not derived from PHI; a fixed one saturates the moment the claim "
        "states a different threshold")
    assert "lo, hi = _LO, _HI" in _LTM_CODE, "zc_hat still uses a literal bracket"


def test_saturation_is_reported_as_unresolved():
    assert 'print("SE = -1")' in _LTM_CODE, (
        "a run that ends against the bracket must report SE = -1 (the file's convention for "
        "'could not resolve'), not return the edge as a measurement")
    assert "saturated" in _LTM_CODE, "the saturation case says nothing about why"


@pytest.mark.parametrize("phi,zc", [(0.10, 13.6593), (0.18, 5.7647), (0.25, 3.8631)])
def test_the_derived_bracket_contains_the_true_crossing(phi, zc):
    """Checked at three thresholds, not just the calibration one."""
    lo, hi = 1.05, max(9.0, 3.0 / phi)
    assert lo < zc < hi, "phi=%.2f: bracket [%.3g, %.3g] misses z_c=%.4f" % (phi, lo, hi, zc)


def test_phi_comes_from_the_claim_and_a_claim_without_one_is_refused():
    """Measuring at an assumed threshold and comparing to the claim's mean degree would manufacture
    a FAILED out of a units mismatch."""
    # The LIVE claim, verbatim from /brain/replication-target. An invented paraphrase of it is not
    # the string the matcher sees, and asserting on one tests the paraphrase.
    inst = _inst_ltm(
        "The tipping threshold for global cascades decreases with greater network connectivity; "
        "for instance, in a Watts model with mean degree 6 and threshold 0.1, a 1% seed fraction "
        "achieves near-complete cascade")
    assert inst is not None and inst["params"]["PHI"] == 0.1
    assert "__PHI__" not in inst["code"] and "= 0.1," in inst["code"]
    assert _inst_ltm("LTM cascade window upper edge z_c = 5.8 on a Poisson random graph") is None, (
        "a claim stating no threshold must be refused, not measured against an assumed one")


def test_the_calibration_row_is_still_documented():
    """The instrument table is the organ's contract with itself; a row without its measured bias is
    a floor nobody can check."""
    src = (REPO / "agora-game-server" / "organs" / "artificer.py").read_text(encoding="utf-8",
                                                                            errors="replace")
    assert "ltm_cascade_window" in src.split('"""', 2)[1], (
        "the LTM row is missing from the instrument table in the module docstring")
