"""
The Envoy — the outward engagement loop made continuous.

Scout finds open problems; Correspondent drafts and (gated) posts the reply; the Envoy WATCHES
what happens next. It sweeps every posted outreach thread, reads who replied and how the post was
received (reactions), and surfaces real human engagement the moment it appears — so the owner never
has to babysit a GitHub tab to learn whether anyone is responding. Read-only and never posts;
the irreversible outward step stays gated through the Correspondent.

Value (for the Metabolism): replies earned + reactions earned across all posted threads — the only
honest currency of outward reputation.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".envoy.json"
_AGORA_FOOTER = "Drafted by [Agora]"


def _load() -> dict:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {"seen": {}, "ts": 0}


def _save(d: dict) -> None:
    try:
        _STORE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _iso_to_ts(iso: str) -> float:
    try:
        from datetime import datetime, timezone
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return 0.0


def engagement_status() -> list[dict]:
    """Per posted thread: how our outreach landed — reactions on our words, human replies after us,
    and how fresh the thread is. Read-only GitHub reads via the Correspondent's authed client."""
    from agora.execution.correspondent import _api, _load as _corr_load, _REPO, our_login as _our_login
    # One thread can hold several of our comments (an opener + replies). Collapse them to ONE record
    # per repo#issue, keeping the EARLIEST post as the baseline — so every human reply after our first
    # engagement is counted, and the sweep's repo#issue-keyed seen-state can't flip-flop.
    by_thread: dict[str, dict] = {}
    for rec in _corr_load():
        if rec.get("status") != "posted" or not rec.get("issue_number"):
            continue
        key = f"{rec.get('target_repo') or _REPO}#{rec['issue_number']}"
        cur = by_thread.get(key)
        if cur is None or rec.get("posted_ts", 0) < cur.get("posted_ts", 0):
            by_thread[key] = rec
    out = []
    for rec in by_thread.values():
        repo = rec.get("target_repo") or _REPO
        num = rec["issue_number"]
        kind = "comment" if rec.get("target_repo") else "issue"
        item = {"corr_id": rec.get("id"), "repo": repo, "issue": num, "kind": kind,
                "title": rec.get("title", "")[:70], "url": rec.get("issue_url", ""),
                "our_reactions": 0, "replies": 0, "last_activity_ts": rec.get("posted_ts", 0),
                "repliers": []}
        try:
            comments = _api("GET", f"/repos/{repo}/issues/{num}/comments?per_page=100")
        except Exception as e:
            item["error"] = str(e)[:80]
            out.append(item)
            continue
        posted = rec.get("posted_ts", 0)
        mine_login = _our_login().lower()
        for c in comments:
            cts = _iso_to_ts(c.get("created_at") or "")
            item["last_activity_ts"] = max(item["last_activity_ts"], cts)
            login = (c.get("user") or {}).get("login", "")
            mine = login.lower() == mine_login   # by AUTHOR — a reply that quotes our footer is NOT ours
            if mine and kind == "comment":
                item["our_reactions"] = (c.get("reactions") or {}).get("total_count", 0)
            elif cts > posted and not mine:
                item["replies"] += 1
                if login and login not in item["repliers"]:
                    item["repliers"].append(login)
        if kind == "issue":
            try:
                iss = _api("GET", f"/repos/{repo}/issues/{num}")
                item["our_reactions"] = (iss.get("reactions") or {}).get("total_count", 0)
            except Exception:
                pass
        out.append(item)
    return out


def sweep() -> dict:
    """One Envoy pass: harvest new named replies (Correspondent) + current engagement on every
    thread. Returns the full status plus only the events that are NEW since the last sweep, so a
    caller can alert the owner exactly once per real reaction or reply."""
    from agora.execution.correspondent import harvest_replies
    fresh_replies = harvest_replies()          # named external challenge coming home
    status = engagement_status()
    state = _load()
    seen = state.get("seen", {})
    events = []
    for s in status:
        key = f"{s['repo']}#{s['issue']}"
        prev = seen.get(key, {"replies": 0, "our_reactions": 0})
        if s["replies"] > prev.get("replies", 0):
            who = ", ".join(s["repliers"][-3:]) or "someone"
            events.append(f"{key}: {s['replies'] - prev['replies']} new reply ({who})")
        if s["our_reactions"] > prev.get("our_reactions", 0):
            events.append(f"{key}: +{s['our_reactions'] - prev['our_reactions']} reaction(s)")
        seen[key] = {"replies": s["replies"], "our_reactions": s["our_reactions"]}
    state["seen"] = seen
    state["ts"] = time.time()
    _save(state)
    return {"status": status, "new_events": events, "fresh_replies": fresh_replies}


def value_points() -> float:
    """Outward currency: 2 per human reply earned + 1 per reaction, across all posted threads."""
    total = 0.0
    for s in engagement_status():
        total += 2.0 * s.get("replies", 0) + 1.0 * s.get("our_reactions", 0)
    return total


def format_envoy() -> str:
    status = engagement_status()
    if not status:
        return "🛰 _The Envoy is watching no threads yet — post an outreach first._"
    now = time.time()
    lines = ["🛰 *The Envoy* — outward engagement"]
    for s in status:
        age_d = (now - s["last_activity_ts"]) / 86400 if s["last_activity_ts"] else 0
        tail = f"{s['replies']} replies · {s['our_reactions']} reactions · last activity {age_d:.0f}d ago"
        lines.append(f"• {s['repo']}#{s['issue']} — {tail}")
        if s.get("repliers"):
            lines.append(f"   ↳ {', '.join(s['repliers'][-4:])}")
    return "\n".join(lines)
