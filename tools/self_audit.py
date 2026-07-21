#!/usr/bin/env python3
"""
self_audit.py — run the WHOLE Agora Memory Toolkit on Agora's OWN systems and harvest real data.

The big dogfood: we run an autonomous research company; this audits it with the eight tools we ship,
on real internal data (no invented inputs). Every section names its data source. Output: a structured
report (agora_output/self_audit.json) + a readable summary — the "Agora, audited by its own tools"
artifact. Findings that are actionable (agents herding, a gamed metric, a depleting vein, collapse
risk) are real problems to fix, which is the point.

Usage:  python tools/self_audit.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SERVER = ROOT / "server"

import inspeximus, ragfresh, nullcheck, selfref, quitkit, idcheck, goodhart, herdcheck  # noqa: E402


def _load(name):
    p = SERVER / name
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _corr(a, b):
    n = len(a)
    if n < 3:
        return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((y - mb) ** 2 for y in b) ** 0.5
    return cov / (va * vb) if va and vb else 0.0


def audit_inspeximus(rep):
    """inspeximus <- the brain's own inspeximus store (.inspeximus_brain.json)."""
    mem = _load(".inspeximus_brain.json") or []
    contras = _load(".contradictions.json") or []
    vals = [m.get("value", 1.0) for m in mem if isinstance(m, dict)]
    active = sum(1 for m in mem if isinstance(m, dict) and m.get("status", "active") == "active")
    linked = sum(1 for m in mem if isinstance(m, dict) and m.get("links"))
    rep["inspeximus"] = {
        "status": "ok",
        "source": ".inspeximus_brain.json (the brain's live memory)",
        "memories": len(mem), "active": active,
        "mean_value": round(statistics.fmean(vals), 3) if vals else None,
        "linked_fraction": round(linked / len(mem), 3) if mem else None,
        "contradictions_flagged": len(contras) if isinstance(contras, list) else None,
        "finding": f"{len(mem)} memories running live, {round(100*linked/max(1,len(mem)))}% interlinked; "
                   f"inspeximus is governing the brain's own recall.",
    }


def audit_ragfresh(rep):
    """ragfresh <- triage the brain's own memories by value x freshness."""
    mem = _load(".inspeximus_brain.json") or []
    now = time.time()
    items = [ragfresh.Item(id=str(m.get("id", i)), updated_ts=float(m.get("ts", now)),
                           value=float(m.get("value", 0.5))) for i, m in enumerate(mem) if isinstance(m, dict)]
    if not items:
        rep["ragfresh"] = {"source": ".inspeximus_brain.json", "finding": "no items"}
        return
    plan = ragfresh.triage(items, now=now, stale_days=90)
    counts = {}
    for _vid, (action, _why) in plan["decisions"].items():
        counts[action] = counts.get(action, 0) + 1
    rep["ragfresh"] = {
        "status": "ok",
        "source": ".inspeximus_brain.json (our own memory, real timestamps)",
        "items": len(items), "decisions": counts,
        "finding": f"of {len(items)} live memories: " +
                   ", ".join(f"{v} {k}" for k, v in counts.items()) +
                   " — real staleness in our own store.",
    }


