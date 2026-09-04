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
    """Meter one SUCCESSFUL LLM call against its organ (called from inside call_llm).

    `first_ts` is recorded because without it a total is not a rate. Measured 2026-09-04: the store
    held 8.75M tokens and every organ carried only a LAST-call timestamp, so nobody could say
    whether that was a day of spend or three months of it, and the same number supports either
    "we are fine" or "stop everything".
    """
    _bump(_caller_organ(), 1, max(0, int(prompt_tokens or 0)), max(0, int(completion_tokens or 0)), 0)


def record_failure(note: str = "") -> None:
    """Meter one FAILED call: a refusal, a rate limit, a timeout, an empty completion.

    A failure costs the provider's quota and our wall-clock and, before this, left no trace at all:
    the meter sat on the success path only. So a retry storm against a 429 was invisible in the one
    artifact meant to explain where the quota went, which is how a weekly limit arrived unannounced.
    """
    _bump(_caller_organ(), 0, 0, 0, 1, note)


def _bump(organ, calls, tin, tout, fails, note=""):
    try:
        d = _load()
        e = d.setdefault(organ, {"calls": 0, "tok_in": 0, "tok_out": 0, "fails": 0})
        e["calls"] += calls
        e["tok_in"] += tin
        e["tok_out"] += tout
        e["fails"] = e.get("fails", 0) + fails
        now = time.time()
        e.setdefault("first_ts", now)
        e["ts"] = now
        if note:
            e["last_fail"] = str(note)[:120]
        _save(d)
    except Exception:
        pass


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
    "seminar": "dialogue",              # the same organ under its MODULE name, see _caller_organ
}

# Organs that will never have a value ledger of their own, each with the reason. An organ that is
# in neither this map nor _SPEND2VALUE is UNCLASSIFIED, which is reported as a defect rather than
# quietly ranked at ROI 0.0.
#
# WHY THIS EXISTS. `roi_report` used to fall back to `value.get(organ, 0.0)`, so an organ whose
# value key the mapping could not reach scored 0.0 and sat in the ranking next to an organ that
# genuinely produced nothing. Those are opposite diagnoses wearing one number. Measured 2026-09-04:
# all 10 spend organs read ROI 0.0 while 3,919 value points sat in the ledgers, because the spend
# label is a ROUTE name when the HTTP middleware sets one and a MODULE name otherwise, and the map
# was written entirely against route names. The churn detector reads this number, so the drift also
# left it unable to tell a wasteful organ from an unmapped one.
_NO_VALUE_LEDGER = {
    "unknown": "the stack walk found no Agora namespace, so this spend is unattributable by "
               "construction; it is a gap in the meter, not an organ",
    "frontier-seed": "a SELECTOR: it picks the next research direction, and whatever value follows "
                     "is recorded by the organ that acts on the direction, never here",
    "directions": "a SELECTOR, same shape as frontier-seed",
    "match": "a ROUTER: it matches work to an agent; the value lands in the work",
    "scan": "an INTAKE path: it reads sources into the pool that other organs draw from",
    "vault-note": "the write path into the vault; the note's value is scored by the organs that "
                  "later cite it, not at the moment of writing",
    "empirical-test": "a MEASUREMENT run; its result is recorded by the organ that asked for it",
    "self-upgrades": "changes to our own code, whose value is the repository, not a ledger",
    "agent-think": "roleplay flavour, deliberately value-free and already canned by default",
    "promote-findings": "a PROMOTION path; the promoted finding is scored where it lands",
}


