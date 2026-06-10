"""
Recall — Agora's curated memory, exposed for external agents.

Agora spends every day curating this vault: value-accounting it (Memory Economy), linking it
(bridges/Atlas), re-embedding it nightly, pruning dead weight, auditing coherence. `recall`
is the memory-provider primitive that lets ANY external agent — Hermes, a Claude Desktop MCP
client — query that curated memory and get back the best notes, ranked by relevance × the
curation value Agora already computed, each with its connections. Agora is the librarian;
others are readers. Read-only.
"""
from __future__ import annotations

import re
from pathlib import Path

_WIKILINK = re.compile(r"\[\[([^\]|#]+)")


def _note_value(path: Path, hits: dict) -> dict:
    """Lightweight per-note curation signal (cheap — only for the few retrieved notes)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"value": 0, "links": 0, "evergreen": False, "snippet": ""}
    head = text[:900]
    evergreen = "status: evergreen" in head
    links = len(set(_WIKILINK.findall(text)))
    body = text.split("---", 2)[-1] if text.startswith("---") else text
    snippet = " ".join(body.split())[:240]
    rel = str(path)
    retrievals = int((hits.get(rel) or hits.get(path.name) or {}).get("n", 0))
    value = (2 if len(text) >= 900 else 1) + (2 if links >= 3 else (1 if links else 0)) \
        + (2 if evergreen else 0) + (1 if retrievals else 0)
    return {"value": value, "links": links, "evergreen": evergreen, "snippet": snippet}


def recall(query: str, vault_path: str, k: int = 6) -> dict:
    """Top curated notes for a query: relevance × Agora's curation value, with connections."""
    from agora.execution.semantic_index import SemanticIndex, retrieval_counts, log_retrieval
    si = SemanticIndex()
    if not si.ready:
        return {"query": query, "results": [], "reason": "index not ready"}
    hits = si.search(query, k * 3)
    if not hits:
        return {"query": query, "results": [], "reason": "no match"}
    counts = retrieval_counts()
    root = Path(vault_path)
    enriched = []
    for h in hits:
        if h.get("score", 0) < 0.4:
            continue
        v = _note_value(root / h["path"], counts)
        # combined score: semantic relevance weighted by curation value (1..7 -> ~0.5..1.5x)
        combined = h["score"] * (0.6 + 0.13 * v["value"])
        enriched.append({"title": h["title"], "relevance": round(h["score"], 3),
                         "value": v["value"], "evergreen": v["evergreen"], "links": v["links"],
                         "snippet": v["snippet"], "_c": combined})
    enriched.sort(key=lambda e: -e["_c"])
    top = enriched[:k]
    log_retrieval([h["path"] for h in hits[:k] if h.get("score", 0) > 0.4])  # demand signal
    for e in top:
        e.pop("_c", None)
    return {"query": query, "results": top, "curator": "Agora", "count": len(top)}


def format_recall(d: dict) -> str:
    res = d.get("results", [])
    if not res:
        return f"🧠 _No curated memory for '{d.get('query','')}'._"
    lines = [f"🧠 *Recall: {d.get('query','')[:50]}* ({len(res)} curated notes)"]
    for r in res:
        tag = " 🌲" if r["evergreen"] else ""
        lines.append(f"• *{r['title'][:54]}*{tag} _(rel {r['relevance']}, val {r['value']}, "
                     f"{r['links']} links)_\n  {r['snippet'][:140]}")
    return "\n".join(lines)
