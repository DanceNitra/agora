"""An instrument must fire on the claims it models and refuse the ones it does not.

Artificer Rooke returned `no-instrument` on every cycle while walking eight replication targets.
Measured 2026-07-31: FIVE of those eight were cascade / tipping / threshold claims (Granovetter's
LTM, critical seed fraction, minority tipping, hysteresis width, tipping vs connectivity), and his
four instruments modelled giant components, branching processes, SIR epidemics and scale-free degree
exponents. Nothing overlapped. That is a capability gap, not a defect in the organ, and his refusals
were correct every time.

`ltm_cascade_window` closes ONE of those five quantities: the mean degree above which a single seed
can no longer trigger a global cascade. Its canonical value is DERIVED rather than cited -- bisecting
the vulnerable-cluster percolation condition `sum_{k<=floor(1/phi)} k(k-1) P_k(z) = z` gives 5.7647
at phi=0.18 -- and it was calibrated on this machine before being trusted: measured 5.5123, bias
-4.38%, SE 0.22%, so rel_floor 0.09. The bias is finite-size, the same character as the branching
row. phi comes from the CLAIM, never a default: the window is 5.76 at 0.18 and 13.66 at 0.10, so
measuring at an assumed threshold would manufacture a FAILED out of a units mismatch.

The half of the rule that matters more is the refusals. An instrument applied where it is NOT the
right instrument produces a FAILED that says nothing about the claim -- a seed FRACTION is a
different measurement from a mean DEGREE, and answering one with the other would be an instrument
error wearing a verdict's clothes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "agora-game-server"))

from organs.artificer import _INSTRUMENTS, _LTM_CODE, _inst_ltm  # noqa: E402

# A claim must state BOTH the connectivity and the THRESHOLD. The window moves with phi -- z_c is
# 5.76 at phi=0.18 and 13.66 at phi=0.10 -- so measuring at an assumed threshold and comparing to
# the claim's mean degree would manufacture a FAILED out of a units mismatch. That is the
# "instrument error wearing a verdict's clothes" this organ's contract forbids, so a claim with no
# threshold is refused rather than measured against a default.
SHOULD_MATCH = [
    "The tipping threshold for global cascades decreases with greater network connectivity; the "
    "cascade window closes at mean degree 6.2 for a threshold of 0.18",
    "LTM cascade window upper edge z_c = 5.8 at threshold 0.18 on a Poisson random graph",
]

SHOULD_REFUSE = [
    # a seed FRACTION is not a mean DEGREE
    "The experimental result identifies a critical seed fraction of 1% that triggers a global cascade",
    "Our joint analysis of the minority-tipping experiment shows a tipping fraction of 0.22",
    # topologies with a different threshold entirely
    "Cascades on a small-world lattice stop above mean degree 6.0",
    "On a scale-free network the cascade window closes at mean degree 7.1",
    # no quantity at all
    "Cascades are more likely in sparse networks than dense ones",
    # a connectivity claim that never states its threshold: the window is undefined without phi
    "The cascade window closes at mean degree 6.2 on a Poisson random graph",
]


@pytest.mark.parametrize("claim", SHOULD_MATCH)
def test_it_fires_on_what_it_models(claim):
    inst = _inst_ltm(claim)
    assert inst is not None, "refused a claim it can model: %s" % claim[:60]
    assert inst["claimed"] > 0
    assert inst["label"] == "cascade_window_upper"


@pytest.mark.parametrize("claim", SHOULD_REFUSE)
def test_it_refuses_what_it_does_not_model(claim):
    assert _inst_ltm(claim) is None, (
        "applied where it is not the right instrument -- the FAILED it would produce says nothing "
        "about the claim: %s" % claim[:60])


def test_the_canonical_value_is_derived_not_remembered():
    """Re-derives the anchor from the percolation condition. If someone edits the constant to make a
    verdict come out, this fails -- the number has to keep coming from the mathematics."""
    import math
    phi = 0.18
    def pois(k, z):
        return math.exp(-z + k * math.log(z) - math.lgamma(k + 1)) if z > 0 else (1.0 if k == 0 else 0.0)
    def g(z):
        return sum(k * (k - 1) * pois(k, z) for k in range(0, int(1.0 / phi) + 1)) - z
    lo, hi = 1.5, 20.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if g(lo) * g(mid) <= 0: hi = mid
        else: lo = mid
    zc = (lo + hi) / 2
    assert abs(zc - 5.7647) < 0.001, "the cascade window anchor moved: %.4f" % zc
    assert "5.7647" in _LTM_CODE, "the instrument no longer states the anchor it is judged against"


def test_the_floor_covers_the_measured_bias():
    """rel_floor must absorb the instrument's own systematic error, or it manufactures FAILEDs.

    Measured bias 4.38%, SE 0.22% -> |bias| + 3*SE = 5.0%, so 0.09 covers it with room. A 3-sigma
    rule alone (0.7%) would rule FAILED on a claim the model reproduces -- the branching row's lesson.
    """
    inst = _inst_ltm(SHOULD_MATCH[0])
    assert inst["rel_floor"] >= 0.0438 + 3 * 0.0022, (
        "rel_floor %.3f is below the instrument's own bias+3SE" % inst["rel_floor"])


def test_the_instrument_is_registered_and_stdlib_only():
    assert _inst_ltm in _INSTRUMENTS, "written but never added to the set Rooke walks"
    for bad in ("import numpy", "import scipy", "import networkx", "requests"):
        assert bad not in _LTM_CODE, "instrument scripts must be stdlib-only; found %r" % bad
    assert "MEASURED " in _LTM_CODE and "SE = " in _LTM_CODE, (
        "the Lab contract needs a MEASURED line and an SE line")
