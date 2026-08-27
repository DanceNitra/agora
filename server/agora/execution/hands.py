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

import hashlib
import json
import time
import uuid
from pathlib import Path

_ACTIONS = Path(__file__).resolve().parents[2] / ".actions.json"
OUTPUT_DIR = Path(__file__).resolve().parents[2].parent / "agora_output"

SAFE_KINDS = {"build_tool", "build_file", "analysis", "export_insights", "digest"}  # local → auto
GATED_KINDS = {"publish", "send", "repo", "external", "gist", "curate", "outreach", "press",
               "portfolio", "distribute"}  # → approval


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


# Kinds whose approval must bind the BYTES that go out, not just an id.
#
# WHY. Until 2026-08-14 approval bound `uuid4().hex[:6]` and nothing else. The owner saw at most
# `body[:180]` for outreach and press, a resolved-item COUNT for portfolio, and an insight count for
# publish -- then typed `approve <id>`, and up to 12,000 characters went outward. Worse, the
# executor for `publish` and `portfolio` called compose() FRESH at execution time (its own comments
# said "re-compose fresh"), so the published bytes were generated AFTER the approval and could not
# have been the ones approved even in principle.
#
# So the digest is taken at propose time and re-checked immediately before the send. A change in
# between is a REFUSAL, not a silent publish of whichever version happened to win: the owner
# approved those bytes, and different bytes need a new approval. And a bound kind arriving with no
# digest at all is refused too -- otherwise a proposer that forgets to bind is indistinguishable
# from one that had nothing to bind, which is how the guard stops applying to new callers.
BOUND_KINDS = {"publish", "portfolio", "outreach", "press"}


def content_sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def publishable_text(kind: str, payload: dict | None) -> str | None:
    """The exact text this action will send outward — read the SAME way at propose and execute.

    Returns None when the kind carries no bindable content (an unbound kind, or a record that has
    gone missing). Never raises: a failure here must not be able to take down a proposal.
    """
    payload = payload or {}
    try:
        if kind == "publish":
            from agora.execution.research_exchange import OUTPUT
            return OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None
        if kind == "portfolio":
            from agora.execution.portfolio import OUTPUT
            return OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None
        if kind == "outreach":
            from agora.execution.correspondent import get_draft
            d = get_draft(payload.get("corr_id", ""))
            return d.get("body") if d else None
        if kind == "press":
            from agora.execution.press import _load as _press_load
            r = next((x for x in _press_load() if x.get("id") == payload.get("press_id", "")), None)
            return r.get("body") if r else None
    except Exception:
        return None
    return None


def propose_action(kind: str, title: str, spec: str, payload: dict | None = None) -> dict:
    """Propose an action. Safe kinds are auto-approved (Agora may run them); gated kinds wait for Rasto."""
    kind = (kind or "build_tool").lower().strip()
    gated = kind in GATED_KINDS
    rec = {"id": uuid.uuid4().hex[:6], "kind": kind, "title": title[:120], "spec": spec[:600],
           "payload": payload or {}, "gated": gated,
           "status": "awaiting_approval" if gated else "approved",
           "ts": time.time()}
    body = publishable_text(kind, payload) if kind in BOUND_KINDS else None
    if body is not None:
        rec["content_sha"] = content_sha(body)
        rec["content_len"] = len(body)
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
    """Approve a PENDING action.

    `set_status` never looked at the current status, so a rejected, failed or already-done action
    could be silently re-approved and re-executed. `press` and `correspondent` happen to refuse a
    record whose own status has moved on; `portfolio` and `research_exchange` carry no such guard
    and would publish again.
    """
    a = get_action(aid)
    if a and a.get("status") not in ("awaiting_approval", "approved"):
        return {"error": f"action {aid} is '{a.get('status')}' — only a pending action can be "
                         f"approved. Propose a new one."}
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

    def _check_bound() -> str | None:
        """Refuse unless the bytes about to go out are the ones that were approved.

        Called AFTER any re-compose, so it sees exactly what is about to be published.
        """
        if a["kind"] not in BOUND_KINDS:
            return None
        want = a.get("content_sha")
        if not want:
            return (f"action {aid} ({a['kind']}) carries no content digest, so approval bound only "
                    f"its id. Re-propose it; the proposer must bind the content.")
        now = publishable_text(a["kind"], a.get("payload", {}))
        if now is None:
            return f"the content for action {aid} ({a['kind']}) is gone — nothing to verify or send."
        if content_sha(now) != want:
            return (f"the content changed after approval ({a.get('content_len')} bytes approved, "
                    f"{len(now)} now). Approval binds bytes, so this needs a fresh proposal — "
                    f"nothing was published.")
        return None

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
        elif a["kind"] == "outreach":
            # Correspondent: post the approved draft as a public GitHub issue
            from agora.execution.correspondent import post_outreach
            bad = _check_bound()
            if bad:
                return {"error": bad}
            p = post_outreach(a.get("payload", {}).get("corr_id", ""))
            if p.get("error"):
                raise RuntimeError(p["error"])
            result = f"posted → {p['url']}"
        elif a["kind"] == "publish":
            # Research Exchange: re-compose fresh, then push the digest to the public repo
            from agora.execution.research_exchange import compose_digest, publish_digest
            compose_digest(vault_path)
            bad = _check_bound()          # after the re-compose: this is what would go out
            if bad:
                return {"error": bad}
            p = publish_digest()
            if p.get("error"):
                raise RuntimeError(p["error"])
            result = f"published → {p['url']}" + (f" ({p['note']})" if p.get("note") else "")
        elif a["kind"] == "press":
            # The Press: publish the approved standalone piece into public/posts/
            from agora.execution.press import publish_piece
            bad = _check_bound()
            if bad:
                return {"error": bad}
            p = publish_piece(a.get("payload", {}).get("press_id", ""))
            if p.get("error"):
                raise RuntimeError(p["error"])
            result = f"published → {p['url']}"
        elif a["kind"] == "portfolio":
            # The Portfolio: re-compose fresh, then publish the public track record
            from agora.execution.portfolio import compose, publish
            compose()
            bad = _check_bound()          # after the re-compose: this is what would go out
            if bad:
                return {"error": bad}
            p = publish()
            if p.get("error"):
                raise RuntimeError(p["error"])
            result = f"published → {p['url']}" + (f" ({p['note']})" if p.get("note") else "")
        elif a["kind"] == "distribute":
            # The Distribution Desk: render a ready-to-paste packet + prefilled submit URL
            # (we never auto-post to third-party venues; the owner's one click does).
            from agora.execution.distribution import execute_distribution
            result = execute_distribution(a.get("payload", {}))
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
