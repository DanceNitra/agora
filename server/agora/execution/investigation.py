"""
Multi-step Investigation Engine — depth, not one-shot.

A one-shot Lab run answers a single question. A breakthrough needs a CHAIN: measure, read the result,
refine the question, measure again, until a hard claim is settled or broken. This organ records such a
chain as ONE durable investigation — each step carries a Lab id + a finding + the next question it
provokes — so the system can attack a hard problem with real depth and the whole reasoning path is
auditable. (The reasoning between steps is Claude's; this is the ledger that makes it compounding,
not ephemeral.)
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".investigations.json"


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


def _find(items: list, inv_id: str) -> dict | None:
    return next((x for x in items if x.get("id") == inv_id), None)


def handle(action: str, body: dict) -> dict:
    """One entrypoint for the investigation lifecycle: start | step | conclude."""
    items = _load()
    a = (action or "").strip().lower()

    if a == "start":
        q = (body.get("question") or "").strip()
        if not q:
            return {"error": "a question is required"}
        rec = {"id": uuid.uuid4().hex[:6], "question": q[:300], "ts": time.time(),
               "steps": [], "status": "open", "conclusion": ""}
        items.append(rec)
        _save(items[-80:])
        return {"status": "ok", **rec}

    if a == "step":
        inv = _find(items, body.get("id") or "")
        if not inv:
            return {"error": "no such investigation"}
        if inv.get("status") != "open":
            return {"error": "investigation is not open"}
        step = {"n": len(inv["steps"]) + 1, "name": (body.get("name") or "")[:140],
                "lab_id": (body.get("lab_id") or "")[:80],
                "finding": (body.get("finding") or "")[:500],
                "next_question": (body.get("next_question") or "")[:300], "ts": time.time()}
        inv["steps"].append(step)
        _save(items)
        return {"status": "ok", "investigation": inv["id"], "step": step["n"], "recorded": step}

    if a == "conclude":
        inv = _find(items, body.get("id") or "")
        if not inv:
            return {"error": "no such investigation"}
        inv["status"] = "concluded"
        inv["conclusion"] = (body.get("verdict") or "")[:600]
        inv["concluded_ts"] = time.time()
        _save(items)
        return {"status": "ok", "investigation": inv["id"], "steps": len(inv["steps"]),
                "conclusion": inv["conclusion"]}

    return {"error": f"unknown action '{action}' (use start|step|conclude)"}


def format_investigations() -> str:
    items = _load()
    if not items:
        return "🔬 *Investigations* — none yet."
    icon = {"open": "🟡", "concluded": "✅"}
    lines = ["🔬 *Multi-step investigations* (depth chains):"]
    for inv in items[-6:]:
        lines.append(f"{icon.get(inv['status'],'•')} *{inv['question'][:70]}* — {len(inv['steps'])} steps"
                     + (f"; {inv['conclusion'][:80]}" if inv.get("conclusion") else ""))
    return "\n".join(lines)
