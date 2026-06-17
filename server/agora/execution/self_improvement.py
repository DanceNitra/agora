"""
Recursive self-improvement — the loop closes on itself.

Agora measures its OWN track record (which organs/conditions produce validated results, and at what
external-grounding level), then applies the unifying law it discovered — the critical external-anchor
law — TO ITSELF: a self-referential system preserves quality only while its external-information
flux phi exceeds phi_c. The system's own research loop IS such a system, so this organ checks Agora's
phi against phi_c and emits a law-aware feedback recommendation: where to allocate effort (highest
validated-yield organs) and how to stay out of the self-confirming attractor (keep phi up).

Read-only over the system's real stores. No toy numbers.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

# the law (measured in Lab 46f22b / 5a0d6e): phi_c rises with self-reinforcement alpha.
PHI_C = {1.0: 0.01, 1.5: 0.11, 2.0: 0.18, 3.0: 0.27}
PHI_C_ALARM = 0.30        # below this, even strong self-reinforcement regimes risk lock-in
_CITE = re.compile(r"\(20\d\d|\bdoi\b|et al|arxiv", re.I)
_DB = Path(__file__).resolve().parents[2] / "agora.db"


def _ledger(modpath: str):
    try:
        mod = __import__(modpath, fromlist=["_load"])
        return mod._load()
    except Exception:
        return []


def measure_self(vault_path: str = "") -> dict:
    m: dict = {"grounding_phi": None, "knowledge": {}, "hypotheses": {}, "organs": {}}
    # ---- external-grounding fraction phi (findings carrying a real citation) ----
    try:
        con = sqlite3.connect(f"file:{_DB}?mode=ro", uri=True, timeout=5)
        cur = con.cursor()
        tot = cur.execute("SELECT COUNT(*) FROM collective_knowledge WHERE knowledge_type='discovery'").fetchone()[0] or 0
        rows = cur.execute("SELECT content FROM collective_knowledge WHERE knowledge_type='discovery'").fetchall()
        grounded = sum(1 for (c,) in rows if c and _CITE.search(c))
        m["grounding_phi"] = round(grounded / tot, 3) if tot else None
        m["knowledge"]["discoveries"] = tot
        # hypotheses: count + mean confidence (post-calibration)
        h = cur.execute("SELECT confidence FROM collective_knowledge WHERE knowledge_type='hypothesis'").fetchall()
        confs = [float(x[0]) for x in h if x and x[0] is not None]
        m["hypotheses"] = {"n": len(h),
                           "mean_confidence": round(sum(confs) / len(confs), 3) if confs else None}
        con.close()
    except Exception as e:
        m["knowledge"]["error"] = str(e)[:120]
    # ---- per-organ validated-yield (the meta-learning signal) ----
    reps = _ledger("agora.execution.replication")
    if reps:
        repr_ = sum(1 for r in reps if r.get("outcome") == "REPRODUCED")
        fail = sum(1 for r in reps if r.get("outcome") == "FAILED")
        m["organs"]["replication"] = {"total": len(reps), "REPRODUCED": repr_, "FAILED": fail,
                                       "failed_rate": round(fail / len(reps), 3)}
    th = _ledger("agora.execution.theory")
    if th:
        m["organs"]["theory"] = {"total": len(th),
                                 "corroborated": sum(1 for t in th if t.get("verdict") == "corroborated"),
                                 "strained": sum(1 for t in th if t.get("verdict") == "strained")}
    uni = _ledger("agora.execution.unification")
    if uni:
        m["organs"]["unification"] = {"total": len(uni),
                                      "supported": sum(1 for u in uni if u.get("status") == "supported")}
    return m


def recommend(m: dict) -> dict:
    """Law-aware feedback: self-check phi vs phi_c, then where to allocate effort."""
    recs = []
    phi = m.get("grounding_phi")
    # 1) THE LAW APPLIED TO US: external-grounding self-check
    if phi is not None:
        worst_phi_c = PHI_C[3.0]
        margin = round(phi - worst_phi_c, 3)
        if phi < PHI_C_ALARM:
            recs.append(f"ALARM: external grounding phi={phi:.2f} is near the lock-in threshold "
                        f"(~{PHI_C_ALARM}). The law predicts self-confirming drift — raise paper/vault grounding NOW.")
        else:
            recs.append(f"Self-reference OK: grounding phi={phi:.2f} >> phi_c (margin {margin:+.2f} vs the "
                        f"alpha=3 threshold {worst_phi_c}). The law predicts we track truth. Do NOT let phi dip.")
    # 2) Crucible balance (owner's directive: FAILED must be a live possibility)
    rep = m.get("organs", {}).get("replication")
    if rep and rep["total"] >= 4 and rep["FAILED"] == 0:
        recs.append(f"Crucible is {rep['REPRODUCED']}R/0F over {rep['total']} — replicating too-safe claims. "
                    f"Hunt claims where FAILED is a live possibility (credibility needs real risk).")
    # 3) hypothesis quality (post-calibration)
    h = m.get("hypotheses", {})
    if h.get("mean_confidence") is not None:
        recs.append(f"Hypotheses: n={h['n']}, mean confidence {h['mean_confidence']:.2f} "
                    f"(calibrated — 0% artifact fixed).")
    # 4) where the validated yield is
    if m.get("organs", {}).get("unification", {}).get("supported"):
        recs.append("Unification organ is yielding supported laws — the highest-leverage compounding "
                    "(fuse validated results, severe-test for a novel prediction).")
    return {"recommendations": recs}


def govern() -> dict:
    """ACT, don't just measure: the system applies its own Anchor Law to itself. Returns the current
    operating point + whether external grounding φ has drifted toward the self-confirming lock-in
    threshold (an autonomous early-warning the self_audit_loop fires on). The loop closing on itself."""
    m = measure_self()
    r = recommend(m)
    phi = m.get("grounding_phi")
    return {"phi": phi, "alarm": (phi is not None and phi < PHI_C_ALARM),
            "recommendations": r.get("recommendations", []), "measure": m}


def format_self_improvement(m: dict, r: dict) -> str:
    lines = ["🔁 *Recursive self-improvement* — Agora measured on its own law:"]
    if m.get("grounding_phi") is not None:
        lines.append(f"• external grounding phi = *{m['grounding_phi']:.2f}* (lock-in threshold ~{PHI_C_ALARM})")
    for rec in r.get("recommendations", [])[:5]:
        lines.append(f"• {rec}")
    return "\n".join(lines)
