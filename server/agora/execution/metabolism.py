"""
The Metabolism — cognition that knows what it costs.

Every LLM call is metered and attributed to the ORGAN that made it — automatically, from the
call stack (no call-site changes anywhere). Value points are read from the ledgers the organs
already keep (exam scores, verified findings, tournament hits, salon claims, contradictions,
tutor reviews), so each organ gets an ROI: value per kilotoken. The Custodian Principle
applied to the system's own energy: instrument first, govern next (the Attention Economy
gets the cost side once this ledger has history).
"""
from __future__ import annotations

import contextvars
import inspect
import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".metabolism.json"
_SKIP_MODULES = {"llm_client", "metabolism", "model_router"}

# Set by the HTTP middleware from the route path; asyncio.to_thread copies the context into the
# worker thread, so call_llm can read it even when it runs via to_thread (the dominant pattern).
_ORGAN: contextvars.ContextVar[str] = contextvars.ContextVar("agora_organ", default="")


def set_organ(name: str) -> None:
    _ORGAN.set((name or "")[:30])


def _load() -> dict:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d: dict) -> None:
    try:
        _STORE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _caller_organ() -> str:
    """The organ: the route context (set by the HTTP middleware, copied into worker threads),
    falling back to the nearest agora module up the stack, then 'unknown'."""
    ctx = _ORGAN.get()
    if ctx:
        return ctx
    try:
        for fr in inspect.stack()[2:14]:
            mod = fr.frame.f_globals.get("__name__", "")
            if ".execution." in mod or ".api." in mod:
                name = mod.rsplit(".", 1)[-1]
                if name not in _SKIP_MODULES:
                    return name[:30]
    except Exception:
        pass
    return "unknown"


def record_call(prompt_tokens: int, completion_tokens: int) -> None:
    """Meter one LLM call against its organ (called from inside call_llm)."""
    organ = _caller_organ()
    d = _load()
    e = d.setdefault(organ, {"calls": 0, "tok_in": 0, "tok_out": 0})
    e["calls"] += 1
    e["tok_in"] += max(0, int(prompt_tokens or 0))
    e["tok_out"] += max(0, int(completion_tokens or 0))
    e["ts"] = time.time()
    _save(d)


def value_snapshot() -> dict:
    """Value points per organ, read from the ledgers they already keep."""
    server = Path(__file__).resolve().parents[2]

    def j(name, default):
        try:
            return json.loads((server / name).read_text(encoding="utf-8"))
        except Exception:
            return default
    pts: dict[str, float] = {}
    exams = [e for e in j(".exams.json", []) if e.get("score") is not None]
    pts["exam"] = float(sum(e["score"] for e in exams))
    preds = j(".predictions.json", [])
    pts["prediction_ledger"] = 3.0 * sum(1 for p in preds if p.get("status") == "correct")
    pts["mastery_verified"] = 2.0 * sum(s.get("verified", 0) for s in j(".mastery.json", {}).values())
    pts["salon"] = 1.0 * len(j(".salon.json", {}).get("claims", []))
    cons = j(".contradictions.json", [])
    pts["contradictions"] = 2.0 * sum(1 for c in cons if c.get("contradict"))
    tutor_reviews = sum(len(c.get("history", [])) for c in j(".tutor.json", {}).get("cards", []))
    pts["tutor"] = 0.5 * tutor_reviews
    oracle = j(".oracle.json", [])
    pts["oracle"] = 1.0 * len(oracle) + 3.0 * sum(1 for p in oracle if p.get("beat_market"))
    return pts


def roi_report() -> dict:
    """Per-organ spend + value + ROI (value points per kilotoken)."""
    spend = _load()
    value = value_snapshot()
    organs = {}
    for organ, e in spend.items():
        ktok = (e["tok_in"] + e["tok_out"]) / 1000.0
        v = value.get(organ, 0.0)
        organs[organ] = {"calls": e["calls"], "ktok": round(ktok, 1), "value": v,
                         "roi": round(v / ktok, 2) if ktok > 0.05 else None}
    total_ktok = round(sum(o["ktok"] for o in organs.values()), 1)
    return {"organs": organs, "total_ktok": total_ktok,
            "unmetered_value": {k: v for k, v in value.items() if k not in organs and v}}


def format_metabolism() -> str:
    r = roi_report()
    if not r["organs"]:
        return "🔥 _No metabolic data yet — the meter starts now._"
    lines = [f"🔥 *Metabolism* — {r['total_ktok']}k tokens metered"]
    ranked = sorted(r["organs"].items(), key=lambda kv: -(kv[1]["ktok"]))
    for organ, o in ranked[:10]:
        roi = f"ROI {o['roi']}" if o["roi"] is not None else "—"
        lines.append(f"• {organ}: {o['ktok']}k tok / {o['calls']} calls · value {o['value']:g} · {roi}")
    return "\n".join(lines)
