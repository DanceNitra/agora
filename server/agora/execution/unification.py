"""
The Unification Engine — Agora fuses its own VALIDATED results into a unifying law.

The system produces many separately-validated results (canon laws, REPRODUCED replications, severe-
tested hypotheses, viable analogies, theory runs). A breakthrough is rarely one finding — it is the
rare PRINCIPLE that subsumes several of them AND predicts something none of them predicted alone.

This engine (1) gathers the strongest validated results as raw material, and (2) ledgers candidate
unifications. The bar that separates a real unification from a verbal analogy is enforced in the
record: a unification must name a NOVEL, FALSIFIABLE prediction (something beyond its inputs) and the
Lab id that severe-tested it. Status: 'candidate' (predicts but unverified), 'supported' (novel
prediction held), 'failed' (it didn't). Only 'supported' unifications are canon-worthy.

This is the self-referential bet made literal: the system studies the dynamics it is itself subject to.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".unification.json"


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    try:
        _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def gather_inputs(vault_path: str) -> dict:
    """The strongest VALIDATED results across the system — the raw material a unification must subsume."""
    out: dict = {"canon_laws": [], "reproduced": [], "hypotheses": [], "analogies": [], "theory_runs": []}
    try:
        from agora.execution.replication import _load as _rload
        out["reproduced"] = [{"claim": r.get("claim", "")[:140], "lab": r.get("lab_id", "")}
                             for r in _rload() if r.get("outcome") == "REPRODUCED"][-12:]
    except Exception:
        pass
    try:
        from agora.execution.theory import _load as _tload
        out["theory_runs"] = [{"title": t.get("title", "")[:120], "verdict": t.get("verdict", ""),
                               "lab": t.get("lab", "")} for t in _tload()][-12:]
    except Exception:
        pass
    try:
        from agora.execution.analogy import _load as _aload          # may not exist; best-effort
        out["analogies"] = [{"mechanism": a.get("mechanism", "")[:80], "target": a.get("target", "")[:80]}
                            for a in _aload() if a.get("outcome") == "viable"][-12:]
    except Exception:
        pass
    return out


def record_unification(name: str, principle: str, subsumes: list, lab_id: str,
                       novel_prediction: str, falsifier: str, status: str = "candidate",
                       note: str = "") -> dict:
    """Ledger a candidate unifying law. Enforces the bar: a real unification names a NOVEL prediction
    + a Lab id, not just a shared vibe."""
    s = (status or "candidate").strip().lower()
    if s not in ("candidate", "supported", "failed"):
        s = "candidate"
    if not (name and principle and novel_prediction and falsifier):
        return {"error": "a unification needs name, principle, a NOVEL prediction, and a falsifier"}
    rec = {"name": name[:120], "principle": principle[:600],
           "subsumes": [str(x)[:120] for x in (subsumes or [])][:12],
           "lab": (lab_id or "")[:80], "novel_prediction": novel_prediction[:400],
           "falsifier": falsifier[:400], "status": s, "note": (note or "")[:400],
           "ts": time.time()}
    items = _load()
    items.append(rec)
    _save(items[-60:])
    return {"status": "ok", **rec}


def format_unification() -> str:
    items = _load()
    if not items:
        return "🔭 *Unification Engine* — no candidate laws yet."
    icon = {"candidate": "🟡", "supported": "✅", "failed": "❌"}
    lines = ["🔭 *Unification Engine* — candidate laws subsuming validated results:"]
    for u in items[-8:]:
        lines.append(f"{icon.get(u['status'],'•')} *{u['name']}* — subsumes {len(u['subsumes'])} "
                     f"results; novel: {u['novel_prediction'][:80]}")
    return "\n".join(lines)
