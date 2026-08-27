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

    # AN ORGAN WITH WORK WAITING ON A CONSUMER IS NOT IDLE, AND THIS PANEL COULD NOT TELL THE
    # DIFFERENCE. Measured 2026-08-17: it reported five organs at "0 in 48h" with Bounty/Court as the
    # bottleneck at 399.9h, and every one of them was firing correctly on schedule (replication every
    # 30min, belief 49min, cartography 45min) with its inputs returning data. What they had done for
    # sixteen days was queue the work into the Claude inbox, where 37 of 86 pending tasks belonged to
    # these five. `idle_h` measures when a LEDGER last grew, so it was reporting the consumer's
    # throughput as the organ's health -- and the remedy it implied (fix the organ) was aimed at the
    # wrong half of the system.
    #
    # The organ->task mapping is DERIVED FROM `completion_gate._OWED` rather than restated here. That
    # table already binds a task family to the ledger module it owes, it is measured rather than
    # guessed, and a second copy of the same mapping is how the two answers drift apart -- the defect
    # this file's own neighbours keep recording.
    def _pending_by_module() -> dict:
        try:
            from agora.execution.claude_inbox import pending as _pending
            from agora.execution.completion_gate import _OWED
        except Exception:
            return {}
        out: dict = {}
        tasks = [t.get("text", "") or "" for t in _pending()]
        for prefix, (_name, module, _how) in _OWED.items():
            key = module.rsplit(".", 1)[-1]
            n = sum(1 for t in tasks if t.startswith(prefix) or prefix in t[:80])
            if n:
                out[key] = out.get(key, 0) + n
        return out

    _waiting = _pending_by_module()

    def organ(items, label, module_key=""):
        ts = [x.get("ts", 0) for x in items if x.get("ts")]
        # `waiting` is None when we cannot say -- an organ with no _OWED family has no measured link to
        # the inbox, and printing 0 there would assert something we did not check.
        return {"organ": label, "total": len(items),
                "recent_48h": sum(1 for t in ts if t >= now - 2 * 86400),
                "idle_h": _age_h(max(ts), now) if ts else 1e9,
                "waiting_on_claude": _waiting.get(module_key) if module_key else None}

    rep = rep_load()
    organs = [
        organ(bounty_load(), "Bounty/Court (belief kills)", "bounty"),
        organ(rep, "Replication (Rooke)", "replication"),
        organ(analogy_load(), "Analogy Forge", "analogy_forge"),
        organ(carto_load(), "Cartography (Wren)", "cartography"),
        organ(grave_load(), "Graveyard"),          # no _OWED family -> no measured inbox link
    ]
    syn = syn_signals()
    fw = fw_stats()
    forge_open = sum(1 for g in forge_load() if g.get("status") == "open")
    rep_fail = sum(1 for r in rep if r.get("outcome") == "FAILED")

    # the bottleneck = the organ idle the longest (excluding never-run, which are "not wired yet")
    ran = [o for o in organs if o["idle_h"] < 1e8]
    bottleneck = max(ran, key=lambda o: o["idle_h"])["organ"] if ran else "(no organ has produced yet)"
    # ...and WHERE it is stuck, which is a different question from WHICH one is stuck. An organ whose
    # tasks are sitting in the inbox is blocked on the consumer, and saying "idle organ" there sends
    # the reader to fix the producer.
    _b = next((o for o in ran if o["organ"] == bottleneck), None)
    bottleneck_kind = ("blocked on Claude" if (_b or {}).get("waiting_on_claude")
                       else "idle" if _b else "unknown")
    waiting_total = sum(o["waiting_on_claude"] or 0 for o in organs)

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
        "bottleneck": bottleneck, "bottleneck_kind": bottleneck_kind,
        "waiting_on_claude_total": waiting_total,
        "total_ktok": rr["total_ktok"],
        # Carried through so the CFO line can state its own coverage. Without these the warning below
        # simply never fires, which is the failure it exists to prevent.
        "value_coverage": rr.get("value_coverage"),
        "organs_with_value": rr.get("organs_with_value", 0),
        "organs_total": rr.get("organs_total", 0),
        "unmetered_total": rr.get("unmetered_total", 0),
        "best_roi": {"organ": best_roi[0], **best_roi[1]} if best_roi else None,
        "worst_roi": {"organ": worst_roi[0], **worst_roi[1]} if worst_roi else None,
    }


def format_roadmap() -> str:
    g = gather()
    lines = ["🧭 *Roadmap panel* (Aldric's instrument view)"]
    for o in g["organs"]:
        idle = "never" if o["idle_h"] > 1e8 else f"{o['idle_h']}h ago"
        # The waiting count is the difference between "this organ stopped working" and "this organ is
        # working and nobody is draining it". Printed only when measured.
        wait = ("" if o.get("waiting_on_claude") in (None, 0)
                else f" · ⏳ {o['waiting_on_claude']} waiting on Claude")
        lines.append(f"• {o['organ']}: {o['total']} total · {o['recent_48h']} in 48h · "
                     f"last {idle}{wait}")
    lines.append(f"\n_open falsifiers_ {g['open_falsifiers']} · _deepened_ {g['deepened']} · "
                 f"_synthesis pressure_ {g['synthesis_pressure']}"
                 + (" 🌋" if g["synthesis_due"] else ""))
    lines.append(f"_open forge gaps_ {g['forge_open_gaps']} · "
                 f"_failed replications (publishable)_ {g['failed_replications']}")
    lines.append(f"⛔ _longest-idle organ:_ {g['bottleneck']} — {g['bottleneck_kind']}"
                 + (f" ({g['waiting_on_claude_total']} organ task(s) queued to Claude in total)"
                    if g.get("waiting_on_claude_total") else ""))
    # The best/worst pair is only a ranking if the value side is connected. Measured 2026-08-17: it was
    # connected for 1 of 17 organs, so "worst: frontier-seed 0.000" was reporting a naming drift as a
    # verdict on the biggest spender in the system. The coverage now travels WITH the ranking.
    cov = g.get("value_coverage")
    lines.append(f"\n💰 _CFO:_ {g['total_ktok']}k tok metered"
                 + (f" · best ROI: {g['best_roi']['organ']} ({g['best_roi']['roi']}/ktok)"
                    if g.get("best_roi") else "")
                 + (f" · worst: {g['worst_roi']['organ']} ({g['worst_roi']['roi']}/ktok)"
                    if g.get("worst_roi") else "")
                 + (f" · ⚠️ value resolves for {g['organs_with_value']}/{g['organs_total']} organs "
                    f"({100 * (1 - cov):.0f}% of value unattributed) — a 0.000 means UNMEASURED"
                    if cov is not None and cov < 0.95 else ""))
    return "\n".join(lines)
