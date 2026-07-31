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

# A prediction younger than this must NOT resolve — re-measuring a monotonic count the same day
# it was made yields a vacuous FLAT and poisons the track record. Binds even under force.
_MIN_RESOLVE_AGE = 86400  # 1 day


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


def _window_count(metric: str, theme: str, days: int) -> int:
    """Items created/published for `theme` in the trailing `days` window (a RATE, not a total)."""
    from agora.execution.data_tool import (hackernews_window_count, github_window_count,
                                           pubmed_window_count)
    try:
        if metric == "hackernews_stories":
            return hackernews_window_count(theme, days)
        if metric == "github_repos":
            return github_window_count(theme, days)
        if metric == "pubmed_papers":
            return pubmed_window_count(theme, days)
    except Exception:
        pass
    return 0


def _windowed_baselines(theme: str, days: int) -> dict:
    """Trailing-window counts so the forecast 'will the NEXT window beat the LAST' is genuinely ~50/50
    (rate-of-attention / acceleration), not 'will a cumulative counter go up' (always yes). The chosen
    metric is the most ACTIVE rate (so the forecast is non-degenerate)."""
    from agora.execution.data_tool import (hackernews_window_count, github_window_count,
                                           pubmed_window_count)
    bl = {}
    # pubmed_papers DROPPED 2026-07-23: the resolved ledger measured it 90% wrong (98/109 incorrect),
    # far worse than github_repos (65%) / hackernews (75%), and it dominated the ledger (62% of resolved
    # calls) because cumulative PubMed counts are usually the max baseline. Volatile/laggy proxy; removed
    # from the metric set so predictions run on the two less-noisy attention rates.
    for m, fn in (("github_repos", github_window_count),
                  ("hackernews_stories", hackernews_window_count)):
        try:
            bl[m] = int(fn(theme, days) or 0)
        except Exception:
            bl[m] = 0
    metric = max(bl, key=lambda k: bl[k]) if any(bl.values()) else "github_repos"
    return {"theme": theme, "metric": metric, "metric_label": f"{_METRIC_LABEL[metric]} ({days}d)",
            "baseline": bl[metric], "all_baselines": bl, "mode": "rate", "window_days": days}


# CALIBRATION FLOOR (2026-07-07). The resolved ledger measured this organ WORSE than chance
# (Brier 0.37 vs 0.25; hit-rate 0.23; even >75%-confidence directional calls hit only 25%). The proxies
# it forecasts (14d Hacker News / GitHub / PubMed counts) are noise that does not support directional
# conviction, and the specific defect is OVER-confidence, not ignorance. So every DIRECTIONAL (UP/DOWN)
# forecast has its confidence shrunk toward 0.5 and capped, moving a demonstrably-uncalibrated organ's
# Brier back toward chance and off the credibility storefront's liability column. A FLAT call keeps its
# confidence (a no-change bet on a noisy metric is the honest default). Reversible: raise these toward 1.0
# once the ledger EARNS calibration (resolved hit-rate > 0.5 at high confidence).
_CONF_SHRINK = 0.4    # pull (confidence-0.5) toward 0 for directional calls
_CONF_CAP = 0.62      # hard ceiling on a directional forecast's published confidence


def _calibrate_conf(direction: str, confidence: float) -> float:
    """Regularize an over-confident directional forecast toward chance; FLAT is left unchanged."""
    if direction in ("UP", "DOWN"):
        return round(min(_CONF_CAP, 0.5 + (confidence - 0.5) * _CONF_SHRINK), 3)
    return confidence


