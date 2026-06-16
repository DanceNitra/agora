"""
reliability_receipt - turn an AI-automation's run log into a monthly SLA "receipt".

Why this exists (last30days, 2026-06-16): AI automations sell as $500-1,500/mo
RETAINERS, not products ("I made $75K selling AI automations", r/AI_Agents, 211 pts).
The retainer is fragile because the maintenance is INVISIBLE - clients keep asking
"is this fee just for when it breaks?". The value the freelancer actually delivers is
metis: the tacit work of keeping the automation alive in the client's messy reality
(Scott, Seeing Like a State). This tool makes that invisible work LEGIBLE - it turns a
plain run log into a one-page monthly receipt the client renews against: uptime, the
interventions you absorbed, the dollars of work saved, and an early DRIFT warning.

Input: a JSON-lines run log, one run per line:
    {"ts": "2026-06-01T08:00:00", "ok": true, "interventions": 0,
     "dollars_saved": 42.0, "error": null, "latency_s": 3.1}
Only "ts" and "ok" are required; the rest default sensibly.

Usage:
    python receipt.py runs.jsonl --client "Acme Co" --automation "Invoice agent" --rate 800
    python receipt.py --demo            # generate a sample log + receipt to see the output

Zero dependencies (stdlib only).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(str(s).replace("Z", "+00:00").replace("+00:00", ""))


def load_runs(path: str) -> list[dict]:
    runs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            d["_ts"] = _parse_ts(d["ts"])
            runs.append(d)
    runs.sort(key=lambda r: r["_ts"])
    return runs


def _pct(n: int, d: int) -> float:
    return 100.0 * n / d if d else 0.0


def detect_drift(runs: list[dict], window_days: int = 7, drop_pp: float = 15.0):
    """Compare the most recent `window_days` against the prior baseline. Flag drift if
    the success rate dropped by >= drop_pp percentage points (with enough samples)."""
    if len(runs) < 10:
        return {"drift": False, "reason": "not enough runs to assess drift"}
    end = runs[-1]["_ts"]
    cut = end - timedelta(days=window_days)
    recent = [r for r in runs if r["_ts"] > cut]
    baseline = [r for r in runs if r["_ts"] <= cut]
    if len(recent) < 3 or len(baseline) < 5:
        return {"drift": False, "reason": "windows too small to assess drift"}
    r_ok = _pct(sum(1 for r in recent if r.get("ok")), len(recent))
    b_ok = _pct(sum(1 for r in baseline if r.get("ok")), len(baseline))
    drift = (b_ok - r_ok) >= drop_pp
    return {"drift": drift, "recent_success": r_ok, "baseline_success": b_ok,
            "recent_n": len(recent), "baseline_n": len(baseline),
            "reason": (f"last {window_days}d success {r_ok:.0f}% vs prior {b_ok:.0f}%"
                       + (" - INVESTIGATE" if drift else " - stable"))}


def build_receipt(runs: list[dict], client: str, automation: str, rate: float) -> str:
    if not runs:
        return "No runs in the log - nothing to report."
    n = len(runs)
    ok = sum(1 for r in runs if r.get("ok"))
    interventions = sum(int(r.get("interventions", 0)) for r in runs)
    saved = sum(float(r.get("dollars_saved", 0) or 0) for r in runs)
    errors = [r for r in runs if not r.get("ok")]
    lat = [float(r["latency_s"]) for r in runs if r.get("latency_s") is not None]
    start, end = runs[0]["_ts"], runs[-1]["_ts"]
    drift = detect_drift(runs)
    uptime = _pct(ok, n)
    roi = (saved / rate) if rate else 0.0

    lines = [
        f"# Reliability Receipt - {automation}",
        f"**Client:** {client}  |  **Period:** {start:%Y-%m-%d} to {end:%Y-%m-%d}  "
        f"|  **Retainer:** ${rate:,.0f}/mo",
        "",
        "## What you got this month",
        f"- **Uptime / success rate:** {uptime:.1f}%  ({ok}/{n} runs succeeded)",
        f"- **Runs handled:** {n}",
        f"- **Issues I caught and fixed for you:** {interventions} "
        f"(this is the maintenance the retainer covers)",
        f"- **Value delivered:** ${saved:,.0f} of work the automation did for you"
        + (f"  (~{roi:.1f}x the retainer)" if rate else ""),
    ]
    if lat:
        lat.sort()
        lines.append(f"- **Typical response time:** {lat[len(lat)//2]:.1f}s "
                     f"(p95 {lat[min(len(lat)-1, int(0.95*len(lat)))]:.1f}s)")
    lines += [
        "",
        "## Health check",
        f"- **Drift watch:** {'DRIFT DETECTED - ' if drift['drift'] else 'No drift - '}"
        f"{drift['reason']}",
    ]
    if errors:
        lines.append(f"- **Failures this period:** {len(errors)} "
                     f"(latest: {errors[-1].get('error') or 'unspecified'})")
    else:
        lines.append("- **Failures this period:** 0")
    verdict = ("Action needed - I'm already on it." if drift["drift"]
               else "Running clean. No action needed on your side.")
    lines += ["", f"**Bottom line:** {verdict}",
              "", "_Generated by reliability_receipt - the maintenance you pay for, made visible._"]
    return "\n".join(lines)


def _demo() -> int:
    """Generate a synthetic 30-day run log (with a late drift) and emit a sample receipt."""
    import os
    import random
    rng = random.Random(7)
    here = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(here, "sample_runs.jsonl")
    base = datetime(2026, 5, 17, 8, 0, 0)
    rows = []
    for day in range(30):
        for _ in range(rng.randint(2, 5)):
            ts = base + timedelta(days=day, hours=rng.randint(0, 10), minutes=rng.randint(0, 59))
            # healthy for 24 days, then a drift (an upstream site changed its layout)
            ok = rng.random() < (0.98 if day < 24 else 0.72)
            rows.append({
                "ts": ts.isoformat(), "ok": ok,
                "interventions": 0 if ok else rng.randint(0, 1),
                "dollars_saved": round(rng.uniform(25, 70), 2) if ok else 0.0,
                "error": None if ok else "upstream page layout changed",
                "latency_s": round(rng.uniform(1.5, 6.0), 1),
            })
    rows.sort(key=lambda r: r["ts"])
    with open(log_path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    runs = load_runs(log_path)
    receipt = build_receipt(runs, client="Acme Co", automation="Invoice-intake agent", rate=800)
    out_path = os.path.join(here, "sample_receipt.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(receipt + "\n")
    print(receipt)
    print(f"\n[demo] wrote {len(rows)} runs -> {log_path}")
    print(f"[demo] wrote sample receipt -> {out_path}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate a monthly SLA receipt from an automation run log.")
    ap.add_argument("log", nargs="?", help="path to a JSON-lines run log")
    ap.add_argument("--client", default="Client")
    ap.add_argument("--automation", default="Automation")
    ap.add_argument("--rate", type=float, default=0.0, help="monthly retainer in dollars")
    ap.add_argument("--demo", action="store_true", help="generate a sample log + receipt")
    args = ap.parse_args(argv)
    if args.demo:
        return _demo()
    if not args.log:
        ap.error("provide a run-log path, or use --demo")
    runs = load_runs(args.log)
    print(build_receipt(runs, args.client, args.automation, args.rate))
    return 0


if __name__ == "__main__":
    sys.exit(main())
