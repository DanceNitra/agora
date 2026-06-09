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

SAFE_KINDS = {"build_tool", "build_file", "analysis", "export_insights", "digest"}  # local → auto
GATED_KINDS = {"publish", "send", "repo", "external", "gist", "curate"}  # outward/irreversible → approval


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


def _export_insights(vault_path: str) -> str:
    """Combine all of Agora's Claude-synthesized insights into one shareable markdown file."""
    import glob
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(vault_path) / "04 Resources" / "Concepts" / "Agora Agents"
    files = sorted(glob.glob(str(src / "**" / "insight-*.md"), recursive=True))
    parts = ["# Agora — Insights Digest\n", f"_{len(files)} insights synthesized by Claude via Agora._\n"]
    for f in files:
        parts.append("\n---\n\n" + Path(f).read_text(encoding="utf-8", errors="replace"))
    out = OUTPUT_DIR / "insights_digest.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    return f"exported {len(files)} insights → {out}"


def _run_digest() -> str:
    """Run the digest tool Agora built and capture its output."""
    import subprocess
    import sys
    tool = OUTPUT_DIR / "agora_digest.py"
    if not tool.exists():
        return "digest tool not built yet"
    r = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True, timeout=30)
    return (r.stdout or r.stderr or "")[-400:]


def execute_action(aid: str, vault_path: str = "") -> dict:
    """Carry out an APPROVED deterministic safe action. (build_tool/build_file need Claude; these are
    parameterized actions Agora can run by itself.)"""
    a = get_action(aid)
    if not a or a.get("status") != "approved":
        return {"error": "not approved or not found"}
    try:
        if a["kind"] == "export_insights":
            result = _export_insights(vault_path)
        elif a["kind"] == "digest":
            result = _run_digest()
        elif a["kind"] == "curate":
            # Memory Economy: quarantine the approved batch (reversible move + manifest)
            from agora.execution.memory_economy import quarantine_notes
            q = quarantine_notes(vault_path, a.get("payload", {}).get("paths", []))
            result = f"quarantined {q['moved']} note(s) → {q['batch']}" if q["moved"] \
                else "nothing to quarantine (paths gone or excluded)"
        elif a["kind"] == "publish":
            # Research Exchange: re-compose fresh, then push the digest to the public repo
            from agora.execution.research_exchange import compose_digest, publish_digest
            compose_digest(vault_path)
            p = publish_digest()
            if p.get("error"):
                raise RuntimeError(p["error"])
            result = f"published → {p['url']}" + (f" ({p['note']})" if p.get("note") else "")
        else:
            return {"error": f"kind '{a['kind']}' must be carried out by Claude, not the auto-executor"}
        set_status(aid, "done", result)
        return {"ok": True, "result": result}
    except Exception as e:
        set_status(aid, "failed", str(e)[:200])
        return {"error": str(e)[:200]}


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