def audit_nullcheck(rep):
    """nullcheck <- meant to test if grounded contributions verify more than ungrounded; instead it
    CAUGHT a real process gap: verification outcomes aren't being recorded."""
    contribs = _load(".contributions.json") or []
    n = len(contribs)
    grounded = sum(1 for c in contribs if c.get("grounded"))
    verified = sum(1 for c in contribs if c.get("verified"))
    if verified == 0 and n:
        rep["nullcheck"] = {
            "source": ".contributions.json (verify-rate signal)",
            "contributions": n, "grounded": grounded, "verified": verified,
            "status": "gap", "verdict": "NO SIGNAL TO TEST",
            "finding": f"GAP FOUND: {grounded}/{n} contributions are grounded but {verified} are marked "
                       f"verified — Voss's QA/verification tier isn't writing outcomes back, so there is "
                       f"no verify-rate to A/B. (Fix: have the verify pass set `verified`.) "
                       f"nullcheck's job is to refuse a signal that isn't there — it did.",
        }
        return
    g = [1 if c.get("verified") else 0 for c in contribs if c.get("grounded")]
    u = [1 if c.get("verified") else 0 for c in contribs if not c.get("grounded")]
    res = nullcheck.permutation_test(u, g) if len(g) >= 5 and len(u) >= 5 else {"p_empirical": None, "verdict": "n too small"}
    rep["nullcheck"] = {
        "source": ".contributions.json (grounded vs ungrounded verify-rates)",
        "verify_rate_grounded": round(statistics.fmean(g), 3) if g else None,
        "verify_rate_ungrounded": round(statistics.fmean(u), 3) if u else None,
        "status": "ok", "p_empirical": res.get("p_empirical"), "verdict": res.get("verdict"),
        "finding": f"grounded verify {statistics.fmean(g):.0%} vs ungrounded {statistics.fmean(u):.0%} — {res.get('verdict')}" if g and u else "insufficient data",
    }


def audit_selfref(rep):
    """selfref <- our own self-training data mix: what fraction of contributions are externally grounded?"""
    contribs = _load(".contributions.json") or []
    if not contribs:
        rep["selfref"] = {"source": ".contributions.json", "finding": "no data"}
        return
    external_fraction = sum(1 for c in contribs if c.get("grounded")) / len(contribs)
    a = selfref.audit(external_fraction=external_fraction, self_trust_p=1.0)
    rep["selfref"] = {
        "status": "ok" if a["overall_verdict"].startswith("SAFE") else "gap",
        "source": ".contributions.json (grounded = externally-anchored fraction)",
        "external_fraction": round(external_fraction, 3),
        "collapse_verdict": a["collapse"]["verdict"].split("—")[0].strip(),
        "overall": a["overall_verdict"],
        "finding": f"{external_fraction:.0%} of our contributions are externally grounded (vs self-derived); "
                   f"selfref says: {a['overall_verdict']} (>=5% external anchor avoids collapse).",
    }


