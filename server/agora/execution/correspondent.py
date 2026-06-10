"""
The Correspondent — first contact, gated.

The Salon listens; the Correspondent SPEAKS and listens to the answer. Claude composes a
sharp public post from the system's strongest belief (the claim, the evidence, the falsifier,
and an explicit "what would break this?"), and ONLY after the owner approves the gated
`outreach` action does it get posted — as a GitHub issue on the public agora repo, where real
people can reply. Replies are harvested daily and fed back as named external challenge.
The GitHub token comes from the git credential manager in-process and is never logged.
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".correspondence.json"
_REPO = "DanceNitra/agora"


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


def _github_token() -> str:
    """PAT from the git credential manager — same trust surface as `git push`. Never logged."""
    r = subprocess.run(["git", "credential", "fill"],
                       input="protocol=https\nhost=github.com\n\n",
                       capture_output=True, text=True, timeout=20)
    return next((l[9:] for l in (r.stdout or "").splitlines()
                 if l.startswith("password=")), "")


def _api(method: str, path: str, body: dict | None = None) -> dict:
    tok = _github_token()
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(body).encode() if body else None, method=method,
        headers={"Authorization": "token " + tok, "User-Agent": "agora-correspondent",
                 "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def save_draft(title: str, body: str) -> dict:
    """Store Claude's composed outreach; the caller proposes the gated action around it."""
    rec = {"id": uuid.uuid4().hex[:6], "title": title[:160], "body": body[:6000],
           "status": "draft", "replies_seen": 0, "ts": time.time()}
    items = _load()
    items.append(rec)
    _save(items[-40:])
    return rec


def get_draft(corr_id: str) -> dict | None:
    return next((x for x in _load() if x.get("id") == corr_id), None)


def post_outreach(corr_id: str) -> dict:
    """POST the approved draft as a public GitHub issue (called ONLY from the gated executor)."""
    items = _load()
    rec = next((x for x in items if x.get("id") == corr_id), None)
    if not rec or rec.get("status") not in ("draft", "proposed"):
        return {"error": "no postable draft"}
    issue = _api("POST", f"/repos/{_REPO}/issues",
                 {"title": rec["title"],
                  "body": rec["body"] + "\n\n---\n*Posted by Agora, an autonomous research OS, "
                          "with its owner's approval. Replies are read and challenged back.*"})
    rec["status"] = "posted"
    rec["issue_number"] = issue.get("number")
    rec["issue_url"] = issue.get("html_url", "")
    rec["posted_ts"] = time.time()
    _save(items)
    return {"status": "posted", "url": rec["issue_url"]}


def harvest_replies() -> list[dict]:
    """New comments on posted correspondences — named external challenge coming home."""
    items = _load()
    fresh = []
    for rec in items:
        if rec.get("status") != "posted" or not rec.get("issue_number"):
            continue
        try:
            comments = _api("GET", f"/repos/{_REPO}/issues/{rec['issue_number']}/comments")
        except Exception:
            continue
        new = comments[rec.get("replies_seen", 0):]
        for c in new:
            fresh.append({"corr_id": rec["id"], "title": rec["title"],
                          "by": (c.get("user") or {}).get("login", "?"),
                          "text": (c.get("body") or "")[:500]})
        rec["replies_seen"] = len(comments)
    if fresh:
        _save(items)
    return fresh


def format_correspondence() -> str:
    items = _load()
    if not items:
        return "✉️ _No correspondence yet — the first letter is unwritten._"
    icon = {"draft": "📝", "proposed": "⏸️", "posted": "📮"}
    lines = ["✉️ *The Correspondent*"]
    for r in items[-6:]:
        lines.append(f"{icon.get(r['status'], '•')} [{r['status']}] {r['title'][:60]}")
        if r.get("issue_url"):
            lines.append(f"   {r['issue_url']} · {r.get('replies_seen', 0)} replies")
    return "\n".join(lines)
