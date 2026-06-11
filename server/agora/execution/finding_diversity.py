"""
Finding-diversity metric — measure the RAW (pre-promotion) findings stream for churn.

The system's self-proposals periodically claim it "keeps re-deriving the same findings / returning to
the same papers". The vault output is already deduped, so that complaint is about the raw
`collective_knowledge` discovery stream. This turns the complaint into a NUMBER: what fraction of
recent findings have a near-duplicate, and how concentrated are the cited sources — so we decide on
data (and can watch it change after a planner swap), not on a guess.
"""
from __future__ import annotations

import re
from collections import Counter

_STOP = set((
    "the a an of to in on and or for with that this from are is was were be been being it its as at "
    "by we our their they them not no does can will would could should which who whom whose into "
    "about between among across over under more most less than then thus also such these those some "
    "any each both either neither finding findings result results study studies paper papers source"
).split())


def _tokens(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 3 and w not in _STOP}


def _containment(a: set, b: set) -> float:
    """Overlap coefficient — fraction of the SMALLER token set shared (catches 'A restated as a
    longer A' paraphrases that Jaccard would dilute)."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _claim(content: str) -> str:
    return (content or "").split("Source:")[0][:600]


_CITE = re.compile(r"[A-Z][A-Za-z\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\-]+|\s+et al\.?)?\s*\((?:19|20)\d{2}\)")


def _source(content: str):
    m = _CITE.search(content or "")
    return m.group(0).strip() if m else None


async def finding_diversity(db, n: int = 60, threshold: float = 0.6) -> dict:
    cur = await db.execute(
        "SELECT title, content FROM collective_knowledge WHERE knowledge_type='discovery' "
        "ORDER BY created_at DESC LIMIT ?", (n,))
    rows = await cur.fetchall()
    toks = [_tokens((r["title"] or "") + " " + _claim(r["content"] or "")) for r in rows]
    near = 0
    for i in range(len(toks)):
        if any(i != j and _containment(toks[i], toks[j]) >= threshold for j in range(len(toks))):
            near += 1
    srcs = [s for s in (_source(r["content"] or "") for r in rows) if s]
    sc = Counter(srcs)
    total = len(rows)
    top = sc.most_common(3)
    return {
        "window": total,
        "near_dup_rate": round(near / total, 3) if total else 0.0,
        "near_dup_count": near,
        "distinct_sources": len(sc),
        "sources_cited": len(srcs),
        "source_concentration": round(top[0][1] / len(srcs), 3) if srcs else 0.0,
        "top_sources": [{"source": s, "count": c} for s, c in top],
        "threshold": threshold,
    }


def format_diversity(d: dict) -> str:
    pct = f"{d['near_dup_rate']:.0%}"
    lines = [f"🔬 *Finding diversity* — last {d['window']} raw findings",
             f"• near-duplicate rate: *{pct}* ({d['near_dup_count']}/{d['window']}, "
             f"containment≥{d['threshold']})",
             f"• distinct cited sources: *{d['distinct_sources']}* / {d['sources_cited']} citations"]
    if d.get("top_sources"):
        top = d["top_sources"][0]
        lines.append(f"• most-cited: {top['source']} ×{top['count']} "
                     f"({d['source_concentration']:.0%} of citations)")
    return "\n".join(lines)
