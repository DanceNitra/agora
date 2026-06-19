"""
Frontier harvester — the unbounded external feed for the chosen frontier.

The vault gap-pool is large but finite (the owner's own notes). To keep the OS from ever idling,
this pulls a constant stream of FRESH arXiv papers in the standing-frontier domains (Science of
Better Thinking + Future of Work & Society) and queues them to the Library's reading list. The
existing 'Read paper' flow then digests each into a structured note — so external research is
genuinely unlimited and anchored to the frontier, not a random firehose.
"""
from __future__ import annotations

import time

# Rotating queries that span the standing frontier. One topic per harvest so the feed stays varied
# and on-direction; the Library dedups against already-read/queued papers.
_FRONTIER_QUERIES = [
    "human-AI collaboration productivity",
    "large language model reasoning",
    "automation labor market employment effects",
    "collective intelligence wisdom of crowds",
    "metascience reproducibility research methods",
    "forecasting calibration human judgment",
    "creativity insight problem solving cognition",
    "causal inference machine learning",
    "complex systems emergence self-organization",
    "future of work generative AI economy",
    "knowledge management organizational learning",
    "decision making under uncertainty",
]


def _ids_from(papers: list[dict]) -> list[str]:
    from agora.execution.library import _arxiv_id
    out = []
    for p in papers:
        aid = _arxiv_id(p.get("url", ""))
        if aid:
            out.append(aid)
    return out


def harvest(per_topic: int = 5) -> dict:
    """Search one rotating frontier topic on arXiv and queue any NEW papers to the reading list."""
    from agora.execution.research_tool import arxiv_search
    from agora.execution.library import queue_reading
    rot = int(time.time() // 3600) % len(_FRONTIER_QUERIES)   # rotate hourly through the topics
    topic = _FRONTIER_QUERIES[rot]
    try:
        # newest-first so each harvest pulls FRESH submissions; relevance-sort re-found the same
        # already-read top hits every cycle (0 added) and let the reading list starve to ~2 papers,
        # which collapsed the swarm onto the flywheel's few questions (monoculture). 2026-06-19.
        papers = arxiv_search(topic, per_topic, sort="submittedDate")
    except Exception as e:
        return {"topic": topic, "error": str(e)[:120], "queued": 0}
    ids = _ids_from(papers)
    res = queue_reading(ids, source=f"frontier:{topic}") if ids else {"added": 0}
    return {"topic": topic, "found": len(ids), "queued": res.get("added", 0),
            "titles": [p.get("title", "")[:70] for p in papers[:3]]}
