"""
Agora's Hands — from a mind that knows to an agent that DOES.

Everything so far is contemplative: Agora thinks and writes notes. This lets it ACT in the real world —
build real working tools and files, run analyses, and (gated) reach outward. Safety is the core design,
not an afterthought:

  • SAFE actions (build a local tool/file, run a read-only analysis) are local and reversible → Agora
    may execute them autonomously.
  • GATED actions (publish, send, modify a real repo, call an external service) are outward or hard to
    reverse → Agora may only PROPOSE them; nothing runs until Rasto approves it from Telegram.

So Agora gains hands without gaining the ability to do something irreversible behind your back.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

_ACTIONS = Path(__file__).resolve().parents[2] / ".actions.json"
OUTPUT_DIR = Path(__file__).resolve().parents[2].parent / "agora_output"

SAFE_KINDS = {"build_tool", "build_file", "analysis"}          # local + reversible → auto
GATED_KINDS = {"publish", "send", "repo", "external"}          # outward / irreversible → needs approval


def _load() -> list:
    try:
        return json.loads(_ACTIONS.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(a: list) -> None:
    try:
        _ACTIONS.write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def propose_action(kind: str, title: str, spec: str, payload: dict | None = None) -> dict:
    """Propose an action. Safe kinds are auto-approved (Agora may run them); gated kinds wait for Rasto."""
    kind = (kind or "build_tool").lower().strip()
    gated = kind in GATED_KINDS
    rec = {"id": uuid.uuid4().hex[:6], "kind": kind, "title": title[:120], "spec": spec[:600],
           "payload": payload or {}, "gated": gated,
           "status": "awaiting_approval" if gated else "approved",
           "ts": time.time()}
    a = _load()
    a.append(rec)
    _save(a[-100:])
    return rec


def list_actions(n: int = 20) -> list:
    return sorted(_load(), key=lambda x: -x.get("ts", 0))[:n]


def get_action(aid: str) -> dict | None:
    return next((x for x in _load() if x.get("id") == aid), None)


def set_status(aid: str, status: str, result: str = "") -> dict | None:
    a = _load()
    hit = None
    for x in a:
        if x.get("id") == aid:
            x["status"] = status
            if result:
                x["result"] = result[:400]
            x[f"{status}_ts"] = time.time()
            hit = x
    _save(a)
    return hit


def approve_action(aid: str) -> dict | None:
    return set_status(aid, "approved")


def reject_action(aid: str) -> dict | None:
    return set_status(aid, "rejected")


def ready_to_execute() -> list:
    """Approved actions that have not run yet — what Agora's hands may now carry out."""
    return [x for x in _load() if x.get("status") == "approved"]


def pending_approvals() -> list:
    return [x for x in _load() if x.get("status") == "awaiting_approval"]


def format_actions() -> str:
    a = list_actions(8)
    if not a:
        return "🦾 No actions yet."
    icon = {"approved": "▶️", "awaiting_approval": "⏸️", "done": "✅", "failed": "❌", "rejected": "🚫"}
    lines = ["🦾 *Agora's actions*"]
    for x in a:
        gate = " _(needs approve)_" if x["status"] == "awaiting_approval" else ""
        lines.append(f"{icon.get(x['status'], '•')} `{x['id']}` [{x['kind']}] {x['title'][:50]}{gate}")
    return "\n".join(lines)
