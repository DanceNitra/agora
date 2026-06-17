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

import re

import numpy as np

# Dungeon findings are recorded with QUEST-phrased titles ("Collaborate with King Aldric on X",
# "Pipeline: build on Mira's finding: Y") — internal agent names + quest scaffolding. A hypothesis
# themed on that chatter is junk. Clean the theme down to its substance before it seeds a hypothesis.
_AGENT_NAMES_RE = re.compile(
    r"\b(King Aldric|Cartographer Wren|Sage Mira|Shadow Kael|Dame Elara|High Priest Orin|"
    r"Sergeant Voss|Artificer Rooke|Aldric|Wren|Mira|Kael|Elara|Orin|Voss|Rooke)\b", re.I)
_QUEST_PREFIX_RE = re.compile(
    r"^\s*(collaborate with|building on|build on|pipeline:|upgrade|extend|explore|develop|create|"
    r"connect|bridge|challenge|deepen|investigate|test agora'?s? claim:?|"
    r"[A-Za-z]+'s (?:finding|work|result)s?:?)\s*[:,]?\s*", re.I)


def _clean_theme(title: str) -> str:
    """Strip quest scaffolding + internal agent names so the theme is the substance, not the chatter."""
    t = title or ""
    t = re.sub(r"\(with [^)]*\)", "", t)                       # "(with King Aldric)"
    t = re.sub(r"\s*<->\s*", " vs ", t)                        # normalize "A <-> B"
    for _ in range(4):                                          # peel stacked prefixes
        t2 = re.sub(r"^[^:]{1,40}\+[^:]{1,40}:\s*", "", t)     # "A + B:" collab prefix
        t2 = _QUEST_PREFIX_RE.sub("", t2)
        if t2 == t:
            break
        t = t2
    t = _AGENT_NAMES_RE.sub("", t)                              # any standalone names left
    t = re.sub(r"\b's\s+(finding|work|result)s?\b:?", "", t, flags=re.I)
    t = re.sub(r"^\s*(on|with|the|a|an)\b", "", t, flags=re.I)
    t = re.sub(r"[\s:,]+", " ", t).strip(" :+,-")
    return t.strip()


def _is_substantive_title(title: str) -> bool:
    """A title worth theming a hypothesis on: cleans to >=2 real words, not a dated report."""
    c = _clean_theme(title)
    if re.search(r"team run report|^\d|report \d", c, re.I):
        return False
    return len(re.findall(r"[A-Za-z]{3,}", c)) >= 2


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
        if not _is_substantive_title(finds[i]["title"]):
            continue                                  # the seed's title becomes the theme — it must be real
        nbrs = [j for j in np.argsort(-sims[i])[:8]
                if 0.50 < float(sims[i, j]) < 0.88][:5]
        # cross-domain proxy: the cluster must span >=2 NAMED contributors ('?' doesn't count)
        agents = {finds[i]["by"]} | {finds[j]["by"] for j in nbrs}
        agents = {a for a in agents if a and a != "?"}
        if len(nbrs) >= 2 and len(agents) >= 2 and len(nbrs) > len(best_nbrs):
            best_seed, best_nbrs = i, nbrs
    if best_seed < 0:
        return {"cluster": [], "reason": "no coherent cross-agent cluster with a substantive theme"}

    members = [best_seed] + list(best_nbrs)
    return {"theme": _clean_theme(finds[best_seed]["title"]),
            "cluster": [{"title": finds[m]["title"], "by": finds[m]["by"],
                         "content": finds[m]["content"][:400],
                         "sim": round(float(sims[best_seed, m]), 3) if m != best_seed else 1.0}
                        for m in members]}


async def synthesize_and_record_hypothesis(db, vault_path: str) -> dict:
    """The trigger that was never wired: bridge a coherent cross-domain finding cluster into ONE
    tested, RECORDED hypothesis (knowledge_type='hypothesis') whose falsifier is registered as an
    open question for the agents to test. This is what turns thousands of isolated findings into
    actual science. Returns the recorded hypothesis, or a skip reason if no cluster is ripe."""
    from agora.execution.scientist import hypothesize_and_test
    from agora.execution import flywheel

    cluster = await gather_hypothesis_inputs(db)
    theme = (cluster.get("theme") or "").strip()
    members = cluster.get("cluster") or []
    if not theme or not members:
        return {"status": "skip", "reason": cluster.get("reason", "no cluster")}

    h = await hypothesize_and_test(theme, vault_path)         # generate + TEST against real literature
    hyp = (h.get("hypothesis") or "").strip()
    if not hyp or hyp.startswith("[LLM Error") or "[LLM Error" in hyp:
        return {"status": "skip", "reason": "no hypothesis generated (LLM unavailable)", "theme": theme}

    contributors = sorted({m.get("by", "?") for m in members})
    conf = float(h.get("confidence") or 0.5)
    title = f"Hypothesis: {hyp[:88]}"
    content = (
        f"{hyp}\n\n"
        f"Verdict: {h.get('verdict', 'UNCERTAIN')} (confidence {conf:.0%}).\n"
        f"Evidence: {h.get('evidence', '')}\n"
        f"Falsifier: {h.get('falsifier', '')}\n"
        f"Source: {h.get('source', '')}\n"
        f"Bridged from {len(members)} findings across {len(contributors)} agents "
        f"({', '.join(contributors)}); theme: {theme[:80]}.")
    await db.execute(
        "INSERT INTO collective_knowledge (title, content, contributor_id, contributor_name, "
        "knowledge_type, confidence) VALUES (?, ?, ?, ?, 'hypothesis', ?)",
        (title, content[:500], "agora-scientist", "Hypothesis Engine", conf))
    await db.commit()

    fal = (h.get("falsifier") or "").strip()
    if fal:
        try:
            flywheel.register_question(fal, origin=f"hypothesis: {hyp[:60]}")
        except Exception:
            pass
    return {"status": "recorded", "hypothesis": hyp, "verdict": h.get("verdict"),
            "confidence": conf, "falsifier": fal, "evidence": h.get("evidence"),
            "theme": theme, "contributors": contributors, "formatted": h}
