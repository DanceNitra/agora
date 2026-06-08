"""
Real research grounding — gives agents access to actual frontier papers (arXiv API, free,
no key). Findings written from these are grounded in REAL sources (real titles, authors,
abstracts, URLs) instead of LLM-hallucinated citations.
"""
from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_ARXIV = "http://export.arxiv.org/api/query"
_NS = {"a": "http://www.w3.org/2005/Atom"}


def arxiv_search(query: str, max_results: int = 5) -> list[dict]:
    """Search arXiv for real papers. Returns [{title, authors, summary, url, published}]."""
    q = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
    })
    req = urllib.request.Request(f"{_ARXIV}?{q}",
                                 headers={"User-Agent": "agora-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        return [{"error": str(e)[:120]}]
    out = []
    for entry in root.findall("a:entry", _NS):
        title = (entry.findtext("a:title", "", _NS) or "").strip().replace("\n", " ")
        summary = (entry.findtext("a:summary", "", _NS) or "").strip().replace("\n", " ")
        published = (entry.findtext("a:published", "", _NS) or "")[:10]
        url = (entry.findtext("a:id", "", _NS) or "").strip()
        authors = [a.findtext("a:name", "", _NS) for a in entry.findall("a:author", _NS)]
        out.append({
            "title": title,
            "authors": ", ".join(a for a in authors[:4] if a),
            "summary": summary[:600],
            "url": url,
            "published": published,
        })
    return out


def format_for_prompt(papers: list[dict]) -> str:
    """Compact real-sources block to ground an agent's writing."""
    if not papers or papers[0].get("error"):
        return "(no external sources found)"
    lines = []
    for p in papers:
        lines.append(f"- \"{p['title']}\" ({p['authors']}, {p['published']}) {p['url']}\n"
                     f"  {p['summary'][:280]}")
    return "\n".join(lines)
