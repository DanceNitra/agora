"""Audit of Marat Sultanov's TAT-vs-baseline result on S&P 500 volatility (2026-07-27).

He followed the protocol we recommended (70/15/15 split, early stopping, config sweep, linear baseline) and
reports TAT r=0.739 vs baseline r=0.652 on a held-out test set. Three things need checking before that
number means what it says, and none of them need his model — they are properties of the SETUP:

  1. SELECTION CHANNEL. His own log picks the winning head configuration by `test_corr`, while stating the
     test set was never used for hyperparameter selection. The lowest validation loss belongs to a
     DIFFERENT configuration. This measures what the honest protocol would have chosen.

  2. THE BASELINE. Linear regression on five features is not the standard baseline for volatility; the
     standard one is PERSISTENCE (tomorrow's realised vol ~ today's). Volatility is strongly
     autocorrelated, so a large r can be entirely persistence. If persistence alone beats 0.739, both
     models are below the honest floor.

  3. OVERLAP / LEAKAGE. A 10-day realised-vol target computed on a rolling window makes consecutive
     targets share 9 of 10 days. With a chronological split that costs a little at the boundary; with a
     RANDOM split it is leakage, because a test window overlaps train windows almost entirely.

RUN:  python research/probes/tat_sp500_audit.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

START, END, TICKER = "2021-01-01", "2026-01-01", "^GSPC"
HORIZON = 10


def _corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 3:
        return float("nan")
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def _ols(xtr, ytr, xte):
    """Least squares with an intercept -- the same baseline he ran."""
    A = np.column_stack([np.ones(len(xtr)), xtr])
    coef, *_ = np.linalg.lstsq(A, ytr, rcond=None)
    return np.column_stack([np.ones(len(xte)), xte]) @ coef


def build():
    import yfinance as yf

    px = yf.download(TICKER, start=START, end=END, progress=False, auto_adjust=True)
    if isinstance(px.columns, pd.MultiIndex):
        px.columns = px.columns.get_level_values(0)
    df = pd.DataFrame(index=px.index)
    df["ret"] = px["Close"].pct_change()
    df["hl"] = (px["High"] - px["Low"]) / px["Close"]
    df["oc"] = (px["Open"] - px["Close"]) / px["Close"]
    df["dvol"] = px["Volume"].pct_change()
    df["close"] = px["Close"]
    # target: realised volatility of the NEXT `HORIZON` days
    df["target"] = df["ret"].rolling(HORIZON).std().shift(-HORIZON)
    # the persistence feature: realised vol of the LAST `HORIZON` days, known at prediction time
    df["vol_now"] = df["ret"].rolling(HORIZON).std()
    # Volume pct_change is +/-inf on a zero-volume day (holidays in this series), which makes the least
    # squares fail outright rather than quietly -- worth keeping loud, but it has to be cleaned to compare.
    df = df.replace([np.inf, -np.inf], np.nan)
    return df.dropna()


def main() -> int:
    df = build()
    X = df[["ret", "hl", "oc", "dvol", "close"]].to_numpy(float)
    y = df["target"].to_numpy(float)
    vol_now = df["vol_now"].to_numpy(float)
    n = len(df)
    n_tr, n_va = int(n * 0.70), int(n * 0.15)
    tr = slice(0, n_tr)
    va = slice(n_tr, n_tr + n_va)
    te = slice(n_tr + n_va, n)
    print(f"{TICKER} {START}..{END}: {n} usable rows -> train {n_tr}, val {n_va}, test {n - n_tr - n_va}")
    print(f"(his run: train 870, val 187, test 187)\n")

    rows = {}
    rows["linear regression (his baseline), 5 features"] = _corr(_ols(X[tr], y[tr], X[te]), y[te])
    # THE FLOOR he did not measure: today's realised vol, as the forecast, with no model at all.
    rows["PERSISTENCE: today's 10d realised vol, no model"] = _corr(vol_now[te], y[te])
    # and the same floor given a fitted scale, which is the fairest one-feature regression
    rows["linear regression on vol_now ALONE"] = _corr(
        _ols(vol_now[tr, None], y[tr], vol_now[te, None]), y[te])
    rows["linear regression, 5 features + vol_now"] = _corr(
        _ols(np.column_stack([X, vol_now])[tr], y[tr], np.column_stack([X, vol_now])[te]), y[te])

    print("held-out test correlation (chronological split):")
    for k, v in rows.items():
        print(f"  {v:6.4f}   {k}")
    print(f"\n  his reported TAT adaptive: 0.7385")
    print(f"  his reported baseline    : 0.6520")

    # (3) what a RANDOM split does to the same linear baseline -- the overlap question, quantified
    rng = np.random.default_rng(20260727)
    idx = rng.permutation(n)
    r_tr, r_te = idx[: n_tr + n_va], idx[n_tr + n_va:]
    rows["linear regression, RANDOM split (overlapping windows leak)"] = _corr(
        _ols(X[r_tr], y[r_tr], X[r_te]), y[r_te])
    print(f"\n  {rows['linear regression, RANDOM split (overlapping windows leak)']:6.4f}   "
          f"same baseline under a RANDOM split (chronological above)")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tat_sp500_audit_result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"ticker": TICKER, "start": START, "end": END, "horizon": HORIZON,
                   "n": int(n), "results": rows,
                   "his_tat": 0.7385, "his_baseline": 0.6520}, fh, indent=1)
    print(f"\nwrote {os.path.basename(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
