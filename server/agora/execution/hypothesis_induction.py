"""
Hypothesis Induction — from verified finding clusters to testable conjectures.

Agora's own self-reflection flagged this gap: hundreds of findings, almost no hypotheses. Isolated
facts never become science until something bridges them into a falsifiable conjecture. This module
GATHERS the raw material (the established pattern: Agora gathers, Claude creates): it embeds findings,
finds semantically coherent cross-agent clusters, and hands each to Claude, whose synthesized
'Hypothesis: …' note ships with a falsifier the flywheel auto-registers — so the agents then go TEST it.

2026-06-19 FIX (owner: "8489 findings but only 3 hypotheses — the induction pipeline fails to bridge
findings into hypotheses"). Root cause: it only ever looked at the most-recent 120 findings (98.6% of the
corpus never mined) and produced ONE cluster per call. Now it samples ACROSS THE WHOLE CORPUS, extracts
the TOP-K non-overlapping cross-agent clusters per pass, and DEDUPES against already-recorded hypotheses —
turning the dormant 8489-finding corpus into a hypothesis engine.
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
    r"connect|bridge|challenge|deepen|investigate|measured:|ground a finding from:|"
    r"test agora'?s? claim:?|hypothesize on:|"
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


def _theme_words(s: str) -> set:
    return set(re.findall(r"[a-z]{4,}", (s or "").lower()))


def _theme_is_dup(theme: str, existing: list[set]) -> bool:
    """A cluster theme is a duplicate if its content words heavily overlap an existing hypothesis."""
    t = _theme_words(theme)
    if not t:
        return True
    for e in existing:
        if e and len(t & e) / len(t) > 0.6:                    # >60% word overlap = already hypothesized
            return True
    return False


async def _existing_hypothesis_wordsets(db) -> list[set]:
    cur = await db.execute(
        "SELECT title, content FROM collective_knowledge WHERE knowledge_type='hypothesis'")
    out = []
    for r in await cur.fetchall():
        words = _theme_words(r["title"] or "")
        m = re.search(r"theme:\s*([^.\n]+)", (r["content"] or ""), re.I)
        if m:
            words |= _theme_words(m.group(1))
        if words:
            out.append(words)
    return out


async def gather_hypothesis_clusters(db, sample: int = 1200, top_k: int = 6) -> dict:
    """Mine the WHOLE corpus (random sample, not just recent) for the TOP-K non-overlapping cross-agent
    clusters (seed + several 0.50<cos<0.88 neighbours from >=2 named contributors), deduped against
    already-recorded hypotheses. This is what converts thousands of dormant findings into hypotheses."""
    import asyncio
    from agora.execution.semantic_index import _embed_batch

    cur = await db.execute(
        "SELECT title, content, contributor_name FROM collective_knowledge "
        "WHERE knowledge_type='discovery' AND length(content) > 80 "
        "ORDER BY RANDOM() LIMIT ?", (sample,))           # RANDOM -> mine the whole corpus, not recent-120
    rows = await cur.fetchall()
    finds = [{"title": (r["title"] or "").strip()[:90],
              "content": (r["content"] or "").strip(),
              "by": (r["contributor_name"] or "?").strip()} for r in rows]
    finds = [f for f in finds if f["title"]]
    if len(finds) < 8:
        return {"clusters": [], "reason": "too few findings"}

    texts = [f"{f['title']}. {f['content'][:300]}" for f in finds]
    # CHUNK the embedding: the embedder rejects very large single requests, so batch it (this is what
    # lets us mine the whole corpus instead of just the recent 120).
    embs: list = []
    CHUNK = 96
    for c in range(0, len(texts), CHUNK):
        part = await asyncio.to_thread(_embed_batch, texts[c:c + CHUNK])
        if not part or len(part) != len(texts[c:c + CHUNK]):
            return {"clusters": [], "reason": "embedding failed"}
        embs.extend(part)
    if len(embs) != len(finds):
        return {"clusters": [], "reason": "embedding failed"}
    v = np.array(embs, dtype=np.float32)
    v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    sims = v @ v.T
    np.fill_diagonal(sims, -1.0)

    existing = await _existing_hypothesis_wordsets(db)
    used: set[int] = set()
    clusters = []
    for _ in range(top_k * 3):                              # extra rounds: dup/used clusters are skipped
        if len(clusters) >= top_k:
            break
        best_seed, best_nbrs = -1, []
        for i in range(len(finds)):
            if i in used or not _is_substantive_title(finds[i]["title"]):
                continue
            nbrs = [j for j in np.argsort(-sims[i])[:10]
                    if j not in used and 0.50 < float(sims[i, j]) < 0.88][:5]
            agents = {finds[i]["by"]} | {finds[j]["by"] for j in nbrs}
            agents = {a for a in agents if a and a != "?"}
            if len(nbrs) >= 2 and len(agents) >= 2 and len(nbrs) > len(best_nbrs):
                best_seed, best_nbrs = i, nbrs
        if best_seed < 0:
            break
        members = [best_seed] + list(best_nbrs)
        used.update(members)                               # never reuse these findings in another cluster
        theme = _clean_theme(finds[best_seed]["title"])
        if not theme or _theme_is_dup(theme, existing):
            continue                                       # already hypothesized -> skip, mine the next
        existing.append(_theme_words(theme))
        clusters.append({"theme": theme,
                         "cluster": [{"title": finds[m]["title"], "by": finds[m]["by"],
                                      "content": finds[m]["content"][:400],
                                      "sim": round(float(sims[best_seed, m]), 3) if m != best_seed else 1.0}
                                     for m in members]})
    if not clusters:
        return {"clusters": [], "reason": "no fresh cross-agent cluster (all dup/saturated)"}
    return {"clusters": clusters}


async def gather_hypothesis_inputs(db, limit: int = 120) -> dict:
    """Backward-compatible single-cluster view (used by the /brain/hypothesis-inputs endpoint)."""
    got = await gather_hypothesis_clusters(db, top_k=1)
    cls = got.get("clusters") or []
    return cls[0] if cls else {"cluster": [], "reason": got.get("reason", "no cluster")}


async def _record_one(db, theme: str, members: list, vault_path: str) -> dict | None:
    from agora.execution.scientist import hypothesize_and_test
    from agora.execution import flywheel
    h = await hypothesize_and_test(theme, vault_path)         # generate + TEST against real literature
    hyp = (h.get("hypothesis") or "").strip()
    # severe-test rule: a hypothesis with no real verdict (e.g. no Lab template fit / no measured number
    # under AGORA_SCIENTIST_LAB) is NOT a claim -> do not record it.
    if not hyp or "[LLM Error" in hyp or str(h.get("verdict")) == "NONE":
        return None
    contributors = sorted({m.get("by", "?") for m in members})
    conf = float(h.get("confidence") or 0.5)
    title = f"Hypothesis: {hyp[:88]}"
    content = (
        f"{hyp}\n\nVerdict: {h.get('verdict', 'UNCERTAIN')} (confidence {conf:.0%}).\n"
        f"Evidence: {h.get('evidence', '')}\nFalsifier: {h.get('falsifier', '')}\n"
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
    return {"status": "recorded", "hypothesis": hyp, "verdict": h.get("verdict"), "confidence": conf,
            "falsifier": fal, "evidence": h.get("evidence"), "theme": theme,
            "contributors": contributors, "formatted": h}


async def synthesize_and_record_hypothesis(db, vault_path: str, max_new: int = 3) -> dict:
    """Bridge the TOP cross-domain finding clusters (mined from the WHOLE corpus) into up to `max_new`
    tested, RECORDED hypotheses per pass, each with its falsifier registered as an open question.
    Returns the first recorded (old shape, for the loop's Telegram) + recorded_count + all."""
    got = await gather_hypothesis_clusters(db, top_k=max(max_new, 3))
    clusters = got.get("clusters") or []
    # Wren forced-collision: lead the pass with the vault's WIDEST structural HOLE so Orin attempts a real
    # cross-domain bridge (Burt brokerage - value is in bridging holes, not cluster density), not only
    # same-domain finding clusters. Marked charted on use so the next pass advances to the next hole.
    try:
        import asyncio as _aio
        from agora.execution.cartography import find_hole
        _hole = await _aio.to_thread(find_hole, vault_path)
        if _hole and _hole.get("a") and _hole.get("b"):
            _ht = f"a testable mechanism that bridges {_hole['a']} and {_hole['b']}"
            if not _theme_is_dup(_ht, [_theme_words(c.get("theme", "")) for c in clusters]):
                clusters.insert(0, {"theme": _ht, "cluster": [], "_hole": _hole})
    except Exception:
        pass
    if not clusters:
        return {"status": "skip", "reason": got.get("reason", "no cluster")}
    recorded = []
    for cl in clusters[:max_new]:
        rec = await _record_one(db, cl.get("theme", ""), cl.get("cluster", []), vault_path)
        if rec:
            recorded.append(rec)
            if cl.get("_hole"):                              # Wren: mark the hole charted so it advances
                try:
                    from agora.execution.cartography import record_charted
                    record_charted(cl["_hole"]["a"], cl["_hole"]["b"], cl["_hole"].get("bridges", 0),
                                   note="forced-collision hypothesis", outcome="hypothesized")
                except Exception:
                    pass
    if not recorded:
        return {"status": "skip", "reason": "no hypothesis generated (LLM unavailable)"}
    return {**recorded[0], "recorded_count": len(recorded), "all": recorded}
