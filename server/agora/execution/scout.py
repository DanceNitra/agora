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
# Mix of the proven memory/causal themes (landed the zeroclaw win) + frontier-aligned themes
# (Science of Better Thinking + Future of Work) where our vault can still answer with EVIDENCE.
_THEMES = [
    "agent memory consolidation",
    "LLM long-term memory",
    "knowledge base contradiction detection",
    "causal inference difference-in-differences assumptions",
    "RAG memory retrieval forgetting",
    "personal knowledge management note decay",
    "vector store memory pruning",
    "experience replay catastrophic forgetting",
    # memory-INTEGRITY themes (2026-07-12): we now have the open cross-system benchmark
    # (github.com/DanceNitra/agent-memory-integrity) + measured receipts (echo_guard, revert,
    # retract_lineage) to answer these with evidence — the receipts-flywheel outreach surface.
    "agent memory stale facts correction",
    "memory update supersede outdated fact",
    "agent memory undo revert correction",
    "temporal validity bitemporal agent memory",
    # frontier-aligned (only where we have measured evidence to back a reply)
    "LLM agent reasoning evaluation",
    "forecasting calibration prediction scoring",
    "multi-agent coordination orchestration",
    "knowledge graph completion link prediction",
    "causal inference machine learning treatment effect",
    "early warning critical slowing down detection",
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


def _iso_to_ts(iso: str) -> float:
    try:
        from datetime import datetime, timezone
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return 0.0


MIN_STARS = 3   # a real-community bar: drop solo/0-star repos (keyword match != engagement target)


def find_opportunity() -> dict | None:
    """Search GitHub open issues across a rotating strength-theme; return the best-fit candidate
    not already contacted, with a fit score and its text for Claude to judge. Quality-gated: skip
    self-authored 'issues-as-notebook' entries and require a real-community repo (stars/forks), so a
    mere keyword match on a solo personal project is not surfaced as an outreach target."""
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
    now = time.time()
    cands = []
    for it in res.get("items", []):
        url = it.get("html_url", "")
        if not url or url in seen or it.get("pull_request"):
            continue
        m = re.match(r"https://github\.com/([^/]+/[^/]+)/issues/(\d+)", url)
        if not m:
            continue
        repo = m.group(1)
        # never pitch our own repo (no audience there) — that is announcing, not engaging
        if repo.lower().startswith("dancenitra/"):
            continue
        title, body = it.get("title", ""), (it.get("body") or "")[:1200]
        reactions = (it.get("reactions") or {}).get("total_count", 0)
        comments = it.get("comments", 0)
        author = (it.get("user") or {}).get("login", "").lower()
        owner = repo.split("/")[0].lower()
        # SKIP solo 'issues-as-notebook': the repo owner filing their own issue with NO community
        # response (0 comments + 0 reactions) is a private planning note, not a question to engage.
        if author == owner and comments == 0 and reactions == 0:
            continue
        # FRESHNESS — a reply only lands if the participants are still present. Skip cold threads.
        upd = it.get("updated_at") or ""
        age_d = (now - _iso_to_ts(upd)) / 86400 if upd else 999
        if age_d > 45:                      # cold thread — engaging it is shouting into a void
            continue
        # fit = how much the issue overlaps our strength theme + is it actually a question
        overlap = len(theme_words & _words(title + " " + body))
        asks = 1 if ("?" in title or "?" in body[:400]
                     or re.search(r"\bhow\b|\bwhy\b|\bbest way\b", (title + body[:200]).lower())) else 0
        fresh = 3 if age_d <= 7 else 2 if age_d <= 21 else 0
        score = overlap * 2 + asks * 3 + min(reactions, 5) + min(comments, 5) + fresh
        if score >= 5:
            cands.append({"url": url, "repo": repo, "issue_number": int(m.group(2)),
                          "title": title[:160], "body": body[:900], "theme": theme,
                          "score": score, "reactions": reactions, "comments": comments,
                          "age_days": round(age_d, 1)})
    # COMMUNITY GATE: check the top-scoring candidates' repos (bounded API calls) and return the first
    # that clears the real-community bar (stars/forks). Drops 0-star/0-fork solo projects entirely.
    for c in sorted(cands, key=lambda z: -z["score"])[:6]:
        try:
            rp = _api("GET", f"/repos/{c['repo']}")
            stars = int(rp.get("stargazers_count", 0) or 0)
            forks = int(rp.get("forks_count", 0) or 0)
        except Exception:
            continue
        if stars >= MIN_STARS or forks >= 1:
            c["stars"] = stars
            c["forks"] = forks
            return c
    return None


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
