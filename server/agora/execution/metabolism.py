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
_SKIP_MODULES = {"llm_client", "metabolism", "model_router", "main"}
# Agora subsystems whose modules count as organs when found on the call stack.
_ORGAN_NAMESPACES = (".execution.", ".api.", ".agent_os.", ".controller.",
                     ".coordination.", ".harness.", ".scheduler.", ".dungeon_os.")

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
    falling back to the nearest agora module up the stack, then 'unknown'.

    The stack-walk recognises every Agora subsystem that makes LLM calls — not just the HTTP
    routes (.api.) and research organs (.execution.), but also the autonomous tick-loop
    cognition (.agent_os., .controller., .coordination., .harness., .scheduler., .dungeon_os.).
    Before this was added, the background tick loop's calls climbed past every matched namespace
    to agora.main and collapsed into 'unknown' — ~70% of all spend, invisibly."""
    ctx = _ORGAN.get()
    if ctx:
        return ctx
    try:
        for fr in inspect.stack()[2:16]:
            mod = fr.frame.f_globals.get("__name__", "")
            if any(ns in mod for ns in _ORGAN_NAMESPACES):
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
    # the 2026-06-10 organs — value read from the ledgers each one already keeps
    bounty = j(".bounty.json", [])
    pts["bounty"] = 3.0 * sum(1 for x in bounty if x.get("kill")) \
        + 0.75 * sum(1 for x in bounty if not x.get("kill"))
    reps = j(".replications.json", [])
    # Anti-manufactured-FAILED guard (Crucible integrity): FAILED and REPRODUCED are valued EQUALLY.
    # Paying more for FAILED (was 4.0 vs 2.0) created a perverse incentive to MANUFACTURE failures (rig a
    # weak baseline / underpowered run) and poison the Crucible, whose entire value is that its FAILEDs are
    # honest. The reward is now verdict-neutral - replicate honestly and let the evidence decide. FAILED's
    # higher DISTRIBUTION value is handled separately (the falsified digest + owner approval), not by the
    # agent reward. NOT_COMPUTABLE stays lower (inconclusive).
    pts["replication"] = (2.5 * sum(1 for r in reps if r.get("outcome") in ("FAILED", "REPRODUCED"))
                          + 0.5 * sum(1 for r in reps if r.get("outcome") == "NOT_COMPUTABLE"))
    ana = j(".analogies.json", [])
    pts["analogy"] = 4.0 * sum(1 for a in ana if "survived" in (a.get("outcome") or "").lower()) \
        + 1.0 * sum(1 for a in ana if "survived" not in (a.get("outcome") or "").lower())
    carto = j(".cartography.json", [])
    pts["cartography"] = 4.0 * sum(1 for c in carto if c.get("status") == "bridged") \
        + 1.0 * sum(1 for c in carto if c.get("status") == "charted")
    graves = j(".graveyard.json", [])
    pts["graveyard"] = 1.0 * len(graves) + 2.0 * sum(1 for g in graves
                                                     if g.get("status") == "resurrected")
    press = j(".press.json", [])
    pts["press"] = 5.0 * sum(1 for p in press if p.get("status") == "published") \
        + 1.0 * sum(1 for p in press if p.get("status") != "published")
    scout = j(".scout.json", [])
    pts["scout"] = 2.0 * sum(1 for s in scout if s.get("outcome") == "drafted") \
        + 0.5 * sum(1 for s in scout if s.get("outcome") != "drafted")
    fly = j(".flywheel.json", [])
    pts["flywheel"] = 2.0 * sum(1 for q in fly if q.get("status") == "deepened")
    camps = j(".campaigns.json", [])
    pts["campaigns"] = 3.0 * sum(1 for c in camps if c.get("status") == "complete")
    # Envoy — outward reputation, read from the last sweep's cache (no network here): 2 per human
    # reply earned + 1 per reaction across all posted threads.
    env_seen = j(".envoy.json", {}).get("seen", {})
    pts["envoy"] = sum(2.0 * v.get("replies", 0) + 1.0 * v.get("our_reactions", 0)
                       for v in env_seen.values())
    # the Seminar — agent conversation/brainstorm now must terminate in a recorded, grounded
    # Contribution; its value is read from that ledger so 'agent-dialogue' spend finally scores.
    try:
        from agora.execution.seminar import value_points as _seminar_value
        pts["dialogue"] = _seminar_value()
    except Exception:
        pts["dialogue"] = 0.0
    return pts


# spend keys are ROUTE segments (set by the middleware); value keys are LEDGER buckets.
# This map joins the clean pairs so ROI is computed on real correspondences, not key luck.
_SPEND2VALUE = {
    "verify-findings": "mastery_verified",
    "exam": "exam",
    "predict-tournament": "prediction_ledger",
    "predict-baseline": "prediction_ledger",
    "oracle": "oracle",
    "salon": "salon",
    "tutor": "tutor",
    "contradictions": "contradictions",
    "hypothesize": "flywheel",          # hypotheses' downstream value lands as deepened falsifiers
    "analogy-inputs": "analogy",
    "replication-target": "replication",
    "cartography-hole": "cartography",
    "scout-target": "scout",
    "press-target": "press",
    "agent-dialogue": "dialogue",       # conversations + brainstorms → Seminar contributions
}


def roi_report() -> dict:
    """Per-organ spend + value + ROI (value points per kilotoken)."""
    spend = _load()
    value = value_snapshot()
    organs = {}
    for organ, e in spend.items():
        ktok = (e["tok_in"] + e["tok_out"]) / 1000.0
        v = value.get(_SPEND2VALUE.get(organ, organ), 0.0)
        organs[organ] = {"calls": e["calls"], "ktok": round(ktok, 1), "value": v,
                         "roi": round(v / ktok, 2) if ktok > 0.05 else None}
    total_ktok = round(sum(o["ktok"] for o in organs.values()), 1)
    mapped = set(_SPEND2VALUE.get(o, o) for o in organs)
    unmetered = {k: v for k, v in value.items() if k not in mapped and v}
    # HOW MUCH OF THIS RANKING IS ACTUALLY CONNECTED. `unmetered_value` has always been computed here
    # and never shown, so the CFO line published "best X / worst Y" while a third of the recorded value
    # had no spend row to pair with. Measured 2026-08-17: 3,912.5 unattributable points against 8,708
    # attributed (31%), and of 17 spend organs exactly ONE resolved to a value key -- every other organ
    # reported ROI 0.000 not because it produced nothing but because its value lives under a name the
    # mapping no longer reaches.
    #
    # The cause is a naming drift, not a missing writer: the spend label is a ROUTE name when the HTTP
    # middleware sets one and a MODULE name otherwise, while _SPEND2VALUE was written entirely against
    # route names (verify-findings, replication-target, cartography-hole). Today's spend is mostly
    # module names (seminar, scan, match, directions). The pairs are not guessed back into place here,
    # because inventing an attribution is worse than admitting there is none -- what ships is the
    # ADMISSION, so a reader can see the ranking's coverage before trusting its order.
    attributed = sum(o["value"] for o in organs.values())
    priced = sum(1 for o in organs.values() if o["value"])
    return {"organs": organs, "total_ktok": total_ktok, "unmetered_value": unmetered,
            "unmetered_total": round(sum(unmetered.values()), 1),
            "attributed_total": round(attributed, 1),
            "organs_with_value": priced, "organs_total": len(organs),
            "value_coverage": round(attributed / (attributed + sum(unmetered.values())), 3)
            if (attributed + sum(unmetered.values())) else None}


def format_metabolism() -> str:
    r = roi_report()
    if not r["organs"]:
        return "🔥 _No metabolic data yet — the meter starts now._"
    lines = [f"🔥 *Metabolism* — {r['total_ktok']}k tokens metered"]
    ranked = sorted(r["organs"].items(), key=lambda kv: -(kv[1]["ktok"]))
    for organ, o in ranked[:10]:
        roi = f"ROI {o['roi']}" if o["roi"] is not None else "—"
        lines.append(f"• {organ}: {o['ktok']}k tok / {o['calls']} calls · value {o['value']:g} · {roi}")
    # The coverage line goes FIRST among the notes, because it decides whether the ROI column above is
    # a ranking or a rumour.
    if r.get("organs_total"):
        lines.append(f"\n⚖️ _value coverage:_ {r['organs_with_value']}/{r['organs_total']} organs "
                     f"resolve to a value ledger; {r['unmetered_total']:g} points "
                     f"({100 * (1 - (r['value_coverage'] or 1)):.0f}%) have no spend row to pair with, "
                     f"so a 0.000 below means UNMEASURED, not unproductive.")
    if r.get("unmetered_value"):
        top = sorted(r["unmetered_value"].items(), key=lambda kv: -kv[1])[:5]
        lines.append("_unattributed:_ " + " · ".join(f"{k} {v:g}" for k, v in top))
    return "\n".join(lines)
