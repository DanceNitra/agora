"""
Prediction Ledger — the Accountable Mind.

Agora doesn't just ground existing claims in reality; it makes FALSIFIABLE predictions about the
future and holds itself accountable. For a theme it records the current real-world metric (Hacker
News discussion / GitHub repos / PubMed papers), predicts its direction over a horizon, and stores
it. Later the Reality Bridge RE-FETCHES the metric and the prediction resolves correct/incorrect.
Over time Agora tracks its hit-rate and calibration — it learns what it actually knows.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from pathlib import Path

_LEDGER = Path(__file__).resolve().parents[2] / ".predictions.json"


def _load() -> list:
    try:
        return json.loads(_LEDGER.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(preds: list) -> None:
    try:
        _LEDGER.write_text(json.dumps(preds, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


# metric name -> (fetcher, key, human label)
def _metric_value(metric: str, theme: str) -> int:
    from agora.execution.data_tool import fetch_hackernews, fetch_github, fetch_pubmed
    try:
        if metric == "hackernews_stories":
            return int(fetch_hackernews(theme).get("total_stories_ever", 0) or 0)
        if metric == "github_repos":
            return int(fetch_github(theme).get("total_repos", 0) or 0)
        if metric == "pubmed_papers":
            return int(fetch_pubmed(theme).get("paper_count", 0) or 0)
    except Exception:
        pass
    return 0


_METRIC_LABEL = {"hackernews_stories": "Hacker News stories", "github_repos": "GitHub repos",
                 "pubmed_papers": "PubMed papers"}


async def make_prediction(theme: str, horizon_days: int = 14) -> dict:
    """Record a falsifiable prediction: the current metric + a forecast of its direction."""
    from agora.execution.data_tool import fetch_hackernews, fetch_github, fetch_pubmed
    from agora.execution.llm_client import call_llm

    hn, gh, pm = (await asyncio.to_thread(fetch_hackernews, theme),
                  await asyncio.to_thread(fetch_github, theme),
                  await asyncio.to_thread(fetch_pubmed, theme))
    baselines = {"hackernews_stories": int(hn.get("total_stories_ever", 0) or 0),
                 "github_repos": int(gh.get("total_repos", 0) or 0),
                 "pubmed_papers": int(pm.get("paper_count", 0) or 0)}
    metric = max(baselines, key=lambda k: baselines[k])           # the strongest real-world signal
    baseline = baselines[metric]

    raw = await asyncio.to_thread(
        call_llm,
        "You are a calibrated forecaster. Given a theme and its CURRENT real-world metric, predict how "
        f"that metric will move over the next {horizon_days} days. Reply in EXACTLY this form:\n"
        "DIRECTION: UP or DOWN or FLAT\nCONFIDENCE: <integer 0-100>\nWHY: <one sentence>",
        f"THEME: {theme}\nMETRIC: {_METRIC_LABEL[metric]} = {baseline} now\n"
        f"(other signals: {baselines})", "cheap", 0.3, 200) or ""
    dm = re.search(r"DIRECTION:\s*(UP|DOWN|FLAT)", raw, re.I)
    cm = re.search(r"CONFIDENCE:\s*(\d+)", raw)
    wm = re.search(r"WHY:\s*(.+)", raw, re.DOTALL | re.I)
    direction = dm.group(1).upper() if dm else "FLAT"
    confidence = min(100, int(cm.group(1))) / 100 if cm else 0.5
    why = (wm.group(1).strip()[:200] if wm else "")

    pred = {"id": uuid.uuid4().hex[:8], "theme": theme[:120], "metric": metric,
            "metric_label": _METRIC_LABEL[metric], "baseline": baseline, "all_baselines": baselines,
            "direction": direction, "confidence": confidence, "why": why,
            "made_ts": time.time(), "resolve_ts": time.time() + horizon_days * 86400,
            "horizon_days": horizon_days, "status": "pending"}
    preds = _load()
    preds.append(pred)
    _save(preds)
    return pred


async def resolve_due(force: bool = False) -> list:
    """Re-fetch each due prediction's metric and resolve it correct/incorrect (the accountability)."""
    preds = _load()
    now = time.time()
    resolved = []
    for p in preds:
        if p.get("status") != "pending" or (not force and now < p.get("resolve_ts", 0)):
            continue
        new = await asyncio.to_thread(_metric_value, p["metric"], p["theme"])
        base = p.get("baseline", 0)
        thresh = max(1, base * 0.05)
        actual = "UP" if new > base + thresh else ("DOWN" if new < base - thresh else "FLAT")
        p["resolved_value"] = new
        p["actual"] = actual
        p["status"] = "correct" if actual == p["direction"] else "incorrect"
        p["resolved_ts"] = now
        resolved.append(p)
    if resolved:
        _save(preds)
    return resolved


def calibration() -> dict:
    """Agora's track record — hit-rate overall and split by its own stated confidence."""
    preds = _load()
    done = [p for p in preds if p.get("status") in ("correct", "incorrect")]
    correct = sum(1 for p in done if p["status"] == "correct")
    bins = {"low (<50%)": [0, 0], "med (50-75%)": [0, 0], "high (>75%)": [0, 0]}
    for p in done:
        c = p.get("confidence", 0.5)
        b = "low (<50%)" if c < 0.5 else ("med (50-75%)" if c <= 0.75 else "high (>75%)")
        bins[b][0] += 1
        bins[b][1] += 1 if p["status"] == "correct" else 0
    return {"total": len(preds), "resolved": len(done), "pending": len(preds) - len(done),
            "correct": correct, "hit_rate": (correct / len(done)) if done else None,
            "by_confidence": {k: f"{v[1]}/{v[0]}" for k, v in bins.items() if v[0]}}


def format_predictions(limit: int = 8) -> str:
    preds = sorted(_load(), key=lambda p: -p.get("made_ts", 0))
    cal = calibration()
    lines = ["🔮 *Prediction Ledger*"]
    if cal["resolved"]:
        hr = f"{cal['hit_rate']:.0%}" if cal["hit_rate"] is not None else "—"
        lines.append(f"_Track record: {cal['correct']}/{cal['resolved']} correct ({hr}) · "
                     f"{cal['pending']} pending_")
    icon = {"correct": "✅", "incorrect": "❌", "pending": "⏳"}
    for p in preds[:limit]:
        lines.append(f"{icon.get(p['status'], '•')} *{p['direction']}* {p['metric_label']} for "
                     f"_{p['theme'][:46]}_ ({p['confidence']:.0%})"
                     + (f" → was {p.get('actual')}" if p["status"] != "pending" else ""))
    return "\n".join(lines)
