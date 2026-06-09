"""
The Salon — external minds as sparring partners.

The system has been an epistemic island: all challenge is generated from itself and from raw
data. The Salon follows a curated set of living, high-grade external feeds (verified live on
2026-06-10: validity + recency + fit to the project's domains), senses their NEW pieces, and
extracts ONE contestable claim a day to throw into the dialectic pipeline — named external
disagreement, the best kind. Curation favours low-noise depth over volume.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".salon.json"

# Live-verified 2026-06-10 (feed validity + last-post recency + project fit).
# Dropped at research time: Gwern substack (dormant since 2021), Dan Luu (dormant since 2024).
FEEDS = [
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),       # LLM/agent engineering
    ("Andrew Gelman", "https://statmodeling.stat.columbia.edu/feed/"),      # stats + causal inference
    ("Astral Codex Ten", "https://www.astralcodexten.com/feed"),            # epistemics, forecasting
    ("Quanta Magazine", "https://www.quantamagazine.org/feed/"),            # complexity, neuro, math
    ("Interconnects", "https://www.interconnects.ai/feed"),                 # frontier AI analysis
    ("Marginal Revolution", "https://marginalrevolution.com/feed"),         # econ/finance cross-domain
    ("Lil'Log", "https://lilianweng.github.io/index.xml"),                  # deep ML/agent essays
    ("Maggie Appleton", "https://maggieappleton.com/rss.xml"),              # tools for thought
]


def _load() -> dict:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {"seen": [], "claims": []}


def _save(d: dict) -> None:
    try:
        _STORE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _fetch_feed(url: str, n: int = 5) -> list[dict]:
    """Newest items from one RSS/Atom feed — stdlib regex parse, robust to both dialects."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "agora-salon/1.0"})
        raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    except Exception:
        return []
    items = []
    for m in list(re.finditer(r"<(item|entry)[\s>](.*?)</\1>", raw, re.DOTALL))[:n]:
        block = m.group(2)
        tm = re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
        lm = (re.search(r"<link[^>]*href=\"([^\"]+)\"", block)
              or re.search(r"<link[^>]*>([^<]+)</link>", block))
        sm = re.search(r"<(?:description|summary|content)[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?"
                       r"</(?:description|summary|content)>", block, re.DOTALL)
        title = re.sub(r"\s+", " ", (tm.group(1) if tm else "")).strip()[:160]
        summary = re.sub(r"<[^>]+>", " ", (sm.group(1) if sm else ""))
        summary = re.sub(r"\s+", " ", summary).strip()[:600]
        if title:
            items.append({"title": title, "link": (lm.group(1).strip() if lm else "")[:300],
                          "summary": summary})
    return items


def sense_salon(per_feed: int = 4) -> list[dict]:
    """New (unseen) pieces across the salon — newest first per feed."""
    d = _load()
    seen = set(d.get("seen", []))
    fresh = []
    for author, url in FEEDS:
        for it in _fetch_feed(url, per_feed):
            key = it["link"] or f"{author}:{it['title']}"
            if key in seen:
                continue
            seen.add(key)
            fresh.append({"author": author, **it})
    d["seen"] = list(seen)[-2000:]
    _save(d)
    return fresh


def extract_claim(item: dict) -> str:
    """One contestable claim from a piece (flash labeled-text; '' when there is none)."""
    from agora.execution.llm_client import call_llm
    raw = call_llm(
        "From the article below extract ONE strong, contestable, self-contained CLAIM the "
        "author makes or clearly implies (a position someone informed could argue against — "
        "not a fact report, not an announcement). Reply EXACTLY:\nCLAIM: <one sentence>\n"
        "or\nCLAIM: NONE",
        f"AUTHOR: {item['author']}\nTITLE: {item['title']}\nEXCERPT: {item['summary'][:550]}",
        "cheap", 0.3, 200) or ""
    m = re.search(r"CLAIM:\s*(.+)", raw, re.DOTALL | re.I)
    claim = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    return "" if (not claim or claim.upper().startswith("NONE") or len(claim) < 25) else claim[:200]


def record_claim(author: str, title: str, claim: str) -> None:
    d = _load()
    d.setdefault("claims", []).append({"author": author, "title": title[:120],
                                       "claim": claim, "ts": time.time()})
    d["claims"] = d["claims"][-100:]
    _save(d)


def format_salon(n: int = 8) -> str:
    d = _load()
    claims = d.get("claims", [])[-n:]
    lines = [f"🥂 *The Salon* — {len(FEEDS)} minds followed"]
    if claims:
        lines.append("*Recent claims taken to the dialectic:*")
        for c in reversed(claims):
            lines.append(f"• [{c['author']}] {c['claim'][:90]}")
    else:
        lines.append("_No claims extracted yet — the conversation starts tonight._")
    return "\n".join(lines)
