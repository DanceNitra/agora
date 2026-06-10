"""
The Opportunity Scout — Shadow Kael turns the keep outward.

The first public win (a substantive comment on a 189k-star repo's open issue, answered with running
architecture + simulation numbers) was a one-off. The Scout makes it a pipeline: search GitHub for
OPEN issues that are genuine questions Agora's vault can answer with evidence, score the fit, and
surface the best as a candidate for a gated outreach reply. Reputation compounds when you answer
other people's open problems, not when you announce your own — so the Scout hunts other people's
problems. Contacted issues are ledgered; nothing is posted without the owner's approval.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".scout.json"

# Agora's areas of genuine, evidenced strength — the Scout only pitches where we have real notes.
_THEMES = [
    "agent memory consolidation",
    "LLM long-term memory",
    "knowledge base contradiction detection",
    "causal inference difference-in-differences assumptions",
    "RAG memory retrieval forgetting",
    "personal knowledge management note decay",
    "vector store memory pruning",
    "experience replay catastrophic forgetting",
]
_STOP = frozenset("the a an of for to in on and or is are how do does can with this that your you "
                  "what when where why who which from into our we us it its as be by at".split())


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


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z\-]{2,}", (text or "").lower()) if w not in _STOP}


def find_opportunity() -> dict | None:
    """Search GitHub open issues across a rotating strength-theme; return the best-fit candidate
    not already contacted, with a fit score and its text for Claude to judge."""
    from agora.execution.correspondent import _api
    seen = {x.get("url") for x in _load()}
    rot = int(time.time() // 3600) % len(_THEMES)
    theme = _THEMES[rot]
    theme_words = _words(theme)
    q = urllib.parse.quote(f'{theme} is:issue is:open')
    try:
        res = _api("GET", f"/search/issues?q={q}&sort=updated&order=desc&per_page=15")
    except Exception as e:
        return {"error": str(e)[:120], "theme": theme}
    best = None
    for it in res.get("items", []):
        url = it.get("html_url", "")
        if not url or url in seen or it.get("pull_request"):
            continue
        title, body = it.get("title", ""), (it.get("body") or "")[:1200]
        # fit = how much the issue overlaps our strength theme + is it actually a question
        overlap = len(theme_words & _words(title + " " + body))
        asks = 1 if ("?" in title or "?" in body[:400]
                     or re.search(r"\bhow\b|\bwhy\b|\bbest way\b", (title + body[:200]).lower())) else 0
        reactions = (it.get("reactions") or {}).get("total_count", 0)
        score = overlap * 2 + asks * 3 + min(reactions, 5)
        if score >= 5 and (best is None or score > best["score"]):
            m = re.match(r"https://github\.com/([^/]+/[^/]+)/issues/(\d+)", url)
            if not m:
                continue
            best = {"url": url, "repo": m.group(1), "issue_number": int(m.group(2)),
                    "title": title[:160], "body": body[:900], "theme": theme,
                    "score": score, "reactions": reactions}
    return best


def record_contacted(url: str, repo: str, issue: int, outcome: str = "drafted") -> dict | None:
    if not url:
        return None
    items = _load()
    if any(x.get("url") == url for x in items):
        return None
    rec = {"url": url, "repo": (repo or "")[:80], "issue": int(issue or 0),
           "outcome": (outcome or "")[:60], "ts": time.time()}
    items.append(rec)
    _save(items[-120:])
    return rec


def format_scout() -> str:
    items = _load()
    if not items:
        return "🔭 _The scout has logged no opportunities yet._"
    lines = [f"🔭 *The Opportunity Scout* — {len(items)} issues engaged"]
    for x in items[-6:][::-1]:
        lines.append(f"• [{x.get('outcome', '?')}] {x['repo']}#{x['issue']}")
    return "\n".join(lines)
