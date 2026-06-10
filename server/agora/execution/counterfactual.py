"""
The Counterfactual Self — causal inference turned inward.

The measurement dossier's hardest recommendation was a within-system randomized comparison.
This is the honest version available today: REPLAY the system's own recorded history under
alternative policies and score each against what actually happened. Three replayable traces:

  1. Predictions — every resolved prediction re-scored under counterfactual forecasting
     policies (always-FLAT, always-UP, lazy-0.5, as-played), Brier on the SAME resolved set.
  2. The editorial trace — done inbox tasks classified shipped vs skipped; the counterfactual
     'gatekeeper from day 0' counts the cycles that upstream filtering would have saved.
  3. Tournament — once calls resolve: follow-majority vs follow-best-agent vs as-played.

Caveat carried honestly: same-trace replay estimates effects on OBSERVED cases only — it
cannot see themes a different policy would have generated. It bounds, not settles.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[2]


def _j(name, default):
    try:
        return json.loads((_SERVER / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def replay_predictions() -> dict:
    """Brier of counterfactual forecasting policies on the SAME resolved predictions."""
    preds = [p for p in _j(".predictions.json", [])
             if p.get("status") in ("correct", "incorrect") and p.get("actual")]
    if not preds:
        return {"resolved": 0}

    def prob_up(p, policy):
        conf, d = p.get("confidence", 0.5), p.get("direction")
        if policy == "as_played":
            return conf if d == "UP" else (1 - conf if d == "DOWN" else 0.34)
        if policy == "always_flat_lazy":
            return 0.34                      # 'no move' with uniform 1/3 spread to UP
        if policy == "always_up_60":
            return 0.60
        if policy == "coin":
            return 0.50
        return 0.34

    out = {}
    for policy in ("as_played", "always_flat_lazy", "always_up_60", "coin"):
        sq = []
        for p in preds:
            target = 1.0 if p["actual"] == "UP" else 0.0
            sq.append((prob_up(p, policy) - target) ** 2)
        out[policy] = round(sum(sq) / len(sq), 4)
    return {"resolved": len(preds), "brier_by_policy": out,
            "note": "UP-probability framing; actuals so far: "
                    + ",".join(p["actual"] for p in preds)}


def replay_editorial() -> dict:
    """The editorial trace: how many completed cycles were skips, and how many of those the
    upstream Gatekeeper (had it existed from day 0) would have prevented."""
    tasks = [t for t in _j(".claude_inbox.json", []) if t.get("status") == "done"]
    skips = [t for t in tasks if re.search(r"editorial skip|duplicate|skipped|vacuous|off-priority",
                                           (t.get("result") or ""), re.I)]
    shipped = len(tasks) - len(skips)
    # which skipped themes repeat earlier-skipped themes (= preventable by the ledger)
    seen, preventable = [], 0
    for t in skips:
        words = {w for w in re.findall(r"[a-z]+", (t.get("text") or "").lower()) if len(w) > 3}
        if any(len(words & s) >= 2 and len(words & s) >= 0.5 * len(words or {1}) for s in seen):
            preventable += 1
        seen.append(words)
    return {"done_tasks": len(tasks), "shipped": shipped, "skips": len(skips),
            "skip_rate": round(len(skips) / len(tasks), 3) if tasks else None,
            "preventable_by_gatekeeper": preventable}


def replay_tournament() -> dict:
    """Once tournament records resolve: follow-majority vs follow-best vs as-played."""
    recs = [p for p in _j(".predictions.json", [])
            if p.get("by") == "tournament" and p.get("status") in ("correct", "incorrect")]
    if not recs:
        return {"resolved": 0, "note": "no tournament resolutions yet — policies unrankable"}
    policies = {"majority_as_played": 0, "follow_kael": 0, "follow_voss": 0}
    for r in recs:
        actual = r.get("actual")
        policies["majority_as_played"] += int(r.get("direction") == actual)
        calls = {c["agent"]: c["direction"] for c in r.get("calls", [])}
        policies["follow_kael"] += int(calls.get("Kael") == actual)
        policies["follow_voss"] += int(calls.get("Voss") == actual)
    return {"resolved": len(recs),
            "hits_by_policy": {k: f"{v}/{len(recs)}" for k, v in policies.items()}}


def full_report() -> dict:
    return {"predictions": replay_predictions(), "editorial": replay_editorial(),
            "tournament": replay_tournament()}


def format_counterfactual() -> str:
    r = full_report()
    lines = ["🔁 *The Counterfactual Self* — history replayed under other policies"]
    p = r["predictions"]
    if p.get("resolved"):
        b = p["brier_by_policy"]
        ranked = sorted(b.items(), key=lambda kv: kv[1])
        lines.append(f"Predictions (n={p['resolved']} resolved, Brier↓): "
                     + " · ".join(f"{k} {v}" for k, v in ranked))
    e = r["editorial"]
    if e.get("done_tasks"):
        lines.append(f"Editorial: {e['shipped']} shipped / {e['skips']} skips "
                     f"(skip rate {e['skip_rate']:.0%}); gatekeeper-from-day-0 would have "
                     f"prevented {e['preventable_by_gatekeeper']} repeat skips")
    t = r["tournament"]
    if t.get("resolved"):
        lines.append("Tournament: " + " · ".join(f"{k} {v}" for k, v in t["hits_by_policy"].items()))
    else:
        lines.append("_Tournament: no resolutions yet._")
    return "\n".join(lines)
