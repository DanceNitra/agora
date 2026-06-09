"""
Hypothesis Induction — from verified finding clusters to testable conjectures.

Agora's own self-reflection flagged this gap: hundreds of findings, zero hypotheses. Isolated
facts never become science until something bridges them into a falsifiable cross-domain
conjecture. This module GATHERS the raw material (the established pattern: Agora gathers,
Claude creates): it embeds recent findings, finds a semantically coherent cluster that spans
multiple contributors, and hands it to Claude, whose synthesized 'Hypothesis: …' vault note
ships with a falsifier that the flywheel auto-registers — so the agents then go TEST it.
"""
from __future__ import annotations

import numpy as np


async def gather_hypothesis_inputs(db, limit: int = 120) -> dict:
    """Find ONE promising cross-domain cluster among recent findings: a seed with several
    related-but-not-duplicate neighbours (0.50 < cos < 0.88) from >=2 different agents."""
    from agora.execution.semantic_index import _embed_batch

    cur = await db.execute(
        "SELECT title, content, contributor_name FROM collective_knowledge "
        "WHERE knowledge_type='discovery' AND length(content) > 80 "
        "ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = await cur.fetchall()
    finds = [{"title": (r["title"] or "").strip()[:90],
              "content": (r["content"] or "").strip(),
              "by": (r["contributor_name"] or "?").strip()} for r in rows]
    finds = [f for f in finds if f["title"]]
    if len(finds) < 6:
        return {"cluster": [], "reason": "too few findings"}

    import asyncio
    texts = [f"{f['title']}. {f['content'][:300]}" for f in finds]
    embs = await asyncio.to_thread(_embed_batch, texts)
    if not embs or len(embs) != len(finds):
        return {"cluster": [], "reason": "embedding failed"}
    v = np.array(embs, dtype=np.float32)
    v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    sims = v @ v.T
    np.fill_diagonal(sims, -1.0)

    best_seed, best_nbrs = -1, []
    for i in range(len(finds)):
        nbrs = [j for j in np.argsort(-sims[i])[:8]
                if 0.50 < float(sims[i, j]) < 0.88][:5]
        # cross-domain proxy: the cluster must span at least two different contributors
        agents = {finds[i]["by"]} | {finds[j]["by"] for j in nbrs}
        if len(nbrs) >= 2 and len(agents) >= 2 and len(nbrs) > len(best_nbrs):
            best_seed, best_nbrs = i, nbrs
    if best_seed < 0:
        return {"cluster": [], "reason": "no coherent cross-agent cluster"}

    members = [best_seed] + list(best_nbrs)
    return {"theme": finds[best_seed]["title"],
            "cluster": [{"title": finds[m]["title"], "by": finds[m]["by"],
                         "content": finds[m]["content"][:400],
                         "sim": round(float(sims[best_seed, m]), 3) if m != best_seed else 1.0}
                        for m in members]}
