"""
The Roadmap — King Aldric's executive view.

Every other organ produces knowledge; Aldric produces DIRECTION. He reads the whole organism's
instrument panel — which organs are yielding, which are idle, where the bottleneck is — and
turns it into ONE concrete, data-backed next move for the owner. This is the strategic layer
that lets priorities be set by measurement instead of guesswork: the company looking at its own
P&L and deciding what to build next.
"""
from __future__ import annotations

import time


def _age_h(ts: float, now: float) -> float:
    return round((now - ts) / 3600, 1) if ts else 1e9


def gather() -> dict:
    """The organ instrument panel: per-organ yield + freshness, plus the global tensions."""
    from agora.execution.bounty import scores as bounty_scores, _load as bounty_load
    from agora.execution.replication import _load as rep_load
    from agora.execution.analogy_forge import _load as analogy_load
    from agora.execution.cartography import _load as carto_load
    from agora.execution.graveyard import _load as grave_load
    from agora.execution.synthesis_detector import signals as syn_signals
    from agora.execution.flywheel import stats as fw_stats
    from agora.execution.forge import _load as forge_load
    now = time.time()

    def organ(items, label):
        ts = [x.get("ts", 0) for x in items if x.get("ts")]
        return {"organ": label, "total": len(items),
                "recent_48h": sum(1 for t in ts if t >= now - 2 * 86400),
                "idle_h": _age_h(max(ts), now) if ts else 1e9}

    rep = rep_load()
    organs = [
        organ(bounty_load(), "Bounty/Court (belief kills)"),
        organ(rep, "Replication (Rooke)"),
        organ(analogy_load(), "Analogy Forge"),
        organ(carto_load(), "Cartography (Wren)"),
        organ(grave_load(), "Graveyard"),
    ]
    syn = syn_signals()
    fw = fw_stats()
    forge_open = sum(1 for g in forge_load() if g.get("status") == "open")
    rep_fail = sum(1 for r in rep if r.get("outcome") == "FAILED")

    # the bottleneck = the organ idle the longest (excluding never-run, which are "not wired yet")
    ran = [o for o in organs if o["idle_h"] < 1e8]
    bottleneck = max(ran, key=lambda o: o["idle_h"])["organ"] if ran else "(no organ has produced yet)"

    # CFO view — value per kilotoken from the Metabolism ledger (only organs with real spend)
    from agora.execution.metabolism import roi_report
    rr = roi_report()
    priced = {k: v for k, v in rr["organs"].items() if v.get("roi") is not None and v["ktok"] >= 3}
    best_roi = max(priced.items(), key=lambda kv: kv[1]["roi"]) if priced else None
    worst_roi = min(priced.items(), key=lambda kv: kv[1]["roi"]) if priced else None
    return {
        "organs": organs,
        "bounty_authority": bounty_scores(),
        "synthesis_pressure": syn["pressure"], "synthesis_due": syn["due"],
        "open_falsifiers": fw["open"], "deepened": fw["deepened"],
        "forge_open_gaps": forge_open, "failed_replications": rep_fail,
        "bottleneck": bottleneck,
        "total_ktok": rr["total_ktok"],
        "best_roi": {"organ": best_roi[0], **best_roi[1]} if best_roi else None,
        "worst_roi": {"organ": worst_roi[0], **worst_roi[1]} if worst_roi else None,
    }


def format_roadmap() -> str:
    g = gather()
    lines = ["🧭 *Roadmap panel* (Aldric's instrument view)"]
    for o in g["organs"]:
        idle = "never" if o["idle_h"] > 1e8 else f"{o['idle_h']}h ago"
        lines.append(f"• {o['organ']}: {o['total']} total · {o['recent_48h']} in 48h · last {idle}")
    lines.append(f"\n_open falsifiers_ {g['open_falsifiers']} · _deepened_ {g['deepened']} · "
                 f"_synthesis pressure_ {g['synthesis_pressure']}"
                 + (" 🌋" if g["synthesis_due"] else ""))
    lines.append(f"_open forge gaps_ {g['forge_open_gaps']} · "
                 f"_failed replications (publishable)_ {g['failed_replications']}")
    lines.append(f"⛔ _longest-idle organ:_ {g['bottleneck']}")
    lines.append(f"\n💰 _CFO:_ {g['total_ktok']}k tok metered"
                 + (f" · best ROI: {g['best_roi']['organ']} ({g['best_roi']['roi']}/ktok)"
                    if g.get("best_roi") else "")
                 + (f" · worst: {g['worst_roi']['organ']} ({g['worst_roi']['roi']}/ktok)"
                    if g.get("worst_roi") else ""))
    return "\n".join(lines)
