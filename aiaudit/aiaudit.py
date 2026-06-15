"""
Agora AI Audit — the reliability report for an AI / agent system.

You describe your system (whichever parts you have); this runs the matching checks and returns ONE
prioritized report: what's failing, how bad, and the fix. It's the audit we run on ourselves
(tools/self_audit.py), turned on YOUR system. Each dimension is a proven, measured check:

  ab_test       -> nullcheck   : is a reported lift real, or noise?
  metric        -> goodhart    : is an optimized proxy/KPI/reward gamed?
  training_mix  -> selfref     : is the model collapsing / locking from self-training?
  multi_agent   -> herdcheck   : will an ensemble / multi-agent system herd?
  causal        -> idcheck     : is a causal/attribution number identified, or biased by bad controls?
  rag_store     -> ragfresh    : is the vector store rotting (stale, orphaned chunks)?
  memory        -> mnemo       : agent-memory health (size, value, links)

Pass only the parts you have; the audit runs what it can. Zero dependencies beyond the toolkit cores.

    from aiaudit import audit
    report = audit({"ab_test": {...}, "training_mix": {...}, "multi_agent": {...}})
    print(report["overall"], report["fixes"])
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# the eight cores are sibling packages in the toolkit
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import nullcheck, selfref, goodhart, herdcheck, idcheck   # noqa: E402

_SEV = {"ok": 0, "warn": 1, "fail": 2}


def _word(verdict: str) -> str:
    return (verdict or "").strip().split(" ")[0].split("—")[0].strip().upper()


def _ab(spec):
    r = nullcheck.ab_test(spec["conv_a"], spec["n_a"], spec["conv_b"], spec["n_b"])
    w = _word(r["verdict"])
    sev = {"REAL": "ok", "LIKELY": "ok", "SUSPECT": "warn", "NOISE": "fail"}.get(w, "warn")
    return {"dimension": "A/B result (nullcheck)", "severity": sev,
            "finding": f"lift {r['lift']:+}, p={r['p_empirical']} — {r['verdict']}",
            "fix": None if sev == "ok" else "collect more data before acting; a no-effect null reproduces this"}


def _metric(spec):
    r = goodhart.audit(spec.get("gameability", 1.0), spec.get("n_metrics", 1))
    w = _word(r["verdict"])
    sev = {"SAFE": "ok", "DEGRADED": "warn", "GAMED": "fail"}.get(w, "warn")
    rec = r.get("recommended_metrics")
    return {"dimension": "Metric / reward (goodhart)", "severity": sev, "finding": r["verdict"],
            "fix": None if sev == "ok" else
            (f"combine >= {rec} independent metrics" if rec else
             "change what you measure — it's too gameable for more metrics to rescue")}


def _training(spec):
    r = selfref.audit(spec.get("external_fraction", 0.0), spec.get("self_trust_p", 1.0))
    w = _word(r["overall_verdict"])
    sev = {"SAFE": "ok", "WATCH": "warn", "COLLAPSE": "fail", "LOCK": "fail"}.get(w, "warn")
    return {"dimension": "Self-training (selfref)", "severity": sev,
            "finding": f"{r['overall_verdict']} (external data {spec.get('external_fraction',0):.0%}, self-trust p={spec.get('self_trust_p',1)})",
            "fix": None if sev == "ok" else "; ".join(r["fix"])}


def _multiagent(spec):
    r = herdcheck.audit(spec.get("peers_seen", 2), spec.get("own_weight", 1.0),
                        discount=spec.get("discount", 1.0))
    w = _word(r["verdict"])
    sev = {"INDEPENDENT": "ok", "DEGRADED": "warn", "HERDED": "fail"}.get(w, "warn")
    return {"dimension": "Multi-agent (herdcheck)", "severity": sev, "finding": r["verdict"],
            "fix": None if sev == "ok" else "; ".join(r["fix"])}


def _causal(spec):
    r = idcheck.audit(spec.get("controls", {}))
    w = _word(r["verdict"])
    sev = {"ADMISSIBLE": "ok", "UNDER-CONTROLLED": "warn", "BIASED": "fail"}.get(w, "warn")
    return {"dimension": "Causal identification (idcheck)", "severity": sev, "finding": r["verdict"],
            "fix": None if sev == "ok" else f"drop bad controls: {', '.join(r.get('drop', []))}"}


def _rag(spec):
    import ragfresh
    now = spec.get("now") or time.time()
    items = [ragfresh.Item(id=str(d.get("id", i)), updated_ts=float(d.get("updated_ts", now)),
                           value=float(d.get("value", 0.5)), source_exists=bool(d.get("source_exists", True)))
             for i, d in enumerate(spec.get("items", []))]
    if not items:
        return {"dimension": "RAG store (ragfresh)", "severity": "ok", "finding": "no items provided", "fix": None}
    plan = ragfresh.triage(items, now=now, stale_days=spec.get("stale_days", 90))
    n = len(items)
    pr = sum(1 for a, _ in plan["decisions"].values() if a == "PRUNE")
    rf = sum(1 for a, _ in plan["decisions"].values() if a == "REFRESH")
    frac = (pr + rf) / n
    sev = "fail" if frac > 0.4 else ("warn" if frac > 0.15 else "ok")
    return {"dimension": "RAG store (ragfresh)", "severity": sev,
            "finding": f"{pr} prune + {rf} refresh of {n} chunks ({frac:.0%} stale/orphaned)",
            "fix": None if sev == "ok" else "run a periodic freshness triage; prune orphans, re-embed stale-but-valuable"}


def _memory(spec):
    import mnemo
    items = spec.get("items", [])
    n = len(items)
    linked = sum(1 for m in items if m.get("links"))
    sev = "ok"
    return {"dimension": "Agent memory (mnemo)", "severity": sev,
            "finding": f"{n} memories, {round(100*linked/max(1,n))}% linked",
            "fix": None}


_RUNNERS = {"ab_test": _ab, "metric": _metric, "training_mix": _training, "multi_agent": _multiagent,
            "causal": _causal, "rag_store": _rag, "memory": _memory}


def audit(spec: dict) -> dict:
    """Run every check whose input is present in `spec`; return one prioritized reliability report."""
    dims = []
    for key, runner in _RUNNERS.items():
        if key in spec:
            try:
                dims.append(runner(spec[key]))
            except Exception as e:
                dims.append({"dimension": key, "severity": "warn", "finding": f"check error: {str(e)[:120]}", "fix": None})
    fails = [d for d in dims if d["severity"] == "fail"]
    warns = [d for d in dims if d["severity"] == "warn"]
    oks = [d for d in dims if d["severity"] == "ok"]
    overall = "FAIL" if fails else ("WARN" if warns else "PASS")
    score = round(100 * (len(oks) + 0.5 * len(warns)) / len(dims)) if dims else None
    fixes = [f"[{d['dimension']}] {d['fix']}" for d in (fails + warns) if d.get("fix")]
    return {"overall": overall, "health_score": score,
            "checked": len(dims), "fail": len(fails), "warn": len(warns), "ok": len(oks),
            "dimensions": dims, "fixes": fixes}


def format_report(rep: dict) -> str:
    icon = {"ok": "PASS", "warn": "WARN", "fail": "FAIL"}
    lines = [f"=== Agora AI Audit === overall: {rep['overall']}  ·  health {rep['health_score']}/100  "
             f"({rep['ok']} pass / {rep['warn']} warn / {rep['fail']} fail)\n"]
    for d in sorted(rep["dimensions"], key=lambda x: -_SEV[x["severity"]]):
        lines.append(f"[{icon[d['severity']]}] {d['dimension']}: {d['finding']}")
        if d.get("fix"):
            lines.append(f"        fix: {d['fix']}")
    if rep["fixes"]:
        lines.append("\nprioritized fixes:")
        lines += [f"  {i+1}. {f}" for i, f in enumerate(rep["fixes"])]
    return "\n".join(lines)