async def make_prediction(theme: str, horizon_days: int = 14) -> dict:
    """Record a falsifiable RATE forecast: will the NEXT window's activity beat the LAST window's
    (acceleration) — a genuinely ~50/50 question, not 'will a cumulative counter go up'."""
    from agora.execution.llm_client import call_llm

    base = await asyncio.to_thread(_windowed_baselines, theme, horizon_days)
    metric, baseline = base["metric"], base["baseline"]

    raw = await asyncio.to_thread(
        call_llm,
        "You are a calibrated forecaster. A topic's RECENT ACTIVITY RATE is given. Predict whether the "
        f"NEXT {horizon_days} days will have MORE (UP = accelerating) or FEWER (DOWN = decelerating) "
        "than the last window — this is genuinely uncertain, so SPREAD your confidence (be near 50 when "
        "unsure, high only when you have a real reason). Reply EXACTLY:\n"
        "DIRECTION: UP or DOWN or FLAT\nCONFIDENCE: <integer 0-100>\nWHY: <one sentence>",
        f"THEME: {theme}\nRATE: {base['metric_label']} = {baseline} in the last {horizon_days} days\n"
        f"(other rates: {base['all_baselines']})", "cheap", 0.3, 200) or ""
    dm = re.search(r"DIRECTION:\s*(UP|DOWN|FLAT)", raw, re.I)
    cm = re.search(r"CONFIDENCE:\s*(\d+)", raw)
    wm = re.search(r"WHY:\s*(.+)", raw, re.DOTALL | re.I)
    direction = dm.group(1).upper() if dm else "FLAT"
    confidence = min(100, int(cm.group(1))) / 100 if cm else 0.5
    confidence = _calibrate_conf(direction, confidence)   # shrink over-confident directional calls toward chance
    why = (wm.group(1).strip()[:200] if wm else "")

    pred = {"id": uuid.uuid4().hex[:8], "theme": theme[:120], "metric": metric,
            "metric_label": base["metric_label"], "baseline": baseline,
            "all_baselines": base["all_baselines"], "mode": "rate", "window_days": horizon_days,
            "direction": direction, "confidence": confidence, "why": why,
            "made_ts": time.time(), "resolve_ts": time.time() + horizon_days * 86400,
            "horizon_days": horizon_days, "status": "pending"}
    preds = _load()
    preds.append(pred)
    _save(preds)
    return pred


# ── The Forecasting Tournament: every agent calls the same theme; trust follows truth ──
_FORECASTERS = {
    "Kael":   "Shadow Kael, the Research Scout — drawn to the new; leans into emerging signals.",
    "Mira":   "Sage Mira, the Knowledge Curator — conservative; trusts established base rates.",
    "Orin":   "High Priest Orin, the Idea Alchemist — contrarian; looks for the consensus to be wrong.",
    "Aldric": "King Aldric, the Engineering Lead — pragmatic; weighs base size and momentum only.",
    "Elara":  "Dame Elara, the Bridge Builder — integrative; reads the cross-domain spillovers.",
    "Voss":   "Sergeant Voss, Quality Assurance — skeptical; demands strong evidence before calling a move.",
}


def _persona_reliability() -> dict:
    """Each forecaster's track record from RESOLVED tournaments: a Beta-smoothed hit-rate (a call hits
    if its direction matched the realized outcome). 0.5 with no history — so the tournament blends
    calls by WAS-IT-RIGHT, not one-agent-one-vote (direction #7, the accuracy loop applied to the swarm)."""
    good: dict = {}
    bad: dict = {}
    for p in _load():
        if p.get("by") != "tournament" or "actual" not in p or p.get("status") not in ("correct", "incorrect"):
            continue
        actual = p["actual"]
        for c in p.get("calls", []):
            a = c.get("agent")
            if not a:
                continue
            if c.get("direction") == actual:
                good[a] = good.get(a, 0) + 1
            else:
                bad[a] = bad.get(a, 0) + 1
    return {a: (good.get(a, 0) + 1) / (good.get(a, 0) + bad.get(a, 0) + 2)
            for a in set(good) | set(bad)}


