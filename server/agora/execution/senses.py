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
import time
import urllib.parse
import urllib.request


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
    return {"domains": domains, "signals": signals, "sensed_at": int(time.time())}


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
    for s in r["signals"]:
        lines.append(f"*{s['domain']}*")
        for st in s.get("stories", []):
            lines.append(f"  • {st.get('title', '')[:62]} _({st.get('points')}pts · {st.get('date', '')})_")
        for p in s.get("papers", []):
            if p.get("title"):
                lines.append(f"  📄 {p['title'][:60]} _({p.get('year', '')})_")
    return "\n".join(lines)