def audit_quitkit(rep):
    """quitkit <- is our overall research YIELD in drawdown? (grounded contributions per time-bucket)."""
    contribs = sorted([c for c in (_load(".contributions.json") or []) if c.get("ts")],
                      key=lambda c: c["ts"])
    if len(contribs) < 30:
        rep["quitkit"] = {"source": ".contributions.json", "finding": "too few to trend"}
        return
    # bucket into ~20 equal-count windows, yield = grounded fraction per window
    k = max(10, len(contribs) // 20)
    yields = []
    for i in range(0, len(contribs) - k + 1, k):
        win = contribs[i:i + k]
        yields.append(sum(1 for c in win if c.get("grounded")) / len(win))
    q = quitkit.should_quit(yields, window=max(3, len(yields) // 3))
    rep["quitkit"] = {
        "status": "gap" if q.get("quit") else "ok",
        "source": ".contributions.json (grounded-yield trend over time)",
        "windows": len(yields), "recent_yield": q.get("recent_rate"), "peak_yield": q.get("peak_rate"),
        "drawdown": q.get("drawdown"), "quit": q.get("quit"),
        "finding": f"research grounded-yield: {q.get('reason','')}",
    }


def audit_goodhart(rep):
    """goodhart <- is our 'standing' proxy still tracking real value? (standing vs grounded output)."""
    standing = (_load_dungeon("agent_standing.json") or {}).get("standing", {})
    contribs = _load(".contributions.json") or []
    # real value per agent ~ count of grounded contributions they partnered on
    val = {}
    for c in contribs:
        if not c.get("grounded"):
            continue
        for pn in (c.get("partners") or []):
            val[pn] = val.get(pn, 0) + 1
    keys = [k for k in standing if k in val] if standing else []
    if len(keys) < 4:
        rep["goodhart"] = {"source": "agent_standing.json x .contributions.json",
                           "finding": f"only {len(keys)} agents matchable — proxy/value link not computable"}
        return
    corr = _corr([standing[k] for k in keys], [val[k] for k in keys])
    # map proxy-goal corr to an effective gameability for goodhart's verdict (corr 1 -> 0, lower -> higher)
    gameability = max(0.0, (1.0 - corr) * 4)
    a = goodhart.audit(gameability, n_metrics=1)
    rep["goodhart"] = {
        "status": "ok" if corr >= 0.5 else "gap",
        "source": "agent_standing.json (proxy) x grounded contributions (true value)",
        "proxy_value_corr": round(corr, 3), "implied_gameability": round(gameability, 2),
        "verdict": a["verdict"].split("—")[0].strip(),
        "finding": f"agent standing correlates {corr:.2f} with real grounded output — "
                   f"{'healthy' if corr > 0.6 else 'weak: the metric may be drifting from value'}.",
    }


def audit_herdcheck(rep):
    """herdcheck <- do our 8 agents herd? topic concentration of their contributions (Herfindahl)."""
    contribs = _load(".contributions.json") or []
    topics = {}
    for c in contribs:
        t = (c.get("topic") or "").strip().lower()[:40]
        if t:
            topics[t] = topics.get(t, 0) + 1
    if not topics:
        rep["herdcheck"] = {"source": ".contributions.json", "finding": "no topics"}
        return
    total = sum(topics.values())
    hhi = sum((n / total) ** 2 for n in topics.values())          # 1=all one topic (herded), ~0=diverse
    effective_topics = round(1 / hhi, 1)
    # contrast: our 8-agent system audited at its observed config (agents do read each other -> peers~2)
    a = herdcheck.audit(peers_seen=2, own_weight=1.0)
    rep["herdcheck"] = {
        "status": "gap" if hhi >= 0.15 else "ok",
        "source": ".contributions.json (topic concentration) + herdcheck model",
        "distinct_topics": len(topics), "herfindahl": round(hhi, 3),
        "effective_independent_topics": effective_topics,
        "model_verdict_at_observed_config": a["verdict"].split("—")[0].strip(),
        "finding": f"{len(topics)} topics but effectively {effective_topics} independent "
                   f"(HHI {hhi:.2f}); " +
                   ("diverse — not herding on topics." if hhi < 0.15 else
                    "concentrated — agents may be piling on the same themes (herding risk)."),
    }


def audit_idcheck(rep):
    """idcheck <- the mechanism we rely on for claim-diligence; proof on our own terms."""
    cb = idcheck.collider_bias(0.5)
    rep["idcheck"] = {
        "status": "ok",
        "source": "idcheck collider proof (the engine behind our claim-diligence)",
        "true_beta": cb["true_beta"], "naive": cb["naive_Y_on_X"],
        "controlled_for_collider": cb["adjusted_for_collider"],
        "finding": f"our identification engine, on its own proof: true +0.5 -> naive {cb['naive_Y_on_X']}, "
                   f"but 'controlling for' a collider -> {cb['adjusted_for_collider']} (bias {cb['bias_injected_by_adjusting']}).",
    }


def _load_dungeon(name):
    try:
        return json.loads((ROOT / "agora-game-server" / name).read_text(encoding="utf-8"))
    except Exception:
        return None


def main():
    rep = {"generated_for": "Agora self-audit (toolkit on its own systems)"}
    for fn in (audit_inspeximus, audit_ragfresh, audit_nullcheck, audit_selfref, audit_quitkit,
               audit_goodhart, audit_herdcheck, audit_idcheck):
        try:
            fn(rep)
        except Exception as e:
            rep[fn.__name__.replace("audit_", "")] = {"error": str(e)[:160]}
    out = ROOT / "agora_output" / "self_audit.json"
    out.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=== AGORA SELF-AUDIT — the toolkit run on our own systems (real data) ===\n")
    for tool in ("inspeximus", "ragfresh", "nullcheck", "selfref", "quitkit", "goodhart", "herdcheck", "idcheck"):
        sec = rep.get(tool, {})
        print(f"[{tool}]  src: {sec.get('source','?')}")
        print(f"   {sec.get('finding') or sec.get('error') or sec}")
    print(f"\nfull report -> {out}")


if __name__ == "__main__":
    main()