async def run_tournament(theme: str, horizon_days: int = 14) -> dict:
    """Every agent makes its OWN call on the same theme (one labeled-text flash call for all six).
    Stored as a single ledger record with per-agent calls; resolve_due scores each agent, and the
    dungeon blends each agent's hit-rate into its standing — reputation follows truth."""
    from agora.execution.llm_client import call_llm
    base = await gather_prediction_baseline(theme, horizon_days)

    def _one_call(name: str, persona: str) -> dict | None:
        # one tiny labeled-text call per agent — flash returns EMPTY on anything bigger
        raw = call_llm(
            f"You are {persona} A topic's activity in the LAST {horizon_days} days is given. Will the "
            f"NEXT {horizon_days} days be HIGHER (UP=accelerating) or LOWER (DOWN=decelerating)? This is "
            "genuinely uncertain — spread your confidence. Reply EXACTLY one line: DIRECTION CONFIDENCE "
            "(e.g. 'UP 60'). DIRECTION is UP, DOWN or FLAT. Nothing else.",
            f"THEME: {theme}\nRATE: {base['metric_label']} = {base['baseline']} in the last {horizon_days}d",
            "cheap", 0.6, 150) or ""        # >=120: flash spends tokens reasoning before output
        m = re.search(r"\b(UP|DOWN|FLAT)\b\s*(\d+)?", raw, re.I)
        if not m:
            return None
        return {"agent": name, "direction": m.group(1).upper(),
                "confidence": min(100, int(m.group(2) or 60)) / 100}

    results = await asyncio.gather(
        *[asyncio.to_thread(_one_call, n, p) for n, p in _FORECASTERS.items()])
    calls = [c for c in results if c]
    if len(calls) < 3:          # flash returned junk — don't store a hollow tournament
        return {"status": "skipped", "reason": "fewer than 3 parseable calls"}
    # Calibration-weighted blend (not one-agent-one-vote): each call counts as reliability x confidence,
    # so a forecaster with a better track record moves the verdict more — reputation follows truth.
    rel = _persona_reliability()
    wt: dict = {}
    for c in calls:
        c["weight"] = round(rel.get(c["agent"], 0.5) * c["confidence"], 3)
        wt[c["direction"]] = wt.get(c["direction"], 0.0) + c["weight"]
    chosen = max(wt, key=wt.get)
    sel = [c for c in calls if c["direction"] == chosen]
    pred = {"id": uuid.uuid4().hex[:8], "theme": theme[:120], "metric": base["metric"],
            "metric_label": base["metric_label"], "baseline": int(base["baseline"]),
            "all_baselines": base["all_baselines"], "mode": "rate", "window_days": horizon_days,
            "direction": chosen,
            "confidence": _calibrate_conf(chosen, round(sum(c["confidence"] for c in sel) / max(1, len(sel)), 3)),
            "why": "tournament (calibration-weighted)", "by": "tournament", "calls": calls,
            "made_ts": time.time(), "resolve_ts": time.time() + horizon_days * 86400,
            "horizon_days": horizon_days, "status": "pending"}
    preds = _load()
    preds.append(pred)
    _save(preds)
    return {"status": "ok", **pred}


def agent_scores() -> dict:
    """Each agent's forecasting track record across resolved tournament calls."""
    out = {n: {"total": 0, "correct": 0} for n in _FORECASTERS}
    for p in _load():
        actual = p.get("actual")
        if p.get("status") not in ("correct", "incorrect") or not actual:
            continue
        for c in p.get("calls", []):
            s = out.get(c.get("agent"))
            if s is not None:
                s["total"] += 1
                s["correct"] += 1 if c.get("direction") == actual else 0
    for n, s in out.items():
        s["hit_rate"] = round(s["correct"] / s["total"], 3) if s["total"] else None
    return out


async def gather_prediction_baseline(theme: str, horizon_days: int = 14) -> dict:
    """Trailing-window RATE baselines for a theme (so the forecast is acceleration — a ~50/50 question —
    not the direction of a monotonic cumulative counter). Degrades gracefully per source."""
    return await asyncio.to_thread(_windowed_baselines, theme, horizon_days)


