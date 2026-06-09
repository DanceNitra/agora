"""
Agora's Senses — perceive your NOW.

Until now Agora lives in a static vault and the timeless literature. This gives it a sense of the
present moment, tuned to YOU: for the domains the user actually works in (from the Personal Context
Model), it perceives what is live right now — the hottest current discussions and the latest research.
The vault is your past; the senses are your present. And what they perceive can feed cognition: Agora
can think about what is hot NOW, not only what is already written down.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


def _hn_recent(query: str, n: int = 5, days: int = 60) -> list:
    """Recent + popular Hacker News stories on a topic — 'what's hot NOW', not all-time favourites."""
    cutoff = int(time.time()) - days * 86400
    url = (f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(query)}"
           f"&tags=story&numericFilters=created_at_i>{cutoff}&hitsPerPage={n}")
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            hits = json.loads(r.read()).get("hits", [])
        return [{"title": h.get("title"), "points": h.get("points"), "comments": h.get("num_comments"),
                 "date": (h.get("created_at") or "")[:10]} for h in hits if h.get("title")]
    except Exception:
        return []


# ── Today senses: the OWNER's actual day, not just the world's ──────────────

def _ics_today(ics_path: str) -> list:
    """Today's events from an exported .ics file (set AGORA_ICS_PATH in server/.env; no OAuth).
    Stdlib parse: unfold lines, walk VEVENT blocks, keep events whose DTSTART date is today."""
    p = Path(ics_path) if ics_path else None
    if not p or not p.is_file():
        return []
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    lines, today = [], datetime.now().strftime("%Y%m%d")
    for ln in raw.splitlines():          # unfold RFC5545 continuation lines
        if ln[:1] in (" ", "\t") and lines:
            lines[-1] += ln[1:]
        else:
            lines.append(ln)
    events, cur = [], None
    for ln in lines:
        if ln.startswith("BEGIN:VEVENT"):
            cur = {}
        elif ln.startswith("END:VEVENT") and cur is not None:
            if cur.get("date") == today and cur.get("summary"):
                events.append({"time": cur.get("time", ""), "summary": cur["summary"][:80]})
            cur = None
        elif cur is not None:
            if ln.startswith("DTSTART"):
                m = re.search(r":(\d{8})(?:T(\d{4}))?", ln)
                if m:
                    cur["date"] = m.group(1)
                    cur["time"] = f"{m.group(2)[:2]}:{m.group(2)[2:]}" if m.group(2) else "all-day"
            elif ln.startswith("SUMMARY"):
                cur["summary"] = ln.split(":", 1)[-1].strip()
    return sorted(events, key=lambda e: (e.get("time") != "all-day", e.get("time", "")))[:8]


def _vault_recent_edits(vault_path: str, hours: int = 36, n: int = 6) -> list:
    """The notes the OWNER actually touched recently (agent-written dirs excluded) — what
    Rasto is working on right now, by mtime."""
    root = Path(vault_path)
    if not root.is_dir():
        return []
    cutoff = time.time() - hours * 3600
    skip = ("\\.obsidian", "/.obsidian", "\\.git", "/.git", "Agora Agents", ".trash")
    out = []
    try:
        for p in root.rglob("*.md"):
            sp = str(p)
            if any(s in sp for s in skip):
                continue
            mt = p.stat().st_mtime
            if mt >= cutoff:
                out.append({"title": p.stem, "ago_h": round((time.time() - mt) / 3600, 1)})
    except Exception:
        pass
    return sorted(out, key=lambda e: e["ago_h"])[:n]


def _repo_activity(repo: str = "", hours: int = 24, n: int = 5) -> list:
    """What shipped in the agora repo today (subject lines)."""
    repo = repo or str(Path(__file__).resolve().parents[3])
    try:
        r = subprocess.run(["git", "-C", repo, "log", f"--since={hours} hours ago",
                            "--pretty=%s", f"-{n}"],
                           capture_output=True, text=True, timeout=10)
        return [ln.strip()[:80] for ln in r.stdout.splitlines() if ln.strip()]
    except Exception:
        return []


def sense_today(vault_path: str) -> dict:
    """The owner's live day: calendar (optional .ics), fresh vault edits, repo activity."""
    return {"calendar": _ics_today(os.environ.get("AGORA_ICS_PATH", "")),
            "vault_edits": _vault_recent_edits(vault_path),
            "repo": _repo_activity()}


async def sense_now(vault_path: str, max_domains: int = 3) -> dict:
    """Perceive the live signal in the user's own domains — current discussion + fresh research."""
    from agora.execution.user_model import build_user_model
    from agora.execution.research_tool import research

    model = await build_user_model(vault_path)
    domains = [d.strip() for d in (model.get("domains", "") or "").split(",") if d.strip()][:max_domains]
    if not domains:
        domains = ["artificial intelligence"]

    signals = []
    for dom in domains:
        recent = await asyncio.to_thread(_hn_recent, dom, 6)
        stories = sorted(recent, key=lambda s: -(s.get("points") or 0))[:2]
        papers = await asyncio.to_thread(research, dom, 2)
        latest = [{"title": getattr(p, "title", None) or p.get("title", ""),
                   "year": getattr(p, "year", None) or p.get("year", "")}
                  for p in (papers or [])][:1]
        signals.append({"domain": dom, "stories": stories, "papers": latest})
    today = await asyncio.to_thread(sense_today, vault_path)
    return {"domains": domains, "signals": signals, "today": today,
            "sensed_at": int(time.time())}


def hottest_topic(sensed: dict) -> str:
    """The single liveliest thing right now — the most-discussed current story title."""
    best, best_pts = "", -1
    for s in sensed.get("signals", []):
        for st in s.get("stories", []):
            if (st.get("points") or 0) > best_pts:
                best, best_pts = st.get("title", ""), st.get("points") or 0
    return best


def format_now(r: dict) -> str:
    if not r.get("signals"):
        return "🌐 Couldn't sense the world right now."
    lines = ["🌐 *Pulse of your world* — live in your domains\n"]
    today = r.get("today") or {}
    if any(today.get(k) for k in ("calendar", "vault_edits", "repo")):
        lines.append("*Your day*")
        for e in today.get("calendar", []):
            lines.append(f"  🗓 {e.get('time', '')} {e.get('summary', '')}")
        for e in today.get("vault_edits", [])[:3]:
            lines.append(f"  ✏️ {e['title'][:56]} _({e['ago_h']}h ago)_")
        for s in today.get("repo", [])[:3]:
            lines.append(f"  ⚙ {s[:64]}")
        lines.append("")
    for s in r["signals"]:
        lines.append(f"*{s['domain']}*")
        for st in s.get("stories", []):
            lines.append(f"  • {st.get('title', '')[:62]} _({st.get('points')}pts · {st.get('date', '')})_")
        for p in s.get("papers", []):
            if p.get("title"):
                lines.append(f"  📄 {p['title'][:60]} _({p.get('year', '')})_")
    return "\n".join(lines)
