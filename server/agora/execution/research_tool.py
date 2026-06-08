"""
Real research grounding — gives agents access to actual frontier papers (arXiv API, free,
no key). Findings written from these are grounded in REAL sources (real titles, authors,
abstracts, URLs) instead of LLM-hallucinated citations.
"""
from __future__ import annotations

import json
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


_OPENALEX = "https://api.openalex.org/works"


def _reconstruct_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    words = {}
    for word, positions in inv.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words))[:600]


def openalex_search(query: str, max_results: int = 4) -> list[dict]:
    """Search OpenAlex (ALL scholarly fields, free, no key) — real papers + citation counts."""
    url = (f"{_OPENALEX}?search={urllib.parse.quote(query)}&per-page={max_results}"
           f"&sort=relevance_score:desc&mailto=research@agora.local")
    req = urllib.request.Request(
        url, headers={"User-Agent": "agora-research/1.0 (mailto:research@agora.local)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            results = json.loads(r.read()).get("results", [])
    except Exception as e:
        return [{"error": str(e)[:120]}]
    out = []
    for w in results:
        out.append({
            "title": (w.get("title") or "").strip(),
            "authors": ", ".join((a.get("author") or {}).get("display_name", "")
                                  for a in (w.get("authorships") or [])[:4]),
            "summary": _reconstruct_abstract(w.get("abstract_inverted_index")),
            "url": w.get("doi") or w.get("id", ""),
            "published": str(w.get("publication_year") or ""),
            "citations": w.get("cited_by_count", 0),
        })
    return out


def research(query: str, n: int = 4) -> list[dict]:
    """Real sources across ALL fields: OpenAlex (broad, citation-ranked) + arXiv (latest preprints)."""
    papers = [p for p in openalex_search(query, n) if not p.get("error")]
    papers += [p for p in arxiv_search(query, 2) if not p.get("error")]
    return papers or [{"error": "no sources"}]


def format_for_prompt(papers: list[dict]) -> str:
    """Compact real-sources block to ground an agent's writing."""
    if not papers or papers[0].get("error"):
        return "(no external sources found)"
    lines = []
    for p in papers:
        cite = f", {p['citations']} citations" if p.get("citations") else ""
        lines.append(f"- \"{p['title']}\" ({p['authors']}, {p['published']}{cite}) {p['url']}\n"
                     f"  {p['summary'][:280]}")
    return "\n".join(lines)
