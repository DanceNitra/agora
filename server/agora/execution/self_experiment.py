"""
The self-experiment — make the recursive self-improvement loop FALSIFIABLE.

The self-scientist asserts that tuning the seminar by Agora's own laws (raise external-grounding floor,
dedup harder) raises validated-yield. But it never ran the counterfactual, so by our OWN Identification
Threshold Law that claim is "confidently wrong"-prone: high activity, zero identification of the
controller's causal effect. (The observed yield trend is also confounded — it's dominated by Claude's
manual capstones, not the autonomous controller.)

This organ fixes that. The controller alternates two POLICY REGIMES on a fixed-length epoch schedule:
  • intervention — the law-derived policy (higher grounding floor, active cross-topic dedup);
  • control      — a neutral baseline (historical default floor, dedup effectively off).
The regime is a DETERMINISTIC function of wall-clock time from a persisted start_ts, evaluated
ON-READ by the seminar — so the schedule is independent of any loop cadence and survives restarts.

We then measure AUTONOMOUS validated-yield (the seminar's grounded/verified contributions, quality-
weighted, per active hour) SEPARATELY per regime, attributing each contribution to the regime active
when it was created. Claude's manual laws/replications are NOT in this channel, so the controller's
effect is identified, not confounded. The readout gives an effect size and an honest verdict —
improves / no detectable effect (null) / worse — turning "we have a self-improvement loop" into
"we measured whether it self-improves." The severe-test rule, applied to the loop itself.

Fully reversible: delete .self_experiment.json -> the seminar falls back to the static policy/default.
The control regime never starves the system (floor stays at the historical-safe 0.40).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STATE = Path(__file__).resolve().parents[2] / ".self_experiment.json"
_CONTRIB = Path(__file__).resolve().parents[2] / ".contributions.json"

EPOCH_HOURS_DEFAULT = 6.0
# The two regimes. Both are SAFE (control's 0.40 floor is the historical default; loosened dedup only
# admits more near-duplicates, it cannot break anything). The contrast is exactly the controller's
# thesis: does MORE external grounding + active dedup raise quality-weighted autonomous yield?
POLICIES = {
    "intervention": {"grounding_floor": 0.50, "dedup_threshold": 0.62},
    "control":      {"grounding_floor": 0.40, "dedup_threshold": 0.95},
}
# quality weights for autonomous yield (match self_scientist.W for contributions)
_W_GROUNDED, _W_VERIFIED = 0.05, 0.25
_MIN_EPOCHS = 2        # per regime, before any verdict
_MIN_CONTRIB = 15      # per regime, before any verdict
_EFFECT_BAND = 0.10    # +-10% on yield/hr counts as "no detectable effect"


def _truthy(x) -> bool:
    return str(x).lower() == "true"


def _read_state() -> dict | None:
    try:
        s = json.loads(_STATE.read_text(encoding="utf-8"))
        return s if s.get("enabled", True) else None
    except Exception:
        return None


def start(epoch_hours: float = EPOCH_HOURS_DEFAULT) -> dict:
    """Begin the experiment (idempotent — keeps the original start_ts if already running)."""
    s = None
    try:
        s = json.loads(_STATE.read_text(encoding="utf-8"))
    except Exception:
        s = None
    if not s or "start_ts" not in s:
        s = {"start_ts": time.time(), "epoch_hours": float(epoch_hours), "enabled": True}
        try:
            _STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass
    return s


def regime_at(ts: float, state: dict) -> str:
    """Deterministic alternating schedule: epoch 0 = intervention, 1 = control, 2 = intervention, ..."""
    epoch_sec = float(state.get("epoch_hours", EPOCH_HOURS_DEFAULT)) * 3600.0
    if epoch_sec <= 0 or ts < state["start_ts"]:
        return "intervention"
    epoch = int((ts - state["start_ts"]) // epoch_sec)
    return "intervention" if epoch % 2 == 0 else "control"


def active_policy() -> dict | None:
    """The policy the seminar should use RIGHT NOW (None -> experiment off, use static/default)."""
    s = _read_state()
    if not s:
        return None
    r = regime_at(time.time(), s)
    pol = dict(POLICIES[r])
    pol["regime"] = r
    return pol


def _hours_active(state: dict, now: float) -> dict:
    """Exact active-hours per regime over [start_ts, now] under the alternating schedule."""
    epoch_sec = float(state.get("epoch_hours", EPOCH_HOURS_DEFAULT)) * 3600.0
    out = {"intervention": 0.0, "control": 0.0}
    epochs = {"intervention": 0, "control": 0}
    if epoch_sec <= 0 or now <= state["start_ts"]:
        return {"hours": out, "epochs": epochs}
    cur = int((now - state["start_ts"]) // epoch_sec)
    for e in range(0, min(cur + 1, 20000)):
        e_start = state["start_ts"] + e * epoch_sec
        e_end = min(now, e_start + epoch_sec)
        dur = max(0.0, e_end - e_start)
        r = "intervention" if e % 2 == 0 else "control"
        out[r] += dur / 3600.0
        if dur > 0:
            epochs[r] += 1
    return {"hours": out, "epochs": epochs}


def readout() -> dict:
    """The verdict: did the controller's intervention raise AUTONOMOUS validated-yield vs control?"""
    s = _read_state()
    if not s:
        return {"status": "not_started"}
    now = time.time()
    ha = _hours_active(s, now)
    hours, epochs = ha["hours"], ha["epochs"]
    try:
        contribs = json.loads(_CONTRIB.read_text(encoding="utf-8"))
    except Exception:
        contribs = []
    buckets: dict = {"intervention": {"n": 0, "grounded": 0, "verified": 0},
                     "control": {"n": 0, "grounded": 0, "verified": 0}}
    for c in contribs:
        ts = float(c.get("ts", 0) or 0)
        if ts < s["start_ts"]:
            continue
        r = regime_at(ts, s)
        b = buckets[r]
        b["n"] += 1
        if _truthy(c.get("grounded")):
            b["grounded"] += 1
        if _truthy(c.get("verified")):
            b["verified"] += 1

    def _metrics(r: str) -> dict:
        b = buckets[r]
        h = hours[r] or 1e-9
        qy = _W_GROUNDED * b["grounded"] + _W_VERIFIED * b["verified"]
        return {"n": b["n"], "grounded": b["grounded"], "verified": b["verified"],
                "hours_active": round(hours[r], 2), "epochs": epochs[r],
                "grounded_rate": round(b["grounded"] / b["n"], 3) if b["n"] else None,
                "verified_rate": round(b["verified"] / b["n"], 3) if b["n"] else None,
                "quality_yield": round(qy, 3), "yield_per_hr": round(qy / h, 4)}

    iv, ct = _metrics("intervention"), _metrics("control")
    enough = (iv["epochs"] >= _MIN_EPOCHS and ct["epochs"] >= _MIN_EPOCHS
              and iv["n"] >= _MIN_CONTRIB and ct["n"] >= _MIN_CONTRIB)
    effect = None
    verdict = "running — insufficient data (need >=2 epochs and >=15 contributions per regime)"
    if enough:
        ratio = iv["yield_per_hr"] / (ct["yield_per_hr"] or 1e-9)
        gdiff = (iv["grounded_rate"] or 0) - (ct["grounded_rate"] or 0)
        effect = {"yield_per_hr_ratio": round(ratio, 3),
                  "grounded_rate_delta": round(gdiff, 3)}
        if ratio > 1 + _EFFECT_BAND:
            verdict = (f"INTERVENTION IMPROVES autonomous yield: {ratio:.2f}x per active hour "
                       f"(grounded-rate delta {gdiff:+.3f}). The controller's law-derived tuning has a "
                       f"measured positive effect — recursive self-improvement is demonstrated, not asserted.")
        elif ratio < 1 - _EFFECT_BAND:
            verdict = (f"INTERVENTION WORSE: {ratio:.2f}x per active hour. The current lever HARMS "
                       f"autonomous yield — honest negative result; the controller must be redesigned.")
        else:
            verdict = (f"NO DETECTABLE EFFECT (null): {ratio:.2f}x per active hour (within +-{int(_EFFECT_BAND*100)}%). "
                       f"The current lever does not move autonomous yield — an honest null; the loop is "
                       f"NOT yet a working self-improver on this knob.")
    return {"status": "ok", "started": s["start_ts"], "epoch_hours": s.get("epoch_hours"),
            "elapsed_hours": round((now - s["start_ts"]) / 3600.0, 2),
            "current_regime": regime_at(now, s),
            "intervention": iv, "control": ct, "effect": effect, "enough_data": enough,
            "verdict": verdict,
            "caveat": "Identified channel: AUTONOMOUS seminar contributions only — Claude's manual "
                      "laws/replications are excluded, so this isolates the controller's causal effect."}


def format_self_experiment() -> str:
    r = readout()
    if r.get("status") != "ok":
        return "🧪 *Self-experiment*: not started yet."
    iv, ct = r["intervention"], r["control"]
    return "\n".join([
        "🧪 *Self-experiment* — is the self-improvement loop real? (controlled, autonomous channel)",
        f"• elapsed {r['elapsed_hours']}h, now in *{r['current_regime']}* (epoch {r['epoch_hours']}h)",
        f"• intervention: yield/hr {iv['yield_per_hr']} (n={iv['n']}, {iv['epochs']} epochs, grounded {iv['grounded_rate']})",
        f"• control:      yield/hr {ct['yield_per_hr']} (n={ct['n']}, {ct['epochs']} epochs, grounded {ct['grounded_rate']})",
        f"• {r['verdict']}",
    ])
