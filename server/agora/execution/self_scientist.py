"""
The Self-Improving Scientist — the apex of the self-referential bet.

Agora discovered laws about how self-referential systems track truth (grounding, identification,
anti-lock-in). This organ turns that lens on AGORA'S OWN research process: it measures a single
VALIDATED-DISCOVERY YIELD over time, derives a self-tuning directive from its own laws, and lets us
test the founding thesis empirically — *does applying the laws to ourselves raise our yield?*

Validated-yield = a weighted count of the system's VALIDATED outputs (laws, corroborated theory,
reproduced/failed replications, grounded supported hypotheses, viable analogies, charted bridges,
concluded investigations) in a recent window. Tracked over time so improvement is measurable, not
asserted. Read-only over the ledgers + a tiny history file.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

_HIST = Path(__file__).resolve().parents[2] / ".self_scientist.json"
_POLICY = Path(__file__).resolve().parents[2] / ".scientist_policy.json"
_DB = Path(__file__).resolve().parents[2] / "agora.db"

# v2: the controller writes a bounded, reversible POLICY that real organs (the seminar) read and obey.
# Defaults match prior behaviour, so a missing/corrupt file is safe. Values are clamped on write.
_DEFAULT_POLICY = {"grounding_floor": 0.40, "dedup_threshold": 0.62, "allocate": "law-discovery"}


def get_policy() -> dict:
    """Read the active self-tuning policy (organs call this). Safe defaults if absent."""
    try:
        p = json.loads(_POLICY.read_text(encoding="utf-8"))
        return {**_DEFAULT_POLICY, **{k: p[k] for k in _DEFAULT_POLICY if k in p}}
    except Exception:
        return dict(_DEFAULT_POLICY)


def apply_policy() -> dict:
    """v2 — the controller ACTS: derive bounded organ parameters from our own laws + operating point
    and write them where the organs read. Reversible (delete the file -> defaults)."""
    try:
        from agora.execution.self_improvement import measure_self
        phi = measure_self().get("grounding_phi")
    except Exception:
        phi = None
    # Grounding-Coupling lever: raise the seminar's grounding floor as phi falls; a modest push when
    # healthy. Clamped to [0.40, 0.55] so it can never starve the seminar.
    gf = 0.45
    if phi is not None and phi < 0.40:
        gf = 0.55
    elif phi is not None and phi < 0.55:
        gf = 0.50
    gf = max(0.40, min(0.55, gf))
    pol = {"grounding_floor": round(gf, 2), "dedup_threshold": 0.62, "allocate": "law-discovery",
           "phi": phi, "ts": time.time()}
    try:
        _POLICY.write_text(json.dumps(pol, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
    return pol

# weights reward VALIDATED, severe-tested, externally-grounded outputs; FAILED replications count
# (shareable, per the Crucible thesis); churn (strained / no-mapping) counts little.
W = {"law": 10.0, "theory_corroborated": 3.0, "theory_strained": 0.5, "reproduced": 2.0,
     "failed": 3.0, "analogy_viable": 2.0, "bridge": 1.5, "investigation": 3.0,
     "hypothesis_grounded": 1.0,
     # near-term, continuous research output so the trend is responsive (not just rare laws):
     "contribution_grounded": 0.05, "contribution_verified": 0.25}
_CONTRIB = Path(__file__).resolve().parents[2] / ".contributions.json"


def _truthy(x) -> bool:
    return str(x).lower() == "true"


def _ledger(modpath: str) -> list:
    try:
        return __import__(modpath, fromlist=["_load"])._load()
    except Exception:
        return []


def _recent(items: list, hours: float, tskey: str = "ts") -> list:
    cut = time.time() - hours * 3600
    return [x for x in items if float(x.get(tskey, 0) or 0) >= cut]


def validated_yield(hours: float = 48.0) -> dict:
    """Weighted validated-discovery yield over the last `hours`, with the component breakdown."""
    comp: dict = {}
    laws = _recent(_ledger("agora.execution.unification"), hours)
    comp["law"] = sum(1 for u in laws if u.get("status") == "supported")
    th = _recent(_ledger("agora.execution.theory"), hours)
    comp["theory_corroborated"] = sum(1 for t in th if t.get("verdict") == "corroborated")
    comp["theory_strained"] = sum(1 for t in th if t.get("verdict") == "strained")
    rep = _recent(_ledger("agora.execution.replication"), hours)
    comp["reproduced"] = sum(1 for r in rep if r.get("outcome") == "REPRODUCED")
    comp["failed"] = sum(1 for r in rep if r.get("outcome") == "FAILED")
    comp["analogy_viable"] = sum(1 for a in _recent(_ledger("agora.execution.analogy"), hours)
                                 if a.get("outcome") == "viable")
    comp["bridge"] = sum(1 for b in _recent(_ledger("agora.execution.cartography"), hours)
                         if b.get("outcome") and "no honest bridge" not in str(b.get("outcome")).lower())
    # the seminar's continuous validated output (windowed) — makes near-term research move the score
    try:
        contribs = json.loads(_CONTRIB.read_text(encoding="utf-8"))
        rc = _recent(contribs, hours)
        comp["contribution_grounded"] = sum(1 for c in rc if _truthy(c.get("grounded")))
        comp["contribution_verified"] = sum(1 for c in rc if _truthy(c.get("verified")))
    except Exception:
        comp["contribution_grounded"] = comp["contribution_verified"] = 0
    try:
        from agora.execution import investigation as _inv
        comp["investigation"] = sum(1 for i in _recent(_inv._load(), hours)
                                    if i.get("status") == "concluded")
    except Exception:
        comp["investigation"] = 0
    # grounded supported hypotheses from the brain DB
    comp["hypothesis_grounded"] = 0
    try:
        con = sqlite3.connect(f"file:{_DB}?mode=ro", uri=True, timeout=5)
        cut = time.time() - hours * 3600
        rows = con.execute("SELECT confidence, created_at FROM collective_knowledge "
                           "WHERE knowledge_type='hypothesis'").fetchall()
        # created_at is a string/ts; count high-confidence ones (calibrated >=0.6) as validated
        comp["hypothesis_grounded"] = sum(1 for c, _ in rows if c is not None and float(c) >= 0.6)
        con.close()
    except Exception:
        pass
    score = sum(W.get(k, 0) * v for k, v in comp.items())
    return {"window_hours": hours, "yield_score": round(score, 1), "components": comp}


def controller() -> dict:
    """Derive a self-tuning directive from Agora's own laws + measured operating point."""
    from agora.execution.self_improvement import measure_self, PHI_C_ALARM
    m = measure_self()
    phi = m.get("grounding_phi")
    organs = m.get("organs", {})
    directives = []
    # LAW 1 (Grounding-Coupling): keep external grounding above threshold; it is the master lever.
    if phi is not None:
        if phi < PHI_C_ALARM + 0.1:
            directives.append(f"RAISE external grounding (phi={phi:.2f} near floor {PHI_C_ALARM}) — the "
                              f"Anchor Law says yield decays here; require a paper/vault anchor on more contributions.")
        else:
            directives.append(f"Hold grounding (phi={phi:.2f}, safe) — do not let it dip; it is the master yield lever.")
    # allocate toward the highest-yield organ
    rep = organs.get("replication", {})
    if rep and rep.get("FAILED", 1) == 0:
        directives.append("Crucible all-REPRODUCED — hunt FAILED-possible claims (higher shareable yield).")
    directives.append("Prioritize the law-discovery path (unification + investigation): highest validated-yield "
                      "per the ledger; route Claude-cycles there over low-yield dialectic/synth churn.")
    # IDENTIFICATION law: avoid spec-unstable churn
    directives.append("Avoid under-identified themes (spec-unstable) — they pump activity, not validated yield.")
    return {"grounding_phi": phi, "directives": directives}


