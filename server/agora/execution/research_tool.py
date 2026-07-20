"""
Real research grounding — gives agents access to actual frontier papers (OpenAlex across all
scholarly fields + arXiv for the latest preprints, both free, no key). Findings written from
these are grounded in REAL sources (real titles, authors, abstracts, URLs) instead of
LLM-hallucinated citations.

Two things kept the grounding weak in practice and are fixed here: (1) verbose natural-language
sub-questions were passed straight to keyword search engines, which match them poorly — we now
distil a focused keyword query first; (2) the dungeon's polling hammered OpenAlex into HTTP 429
— we now cache responses on disk and back off on rate-limit.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

_ARXIV = "http://export.arxiv.org/api/query"
_NS = {"a": "http://www.w3.org/2005/Atom"}

# query distillation — strip the interrogative scaffolding so the keyword engines see signal
_STOP = {
    "what", "which", "how", "when", "where", "why", "who", "whom", "does", "do", "did", "is",
    "are", "was", "were", "the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "that",
    "this", "these", "those", "with", "by", "from", "as", "at", "be", "been", "can", "could",
    "would", "should", "may", "might", "have", "has", "had", "its", "their", "it", "they",
    "measured", "give", "given", "exists", "exist", "shows", "show", "based", "such", "e.g",
    "via", "into", "than", "under", "about", "any", "more", "most", "much", "many", "some",
    "not", "no", "yet", "still", "over", "out", "between", "across", "per", "only", "also",
}


def distill_query(question: str, max_terms: int = 8) -> str:
    """Turn a verbose sub-question into a focused keyword query the search APIs handle well.
    Keeps salient words (incl. hyphenated/quoted terms), drops interrogative stopwords."""
    quoted = re.findall(r'"([^"]{3,40})"', question)
    words = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", question)
    seen, terms = set(), []
    for w in words:
        lw = w.lower()
        if lw in _STOP or lw in seen:
            continue
        seen.add(lw)
        terms.append(w)
        if len(terms) >= max_terms:
            break
    q = " ".join(quoted + terms).strip()
    return q or question[:80]


_CACHE_DIR = Path(__file__).resolve().parents[2] / ".research_cache"
_CACHE_TTL = 7 * 86400          # a paper search is stable for a week


def _cache_get(key: str):
    f = _CACHE_DIR / (key + ".json")
    try:
        if f.exists() and time.time() - f.stat().st_mtime < _CACHE_TTL:
            return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _cache_put(key: str, value) -> None:
    try:
        _CACHE_DIR.mkdir(exist_ok=True)
        (_CACHE_DIR / (key + ".json")).write_text(
            json.dumps(value, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _cache_key(prefix: str, query: str, n: int) -> str:
    import hashlib
    return f"{prefix}_{hashlib.sha1(f'{query}|{n}'.encode()).hexdigest()[:16]}"


def _get_json(url: str, headers: dict, retries: int = 2):
    """GET with a small backoff on HTTP 429 (OpenAlex rate-limits a polling fleet)."""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                        timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def arxiv_search(query: str, max_results: int = 5, sort: str = "relevance") -> list[dict]:
    """Search arXiv for real papers. Returns [{title, authors, summary, url, published}].
    sort='relevance' (default) for best-match; sort='submittedDate' for newest-first (used by the
    frontier harvester so it pulls FRESH papers instead of re-finding the same already-read top hits)."""
    # A bare multi-word phrase under `all:` is OR-matched by arXiv, so combining it with
    # sortBy=submittedDate returns "the newest papers containing ANY of these words" — effectively the
    # arXiv firehose (measured 2026-07-20: the query "conversational memory long-term dialogue" returned
    # MoE serving, risky-driving vision and physics-RL papers). Callers may therefore pass FULL arXiv
    # query syntax (field prefixes, quoted phrases, AND/OR); we only wrap a bare phrase in `all:`.
    _raw = (query or "").strip()
    _structured = bool(re.search(r'(?:\b(?:all|ti|abs|au|cat|id):)|\b(?:AND|OR|ANDNOT)\b', _raw))
    params = {
        "search_query": _raw if _structured else f"all:{_raw}",
        "start": 0,
        "max_results": max_results,
        "sortBy": sort,
    }
    if sort == "submittedDate":
        params["sortOrder"] = "descending"
    q = urllib.parse.urlencode(params)
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
    """Search OpenAlex (ALL scholarly fields, free, no key) — real papers + citation counts.
    Cached on disk and backed off on 429 so the dungeon's polling can't starve grounding."""
    ck = _cache_key("oa", query, max_results)
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    url = (f"{_OPENALEX}?search={urllib.parse.quote(query)}&per-page={max_results}"
           f"&sort=relevance_score:desc&mailto=research@agora.local")
    try:
        results = _get_json(
            url, {"User-Agent": "agora-research/1.0 (mailto:research@agora.local)"}
        ).get("results", [])
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
    _cache_put(ck, out)
    return out


def research(query: str, n: int = 4) -> list[dict]:
    """Real sources across ALL fields: OpenAlex (broad, citation-ranked) + arXiv (latest
    preprints). The verbose query is distilled to keywords first so the engines match on signal."""
    kw = distill_query(query)
    papers = [p for p in openalex_search(kw, n) if not p.get("error")]
    papers += [p for p in arxiv_search(kw, 2) if not p.get("error")]
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