def record_prediction(theme: str, metric: str, baseline: int, direction: str,
                      confidence: float, why: str, horizon_days: int = 14) -> dict:
    """Store a prediction MADE BY CLAUDE (reasoned, high-quality) into the ledger.

    `mode="rate"` IS NOT OPTIONAL HERE. The baseline this receives comes from
    `gather_prediction_baseline`, which returns a TRAILING 14-DAY WINDOW count. `resolve_due`
    branches on this field and, without it, falls to `_metric_value` -- the ALL-TIME CUMULATIVE
    total. A window baseline scored against a cumulative total is not a forecast, it is a rigged
    scoreboard: measured 2026-07-31 over the 32 resolved records with by="claude", the median
    resolved/baseline ratio is **51.7x** against 1.0x for every rate-mode record. Any FLAT or DOWN
    call is dead on arrival and any UP call is free.

    King Aldric's organ found this before I did and REFUSES to record through this path for exactly
    this reason (`organs/king.py`, rule 4). I then recorded two forecasts through it the same
    evening without setting the field. Setting it here means the ledger arm cannot make that mistake
    again, whoever is driving.
    """
    pred = {"id": uuid.uuid4().hex[:8], "theme": theme[:120], "metric": metric, "mode": "rate",
            "metric_label": _METRIC_LABEL.get(metric, metric), "baseline": int(baseline),
            "all_baselines": {metric: int(baseline)},
            "direction": str(direction).upper().strip()[:5] if str(direction).upper().strip()[:4] in
            ("UP", "DOWN", "FLAT") else "FLAT",
            "confidence": max(0.0, min(1.0, float(confidence))), "why": why[:240], "by": "claude",
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
        if p.get("status") != "pending":
            continue
        if now - p.get("made_ts", now) < _MIN_RESOLVE_AGE:   # too young — binds even under force
            continue
        if not force and now < p.get("resolve_ts", 0):
            continue
        if p.get("mode") == "rate":      # next-window rate vs the last-window baseline (acceleration)
            new = await asyncio.to_thread(_window_count, p["metric"], p["theme"], p.get("horizon_days", 14))
        else:                            # legacy cumulative-total predictions resolve unchanged
            new = await asyncio.to_thread(_metric_value, p["metric"], p["theme"])
        base = p.get("baseline", 0)
        thresh = max(1, base * 0.05)
        actual = "UP" if new > base + thresh else ("DOWN" if new < base - thresh else "FLAT")
        correct = actual == p["direction"]
        p["resolved_value"] = new
        p["actual"] = actual
        p["status"] = "correct" if correct else "incorrect"
        # Brier score for the called direction (prob = confidence, outcome = 1 if right): lower better,
        # 0.25 = a coin-flip 50% call. This is what makes the record CALIBRATION, not just hit-rate.
        p["brier"] = round((p.get("confidence", 0.5) - (1.0 if correct else 0.0)) ** 2, 4)
        p["resolved_ts"] = now
        # Stage 3 (accuracy loop closed onto the substrate): the external verdict credits the
        # brain-memories most relevant to this theme by whether the call was RIGHT.
        try:
            from agora.execution.inspeximus_bridge import credit_outcome
            credit_outcome(f"{p.get('theme', '')} {p.get('metric_label', '')}".strip(), good=correct)
        except Exception:
            pass
        resolved.append(p)
    if resolved:
        _save(preds)
    return resolved


def calibration() -> dict:
    """Agora's track record — hit-rate, mean Brier, and a confidence split. A resolution counts
    only if it matured at least the minimum age; a same-day re-measure is VOID (not skill)."""
    preds = _load()

    def _valid(p):
        return (p.get("status") in ("correct", "incorrect")
                and (p.get("resolved_ts", 0) - p.get("made_ts", 0)) >= _MIN_RESOLVE_AGE)

    done = [p for p in preds if _valid(p)]
    pending = [p for p in preds if p.get("status") == "pending"]
    voided = sum(1 for p in preds if p.get("status") in ("correct", "incorrect") and not _valid(p))
    correct = sum(1 for p in done if p["status"] == "correct")
    briers = [p["brier"] for p in done if isinstance(p.get("brier"), (int, float))]
    brier = round(sum(briers) / len(briers), 3) if briers else None
    bins = {"low (<50%)": [0, 0], "med (50-75%)": [0, 0], "high (>75%)": [0, 0]}
    for p in done:
        c = p.get("confidence", 0.5)
        b = "low (<50%)" if c < 0.5 else ("med (50-75%)" if c <= 0.75 else "high (>75%)")
        bins[b][0] += 1
        bins[b][1] += 1 if p["status"] == "correct" else 0
    return {"total": len(preds), "resolved": len(done), "pending": len(pending), "voided": voided,
            "correct": correct, "hit_rate": (correct / len(done)) if done else None,
            "brier": brier,
            "by_confidence": {k: f"{v[1]}/{v[0]}" for k, v in bins.items() if v[0]}}


def format_predictions(limit: int = 8) -> str:
    preds = sorted(_load(), key=lambda p: -p.get("made_ts", 0))
    cal = calibration()
    lines = ["🔮 *Prediction Ledger*"]
    if cal["resolved"]:
        hr = f"{cal['hit_rate']:.0%}" if cal["hit_rate"] is not None else "—"
        br = f" · Brier {cal['brier']:.3f}" if cal.get("brier") is not None else ""
        lines.append(f"_Track record: {cal['correct']}/{cal['resolved']} correct ({hr}){br} · "
                     f"{cal['pending']} pending_")
    else:
        lines.append(f"_Track record: 0 resolved yet · {cal['pending']} pending (maturing)_")
    icon = {"correct": "✅", "incorrect": "❌", "pending": "⏳"}
    for p in preds[:limit]:
        lines.append(f"{icon.get(p['status'], '•')} *{p['direction']}* {p['metric_label']} for "
                     f"_{p['theme'][:46]}_ ({p['confidence']:.0%})"
                     + (f" → was {p.get('actual')}" if p["status"] != "pending" else ""))
    return "\n".join(lines)
