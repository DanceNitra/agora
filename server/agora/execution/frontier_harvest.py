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
# RETARGETED 2026-07-20 to the owner-locked inspeximus frontier. Root cause of an all-night off-mission run:
# this list is the ONLY RENEWABLE source of research themes (the durable .frontier_directions.json is a
# fixed 11 that the experiment-dedup exhausts after one pass, and the `findings` bucket just re-seeds the
# stale top-8). So whatever THIS list says is what the swarm actually researches over a long night — and it
# was still the retired "Science of Better Thinking / Future of Work" frontier, which is why the Lab spent
# hours on dense-supervision, image-synthesis and 3D-Gaussian papers. Memory-domain queries make the
# renewable bucket on-mission. Test-bed domains (finance/health/physics) stay OUT per the Board.
# STRUCTURED arXiv syntax (quoted phrases + AND), not bare words: a bare multi-word phrase is OR-matched,
# so with sortBy=submittedDate the harvest returned the newest paper containing ANY word — the firehose.
# Each entry pins at least one exact phrase so "newest-first" stays ON-TOPIC.
_FRONTIER_QUERIES = [
    'abs:"agent memory" AND (abs:"language model" OR abs:LLM OR abs:agent)',
    'abs:"long-term memory" AND (abs:"language model" OR abs:LLM OR abs:dialogue)',
    'abs:"retrieval-augmented generation" AND (abs:memory OR abs:conflict OR abs:stale)',
    'abs:"knowledge editing" AND (abs:"language model" OR abs:LLM)',
    'abs:"memory poisoning" OR abs:"knowledge poisoning" OR (abs:"prompt injection" AND abs:memory)',
    'abs:"machine unlearning" AND (abs:verification OR abs:certified OR abs:deletion)',
    'abs:"temporal knowledge" AND (abs:validity OR abs:outdated OR abs:"knowledge graph")',
    'abs:"catastrophic forgetting" AND (abs:"continual learning" OR abs:retention)',
    'abs:"knowledge conflict" AND (abs:"language model" OR abs:retrieval)',
    'abs:provenance AND (abs:retrieval OR abs:attribution) AND abs:"language model"',
    'abs:"multi-agent" AND abs:memory AND (abs:shared OR abs:coordination)',
    'abs:"vector database" OR (abs:"dense retrieval" AND abs:evaluation)',
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
