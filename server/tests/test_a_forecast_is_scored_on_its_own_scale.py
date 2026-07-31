"""A forecast must be resolved against the same quantity its baseline measured.

`resolve_due` branches on one field:

    if p.get("mode") == "rate":  new = _window_count(...)   # trailing 14-day RATE
    else:                        new = _metric_value(...)   # ALL-TIME CUMULATIVE total

and `record_prediction` never set it. Its baseline comes from `gather_prediction_baseline`, which
returns a trailing 14-day WINDOW count -- so every forecast recorded through that path had a window
baseline scored against a cumulative total.

Measured 2026-07-31 over 207 resolved records: median resolved/baseline is **51.7x** for by="claude"
against **1.0x** for rate-mode records. On that scale a FLAT or DOWN call is dead on arrival and an
UP call is free, so the by=claude hit rate is not a measurement of forecasting at all.

King Aldric's organ (`organs/king.py`, rule 4) diagnosed this and REFUSES to record through the
ledger path unless baseline and resolution measure the same quantity. Two forecasts were recorded
through it anyway the same evening. This test is why that cannot recur.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agora.execution import prediction_ledger as PL  # noqa: E402


def test_a_recorded_forecast_declares_its_scale():
    rec = PL.record_prediction.__wrapped__ if hasattr(PL.record_prediction, "__wrapped__") \
        else PL.record_prediction
    src = inspect.getsource(rec)
    assert '"mode": "rate"' in src, (
        "record_prediction does not set mode, so resolve_due will score a 14-day window baseline "
        "against an all-time cumulative total")


def test_the_resolver_still_branches_on_that_field():
    """Pins the two sides together: if the resolver stops reading `mode`, setting it means nothing."""
    src = inspect.getsource(PL.resolve_due)
    assert 'get("mode") == "rate"' in src, "resolve_due no longer branches on mode"
    assert "_window_count" in src and "_metric_value" in src, (
        "the two resolution paths this field selects between are gone")


def test_the_baseline_source_is_a_window_not_a_total():
    """The reason `rate` is the correct value: the baseline handed to record_prediction is a
    trailing-window count. If that ever becomes cumulative, this file's premise inverts."""
    src = inspect.getsource(PL.gather_prediction_baseline)
    assert "window" in src.lower() or "trailing" in src.lower(), (
        "gather_prediction_baseline no longer documents a trailing window; re-check which mode "
        "record_prediction should declare before trusting either")


def test_no_pending_claude_forecast_is_on_the_cumulative_scale():
    """The live check. A pending forecast without `mode` will resolve on the rigged scale, and
    unlike a resolved one it can still be fixed."""
    bad = [p for p in PL._load()
           if p.get("status") == "pending" and p.get("by") == "claude" and not p.get("mode")]
    assert not bad, (
        "%d pending Claude forecast(s) carry no mode and will be scored against an all-time total: "
        "%s" % (len(bad), [str(p.get("theme"))[:40] for p in bad[:4]]))


def test_the_rigged_scale_is_still_visible_in_the_history():
    """The control. This suite must not be able to pass because the defect never existed -- the
    resolved records still carry it, and if that stops being true the fixture has drifted."""
    recs = [p for p in PL._load() if p.get("status") in ("correct", "incorrect")]
    if len(recs) < 30:
        import pytest
        pytest.skip("too little history to show the effect")
    def ratio(rs):
        v = sorted(float(p.get("resolved_value") or 0) / max(1.0, float(p.get("baseline") or 1))
                   for p in rs)
        return v[len(v) // 2] if v else 0.0
    # Split by AUTHOR, not by `mode`. A first cut of this control compared mode=None against
    # mode=rate and measured 1.0x vs 1.0x -- because the 72 mode-less records are 32 Claude ones at
    # 51.7x plus 40 tournament ones whose metric happens to make the cumulative and the window
    # nearly equal. The rigged scale is a property of the Claude+github_repos path, and a control
    # aimed at the wrong split reports "no defect" on a defect that is right there.
    claude = ratio([p for p in recs if p.get("by") == "claude"])
    rate = ratio([p for p in recs if p.get("mode") == "rate"])
    assert claude > 5 * max(rate, 0.1), (
        "the historical rigged scale is no longer visible (by=claude median %.1fx vs rate-mode "
        "%.1fx); this suite would be passing vacuously" % (claude, rate))
