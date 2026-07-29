"""
The Library — Agora reads a whole paper, not just the abstract.

The entire system grounds itself in abstracts: breadth without depth. Once a day the Library
fetches ONE full paper, reads it section by section, and (gathers → Claude writes) produces a
structured note: the central claims, the strength of evidence (N, method, limitations), and
links to the owner's real notes. Over a month this turns the second brain's grounding from
abstract-deep to actually-read-deep. HTML-first via ar5iv (arXiv's HTML mirror) — far more
robust than PDF parsing.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".library.json"
_READLIST = Path(__file__).resolve().parents[2] / ".reading_list.json"


def _read_list() -> list:
    try:
        return json.loads(_READLIST.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_read_list(items: list) -> None:
    try:
        _READLIST.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def queue_reading(arxiv_ids: list[str], source: str = "") -> dict:
    """Add curated arXiv IDs to the priority reading list (the Library reads these before it
    falls back to domain search). Skips already-read and already-queued."""
    rl = _read_list()
    have = {x["arxiv_id"] for x in rl} | _already_read()
    added = 0
    for aid in arxiv_ids:
        aid = (aid or "").strip()
        if re.fullmatch(r"\d{4}\.\d{4,5}", aid) and aid not in have:
            rl.append({"arxiv_id": aid, "source": source[:80], "ts": time.time()})
            have.add(aid)
            added += 1
    _save_read_list(rl[-200:])
    return {"added": added, "queued_total": len(rl)}


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


def _already_read() -> set[str]:
    return {x.get("arxiv_id") for x in _load() if x.get("arxiv_id")}


def _arxiv_id(url: str) -> str:
    m = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+)", url or "")
    return m.group(1) if m else ""


def _fetch_fulltext(arxiv_id: str) -> str:
    """Full text via ar5iv (arXiv HTML mirror). Strip tags to readable text — no PDF parsing."""
    url = f"https://ar5iv.org/abs/{arxiv_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "agora-library/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception:
        return ""
    html = re.sub(r"(?is)<(script|style|nav|footer|head).*?</\1>", " ", html)
    html = re.sub(r"(?is)<math.*?</math>", " ", html)            # drop MathML noise
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&#?\w+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def gather_paper_inputs(query: str = "") -> dict:
    """Pick one unread, relevant, recent paper and return its readable full text for Claude to
    digest into a structured note. Query defaults to the user's top domain."""
    import asyncio
    from agora.execution.research_tool import arxiv_search
    # PRIORITY: serve the curated reading list first (deep-read what we deliberately queued)
    seen0 = _already_read()
    rl = _read_list()
    for entry in list(rl):
        aid = entry["arxiv_id"]
        if aid in seen0:
            rl.remove(entry)
            continue
        text = await asyncio.to_thread(_fetch_fulltext, aid)
        if len(text) < 2500:
            rl.remove(entry)                 # ar5iv miss → drop, try next time
            _save_read_list(rl)
            continue
        meta = await asyncio.to_thread(arxiv_search, aid, 1)
        title = (meta[0]["title"] if meta and not meta[0].get("error") else aid)
        rl.remove(entry)
        _save_read_list(rl)
        return {"arxiv_id": aid, "title": title, "authors": "", "from_reading_list": True,
                "url": f"http://arxiv.org/abs/{aid}", "published": "", "query": entry.get("source", ""),
                "fulltext": text[:14000]}
    if not query:
        # FALL BACK TO THE FRONTIER LIST, not to a word from the vault.
        #
        # This took `domains[0]` from the vault model -- currently 'AI/agent systems', a bare multi-word
        # string, and the vault's domains are the owner's GENERAL interests, not the locked frontier. So
        # the fallback aimed at a different target than every other reader in the system.
        #
        # It is NOT where the 202 off-mission papers in .library.json came from -- I accused it of that and
        # the measurement refuted me: under sort='relevance' (what this caller uses) even the bare phrase
        # returns 8/8 on-mission hits. Those papers came in through the READING LIST, queued by the
        # pre-2026-07-20 frontier queries, and their `source` field says so. Fixing this is still right,
        # but it fixes an aim, not that incident.
        #
        # _FRONTIER_QUERIES is curated, quoted-phrase, AND-joined and locked to the owner's frontier. The
        # reading list drains precisely because those queries are narrow, so the moment the Library needs
        # a fallback is the moment it most needs them.
        try:
            from agora.execution.frontier_harvest import _FRONTIER_QUERIES
            query = _FRONTIER_QUERIES[int(time.time() // 3600) % len(_FRONTIER_QUERIES)]
        except Exception:
            query = 'abs:"agent memory" AND (abs:"language model" OR abs:LLM)'
    papers = await asyncio.to_thread(arxiv_search, query, 8)
    seen = _already_read()
    for p in papers:
        if p.get("error"):
            continue
        aid = _arxiv_id(p.get("url", ""))
        if not aid or aid in seen:
            continue
        text = await asyncio.to_thread(_fetch_fulltext, aid)
        if len(text) < 2500:        # ar5iv miss / too thin → try the next paper
            continue
        return {"arxiv_id": aid, "title": p["title"], "authors": p.get("authors", ""),
                "url": p["url"], "published": p.get("published", ""), "query": query,
                "fulltext": text[:14000]}
    return {"arxiv_id": "", "reason": "no unread full-text paper found", "query": query}


def record_paper(arxiv_id: str, title: str, url: str, note_path: str = "") -> dict:
    """Mark a paper read (bibliography ledger)."""
    items = _load()
    rec = {"arxiv_id": arxiv_id, "title": title[:160], "url": url,
           "note": note_path, "ts": time.time()}
    items.append(rec)
    _save(items[-300:])
    return rec


def format_library(n: int = 8) -> str:
    items = _load()[-n:]
    if not items:
        return "📚 _The library is empty — Agora hasn't read a full paper yet._"
    lines = [f"📚 *Agora's library* — {len(_load())} papers read in full"]
    for x in reversed(items):
        lines.append(f"• {x['title'][:64]} _({x['arxiv_id']})_")
    return "\n".join(lines)
