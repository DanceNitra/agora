"""
The Observatory — Agora measures its own vital signs.

Two of Agora's own artifacts demanded this: the phase-transition insight (falsifier: chart
bridge-formation rate and falsifier-closure latency) and the observability hypothesis
(falsifier: track the dead-weight fraction monthly). This takes a periodic snapshot of the
system's vitals into a ledger, so every self-claim becomes longitudinally testable and the
whole organism becomes its own experiment.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".vitals.json"


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(snaps: list) -> None:
    try:
        _STORE.write_text(json.dumps(snaps, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


async def take_snapshot(db, vault_path: str) -> dict:
    """One vital-signs reading across every subsystem. Heavy-ish (full vault scan) — weekly."""
    import asyncio
    from agora.execution.memory_economy import score_notes

    notes = await asyncio.to_thread(score_notes, vault_path)
    total = len(notes)
    dead = [x for x in notes
            if not x["evergreen"] and x["age_days"] > 30 and x["chars"] < 700
            and x["inlinks"] == 0 and x["retrievals"] == 0 and x["value"] <= 2]
    links_total = sum(x["inlinks"] + x["outlinks"] for x in notes)
    orphans = sum(1 for x in notes if x["inlinks"] == 0 and x["outlinks"] == 0)

    # flywheel: open-question age + closure latency (the phase-transition signals)
    from agora.execution.flywheel import _load as fw_load
    now = time.time()
    qs = fw_load()
    open_qs = [q for q in qs if q.get("status") == "open"]
    deepened = [q for q in qs if q.get("status") == "deepened" and q.get("deepened_ts")]
    open_age = (sum(now - q.get("ts", now) for q in open_qs) / len(open_qs) / 86400) if open_qs else 0
    closure = (sum(q["deepened_ts"] - q.get("ts", q["deepened_ts"]) for q in deepened)
               / len(deepened) / 86400) if deepened else None

    from agora.execution.prediction_ledger import calibration
    cal = calibration()
    from agora.execution.exam import exam_history
    graded = [s for s in exam_history(20)["series"] if s.get("score") is not None]

    cur = await db.execute(
        "SELECT COUNT(*) AS n FROM collective_knowledge WHERE knowledge_type='discovery'")
    findings = (await cur.fetchone())["n"]
    agora_dir = Path(vault_path) / "04 Resources" / "Concepts" / "Agora Agents"
    verified = sum(1 for p in agora_dir.rglob("*.md") if p.name.startswith("✓")) \
        if agora_dir.is_dir() else 0

    snap = {"ts": now,
            "vault_notes": total,
            "dead_weight": len(dead),
            "dead_weight_frac": round(len(dead) / total, 4) if total else 0,
            "link_density": round(links_total / total, 2) if total else 0,
            "orphan_frac": round(orphans / total, 4) if total else 0,
            "flywheel_open": len(open_qs),
            "flywheel_open_age_days": round(open_age, 1),
            "flywheel_closure_days": round(closure, 1) if closure is not None else None,
            "exam_frac": (round(graded[-1]["score"] / graded[-1]["max"], 2) if graded else None),
            "hit_rate": (round(cal["hit_rate"], 2) if cal.get("hit_rate") is not None else None),
            "predictions_resolved": cal.get("resolved", 0),
            "findings_total": findings,
            "verified_notes": verified}
    snaps = _load()
    snaps.append(snap)
    _save(snaps[-260:])          # ~5 years of weekly readings
    return snap


def series(limit: int = 52) -> list:
    return _load()[-limit:]


def format_vitals(n: int = 6) -> str:
    """Telegram-sized vitals with deltas vs the previous reading."""
    snaps = _load()[-n:]
    if not snaps:
        return "🩺 _No vital signs recorded yet._"
    cur, prev = snaps[-1], (snaps[-2] if len(snaps) > 1 else None)

    def d(key):
        if prev is None or cur.get(key) is None or prev.get(key) is None:
            return ""
        diff = round(cur[key] - prev[key], 3)
        return f" ({'+' if diff >= 0 else ''}{diff})"

    lines = [f"🩺 *Agora vital signs* — {time.strftime('%Y-%m-%d', time.localtime(cur['ts']))}",
             f"vault *{cur['vault_notes']}* notes · dead-weight *{cur['dead_weight_frac']:.1%}*{d('dead_weight_frac')}",
             f"link density *{cur['link_density']}*{d('link_density')} · orphans *{cur['orphan_frac']:.1%}*{d('orphan_frac')}",
             f"flywheel open *{cur['flywheel_open']}* (avg {cur['flywheel_open_age_days']}d)"
             + (f" · closure {cur['flywheel_closure_days']}d" if cur.get("flywheel_closure_days") is not None else ""),
             f"exam *{cur['exam_frac']:.0%}*" if cur.get("exam_frac") is not None else "exam —",
             f"predictions hit-rate *{cur['hit_rate']:.0%}* ({cur['predictions_resolved']} resolved)"
             if cur.get("hit_rate") is not None else f"predictions resolved {cur['predictions_resolved']}",
             f"findings *{cur['findings_total']}* · verified notes *{cur['verified_notes']}*",
             f"_readings on record: {len(_load())}_"]
    return "\n".join(lines)
