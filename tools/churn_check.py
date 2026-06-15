#!/usr/bin/env python3
"""
churn_check.py — catch ACTIVE research churn (tokens burned with no value), which the lifetime
metabolism totals hide.

The metabolism (/brain/metabolism) reports cumulative lifetime tok/value per organ, so an old, already
-fixed leak (e.g. agent-think: 1.7M tok / 0 value, but frozen) looks identical to an active one. This
snapshots the metabolism each run and reports the DELTA since last time: an organ spending tokens with
~no new value between snapshots is churning NOW. Run it each loop cycle; the first run sets a baseline.

Usage:  python tools/churn_check.py
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

SNAP = Path(__file__).resolve().parent / ".churn_snapshots.json"
URL = "http://127.0.0.1:8000/api/v1/agent-os/brain/metabolism"
CHURN_KTOK = 20.0          # an organ that burned >20k tokens since last snapshot...
CHURN_VALUE = 0.5          # ...for under +0.5 value points is churning


def _organs():
    try:
        d = json.load(urllib.request.urlopen(URL, timeout=20))
        return d.get("organs", {})
    except Exception as e:
        print("metabolism unavailable:", e)
        return {}


def main(stamp: float | None = None):
    organs = _organs()
    if not organs:
        return
    cur = {k: {"ktok": v.get("ktok", 0.0), "value": v.get("value", 0.0), "calls": v.get("calls", 0)}
           for k, v in organs.items()}
    hist = []
    if SNAP.is_file():
        try:
            hist = json.loads(SNAP.read_text())
        except Exception:
            hist = []
    prev = hist[-1]["organs"] if hist else None

    if prev is None:
        print("churn_check: baseline snapshot set (no prior to diff). Re-run next cycle to see the rate.")
    else:
        print("churn since last snapshot (active churn = tokens up, value flat):")
        rows = []
        for k, c in cur.items():
            p = prev.get(k, {"ktok": 0, "value": 0, "calls": 0})
            dk = round(c["ktok"] - p["ktok"], 1)
            dv = round(c["value"] - p["value"], 1)
            dc = c["calls"] - p["calls"]
            if dk > 0.1 or dc > 0:
                rows.append((dk, dv, dc, k))
        rows.sort(reverse=True)
        if not rows:
            print("  (no token spend since last snapshot — idle)")
        flagged = []
        for dk, dv, dc, k in rows:
            churn = dk >= CHURN_KTOK and dv < CHURN_VALUE
            mark = "  <-- CHURN" if churn else ""
            if churn:
                flagged.append(k)
            print(f"  {k:20} +{dk:>8,.1f}k tok  +{dv:>6.1f} value  +{dc:>4} calls{mark}")
        print("\nVERDICT:", ("CHURN in: " + ", ".join(flagged) + " (tokens, ~no value — investigate)")
              if flagged else "no active churn — every spending organ is producing value")

    hist.append({"ts": stamp, "organs": cur})
    SNAP.write_text(json.dumps(hist[-100:], indent=2))


if __name__ == "__main__":
    main()