def roi_report() -> dict:
    """Per-organ spend, value and ROI, with every organ CLASSIFIED so a 0.0 cannot lie.

    Three classes, and the difference between them is the whole point:
      * `priced`         has a value ledger; its ROI is a real number and churn can judge it.
      * `upstream`       named in `_NO_VALUE_LEDGER` with a reason; it really does spend, and its
                         value really is recorded elsewhere, so an ROI here would be a fiction.
      * `unclassified`   in neither map. Reported as a defect, never ranked.

    The number that was missing entirely is `judgeable_share`: what fraction of all spend sits in
    an organ whose output we can actually price.
    """
    spend = _load()
    value = value_snapshot()
    organs, unclassified = {}, []
    for organ, e in spend.items():
        ktok = (e["tok_in"] + e["tok_out"]) / 1000.0
        row = {"calls": e["calls"], "ktok": round(ktok, 1), "fails": e.get("fails", 0),
               "first_ts": e.get("first_ts"), "last_ts": e.get("ts")}
        if organ in _SPEND2VALUE:
            v = value.get(_SPEND2VALUE[organ], 0.0)
            row.update(cls="priced", value_key=_SPEND2VALUE[organ], value=v,
                       roi=round(v / ktok, 2) if ktok > 0.05 else None)
        elif organ in _NO_VALUE_LEDGER:
            row.update(cls="upstream", value=None, roi=None, why=_NO_VALUE_LEDGER[organ])
        else:
            row.update(cls="unclassified", value=None, roi=None,
                       why="no value key and no declared reason; classify it before trusting any "
                           "ranking that includes it")
            unclassified.append(organ)
        organs[organ] = row

    total_ktok = round(sum(o["ktok"] for o in organs.values()), 1)
    judgeable = round(sum(o["ktok"] for o in organs.values() if o["cls"] == "priced"), 1)
    # The window. A total without one is not a rate, and the same 8.75M tokens reads as calm or as
    # an emergency depending on whether it covers a day or three months.
    firsts = [o["first_ts"] for o in organs.values() if o.get("first_ts")]
    lasts = [o["last_ts"] for o in organs.values() if o.get("last_ts")]
    window_days = round((max(lasts) - min(firsts)) / 86400.0, 1) if firsts and lasts else None
    mapped = {_SPEND2VALUE[o] for o in organs if o in _SPEND2VALUE}
    unmetered = {k: v for k, v in value.items() if k not in mapped and v}
    attributed = sum(o.get("value") or 0.0 for o in organs.values())
    return {"organs": organs, "total_ktok": total_ktok,
            "window_days": window_days,
            "ktok_per_day": round(total_ktok / window_days, 1) if window_days else None,
            "fails_total": sum(o["fails"] for o in organs.values()),
            "judgeable_ktok": judgeable,
            "judgeable_share": round(judgeable / total_ktok, 3) if total_ktok else None,
            "unclassified": unclassified,
            "unmetered_value": unmetered,
            "unmetered_total": round(sum(unmetered.values()), 1),
            "attributed_total": round(attributed, 1),
            "organs_with_value": sum(1 for o in organs.values() if o.get("value")),
            "organs_total": len(organs),
            "value_coverage": round(attributed / (attributed + sum(unmetered.values())), 3)
            if (attributed + sum(unmetered.values())) else None}


def format_metabolism() -> str:
    r = roi_report()
    if not r["organs"]:
        return "No metabolic data yet -- the meter starts now."
    share = r.get("judgeable_share")
    win = ("over %s days, %sk/day" % (r["window_days"], r["ktok_per_day"])
           if r.get("window_days") else "over an UNKNOWN window (no organ carries a first_ts yet)")
    out = ["*Metabolism* -- %sk tokens metered %s, %.0f%% of it in an organ we can price"
           % (r["total_ktok"], win, (share * 100) if share is not None else 0.0)]
    if r.get("fails_total"):
        out.append("failed calls: %d (they cost quota and produce nothing)" % r["fails_total"])
    ranked = sorted(r["organs"].items(), key=lambda kv: -(kv[1]["ktok"]))
    for organ, o in ranked[:10]:
        head = "- %s: %sk tok / %s calls" % (organ, o["ktok"], o["calls"])
        if o["cls"] == "priced":
            roi = ("ROI %s" % o["roi"]) if o["roi"] is not None else "ROI --"
            out.append("%s | value %g | %s" % (head, o["value"], roi))
        else:
            label = "NOT PRICED" if o["cls"] == "upstream" else "UNCLASSIFIED"
            out.append("%s | %s (%s)" % (head, label, (o.get("why") or "")[:60]))
    # This line decides whether the ROI column above is a ranking or a rumour, so it goes first among
    # the notes. An unpriced organ is not a zero-value organ; it is one we cannot judge.
    out.append("")
    out.append("priced: %s/%s organs resolve to a value ledger. The rest are not zero-value, they "
               "are unpriced, and their spend is %.0fk tokens."
               % (r["organs_with_value"], r["organs_total"],
                  r["total_ktok"] - r["judgeable_ktok"]))
    if r.get("unclassified"):
        out.append("UNCLASSIFIED organs (fix the map, do not read their ROI): "
                   + ", ".join(r["unclassified"]))
    if r.get("unmetered_value"):
        top = sorted(r["unmetered_value"].items(), key=lambda kv: -kv[1])[:5]
        out.append("value with no spend row: " + " | ".join("%s %g" % (k, v) for k, v in top))
    return chr(10).join(out)
