"""An instrument for the committed-minority tipping family, and the honesty of its refusals.

Rooke walked eight replication targets and returned `no-instrument` every cycle. Five of the eight were
cascade / tipping / threshold claims and his four instruments modelled giant components, branching, SIR
and scale-free exponents; `ltm_cascade_window` closed the first of the five. This closes the second: the
committed-minority tipping fraction in a mean-field Ising system with a field.

THE SEVERE TEST. The claim states J, h, a tipping fraction and a recovery edge; the model has one
parameter the claim leaves unstated, temperature. Pinning T on the RECOVERY edge leaves the TIPPING
fraction a free prediction -- one knob turned, one number predicted, and the claimed tipping value never
enters the model. A claim carrying only one edge is refused, because with nothing to pin T on any
verdict would be a verdict about an assumed temperature.

CALIBRATION, derived and re-derived here rather than remembered:
  A1  at p=0, h=0 the model is the textbook mean-field Ising, critical at T_c = J exactly.
      Measured 1.000000 for J=1.0, error 3.3e-9.
  A2  as T -> 0 the forward tipping fraction approaches (J - h)/(2J) = 0.475 at J=1, h=0.05.
      Measured 0.2967, 0.3704, 0.4147, 0.4465 at T = 0.20, 0.10, 0.05, 0.02.
A2 is also what caught the solver's one real bug: the root at exactly m=1 (p=1, every agent committed)
sits on the scan's last sample and has no successor, so a sign-change scan never saw it and the solver
reported "never tips" at every temperature. An uncalibrated instrument would have shipped that.

WHY IT RULES NOT_COMPUTABLE ON OUR OWN LAB, and why that is a measurement and not a shrug. The tipping
fraction carries an enormous NEGATIVE finite-size bias -- noise carries a finite system over the barrier
while the barrier is still standing. Measured at the fitted temperature: -56.2% at N=240, -25.1% at
N=600 (and -76.3% at N=200, -36.6% at N=500 in the standalone calibration). Lab 36e60c states no system
size, so its 4.8% is consistent with analytic values spanning tens of percent, and ruling FAILED on the
10% gap to the analytic 5.28% would be the instrument's own systematic error wearing a verdict's
clothes. The script measures that span every run and refuses to rule if it turns out small.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "agora-game-server"))

from organs.artificer import (  # noqa: E402
    _INSTRUMENTS, _MFT_CODE, _inst_mft, _labelled_pct, instrument_for)

TARGET = ("Our joint analysis of the minority-tipping experiment (Lab 36e60c) shows a tipping fraction "
          "of 4.8%, a recovery edge of 4.6%, and a hysteresis width of 0.2% (J=1.0, h=0.05), "
          "demonstrating that a committed minority can flip consensus")

REFUSE = [
    # hysteresis width alone: no recovery edge, so nothing pins the temperature
    ("The observed tipping dynamics in Lab e56879 - specifically a hysteresis width of 0.2% and a "
     "committed 0% minority flipping the consensus - are supported by Earth system tipping elements"),
    # a seed FRACTION on a network is a different measurement entirely
    ("The experimental result identifies a critical seed fraction of 1% that triggers a global cascade "
     "reaching 94% of the network, establishing a quantitative threshold for cascade breakout"),
    # one edge only
    ("A committed minority tipping fraction of 4.8% flips the consensus at J=1.0 and h=0.05 in a "
     "mean-field Ising system"),
    # both edges but no couplings: the edges move with J and h, so measuring at assumed ones would
    # manufacture a verdict out of a units mismatch
    ("The tipping fraction is 4.8% and the recovery edge is 4.6%, giving a hysteresis width of 0.2%"),
]


def test_it_fires_on_the_family_it_models():
    inst = _inst_mft(TARGET)
    assert inst is not None, "refused the claim this instrument was built for"
    assert inst["label"] == "committed_tipping_fraction"
    assert inst["claimed"] == pytest.approx(0.048)
    assert inst["params"]["REC"] == pytest.approx(0.046)
    assert inst["params"]["J"] == pytest.approx(1.0)
    assert inst["params"]["H"] == pytest.approx(-0.05), "the field must oppose the committed minority"


@pytest.mark.parametrize("claim", REFUSE)
def test_it_refuses_what_it_cannot_honestly_rule(claim):
    assert _inst_mft(claim) is None, (
        "applied where it is not the right instrument -- the verdict would say nothing about the "
        "claim: %s" % claim[:70])


def test_each_label_takes_its_own_number():
    """THE REGRESSION THAT NEARLY KILLED IT. `_pct_near` accepts a label anywhere in a +-70/+45 char
    window. This sentence packs three labelled percentages into sixty characters, so the window around
    4.8% already contains the words 'recovery edge' and the helper returned 4.8 for BOTH labels. The
    instrument then refused itself on `rec < tip` -- the guard working, and no verdict ever reachable."""
    assert _labelled_pct(TARGET, r"tipping (?:fraction|point|threshold)") == pytest.approx(0.048)
    assert _labelled_pct(TARGET, r"recovery (?:edge|point|threshold)") == pytest.approx(0.046)
    assert _labelled_pct(TARGET, r"hysteresis (?:width|loop|gap)") == pytest.approx(0.002)


def test_the_window_helper_still_gets_it_wrong():
    """THE FALSIFICATION CONTROL. If `_pct_near` stops confusing the two labels, the directional match
    above is closing nothing and the test before it passes for free."""
    from organs.artificer import _pct_near
    assert _pct_near(TARGET, r"recovery (?:edge|point|threshold)") == pytest.approx(0.048), (
        "the window helper no longer mis-attributes the neighbouring percentage -- re-measure before "
        "trusting that the directional match is load-bearing")


# ---------------------------------------------------------------- calibration, re-derived

def _fixed_points(p, beta, J, h, n=4001):
    def F(m):
        return p + (1.0 - p) * math.tanh(beta * (J * m + h)) - m
    out = [e for e in (-1.0, 1.0) if abs(F(e)) < 1e-12]
    px, pf = -1.0, F(-1.0)
    for i in range(1, n):
        x = -1.0 + 2.0 * i / (n - 1)
        f = F(x)
        if pf * f < 0:
            lo, hi = px, x
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                if F(lo) * F(mid) <= 0: hi = mid
                else: lo = mid
            out.append(0.5 * (lo + hi))
        px, pf = x, f
    return sorted(out)


def test_anchor_A1_the_critical_temperature_is_the_coupling():
    """Mean-field Ising: m = tanh(J*m/T) has a non-zero solution exactly up to T = J."""
    J = 1.0
    def ordered(T):
        return any(abs(m) > 1e-4 for m in _fixed_points(0.0, 1.0 / T, J, 0.0))
    lo, hi = 0.05, 5.0
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        if ordered(mid): lo = mid
        else: hi = mid
    assert abs(0.5 * (lo + hi) - J) < 1e-4, "T_c drifted off the coupling: %.6f" % (0.5 * (lo + hi))


def test_anchor_A2_the_zero_temperature_limit_is_analytic():
    """At T -> 0 a free spin flips when J*(2p-1) + h > 0, so the forward tipping fraction tends to
    (J - h)/(2J). Convergence, not equality: a finite temperature never reaches the limit."""
    J, h = 1.0, -0.05
    analytic = (J - abs(h)) / (2 * J)
    def tip(T):
        beta = 1.0 / T
        def br(p):
            rs = _fixed_points(p, beta, J, h)
            if not rs: return None
            def stable(m):
                c = math.cosh(beta * (J * m + h))
                return (1.0 - p) * beta * J / (c * c) < 1.0
            st = [m for m in rs if stable(m)]
            return (min(st) if st else rs[0])
        a, b = 0.0, 1.0
        for _ in range(60):
            mid = 0.5 * (a + b)
            m = br(mid)
            if m is not None and m > 0: b = mid
            else: a = mid
        return 0.5 * (a + b)
    errs = [abs(tip(T) - analytic) for T in (0.20, 0.10, 0.05)]
    assert errs == sorted(errs, reverse=True), "the T->0 limit is not being approached: %s" % errs
    assert errs[-1] < 0.10, "at T=0.05 the solver is %.4f from the analytic limit" % errs[-1]


def test_the_endpoint_root_is_handled():
    """The bug anchor A2 caught: at p=1 every agent is committed, m=1 exactly, and a sign-change scan
    never tests the last sample. Without this the solver reports 'never tips' at every temperature."""
    assert _fixed_points(1.0, 1.0 / 0.9, 1.0, -0.05) == [1.0]
    assert "for edge in (-1.0, 1.0)" in _MFT_CODE, "the embedded solver lost its endpoint check"


def test_the_lab_script_is_registered_and_stdlib_only():
    assert _inst_mft in _INSTRUMENTS, "written but never added to the set Rooke walks"
    for bad in ("import numpy", "import scipy", "import networkx", "requests", "urllib"):
        assert bad not in _MFT_CODE, "instrument scripts must be stdlib-only; found %r" % bad
    assert "MEASURED " in _MFT_CODE and "SE = " in _MFT_CODE and "VERDICT:" in _MFT_CODE
    assert "__J__" not in _inst_mft(TARGET)["code"], "a placeholder survived substitution"


def test_the_size_sensitivity_control_exists_and_can_refuse():
    """A NOT_COMPUTABLE that cannot fail is a shrug. The script must be able to say the opposite."""
    assert "size-sensitivity control did NOT fire" in _MFT_CODE, (
        "the instrument cannot report that the unstated system size was harmless, so its "
        "NOT_COMPUTABLE is unfalsifiable")
    assert "VERDICT: FAILED" in _MFT_CODE, "the instrument can never rule FAILED, so it cannot fail"


def test_the_router_sends_a_window_edge_claim_to_the_cascade_instrument():
    """Two tipping instruments now exist; a claim about where the window CLOSES must still reach the
    cascade-window one, not this one."""
    edge = ("The tipping threshold for global cascades decreases with greater network connectivity; "
            "the cascade window closes at mean degree 6.2 for a threshold of 0.18")
    assert (instrument_for(edge) or {}).get("key") == "ltm_cascade_window"
    assert _inst_mft(edge) is None


def test_an_operating_point_reaches_no_instrument_at_all():
    """THE FALSE-FAILED REGRESSION, pinned. An earlier version of the test above asserted that this
    claim SHOULD route to the cascade-window instrument, and it did -- taking "mean degree 6" as the
    claimed window edge because the pattern's trailing alternation caught the word "threshold" that
    introduces phi. The true edge at phi=0.1 is 13.66, so the organ recorded

        MEASURED cascade_window_upper=13.586 vs CLAIMED 6 -> FAILED   (lab 712068)

    while the claim was TRUE: a mean degree of 6 sits well inside a window closing at 13.66, which is
    exactly why the cascade it describes happens. A false FAILED, written into the ledger that feeds
    the public Crucible, produced by the instrument rather than by the claim -- the failure the
    instrument's own contract calls "an instrument error wearing a verdict's clothes".
    """
    op = ("The tipping threshold for global cascades decreases with greater network connectivity; in "
          "a Watts model with mean degree 6 and threshold 0.1, a 1% seed fraction achieves cascade")
    assert instrument_for(op) is None, (
        "an operating point is being measured against a window edge; that comparison manufactured a "
        "FAILED on a true claim once already")


def test_the_plural_does_not_defeat_the_cascade_instrument():
    """`\\bcascade\\b` does not match "cascades", so a textbook window-edge claim was refused as
    inapplicable on the plural alone -- the same one-surface-form class as "falsifier" vs
    "falsification"."""
    plural = "On a Poisson random graph cascades stop above mean degree 7.1 at threshold 0.18"
    assert (instrument_for(plural) or {}).get("key") == "ltm_cascade_window"