def snapshot() -> dict:
    """Append a yield snapshot to history so the capstone trend is measurable over time."""
    y = validated_yield()
    rec = {"ts": time.time(), "yield_score": y["yield_score"], "components": y["components"]}
    hist = []
    if _HIST.exists():
        try:
            hist = json.loads(_HIST.read_text(encoding="utf-8"))
        except Exception:
            hist = []
    hist.append(rec)
    try:
        _HIST.write_text(json.dumps(hist[-300:], ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
    return rec


def trend() -> dict:
    """Is validated-yield improving over time? (the capstone's measured question)."""
    try:
        hist = json.loads(_HIST.read_text(encoding="utf-8"))
    except Exception:
        hist = []
    scores = [h.get("yield_score", 0) for h in hist]
    direction = "n/a"
    if len(scores) >= 4:
        half = len(scores) // 2
        early, late = sum(scores[:half])/half, sum(scores[half:])/(len(scores)-half)
        direction = "rising" if late > early*1.05 else ("falling" if late < early*0.95 else "flat")
    return {"snapshots": len(scores), "recent_scores": scores[-6:], "direction": direction}


def format_self_scientist() -> str:
    y = validated_yield(); c = controller(); t = trend()
    L = ["🔬 *The Self-Improving Scientist* — Agora tuning itself by its own laws:",
         f"• validated-yield (48h) = *{y['yield_score']}*  {y['components']}",
         f"• yield trend: {t['direction']} (snapshots {t['snapshots']}, recent {t['recent_scores']})"]
    for d in c["directives"][:4]:
        L.append(f"• {d}")
    return "\n".join(L)
