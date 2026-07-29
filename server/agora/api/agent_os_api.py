"""Agent OS API — soul, brain, body, abilities, skills, help requests."""
import re
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException

from agora.api.dungeon import DUNGEON_AGENT_IDS

# UUID → name reverse lookup
UUID_TO_NAME = {v: k for k, v in DUNGEON_AGENT_IDS.items()}

router = APIRouter(prefix="/api/v1/agent-os", tags=["agent-os"])


def get_os(request: Request):
    return request.app.state.agent_os


@router.get("/{npc_name}/soul")
async def get_agent_soul(npc_name: str, request: Request):
    """Get soul status for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT * FROM agent_soul WHERE npc_id=?", (npc_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"NPC {npc_name} not found")
    return dict(row)


@router.get("/{npc_name}/brain")
async def get_agent_brain(npc_name: str, request: Request):
    """Get brain status for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT * FROM agent_brain WHERE npc_id=?", (npc_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"NPC {npc_name} not found")
    return dict(row)


@router.get("/{npc_name}/body")
async def get_agent_body(npc_name: str, request: Request):
    """Get body status for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT * FROM agent_body WHERE npc_id=?", (npc_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"NPC {npc_name} not found")
    return dict(row)


@router.get("/{npc_name}/abilities")
async def get_agent_abilities(npc_name: str, request: Request):
    """Get abilities for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT ability_name, description, power_level, is_passive FROM agent_abilities "
        "WHERE npc_id=? ORDER BY power_level DESC",
        (npc_id,),
    )
    abilities = [dict(r) for r in await cursor.fetchall()]
    return {"abilities": abilities, "total": len(abilities)}


@router.get("/{npc_name}/skills")
async def get_agent_skills(npc_name: str, request: Request):
    """Get skills for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT skill_name, level, xp, xp_to_next, last_used_at FROM agent_skills "
        "WHERE npc_id=? ORDER BY level DESC",
        (npc_id,),
    )
    skills = [dict(r) for r in await cursor.fetchall()]
    return {"skills": skills, "total": len(skills)}


@router.get("/{npc_name}/help-requests")
async def get_agent_help_requests(npc_name: str, request: Request, status: str | None = None):
    """Get help requests for an NPC (as requester or helper)."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    where_extra = ""
    params = [npc_id, npc_id]
    if status:
        where_extra = " AND hr.status=?"
        params.append(status)

    cursor = await db.execute(
        f"SELECT hr.*, r.npc_name as requester_name, h.npc_name as helper_name "
        f"FROM agent_help_requests hr "
        f"JOIN dungeon_npcs r ON r.npc_id = hr.requester_id "
        f"JOIN dungeon_npcs h ON h.npc_id = hr.helper_id "
        f"WHERE (hr.requester_id=? OR hr.helper_id=?){where_extra} "
        f"ORDER BY hr.created_at DESC LIMIT 20",
        params,
    )
    requests = [dict(r) for r in await cursor.fetchall()]
    return {"help_requests": requests, "total": len(requests)}


@router.get("/help-matrix")
async def get_help_matrix():
    """Get the help-seeking matrix (who helps with what)."""
    from agora.agent_os.agent_os import HELP_MATRIX
    return {"matrix": HELP_MATRIX}


# ═══════════════════════════════════════════════════════════════
# Agentic OS v2 (Phase 2.0) — Brain Ecosystem observability
# Per-agent paths are 2-segment (safe from the /{npc_name} catch-all);
# global paths are namespaced under /brain/ to avoid that collision.
# ═══════════════════════════════════════════════════════════════

@router.get("/{npc_name}/memories")
async def get_memories(npc_name: str, request: Request, memory_type: str = None,
                       limit: int = 20):
    """List an agent's memories (optionally filter by type)."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db
    q = "SELECT memory_type, content, importance, emotional_tag, source, " \
        "related_npc_id, decay_factor, created_at FROM agent_memories WHERE npc_id=?"
    params = [npc_id]
    if memory_type:
        q += " AND memory_type=?"
        params.append(memory_type)
    q += " ORDER BY importance DESC, created_at DESC LIMIT ?"
    params.append(limit)
    cursor = await db.execute(q, params)
    return {"npc": npc_name, "memories": [dict(r) for r in await cursor.fetchall()]}


@router.get("/{npc_name}/memories/recall")
async def recall_memories(npc_name: str, request: Request, q: str = "", limit: int = 5):
    """Recall the most relevant memories for a query (importance+keyword+recency)."""
    from agora.agent_os.memory_agent import MemoryAgent
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    mem = MemoryAgent(request.app.state.db, npc_id)
    return {"npc": npc_name, "query": q, "memories": await mem.recall(q, limit=limit)}


@router.get("/{npc_name}/thoughts")
async def get_thoughts(npc_name: str, request: Request, limit: int = 20):
    """Get an agent's thought journal (reasoning log)."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    cursor = await request.app.state.db.execute(
        "SELECT thought_type, content, context, importance, created_at "
        "FROM agent_thoughts WHERE npc_id=? ORDER BY created_at DESC LIMIT ?",
        (npc_id, limit))
    return {"npc": npc_name, "thoughts": [dict(r) for r in await cursor.fetchall()]}


@router.get("/brain/collective")
async def query_collective(request: Request, q: str = "", limit: int = 20):
    """Query the collective knowledge pool (the dungeon vault)."""
    db = request.app.state.db
    if q:
        os_engine = get_os(request)
        return {"query": q, "knowledge": await os_engine._query_collective(q, limit=limit)}
    cursor = await db.execute(
        "SELECT title, content, contributor_name, knowledge_type, confidence, "
        "verification_count, created_at FROM collective_knowledge "
        "ORDER BY created_at DESC LIMIT ?", (limit,))
    return {"knowledge": [dict(r) for r in await cursor.fetchall()]}


# Finding Novelty & Significance Gate (owner-requested build #2): two write-time checks that
# complement the existing structural filter + vault-novelty dedup. They keep NON-FINDINGS and
# TRIVIAL textbook facts out of the raw discovery pool (which feeds hypotheses/ideation/seminar),
# not just out of the vault at promotion time.
# (a) refusal / no-support: the same negative-claim family already filtered at PROMOTION, applied
#     here at the source so "No paper directly supports ..." never enters the pool.
_REFUSAL_AT_SOURCE = re.compile(
    r"\bno (?:paper|papers|source|sources|study|studies|abstract|abstracts|evidence)\b[^.\n]{0,40}"
    r"\b(?:support|provide|relate|address|mention|match|fit|confirm)\w*"
    r"|\bdoes not (?:support|fit|apply)|\b(?:are|is) unrelated|\bcould not find|\bunable to (?:find|locate)"
    r"|\bno (?:relevant|direct(?:ly)?)\b[^.\n]{0,30}\b(?:paper|source|support|evidence|match)\w*"
    r"|\bthe closest (?:are|is)\b|\bnot supported by|\btotal mismatch|\bas an ai\b"
    r"|\bi (?:cannot|can't|could not|am unable)\b", re.I)
# (b) low significance: a SHORT, copula-led, bare assertion that carries no quantitative or
#     comparative claim (e.g. "linear regression has a Chow test"). Deliberately conservative —
#     it fires only when all three hold (short + definitional shape + no measured/relational signal),
#     so substantive short findings (with a number, %, effect or comparison) always pass.
_SIG_MARK = re.compile(
    r"\d|%|\b(increas|decreas|reduc|improv|impair|enhanc|disrupt|lower|higher|faster|slower|"
    r"more|less|than|correlat|caus|effect|predict|mediat|regulat|drive|outperform|versus|vs|"
    r"compared|ratio|signific|fold|percent|times)\w*", re.I)
_TRIVIAL_COPULA = re.compile(
    r"^[^.\n]{0,55}\b(is|are|was|were|has|have|uses?|consists? of|refers? to|means?)\b", re.I)


def _garbage_finding(title: str, content: str):
    """Conservative quality filter — reject only CLEARLY broken findings (self-upgrade: completion
    filter + novelty/significance gate). Returns a reason string if garbage, else None."""
    t, c = (title or "").strip(), (content or "").strip()
    cl, tl = c.lower(), t.lower()
    _PREFIXES = ("hypothesize on:", "pursue direction:", "develop the gap:", "deepen:",
                 "connect:", "frontier:", "hypothesis:", "pipeline:")
    # Reject ANY 2+ stacked prefixes in the title (e.g. 'Hypothesize on: Pipeline: X'), not just a
    # doubled single one — the old check missed mixed nesting. Also reject a doubled prefix in the body.
    if sum(tl.count(p) for p in _PREFIXES) >= 2 or any(cl.count(p) >= 2 for p in _PREFIXES):
        return "nested quest prefix"
    body = cl.split("source:")[0].strip()
    if len(body) < 50:
        return "too short"
    if body.strip(". ") == tl.strip(". "):               # content merely restates the title
        return "content restates title (no real finding)"
    if _REFUSAL_AT_SOURCE.search(c):
        return "refusal / non-finding (no source supports the claim)"
    if len(body) < 80 and _TRIVIAL_COPULA.match(body) and not _SIG_MARK.search(body):
        return "low significance (bare definitional fact, no measured/comparative claim)"
    return None


@router.post("/brain/collective")
async def add_collective(request: Request):
    """Add an entry to the collective knowledge pool."""
    body = await request.json()
    for f in ("npc", "title", "content"):
        if not body.get(f):
            raise HTTPException(400, f"Missing field: {f}")
    # Completion filter — keep clearly-broken findings (nested prefixes, echoes, stubs) out.
    if body.get("knowledge_type", "observation") == "discovery":
        g = _garbage_finding(body["title"], body["content"])
        if g:
            if g.startswith("refusal"):
                _PROMOTE_STATS["src_refusal"] = _PROMOTE_STATS.get("src_refusal", 0) + 1
            elif g.startswith("low significance"):
                _PROMOTE_STATS["src_trivial"] = _PROMOTE_STATS.get("src_trivial", 0) + 1
            return {"status": "rejected", "reason": g}
        # LAB-FIRST gate (2026-06-19, flag AGORA_REQUIRE_LAB): a 'discovery' must be backed by a REAL
        # Lab experiment (a reproducible measured result), not a paraphrase. Require a lab_id that
        # exists in the Lab/Methods ledger with ok==True. Closes the paraphrase paths (collab/pipeline/
        # literature) at the write chokepoint. Reversible: unset the flag.
        import os as _os
        if _os.environ.get("AGORA_REQUIRE_LAB", "0") == "1":
            import re as _re, json as _json
            from pathlib import Path as _Pth
            _mlab = _re.search(r"[Ll]ab[ _]?(?:id[ =:]*)?([0-9a-f]{6})\b", body["content"] or "")
            _ok_lab = False
            if _mlab:
                _lid = _mlab.group(1)
                for _ledger in (".lab.json", ".methods.json"):
                    try:
                        _items = _json.load(open(_Pth(__file__).resolve().parents[2] / _ledger, encoding="utf-8"))
                        if any((e.get("id") == _lid or e.get("lab_id") == _lid) and e.get("ok") for e in _items):
                            _ok_lab = True
                            break
                    except Exception:
                        pass
            if not _ok_lab:
                _PROMOTE_STATS["src_no_lab"] = _PROMOTE_STATS.get("src_no_lab", 0) + 1
                return {"status": "rejected", "reason": "LAB-FIRST: discovery has no reproducible Lab result (lab_id)"}
        # NOVELTY GATE AT THE SOURCE: if this finding lexically near-duplicates a note the vault
        # already has, don't store it — it would only clog the promotion funnel and be deduped later
        # anyway (~71% of findings were such restatements). Uses the SAME calibrated containment as
        # write-time dedup; measured: semantic similarity does NOT separate dup vs novel at finding
        # granularity (both ~0.7), so the lexical containment is the right tool here.
        _w = getattr(request.app.state, "vault_writer", None)
        if _w is not None and len(body["content"]) >= 160:
            try:
                import asyncio as _a
                if await _a.to_thread(_w._find_duplicate, body["title"], body["content"]):
                    _PROMOTE_STATS["src_deduped"] = _PROMOTE_STATS.get("src_deduped", 0) + 1
                    return {"status": "rejected", "reason": "vault already covers this (source dedup)"}
            except Exception:
                pass
        # INTRA-STREAM novelty (2026-06-27): the vault dedup above only catches findings the VAULT
        # already has, and only at >=160 chars. The measured 90% near-duplicate churn was findings
        # restating EACH OTHER (short, ungrounded paraphrases) — never deduped, so they dominated the
        # discovery stream and buried the genuinely-distinct ones. Reject a discovery that near-
        # duplicates a RECENT discovery (containment >= 0.6, the same metric the Pulse reports), at any
        # length. This is NOT a throttle: distinct findings still flow; only redundant restatements are
        # dropped at the source so the funnel sees signal, not noise.
        try:
            from agora.execution.finding_diversity import _tokens, _containment, _claim
            _newtok = _tokens((body["title"] or "") + " " + _claim(body["content"] or ""))
            if len(_newtok) >= 4:
                _cur = await request.app.state.db.execute(
                    "SELECT title, content FROM collective_knowledge WHERE knowledge_type='discovery' "
                    "ORDER BY created_at DESC LIMIT 80")
                for _r in await _cur.fetchall():
                    _ex = _tokens((_r["title"] or "") + " " + _claim(_r["content"] or ""))
                    if _ex and _containment(_newtok, _ex) >= 0.6:
                        _PROMOTE_STATS["src_stream_dup"] = _PROMOTE_STATS.get("src_stream_dup", 0) + 1
                        return {"status": "rejected", "reason": "near-duplicate of a recent finding (stream dedup)"}
        except Exception:
            pass
    # A SECOND REFUSAL FAMILY, and the two are COMPLEMENTARY — do not delete either believing the
    # other covers it. `_garbage_finding`'s `_REFUSAL_AT_SOURCE` above is the older one and it works;
    # it missed 20 of 400 recent discoveries by ONE LETTER. Its alternation has
    # `does not (support|fit|apply)` — singular — and the production text reads "the provided sources
    # DO not support the claim about deltaG(q=0.6)...". The rest of that pattern keys on
    # "no paper/source/study...", which this sentence never says: it NAMES the sources it was given
    # and then denies them. So it was stored as knowledge, rose to the top of the collective pool,
    # re-seeded itself as a quest, and was re-researched for days.
    # Measured both ways: this gate rejects all five envelope/plural variants and ACCEPTS
    # "No source supports the claim", which the older pattern catches. Neither is a superset.
    # It also runs server-side on purpose — the dungeon checks before it POSTs, but this endpoint
    # takes writes from every organ, and a guard on the client is a guard the next client forgets.
    from agora.execution.non_finding import is_non_finding
    if is_non_finding(body.get("title"), body.get("content")):
        _PROMOTE_STATS["src_refusal"] = _PROMOTE_STATS.get("src_refusal", 0) + 1
        return {"status": "rejected", "reason": "not a finding — a refusal / no-fit statement"}
    npc_id = DUNGEON_AGENT_IDS.get(body["npc"]) or body["npc"]
    os_engine = get_os(request)
    await os_engine._contribute_to_collective(
        npc_id, body["title"], body["content"],
        body.get("knowledge_type", "observation"))
    return {"status": "added", "title": body["title"]}


@router.post("/brain/vault-note")
async def write_vault_note(request: Request):
    """Persist an agent's note into the vault — but ONLY if it passes the quality gate.
    Shallow / ungrounded / generic notes are rejected and never written."""
    from agora.execution.quality_gate import assess_quality
    body = await request.json()
    title = (body.get("title") or "").strip()
    content = (body.get("content") or "").strip()
    if not title or not content:
        raise HTTPException(400, "Missing title or content")
    # QUALITY GATE — keep shallow notes out of the vault (skippable only with gate=false)
    if body.get("gate", True):
        q = await assess_quality(title, content, int(body.get("min_score", 6)))
        if not q["pass"]:
            return {"status": "rejected", "score": q["score"], "reason": q["reason"]}
    else:
        q = {"score": None}
    writer = getattr(request.app.state, "vault_writer", None)
    if not writer:
        raise HTTPException(503, "vault writer not available")
    path = await writer.write_note(
        title=title, content=content,
        tags=body.get("tags") or ["agora", "consolidation"],
        agent_name=body.get("agent") or "Sage Mira")
    # Compounding Flywheel: when an INSIGHT or HYPOTHESIS lands, register its falsifier as an open
    # research question so the agents go test the weak point — outputs become the next inputs.
    if {"insight", "hypothesis"} & set(body.get("tags") or []):
        try:
            from agora.execution.flywheel import extract_falsifier, register_question
            fals = extract_falsifier(content)
            if fals:
                register_question(fals, origin=title[:90])
        except Exception:
            pass
    return {"status": "written", "path": path, "score": q["score"]}


_PROMOTED: set = set()   # finding titles already promoted to the vault (avoid duplicates)
_PROMOTE_STATS = {"promoted": 0, "checked": 0}   # cumulative funnel stats for the research-ROI metric


import re as _grade_re
_G_MEASURED = _grade_re.compile(
    r"MEASURED:|VERDICT:|\blab[:_ ]?[0-9a-f]{6}\b|\bn\s*=\s*\d|\d+(?:\.\d+)?\s*%|\bCI\b|p\s*[<=]\s*0?\.\d", _grade_re.I)
_G_CITE = _grade_re.compile(r"10\.\d{4,9}/|arxiv[:\s]*\d{4}\.\d|\([A-Z][a-zA-Z]+(?: et al\.?)?,? \d{4}\)", _grade_re.I)
_G_FALS = _grade_re.compile(r"falsif|would (?:refute|disprove|be wrong)|refuted if", _grade_re.I)


def _evidence_grade(content: str):
    """Sage Mira's GRADE: rate the strength of the underlying EVIDENCE (not the claim's importance), so the
    vault is honest about confidence per note. HIGH = a measured result + (citation or falsifier);
    MODERATE = one of those; LOW = grounded but no measured result or external citation."""
    c = content or ""
    meas, cite, fals = bool(_G_MEASURED.search(c)), bool(_G_CITE.search(c)), bool(_G_FALS.search(c))
    if meas and (cite or fals):
        return "HIGH", "measured result with a citation/falsifier"
    if meas or cite:
        return "MODERATE", "a measured result or a real external citation"
    return "LOW", "grounded but no measured result or external citation"


_CRED_WEAK = _grade_re.compile(
    r"\b(?:a|one|a single|a recent|a pilot|a preliminary|an exploratory)\s+stud(?:y|ies)\b|\bpilot\b|"
    r"\bpreliminary\b|\bexploratory\b|\bsmall sample\b|\bunderpowered\b|\bcase (?:study|report)\b|\banecdot",
    _grade_re.I)
_CRED_SMALLN = _grade_re.compile(r"\bn\s*=\s*([1-9]\d?)\b", _grade_re.I)
_CRED_STRONG = _grade_re.compile(
    r"meta-?analysis|systematic review|replicat|pre-?regist|large (?:sample|cohort|n)|\bRCT\b|"
    r"randomi[sz]ed|MEASURED:|VERDICT:", _grade_re.I)


def _credibility_audit(content: str):
    """Shadow Kael's effect-size/credibility audit: a finding that leans on a single underpowered /
    preliminary study (and is NOT Lab-measured, meta-analytic, replicated, or pre-registered) is
    low-credibility — replicate before relying. Returns (is_low, caveat)."""
    c = content or ""
    if _CRED_STRONG.search(c):
        return False, ""
    if _CRED_WEAK.search(c):
        return True, "rests on a single / preliminary study - replicate before relying"
    m = _CRED_SMALLN.search(c)
    if m and int(m.group(1)) < 50:
        return True, f"small sample (n={m.group(1)}) - underpowered, replicate before relying"
    return False, ""


def _adversarial_review(title: str, content: str) -> tuple:
    """RESEARCH-QUALITY #4 (owner 2026-06-27): a STRONG-model red-team gate before a finding is
    promoted into the curated vault. Rejects the failure modes that made past notes thin —
    textbook/known prior-art, weak-baseline artifacts, vague/over-general/unfalsifiable claims, and
    cited-source mismatches. Uses the reasoning tier (glm-5.2). FAIL-OPEN: on empty/parse-error the
    finding is NOT blocked (return True) so a model outage can never freeze the research->vault funnel.
    Returns (survives: bool, reason: str)."""
    try:
        from agora.execution.llm_client import call_llm
        import json as _j, re as _re2
        sysp = (
            "You are a brutal senior peer reviewer guarding a curated research vault. A finding is up "
            "for promotion. REJECT if ANY holds: (a) it restates a textbook / well-known result (prior "
            "art exists); (b) the 'result' is likely a weak-baseline artifact or measurement quirk, not "
            "a real effect; (c) it is vague, over-general, or not falsifiable; (d) the cited source does "
            "not actually support the claim. ACCEPT only a specific, grounded, falsifiable, non-obvious "
            'finding. Reply ONLY JSON: {"survive": true|false, "reason": "<=15 words"}')
        out = call_llm(sysp, f"TITLE: {title}\n\nFINDING:\n{content[:1200]}",
                       tier="medium", max_tokens=120, temperature=0.1) or ""
        m = _re2.search(r"\{.*\}", out, _re2.S)
        if not m:
            return (True, "adv: unparseable -> not blocked")
        d = _j.loads(m.group(0))
        return (bool(d.get("survive", True)), str(d.get("reason", ""))[:80])
    except Exception as e:
        return (True, f"adv: error -> not blocked ({type(e).__name__})")


@router.post("/brain/promote-findings")
async def promote_findings(request: Request, n: int = 16):
    """Promote the best recent findings into the vault through the (reliable) quality gate — the
    research→vault path that actually flows. Verification incorporates ~0 (too strict), so without
    this, grounded findings pile up only in the brain and never reach the Obsidian second-brain.
    Throughput note: the LLM judge is now LOCAL (free), so the old scarce-budget rationing (last-40
    window, promote 3) starved a ~1000-finding backlog — most never got vetted. We widen the window
    and promote more per run so genuine gems land instead of rotting (quality gate + dedup unchanged)."""
    from agora.execution.quality_gate import assess_quality
    db = request.app.state.db
    writer = getattr(request.app.state, "vault_writer", None)
    if not writer:
        return {"status": "no-writer", "promoted": 0}
    cur = await db.execute(
        "SELECT title, content FROM collective_knowledge WHERE knowledge_type='discovery' "
        "ORDER BY created_at DESC LIMIT 150")
    rows = await cur.fetchall()
    import re as _re
    # A vault note must carry a real finding — not a quest PLAN, not a NEGATIVE admission, not a
    # placeholder. The audit (2026-06-14) found ~48% of curated notes were thin: intent stubs
    # ("Collaborate with X", "Explore Y"), negatives ("neither cited paper supports the link"), and
    # citation-mismatches that the Source:/year gate alone let through. Reject them before the judge.
    _INTENT_PROMO = _re.compile(
        r"^\s*(extend\s+\w+|(colla?borat|cooperat)(e|ion)\s+with\b|co-?develop\b|review and validate\b|connect\s+\w+"
        r"|build on\s+\w+'?s?\s+(finding|result|work)|explore\s+\w+|investigate\s+\w+|develop\s+(a|an|the)\b"
        r"|jointly\s+\w+|pipeline:\s*(build on|colla?borat|explore|connect))", _re.I)
    _NEGATIVE_PROMO = _re.compile(
        r"(neither|none|no)\s+(of\s+the\s+)?(cited\s+|provided\s+|real\s+)?(paper|source|abstract|study|studie)s?"
        r"[^.\n]{0,40}\b(support|provide|relate|address|mention|match)|does not support|are unrelated|is unrelated"
        r"|no papers? (were|was) provided|could not find any|unable to (find|locate)|total mismatch|not supported by",
        _re.I)
    # 1) gather the window's eligible candidates (cheap filters; don't consume _PROMOTED yet)
    from agora.execution.finding_diversity import _tokens, _containment  # novelty gate (reuse churn detector)
    cands = []
    _acc_toks = []  # token sets of accepted candidates — used to drop near-duplicates within this run
    for r in rows:
        title = (r["title"] or "").strip()
        content = (r["content"] or "").strip()
        tl = title.lower()
        # GROUNDED = a real citation ("Source:") OR a Lab-measured result (MEASURED:/VERDICT:) — the
        # latter is grounded by its own measurement, not a paper, and was previously rejected outright
        # (the bug that blocked ALL Lab findings from the vault: 0 notes/day). The LLM judge + novelty
        # gate downstream still ration quality.
        _cu = content.upper()
        _grounded = ("Source:" in content) or ("MEASURED:" in _cu and "VERDICT:" in _cu)
        if (title in _PROMOTED or len(content) < 160 or not _grounded
                or tl.count("hypothesize on:") >= 2 or tl.count("pursue direction:") >= 2):
            continue
        if _INTENT_PROMO.match(title) or _INTENT_PROMO.match(content) or _NEGATIVE_PROMO.search(content):
            continue                                       # a plan / negative / placeholder, not a finding
        _body, _, _src = content.partition("Source:")     # citation-year-mismatch rigor
        _by = _re.search(r"\b(?:19|20)\d{2}\b", _body)
        _sy = _re.search(r"\b(?:19|20)\d{2}\b", _src)
        if _by and _sy and _by.group(0) != _sy.group(0):
            continue
        _ct = _tokens(title + " " + content[:600])        # NOVELTY GATE (Fix 1): ration the write-budget to
        if any(_containment(_ct, pt) >= 0.6 for pt in _acc_toks):  # NEW findings — drop near-duplicates of ones
            continue                                       # already accepted this run (containment >= 0.6)
        _acc_toks.append(_ct)
        cands.append((title, content))
        if len(cands) >= 40:                              # wider funnel — more gems reach the vault
            break

    # 2) CRITICAL-WINDOW LOAD BALANCER (Agora's own insight, applied to itself): the consolidation
    #    budget (n) is limited, so ration it to the highest FUTURE-RETRIEVAL-VALUE findings in the
    #    window — connectedness to the existing vault (semantic fit) + citation specificity — rather
    #    than the first-seen. Promote the best, not the soonest.
    si = None
    try:
        from agora.execution.semantic_index import SemanticIndex
        global _SEM_INDEX
        if _SEM_INDEX is None or not _SEM_INDEX.ready:
            _SEM_INDEX = SemanticIndex()
        si = _SEM_INDEX if _SEM_INDEX.ready else None
    except Exception:
        si = None

    def _score_all():
        import numpy as np
        conns = [0.5] * len(cands)
        if si:
            try:
                from agora.execution.semantic_index import _embed_batch
                cvecs = _embed_batch([(t + " " + c)[:300] for t, c in cands])  # ONE batched embed call
                V = si.vecs
                for i, cv in enumerate(cvecs):
                    if not cv:
                        continue
                    v = np.array(cv, dtype=np.float32)
                    v /= (np.linalg.norm(v) + 1e-9)
                    sims = V @ v                                  # cosine sim to every vault note
                    conns[i] = float(np.sort(sims)[-3:].mean())   # connectedness = mean top-3
            except Exception:
                pass
        scored = []
        for i, (t, c) in enumerate(cands):
            spec = 0.3 if _re.search(r"\([A-Z][a-zA-Z]+(?: et al\.?)?,? \d{4}\)", c) else 0.0
            scored.append((conns[i] + spec, t, c))
        return sorted(scored, key=lambda x: -x[0])
    import asyncio
    ranked = await asyncio.to_thread(_score_all)

    # 3) promote the top-valued candidates that pass the quality gate
    promoted, checked, deduped = [], 0, 0
    import asyncio as _asyncio
    for _v, title, content in ranked:
        if len(promoted) >= n:
            break
        checked += 1
        # ONE-SHOT-BURN FIX (2026-07-02): _PROMOTED used to be set BEFORE the outcome, so a single
        # TRANSIENT failure (LLM flake in the judge/red-team, a write exception swallowed below)
        # permanently discarded a genuine finding — the funnel silently starved (0 notes/day while
        # candidates verified clean offline). Burn the title only on a DEFINITIVE outcome (dedup,
        # judge/red-team rejection, successful write); on a transient write error leave it un-burned
        # so the next 20-min run retries it.
        # DEDUP-AWARE: don't burn the slot on a near-duplicate of an existing vault note — the
        # write would be silently skipped anyway, leaving "promoted" inflated and 0 notes landed.
        # Skip it and try the next-best NOVEL candidate (reuses the writer's own dedup metric).
        try:
            if await _asyncio.to_thread(writer._find_duplicate, title, content):
                _PROMOTED.add(title)                  # definitive: vault already covers it
                deduped += 1
                continue
        except Exception:
            pass
        q = await assess_quality(title, content)
        if not q["pass"]:
            _PROMOTED.add(title)                      # definitive: judged not vault-worthy
            continue
        # RESEARCH-QUALITY #4: strong-model adversarial red-team before the vault (prior-art /
        # weak-baseline / vagueness / source-mismatch). Only genuinely novel, grounded, falsifiable
        # findings survive; fail-open so a model outage can't freeze the funnel.
        _adv_ok, _adv_why = await _asyncio.to_thread(_adversarial_review, title, content)
        if not _adv_ok:
            _PROMOTED.add(title)                      # definitive: red-team rejection (prior art etc.)
            _PROMOTE_STATS["src_adv_reject"] = _PROMOTE_STATS.get("src_adv_reject", 0) + 1
            continue
        try:
            _g, _gwhy = _evidence_grade(content)
            _lowcred, _caveat = _credibility_audit(content)   # Shadow Kael: cap underpowered single-studies
            if _lowcred and _g == "HIGH":
                _g, _gwhy = "MODERATE", "capped: " + _caveat
            _tags = ["agora", "research", f"grade-{_g.lower()}"] + (["low-credibility"] if _lowcred else [])
            graded = (f"> **Evidence grade: {_g}** — {_gwhy}. (Grades the strength of the evidence, "
                      f"not the claim's importance.)\n\n"
                      + (f"> ⚠ Credibility: {_caveat}\n\n" if _lowcred else "") + content)
            await writer.write_note(title=title[:70], content=graded,
                                    tags=_tags, agent_name="Sage Mira")
            _PROMOTED.add(title)                      # definitive: landed in the vault
            promoted.append(title[:50])
        except Exception as _we:
            # transient (do NOT burn the title — retry next run), and SAY so instead of hiding it
            print(f"[promote] write_note failed for '{title[:60]}': {type(_we).__name__}: {_we}")
            _PROMOTE_STATS["src_write_err"] = _PROMOTE_STATS.get("src_write_err", 0) + 1
    _PROMOTE_STATS["promoted"] += len(promoted)
    _PROMOTE_STATS["checked"] += checked
    return {"status": "ok", "promoted": len(promoted), "checked": checked,
            "deduped": deduped, "titles": promoted}


@router.get("/brain/web-scout")
async def web_scout(request: Request, q: str, n: int = 6):
    """Widest-reach FREE multi-source web search (owner 2026-06-27): HuggingFace papers, Hacker News,
    Crossref, Wikipedia, Semantic Scholar, DuckDuckGo (no-key) + Tavily/Brave/Reddit (key-gated, free
    monthly quota). Fresh external signal to bridge into the vault + feed the Crucible with testable
    claims. Read-only aggregator, fail-soft per source."""
    import asyncio
    try:
        from agora.execution.web_search import web_search
        out = await asyncio.to_thread(web_search, q, n)
        return out
    except Exception as e:
        return {"status": "error", "error": str(e)[:200], "results": []}


_VERIFIED: set = set()   # finding titles already fact-checked (so we work through the backlog)


@router.post("/brain/verify-findings")
async def verify_findings(request: Request, n: int = 4, incorporate: bool = True):
    """Fact-check recent UN-checked findings against real sources; incorporate the VERIFIED ones
    into the vault as validated notes. Run repeatedly to work through the backlog gradually."""
    from agora.execution.verifier import verify_finding
    db = request.app.state.db
    cur = await db.execute(
        "SELECT title, content, contributor_name FROM collective_knowledge "
        "WHERE knowledge_type='discovery' ORDER BY created_at DESC LIMIT 25")
    rows = await cur.fetchall()
    writer = getattr(request.app.state, "vault_writer", None)
    results = []
    for r in rows:
        if len(results) >= n:
            break
        title = (r["title"] or "").strip()
        content = (r["content"] or "").strip()
        if len(content) < 60 or title in _VERIFIED:
            continue
        _VERIFIED.add(title)
        v = await verify_finding(title, content)
        try:
            from agora.execution.source_reliability import record as _src_record
            from agora.execution.mastery import record as _mastery_record
            _src_record(v.get("source", ""), v.get("verdict", ""))
            _mastery_record(r["contributor_name"] or "", v.get("verdict", ""))
        except Exception:
            pass
        if v["verdict"] == "INCONCLUSIVE":
            _VERIFIED.discard(title)        # not actually judged → allow a re-check later
            continue
        if v["verdict"] == "LAB_SOURCED":
            # The claim's evidence is one of OUR OWN Lab runs. It is settled here on purpose: no
            # literature fetch, no note, no credit or blame to the contributor — and NOT re-queued,
            # which is the whole point. Six days of quota went into re-asking the literature about
            # Lab 89ffff's simulated 0.077 N, a question no paper can answer.
            results.append({"title": title[:60], "verdict": v["verdict"],
                            "reason": v["reason"], "incorporated": False})
            continue
        inc = False
        if v["verdict"] in ("VERIFIED", "OVERSTATED") and incorporate and writer:
            ok = v["verdict"] == "VERIFIED"
            stamp = "✓ Verified against real sources" if ok else "⚠️ Partially supported (overstated)"
            note = f"{content}\n\n## Verification\n{stamp} — {v['reason']}\nSource: {v['source']}"
            try:
                await writer.write_note(
                    title=f"{'✓' if ok else '~'} {title[:70]}", content=note,
                    tags=["agora", "verified" if ok else "overstated"], agent_name="Sergeant Voss")
                inc = True
            except Exception:
                pass
        results.append({"title": title[:60], "verdict": v["verdict"],
                        "reason": v["reason"], "incorporated": inc})
    return {"status": "ok",
            "verified": sum(1 for x in results if x["verdict"] == "VERIFIED"),
            "incorporated": sum(1 for x in results if x["incorporated"]),
            "total": len(results), "results": results}


@router.get("/brain/research")
async def brain_research(q: str, n: int = 4):
    """Real research grounding across ALL fields — OpenAlex (cited) + arXiv (preprints), so
    agents write notes grounded in real sources (not hallucinated citations)."""
    import asyncio
    from agora.execution.research_tool import research, format_for_prompt
    papers = await asyncio.to_thread(research, q, n)
    return {"status": "ok", "query": q, "papers": papers,
            "formatted": format_for_prompt(papers)}


_SEM_INDEX = None


@router.get("/brain/vault-search")
async def vault_search(q: str, k: int = 8):
    """Semantic search over the USER's own notes (embeddings, not keywords) — lets agents
    find what the user already knows + spot real gaps."""
    global _SEM_INDEX
    import asyncio
    from agora.execution.semantic_index import SemanticIndex
    if _SEM_INDEX is None or not _SEM_INDEX.ready:
        _SEM_INDEX = SemanticIndex()                 # (re)load cache (built async)
    results = await asyncio.to_thread(_SEM_INDEX.search, q, k) if _SEM_INDEX.ready else []
    return {"status": "ok", "query": q, "ready": _SEM_INDEX.ready, "results": results}


@router.get("/brain/gaps")
async def brain_gaps(n: int = 10):
    """The user's underdeveloped areas — isolated-but-substantive notes (seeds never grown) —
    so agents can do GAP-DRIVEN research aimed at what the user actually lacks.

    ROTATION: find_gaps() sorts most-isolated-first, deterministically, and researching a gap does
    not relink the note — so a broad isolated note (e.g. 'Malware Analysis') stays at the top and
    gets picked forever. We pull a WIDER pool and order it least-recently-served first, so agents
    cover the whole isolated set instead of fixating on the few broadest never-closing notes."""
    global _SEM_INDEX
    import json
    import time
    from agora.execution.semantic_index import SemanticIndex
    if _SEM_INDEX is None or not _SEM_INDEX.ready:
        _SEM_INDEX = SemanticIndex()
    if not _SEM_INDEX.ready:
        return {"status": "ok", "gaps": []}
    return {"status": "ok", "gaps": _SEM_INDEX.rotated_gaps(n)}


@router.get("/brain/believe")
async def brain_believe(q: str, k: int = 8):
    """AGORA 2.0 / Pillar 1 — what the vault BELIEVES about a topic: structured claims
    (subject·relation·object) with confidence + sources + contradictions. The vault thinks."""
    from agora.config import settings
    from agora.execution.knowledge_graph import believe
    return {"status": "ok", **await believe(q, settings.vault_path, k)}


@router.get("/brain/hypothesize")
async def brain_hypothesize(q: str):
    """AGORA 2.0 / Pillar 2 — agents as scientists: take what the vault believes, form a NEW
    testable hypothesis, test it against real literature, return verdict + evidence + falsifier."""
    from agora.config import settings
    from agora.execution.scientist import hypothesize_and_test
    return {"status": "ok", **await hypothesize_and_test(q, settings.vault_path)}


@router.get("/brain/frontier")
async def brain_frontier(q: str, k: int = 8):
    """AGORA 2.0 — the vault's uncertain edges on a topic (low-confidence claims + contradictions)."""
    from agora.config import settings
    from agora.execution.knowledge_graph import frontier
    return {"status": "ok", **await frontier(q, settings.vault_path, k)}


_DIRECTIONS: dict = {"themes": [], "insight": "", "directions": [], "ts": 0}

# Durable, template-backed FRONTIER research directions (the workflow-authored frontier questions, each
# mapping 1:1 to a Methods Library template). Merged into current_directions so the swarm quests on
# FRONTIER-tier questions, not just the textbook-tier directions auto-harvested from recent findings.
_FRONTIER_DIR_FILE = Path(__file__).resolve().parents[3] / ".frontier_directions.json"  # repo root


def _load_frontier_directions() -> list:
    import json
    try:
        return list(json.loads(_FRONTIER_DIR_FILE.read_text(encoding="utf-8")))
    except Exception:
        return []


@router.get("/brain/directions")
async def brain_directions(request: Request, n: int = 14):
    """HARVEST: turn the agents' recent findings into emerging themes + the strongest insight +
    3 concrete NEXT DIRECTIONS (research or system upgrade). Stored so agents pursue them — the
    missing layer that makes research compound into directions, not just pile up as notes."""
    import time
    db = request.app.state.db
    cur = await db.execute(
        "SELECT content FROM collective_knowledge WHERE knowledge_type='discovery' "
        "ORDER BY created_at DESC LIMIT ?", (n,))
    findings = [r["content"] for r in await cur.fetchall() if r["content"]]
    from agora.execution.harvest import synthesize_directions
    d = await synthesize_directions(findings)
    global _DIRECTIONS
    _DIRECTIONS = {**d, "ts": time.time()}
    return {"status": "ok", **d}


@router.get("/brain/directions/current")
async def current_directions():
    """The latest harvested directions — agents pull these to pursue them (closing the loop). Durable
    FRONTIER directions are merged FIRST so the swarm reliably quests on the template-backed frontier
    questions (the swarm's _renewable_quests interleaves + dedups these, so it rotates through them)."""
    frontier = _load_frontier_directions()
    return {"directions": frontier + _DIRECTIONS.get("directions", []),
            "themes": _DIRECTIONS.get("themes", [])}


_LAST_UPGRADES: list = []   # the last self-upgrade proposals (numbered) — pick one by replying its number


@router.get("/brain/self-upgrades")
async def brain_self_upgrades(request: Request, notify: bool = False):
    """Agora reflects on its OWN mechanisms + metrics and proposes concrete upgrades to ITSELF —
    the recursive self-improvement loop. NUMBERED so the user can reply a number to implement one.
    With notify=true, the proposals are pushed to Telegram (the recurring routine)."""
    from agora.execution.self_upgrade import propose_self_upgrades
    global _LAST_UPGRADES
    d = await propose_self_upgrades(request.app.state.db)
    _LAST_UPGRADES = d.get("upgrades", [])
    if notify and _LAST_UPGRADES:
        lines = ["🔧 *Agora proposes upgrades to itself — reply a number to build it:*\n"]
        for i, u in enumerate(_LAST_UPGRADES, 1):
            lines.append(f"*{i}.* {u['title']}\n   _{u.get('why', '')[:90]}_")
        await _send_telegram("\n".join(lines))
    return {"status": "ok", **d}


@router.post("/brain/self-upgrades/pick")
async def pick_self_upgrade(request: Request):
    """The user picked a numbered self-upgrade → queue it for Claude Code to implement."""
    from agora.execution.claude_inbox import add_task
    body = await request.json()
    try:
        n = int(body.get("n", 0))
    except Exception:
        n = 0
    if not (1 <= n <= len(_LAST_UPGRADES)):
        return {"status": "out-of-range", "count": len(_LAST_UPGRADES)}
    u = _LAST_UPGRADES[n - 1]
    tid = add_task(f"Implement Agora self-upgrade: {u['title']}. Why: {u.get('why', '')}. "
                   f"How: {u.get('how', '')}")
    return {"status": "queued", "id": tid, "title": u["title"]}


@router.get("/brain/finding-diversity")
async def brain_finding_diversity(request: Request, n: int = 60, threshold: float = 0.6,
                                  notify: bool = False):
    """Measure the RAW (pre-promotion) findings stream: near-duplicate rate + source concentration.
    Turns 'the system keeps re-deriving the same findings' into a number we can watch over time."""
    from agora.execution.finding_diversity import finding_diversity, format_diversity
    d = await finding_diversity(request.app.state.db, n=n, threshold=threshold)
    if notify:
        await _send_telegram(format_diversity(d))
    return {"status": "ok", **d}


@router.get("/brain/pulse")
async def brain_pulse(request: Request, hours: int = 4, notify: bool = False):
    """PULSE — a plain-language heartbeat: what's being researched + why, how much is meaningful,
    and what actually reached the Obsidian vault / GitHub second-brain. The visibility layer."""
    from agora.config import settings
    from agora.execution.pulse import build_pulse, format_pulse
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    p = await build_pulse(request.app.state.db, vault, hours)
    p["promote"] = dict(_PROMOTE_STATS)          # cumulative funnel stats for the research-ROI line
    gaps = []
    try:
        from agora.execution.semantic_index import SemanticIndex
        global _SEM_INDEX
        if _SEM_INDEX is None or not _SEM_INDEX.ready:
            _SEM_INDEX = SemanticIndex()
        gaps = _SEM_INDEX.rotated_gaps(3) if _SEM_INDEX.ready else []
    except Exception:
        pass
    report = format_pulse(p, gaps, _DIRECTIONS.get("directions", []))
    if notify:
        await _send_telegram(report)
    return {"status": "ok", "pulse": p, "report": report}


@router.get("/brain/empirical-test")
async def brain_empirical_test(q: str):
    """REALITY BRIDGE — test a claim against REAL-WORLD DATA from a free public API (Hacker News /
    Wikipedia / World Bank): route → fetch → judge. Empirical grounding beyond the paper literature."""
    from agora.execution.data_tool import empirical_test
    r = await empirical_test(q)
    try:
        from agora.execution.source_reliability import record as _src_record
        _src_record(r.get("source", ""), r.get("verdict", ""))
    except Exception:
        pass
    return {"status": "ok", **r}


@router.get("/brain/insight")
async def brain_insight(q: str):
    """INSIGHT ENGINE — synthesize ONE genuinely new, falsifiable insight on a theme by connecting the
    vault's beliefs + the literature + real-world data into something stated in none of them. The leap
    from knowledge collector to knowledge CREATOR."""
    from agora.config import settings
    from agora.execution.insight_engine import synthesize_insight
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await synthesize_insight(q, vault)}


@router.get("/brain/insight-inputs")
async def brain_insight_inputs(q: str):
    """Gather the three groundings (vault notes + literature + real-world data) for a theme WITHOUT
    synthesizing — so a stronger model (Claude Opus) can do the creative synthesis itself."""
    from agora.config import settings
    from agora.execution.insight_engine import gather_insight_inputs
    from agora.execution.source_reliability import reliability_text
    from agora.execution.board import priorities_text
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", "source_reliability": reliability_text(),
            "owner_priorities": priorities_text(),
            **await gather_insight_inputs(q, vault)}


@router.get("/brain/predict")
async def brain_predict(q: str, horizon_days: int = 14):
    """PREDICTION LEDGER — record a falsifiable forecast: the current real-world metric for a theme +
    a prediction of its direction. The Reality Bridge resolves it later (the Accountable Mind)."""
    from agora.execution.prediction_ledger import make_prediction
    return {"status": "ok", **await make_prediction(q, horizon_days)}


@router.get("/brain/predictions")
async def brain_predictions():
    """The prediction ledger + Agora's track record (hit-rate + calibration)."""
    from agora.execution.prediction_ledger import _load, calibration, format_predictions
    return {"status": "ok", "predictions": _load()[-20:], "calibration": calibration(),
            "report": format_predictions(10)}


@router.post("/brain/resolve-predictions")
async def brain_resolve_predictions(force: bool = False):
    """Re-fetch due predictions' real-world metrics and resolve them correct/incorrect."""
    from agora.execution.prediction_ledger import resolve_due, calibration
    resolved = await resolve_due(force)
    return {"status": "ok", "resolved": len(resolved), "calibration": calibration(),
            "records": [{"theme": p.get("theme"), "actual": p.get("actual"),
                         "status": p.get("status"), "by": p.get("by", ""),
                         "calls": p.get("calls", [])} for p in resolved]}


@router.post("/brain/predict-tournament")
async def brain_predict_tournament(request: Request):
    """FORECASTING TOURNAMENT — every agent persona calls the same theme; each builds a personal
    track record and (dungeon-side) accuracy feeds standing. Reputation follows truth."""
    from agora.execution.prediction_ledger import run_tournament
    b = await request.json()
    theme = (b.get("theme") or "").strip()
    if not theme:
        return {"status": "empty"}
    return await run_tournament(theme, int(b.get("horizon_days", 14)))


@router.get("/brain/agent-forecasts")
async def brain_agent_forecasts():
    """Per-agent forecasting track record (resolved tournament calls)."""
    from agora.execution.prediction_ledger import agent_scores
    return {"status": "ok", "scores": agent_scores()}


@router.post("/brain/exam/generate")
async def brain_exam_generate(request: Request):
    """THE EXAM — generate a Socratic exam from core vault concepts; Agora self-answers (flash)
    and the sheet waits for Claude's grading. Capability growth becomes a time series."""
    from agora.config import settings
    from agora.execution.exam import generate_exam
    b = await request.json()
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    exam = await generate_exam(vault, int(b.get("n", 6)))
    if exam.get("id"):        # the spread puts the exam's own status (answered) over "ok"
        from agora.execution.claude_inbox import add_task
        add_task(f"Grade exam [{exam['id']}]")
    return exam


@router.post("/brain/exam/grade")
async def brain_exam_grade(request: Request):
    """Record Claude's grading of an exam (one 0-2 score per question)."""
    from agora.execution.exam import grade_exam
    b = await request.json()
    return grade_exam(b.get("id") or "", b.get("scores") or [], b.get("feedback") or "")


@router.get("/brain/exams")
async def brain_exams():
    """Exam ledger: the score time series + the latest full sheet."""
    from agora.execution.exam import exam_history
    return {"status": "ok", **exam_history()}


@router.get("/brain/memory-economy")
async def brain_memory_economy(n: int = 12):
    """MEMORY ECONOMY — per-note value accounting + the current dead-weight candidates (preview,
    no side effects). The Custodian Principle applied to the vault itself."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.memory_economy import score_notes, prune_candidates, format_economy
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    notes = await _aio.to_thread(score_notes, vault)
    cands = sorted([x for x in notes
                    if not x["evergreen"] and x["age_days"] > 30 and x["chars"] < 700
                    and x["inlinks"] == 0 and x["retrievals"] == 0 and x["value"] <= 2],
                   key=lambda x: (x["value"], -x["age_days"]))[:n]
    return {"status": "ok", "total": len(notes), "candidates": cands,
            "report": format_economy(notes, cands)}


@router.post("/brain/correspondent/draft")
async def brain_correspondent_draft(request: Request):
    """THE CORRESPONDENT — store Claude's composed outreach and propose the GATED action.
    Nothing leaves the machine until the owner approves from Telegram."""
    from agora.execution.correspondent import save_draft, novelty_report, format_novelty
    from agora.execution.hands import propose_action, pending_approvals
    b = await request.json()
    title, body = (b.get("title") or "").strip(), (b.get("body") or "").strip()
    if len(title) < 10 or len(body) < 100:
        return {"status": "too_short"}
    if any(x.get("kind") == "outreach" for x in pending_approvals()):
        return {"status": "already_pending"}
    repo, issue_no = (b.get("repo") or "").strip(), int(b.get("issue_number") or 0)
    rec = save_draft(title, body, repo, issue_no)
    nov = novelty_report(body, exclude_id=rec["id"])     # catch templated repetition BEFORE it posts
    where = f"comment on {repo}#{issue_no}" if repo and issue_no else "new public GitHub issue"
    act = propose_action("outreach", f"Post public outreach ({where}): {title[:60]}",
                         body[:300], {"corr_id": rec["id"]})
    nov_line = format_novelty(nov)
    await _send_telegram(f"✉️ Correspondent proposal `{act['id']}`: {where}\n"
                         f"*{title[:80]}*\n_{body[:180]}…_\n"
                         + (nov_line + "\n" if nov_line else "")
                         + f"Reply `approve {act['id']}` or `reject {act['id']}`.")
    return {"status": "proposed", "draft": rec, "action": act, "novelty": nov}


@router.post("/brain/correspondent/harvest")
async def brain_correspondent_harvest(request: Request):
    """Pull new replies to posted correspondences — external challenge coming home."""
    import asyncio as _aio
    from agora.execution.correspondent import harvest_replies
    fresh = await _aio.to_thread(harvest_replies)
    from agora.execution.input_shield import wrap_as_data
    for c in fresh[:3]:
        from agora.execution.claude_inbox import add_task
        safe = wrap_as_data(f"GitHub user {c['by']}", c["text"])
        add_task(f"Correspondence reply by {c['by']} on '{c['title'][:50]}' "
                 f"(corr {c['corr_id']}, thread {c['repo']}#{c['issue']}). {safe}\n"
                 f"If (and only if) a substantive reply is warranted, draft one back into the "
                 f"SAME thread via POST /brain/correspondent/draft "
                 f"{{title, body, repo: '{c['repo']}', issue_number: {c['issue']}}} — "
                 f"gated by owner approval, never automatic.")
    return {"status": "ok", "new_replies": len(fresh)}


@router.get("/brain/correspondence")
async def brain_correspondence():
    from agora.execution.correspondent import format_correspondence, _load
    return {"status": "ok", "report": format_correspondence(), "items": _load()[-10:]}


@router.get("/brain/theory/target")
async def brain_theory_target():
    """THEORY ENGINE — the next mechanistic belief awaiting a model run."""
    from agora.config import settings
    from agora.execution.theory import pick_target
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", "target": pick_target(vault)}


@router.post("/brain/theory/record")
async def brain_theory_record(request: Request):
    """Ledger a theory run and stamp the belief (corroborated/strained/unmodelable)."""
    from agora.execution.theory import record_run
    b = await request.json()
    return record_run(b.get("title") or "", b.get("path") or "", b.get("verdict") or "",
                      b.get("lab") or "", b.get("summary") or "")


@router.get("/brain/theory")
async def brain_theory():
    from agora.execution.theory import format_theory, _load
    return {"status": "ok", "report": format_theory(), "runs": _load()[-15:]}


@router.get("/brain/unification")
async def brain_unification():
    """THE UNIFICATION ENGINE — strongest validated results + candidate unifying laws."""
    from agora.config import settings
    from agora.execution.unification import gather_inputs, format_unification, _load
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", "report": format_unification(),
            "inputs": gather_inputs(vault), "laws": _load()[-15:]}


@router.post("/brain/unification/record")
async def brain_unification_record(request: Request):
    """Ledger a candidate unifying law (must name a NOVEL prediction + falsifier + Lab id)."""
    from agora.execution.unification import record_unification
    b = await request.json()
    return record_unification(b.get("name") or "", b.get("principle") or "", b.get("subsumes") or [],
                              b.get("lab_id") or "", b.get("novel_prediction") or "",
                              b.get("falsifier") or "", b.get("status") or "candidate",
                              b.get("note") or "")


@router.get("/brain/investigation")
async def brain_investigation():
    """THE INVESTIGATION ENGINE — multi-step Lab chains (depth, not one-shot)."""
    from agora.execution.investigation import format_investigations, _load
    return {"status": "ok", "report": format_investigations(), "investigations": _load()[-15:]}


@router.post("/brain/investigation/{action}")
async def brain_investigation_action(action: str, request: Request):
    """Lifecycle of a multi-step investigation: start | step | conclude."""
    from agora.execution.investigation import handle
    return handle(action, await request.json())


@router.get("/brain/self-improvement")
async def brain_self_improvement():
    """RECURSIVE SELF-IMPROVEMENT — Agora measures itself on its own external-anchor law + per-organ
    validated-yield, and emits a law-aware feedback recommendation."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.self_improvement import measure_self, recommend, format_self_improvement
    m = await _aio.to_thread(measure_self, settings.vault_path or "")
    r = recommend(m)
    return {"status": "ok", "report": format_self_improvement(m, r), "measure": m, **r}


@router.get("/brain/self-scientist")
async def brain_self_scientist():
    """THE SELF-IMPROVING SCIENTIST — Agora's validated-discovery yield over time + a self-tuning
    directive derived from its own laws (the apex of the self-referential bet, measured)."""
    import asyncio as _aio
    from agora.execution.self_scientist import (validated_yield, controller, trend,
                                                format_self_scientist)
    y = await _aio.to_thread(validated_yield)
    return {"status": "ok", "report": format_self_scientist(),
            "yield": y, "controller": controller(), "trend": trend()}


@router.get("/brain/self-experiment")
async def brain_self_experiment():
    """THE SELF-EXPERIMENT — is the self-improvement loop real? A controlled A/B over policy regimes,
    measured on the AUTONOMOUS channel only (so the controller's causal effect is identified, not
    confounded by Claude's manual work). Returns an effect size + an honest verdict."""
    import asyncio as _aio
    from agora.execution.self_experiment import readout, format_self_experiment
    r = await _aio.to_thread(readout)
    return {"status": "ok", "report": format_self_experiment(), **r}


@router.get("/brain/self-improver")
async def brain_self_improver():
    """SELF-IMPROVING SCIENTIST v3 (recursive, advisory) — reads the live self-experiment and recommends
    the next falsifiable self-modification, with an adoption bar scaled to the change's cost/
    irreversibility (Lab 39baec). Read-only: proposes, the loop/owner disposes."""
    import asyncio as _aio
    from agora.execution.self_improver import recommend, format_self_improver
    a = await _aio.to_thread(recommend)
    return {"status": "ok", "report": format_self_improver(), **a}


@router.post("/brain/ews")
async def brain_ews(request: Request):
    """CRITICAL-TRANSITION EARLY-WARNING ENGINE (capstone) — score a supplied time series for an
    approaching fold/bifurcation (critical slowing down) AND report the engine's own trustworthiness
    (fold-like = in-scope/trust; rising-variance-without-slowing = volatility/noise regime = out of
    scope). Body: {series: [float, ...], win?: int}."""
    import asyncio as _aio
    from agora.execution.ews import assess, format_ews
    try:
        body = await request.json()
    except Exception:
        body = {}
    series = body.get("series") or []
    win = int(body.get("win") or 0)
    a = await _aio.to_thread(assess, series, win)
    return {"status": "ok", "report": format_ews(a), **a}


@router.get("/brain/self-tipping")
async def brain_self_tipping():
    """CONSENSUS LOCK-IN GUARD — Agora checked by its own minority-tipping / Grounding-Coupling law:
    is one theme crossing the critical mass without the external grounding + domain diversity the law
    says is needed to keep a dominant cluster truth-tracking? Automates the criticality retrospective's
    bias-check."""
    import asyncio as _aio
    from agora.execution.self_tipping import assess, format_self_tipping
    a = await _aio.to_thread(assess)
    return {"status": "ok", "report": format_self_tipping(), **a}


@router.get("/brain/counterfactual")
async def brain_counterfactual():
    """THE COUNTERFACTUAL SELF — the system's history replayed under alternative policies."""
    import asyncio as _aio
    from agora.execution.counterfactual import full_report, format_counterfactual
    r = await _aio.to_thread(full_report)
    return {"status": "ok", "report": format_counterfactual(), **r}


@router.get("/brain/metabolism")
async def brain_metabolism():
    """THE METABOLISM — per-organ token spend, value points, and ROI (value/kilotoken)."""
    from agora.execution.metabolism import format_metabolism, roi_report
    return {"status": "ok", "report": format_metabolism(), **roi_report()}


@router.get("/brain/oracle/scan")
async def brain_oracle_scan():
    """THE ORACLE — open, liquid, in-domain prediction markets worth an independent call."""
    import asyncio as _aio
    from agora.execution.oracle import fetch_candidates
    return {"status": "ok", "candidates": await _aio.to_thread(fetch_candidates)}


@router.post("/brain/oracle/call")
async def brain_oracle_call(request: Request):
    """Record Agora's independent probability vs the market price (a paper position)."""
    from agora.execution.oracle import record_call
    b = await request.json()
    return {"status": "ok", **record_call(
        b.get("market_id") or "", b.get("question") or "", float(b.get("market_prob", 0.5)),
        b.get("ends") or "", float(b.get("agora_prob", 0.5)), b.get("reasoning") or "")}


@router.post("/brain/oracle/resolve")
async def brain_oracle_resolve(request: Request):
    """Score open positions whose markets have resolved — Brier vs hard reality, vs the market."""
    import asyncio as _aio
    from agora.execution.oracle import resolve_open, scorecard
    resolved = await _aio.to_thread(resolve_open)
    return {"status": "ok", "resolved": resolved, **scorecard()}


@router.get("/brain/oracle")
async def brain_oracle():
    from agora.execution.oracle import format_oracle, scorecard, _load
    return {"status": "ok", "report": format_oracle(), "scorecard": scorecard(),
            "positions": _load()[-15:]}


@router.post("/brain/coherence/audit")
async def brain_coherence_audit(request: Request):
    """COHERENCE AUDIT — check one new belief against its closest siblings for incompatibility."""
    from agora.config import settings
    from agora.execution.coherence import audit_once
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return await audit_once(vault)


@router.get("/brain/coherence")
async def brain_coherence():
    from agora.execution.coherence import format_coherence, _load
    return {"status": "ok", "report": format_coherence(), **_load()}


@router.get("/dashboard")
async def brain_dashboard():
    """THE GAUGES — the whole organism on one page (read-only HTML, SVG sparklines)."""
    from fastapi.responses import HTMLResponse
    from agora.execution.dashboard import render_dashboard
    return HTMLResponse(render_dashboard())


@router.get("/brain/funnel")
async def brain_funnel():
    """THE VALUE FUNNEL (JSON) — activity → grounded → curated → shipped, with conversion + ROI."""
    import asyncio as _aio
    from agora.execution.funnel import compute_funnel
    return await _aio.to_thread(compute_funnel)


@router.post("/brain/seminar/topic")
async def brain_seminar_inject(request: Request):
    """Hand the agent team a topic to research (Claude or owner). It becomes an open thread."""
    from agora.execution.seminar import inject_topic
    b = await request.json()
    return inject_topic(b.get("headline") or b.get("topic") or "", b.get("prompt") or "",
                        b.get("source") or "claude")


@router.get("/brain/seminar/report")
async def brain_seminar_report(hours: int = 3):
    """The team's research report — topics advanced, contributions, what was skipped and why."""
    from agora.execution.seminar import research_report, seminar_stats, topic_threads
    return {"report": research_report(hours), "stats": seminar_stats(),
            "threads": topic_threads(10)}


@router.get("/brain/funnel/view")
async def brain_funnel_view():
    """THE VALUE FUNNEL (HTML) — does the work produce value, and at what cost? One page."""
    import asyncio as _aio
    from fastapi.responses import HTMLResponse
    from agora.execution.funnel import render_funnel_html
    return HTMLResponse(await _aio.to_thread(render_funnel_html))


@router.post("/brain/atlas/build")
async def brain_atlas_build(request: Request):
    """THE ATLAS — (re)build the per-domain Maps of Content (idempotent direct writes)."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.atlas import build_atlas, format_atlas
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    d = await _aio.to_thread(build_atlas, vault)
    return {"status": "ok", "report": format_atlas(d), **d}


@router.post("/brain/gatekeeper/skip")
async def brain_gatekeeper_skip(request: Request):
    """THE GATEKEEPER — Claude records an editorial skip so queue generators stop re-offering it."""
    from agora.execution.gatekeeper import record_skip
    b = await request.json()
    return {"status": "ok", "recorded": bool(record_skip(b.get("theme") or "", b.get("reason") or ""))}


@router.get("/brain/gatekeeper/skips")
async def brain_gatekeeper_skips():
    """Recently refused themes (for the dungeon's upstream queue filtering)."""
    from agora.execution.gatekeeper import skipped_themes, format_skips
    return {"status": "ok", "themes": skipped_themes(), "report": format_skips()}


@router.post("/brain/salon/sense")
async def brain_salon_sense(request: Request):
    """THE SALON — pull new pieces from the followed minds; extract at most ONE contestable
    claim and queue it for the dialectic (named external disagreement)."""
    import asyncio as _aio
    from agora.execution.salon import sense_salon, extract_claim, record_claim
    fresh = await _aio.to_thread(sense_salon)
    claim_rec = None
    for it in fresh[:6]:
        if len(it.get("summary", "")) < 120:
            continue
        claim = await _aio.to_thread(extract_claim, it)
        if claim:
            record_claim(it["author"], it["title"], claim)
            from agora.execution.claude_inbox import add_task
            add_task(f"Dialectic: {claim[:140]} (per {it['author']})")
            claim_rec = {"author": it["author"], "claim": claim}
            break
    return {"status": "ok", "new_items": len(fresh), "claim": claim_rec}


@router.get("/brain/salon")
async def brain_salon():
    from agora.execution.salon import format_salon
    return {"status": "ok", "report": format_salon()}


@router.post("/brain/board/agenda")
async def brain_board_agenda(request: Request):
    """THE BOARD MEETING — prepare the weekly agenda and send it to the owner."""
    from agora.execution.board import prepare_agenda, format_agenda
    a = await prepare_agenda(request.app.state.db)
    await _send_telegram(format_agenda(a))
    return {"status": "ok", "agenda": a}


@router.post("/brain/board/decide")
async def brain_board_decide(request: Request):
    """Record the owner's directives — they become standing priorities for all synthesis."""
    from agora.execution.board import record_directives
    b = await request.json()
    return {"status": "ok", "agenda": record_directives(b.get("text") or "")}


@router.get("/brain/board")
async def brain_board():
    from agora.execution.board import format_board, priorities_text
    return {"status": "ok", "report": format_board(), "priorities": priorities_text()}


@router.post("/brain/annals/today")
async def brain_annals_today(request: Request):
    """THE ANNALS — write/refresh today's chronicle as an idempotent vault note."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.annals import compose_day, chronicle_text
    b = await request.json()
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    d = await _aio.to_thread(compose_day, vault, b.get("day") or "")
    writer = getattr(request.app.state, "vault_writer", None)
    path = None
    if writer:
        try:
            path = await writer.write_note(
                title=f"Annals {d['day']}", content=chronicle_text(d),
                tags=["agora", "annals"], agent_name="Agora")
        except Exception:
            pass
    return {"status": "ok", "note": path, **d}


@router.get("/brain/annals")
async def brain_annals(day: str = ""):
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.annals import compose_day, format_annals
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    d = await _aio.to_thread(compose_day, vault, day)
    return {"status": "ok", "report": format_annals(d), **d}


@router.post("/brain/lab/run")
async def brain_lab_run(request: Request):
    """THE LABORATORY — execute a Claude-written experiment script (deterministic runner:
    hard timeout, output cap, results ledgered with source 'simulation').

    THE SCRIPT MUST OPEN WITH A DOCSTRING SAYING WHAT IT MODELS. The ledger's `name` is the QUEST
    title, and a quest title and the model underneath it can disagree completely: a run titled
    "basket-goodhart-interior-k / In a competitive matrix where frontier k..." printed `mean K* = 10.5`
    and was read as an optimal RETRIEVAL DEPTH; the script models an adversary splitting a budget across
    K PROXY METRICS. Measured on the last 60 runs: **100% carried no description of the model at all**,
    so every number in the ledger is attributable only through its quest title.

    A script with no leading docstring/comment block still runs — silencing the Lab would be worse — but
    it is recorded `undocumented: true`, and the response says so, so the gap is visible instead of
    being inherited by whoever quotes the number next.
    """
    import asyncio as _aio
    from agora.execution.lab import run_experiment
    b = await request.json()
    code = b.get("code") or ""
    if len(code) < 20:
        return {"status": "empty"}
    rec = await _aio.to_thread(run_experiment, b.get("name") or "", code)
    out = {"status": "ok", **rec}
    if rec.get("undocumented"):
        out["warning"] = ("this script does not say what it models — open it with a docstring stating "
                          "the mechanism, or the number can only be attributed by its quest title")
    return out


@router.get("/brain/lab")
async def brain_lab():
    from agora.execution.lab import format_lab, recent
    return {"status": "ok", "report": format_lab(), "experiments": recent()}


@router.get("/brain/crucible-synthesis")
async def brain_crucible_synthesis():
    """THE SYNTHESIS ORGAN — the latest candidate unifying thesis across the rigorous corpus."""
    from agora.execution.synthesis import format_synthesis, gather_findings, _load, _STORE
    return {"status": "ok", "report": format_synthesis(),
            "n_findings": len(gather_findings()), "proposals": _load(_STORE, [])[-5:]}


@router.post("/brain/crucible-synthesis/run")
async def brain_crucible_synthesis_run(request: Request):
    """Queue a grand-synthesis task for Claude (the organ gathers the rigorous corpus; Claude
    produces the unifying thesis — cross-finding synthesis is Claude's job, not a cheap LLM call)."""
    import asyncio as _aio
    from agora.execution.synthesis import queue_synthesis
    return await _aio.to_thread(queue_synthesis)


@router.post("/brain/crucible-synthesis/record")
async def brain_crucible_synthesis_record(request: Request):
    """Claude writes the synthesized thesis back to the organ's ledger."""
    from agora.execution.synthesis import record_thesis
    b = await request.json()
    return record_thesis(b.get("thesis") or "", b.get("rests_on") or [], b.get("why") or "",
                         b.get("falsifier") or "", b.get("honest", True), b.get("note_path") or "")


@router.get("/brain/methods")
async def brain_methods():
    """THE METHODS LIBRARY — parameterized experiment templates + the autonomous-run ledger."""
    from agora.execution.methods import catalog, format_methods, _load
    return {"status": "ok", "report": format_methods(), "templates": catalog(),
            "runs": _load()[-15:]}


@router.post("/brain/methods/run")
async def brain_methods_run(request: Request):
    """Instantiate a vetted experiment template with validated params (params, never code)."""
    import asyncio as _aio
    from agora.execution.methods import run_method
    b = await request.json()
    return await _aio.to_thread(run_method, b.get("template") or "", b.get("params") or {},
                                b.get("claim") or "", b.get("requester") or "api")


@router.post("/brain/methods/match")
async def brain_methods_match(request: Request):
    """Map a free-text hypothesis theme to a template via the cheap LLM and run it."""
    from agora.execution.methods import match_and_run
    b = await request.json()
    theme = (b.get("theme") or "").strip()
    if len(theme) < 12:
        return {"status": "empty"}
    return await match_and_run(theme, b.get("requester") or "api")


@router.post("/brain/night-shift")
async def brain_night_shift(request: Request):
    """THE NIGHT SHIFT — nightly consolidation: re-embed the vault (fresh semantic memory by
    morning), trim the retrieval log, apply a couple of waiting bridges."""
    from agora.config import settings
    from agora.execution.night_shift import run_night_shift
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await run_night_shift(vault)}


@router.get("/brain/agent-mastery")
async def brain_agent_mastery():
    """AGENT MASTERY — whose findings survive verification (feeds standing in the dungeon)."""
    from agora.execution.mastery import scores, format_mastery
    return {"status": "ok", "scores": scores(), "report": format_mastery()}


@router.get("/brain/source-reliability")
async def brain_source_reliability():
    """SOURCE RELIABILITY — how often each evidence source delivers a decisive verdict."""
    from agora.execution.source_reliability import format_sources, weights
    return {"status": "ok", "report": format_sources(), "weights": weights()}


@router.post("/brain/contradictions/scan")
async def brain_contradictions_scan(request: Request):
    """CONTRADICTION SWEEP — judge the closest unjudged note pairs for incompatibility."""
    from agora.config import settings
    from agora.execution.contradictions import sweep
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return await sweep(vault)


@router.get("/brain/contradictions")
async def brain_contradictions():
    from agora.execution.contradictions import format_contradictions, open_contradictions
    return {"status": "ok", "report": format_contradictions(), "open": open_contradictions()}


@router.post("/brain/contradictions/status")
async def brain_contradictions_status(request: Request):
    from agora.execution.contradictions import set_status
    b = await request.json()
    set_status(b.get("id") or "", b.get("status") or "open")
    return {"status": "ok"}


@router.get("/brain/desk")
async def brain_desk(request: Request, q: str = "", notify: bool = False, note: bool = False):
    """THE DESK — lay out the owner's working context (his notes + fresh papers + open
    questions) for what he's actually working on. Deterministic gathering, no LLM."""
    from agora.config import settings
    from agora.execution.desk import compose_desk, format_desk, desk_note
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    d = await compose_desk(vault, q.strip())
    report = format_desk(d)
    if notify and d.get("topic"):
        await _send_telegram(report)
    path = None
    writer = getattr(request.app.state, "vault_writer", None)
    if note and d.get("topic") and writer:
        try:
            path = await writer.write_note(
                title=f"Desk: {d['topic'][:60]}", content=desk_note(d),
                tags=["agora", "desk"], agent_name="Agora")
        except Exception:
            pass
    return {"status": "ok", "report": report, "note": path, **d}


@router.post("/brain/attention/report")
async def brain_attention_report(request: Request):
    """ATTENTION ECONOMY — a trigger reports whether its run yielded anything."""
    from agora.execution.attention import report
    b = await request.json()
    report((b.get("trigger") or "?")[:40], bool(b.get("yielded")))
    return {"status": "ok"}


@router.get("/brain/attention")
async def brain_attention():
    """Run-probability per trigger (yield-weighted, bounded [0.4, 1.0]) + a readable report."""
    from agora.execution.attention import policy, format_attention
    return {"status": "ok", "policy": policy(), "report": format_attention()}


@router.post("/brain/forge/scan")
async def brain_forge_scan(request: Request):
    """CAPABILITY FORGE — scan the system's own failure traces for missing capabilities."""
    from agora.execution.forge import detect_gaps, top_open_gap
    found = await detect_gaps(request.app.state.db)
    return {"status": "ok", "new_gaps": found, "top_open": top_open_gap()}


@router.post("/brain/forge/add")
async def brain_forge_add(request: Request):
    """Register a capability gap by hand (Telegram `gap <desc>`)."""
    from agora.execution.forge import add_gap
    b = await request.json()
    g = add_gap(b.get("description") or "", kind="manual")
    return {"status": "ok" if g else "duplicate_or_short", "gap": g}


@router.post("/brain/forge/status")
async def brain_forge_status(request: Request):
    from agora.execution.forge import set_status
    b = await request.json()
    return {"status": "ok", "gap": set_status(b.get("id") or "", b.get("status") or "open")}


@router.get("/brain/forge")
async def brain_forge():
    from agora.execution.forge import format_forge, _load
    return {"status": "ok", "report": format_forge(), "gaps": _load()[-20:]}


@router.post("/brain/tutor/daily")
async def brain_tutor_daily(request: Request):
    """THE TUTOR — today's spaced-repetition micro-quiz, sent to the owner on Telegram."""
    from agora.config import settings
    from agora.execution.tutor import daily_quiz, format_quiz
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    q = await daily_quiz(vault)
    if q["cards"]:
        await _send_telegram(format_quiz(q["cards"]))
    return {"status": "ok", "n": len(q["cards"])}


@router.post("/brain/tutor/grade")
async def brain_tutor_grade(request: Request):
    """Record the owner's recall result (got/forgot) — SM-2 reschedules the card."""
    from agora.execution.tutor import grade
    b = await request.json()
    return grade(int(b.get("idx", 1)), bool(b.get("ok")))


@router.get("/brain/canon-inputs")
async def brain_canon_inputs():
    """THE CANON — current canon text + artifacts that landed since, for Claude to MERGE."""
    from agora.config import settings
    from agora.execution.canon import gather_canon_inputs
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **gather_canon_inputs(vault)}


@router.post("/brain/canon-write")
async def brain_canon_write(request: Request):
    """Replace the Canon with the merged text (history lives in git)."""
    from agora.config import settings
    from agora.execution.canon import write_canon
    b = await request.json()
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    content = (b.get("content") or "").strip()
    if len(content) < 200:
        return {"status": "too_short"}
    return {"status": "written", "path": write_canon(vault, content)}


@router.get("/brain/canon")
async def brain_canon():
    from agora.config import settings
    from agora.execution.canon import read_canon
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", "canon": read_canon(vault)[:8000]}


@router.get("/brain/belief-challenge-target")
async def brain_belief_challenge_target():
    """BELIEF REVISION — the belief that has gone longest untested (the challenge sweep's prey)."""
    from agora.config import settings
    from agora.execution.belief_revision import pick_challenge_targets
    from agora.execution.claude_inbox import recent_texts
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    # `targets` is the walkable list; `target` stays as its head so existing callers keep working.
    # A caller with its own gate MUST walk `targets` -- taking only the head is what wedged the
    # challenge sweep for 42 days when this module's filter and the dungeon's gate disagreed.
    ts = pick_challenge_targets(vault, recent_blob=" || ".join(recent_texts()), n=8)
    return {"status": "ok", "target": (ts[0] if ts else None), "targets": ts}


@router.post("/brain/belief-revise")
async def brain_belief_revise(request: Request):
    """Record a challenge outcome on the belief note itself: survived / revised / retired.
    Superseded notes stay in the vault — stamped and bannered, never deleted.
    Every resolved challenge also pays the Bounty Ledger — kills feed standing."""
    from agora.execution.belief_revision import stamp_belief
    from agora.execution.bounty import record_challenge
    b = await request.json()
    res = stamp_belief(b.get("path") or "", b.get("verdict") or "",
                       b.get("by_note") or "", b.get("reason") or "")
    if not res.get("error"):
        record_challenge(b.get("verdict") or "", Path(b.get("path") or "").stem,
                         b.get("challenger") or "Sergeant Voss")
        if (b.get("verdict") or "").lower() in ("revised", "retired"):
            from agora.execution.graveyard import bury
            bury(Path(b.get("path") or "").stem, b.get("reason") or "challenge succeeded",
                 b.get("resurrect_when") or "", b.get("challenger") or "Sergeant Voss")
    return res


@router.get("/brain/bounty")
async def brain_bounty():
    """THE BOUNTY LEDGER — kill-authority per challenger (science pays for kills)."""
    from agora.execution.bounty import format_bounty, scores
    return {"status": "ok", "report": format_bounty(), "scores": scores()}


@router.get("/brain/analogy-inputs")
async def brain_analogy_inputs():
    """ANALOGY FORGE — the vault's most mechanism-dense un-forged concept note."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.analogy_forge import pick_mechanism
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", "mechanism": await _aio.to_thread(pick_mechanism, vault)}


@router.post("/brain/analogy-record")
async def brain_analogy_record(request: Request):
    """Ledger one forging (mechanism → target domain) so the forge rotates, never repeats.
    A dead forging is buried with its cause — also data."""
    from agora.execution.analogy_forge import record_forged
    b = await request.json()
    outcome = b.get("outcome") or ""
    if "no viable mapping" in outcome.lower():
        from agora.execution.graveyard import bury
        bury(f"analogy: {b.get('mechanism', '')} -> {b.get('target', '')}", outcome,
             "a structural (not surface) correspondence is actually demonstrated", "Sage Mira")
    return {"status": "ok", **record_forged(b.get("mechanism") or "", b.get("target") or "",
                                            b.get("note") or "", outcome)}


@router.post("/brain/graveyard/bury")
async def brain_graveyard_bury(request: Request):
    """THE GRAVEYARD — bury a dead idea with its cause of death + resurrection condition."""
    from agora.execution.graveyard import bury
    b = await request.json()
    g = bury(b.get("claim") or "", b.get("cause") or "", b.get("resurrect_when") or "",
             b.get("killed_by") or "")
    return {"status": "ok" if g else "duplicate_or_short", "grave": g}


@router.post("/brain/graveyard/resurrect")
async def brain_graveyard_resurrect(request: Request):
    """Deliberate resurrection — new evidence overturned a recorded death."""
    from agora.execution.graveyard import resurrect
    b = await request.json()
    g = resurrect(b.get("id") or "", b.get("reason") or "")
    return {"status": "ok" if g else "no_such_grave", "grave": g}


@router.get("/brain/graveyard")
async def brain_graveyard():
    from agora.execution.graveyard import format_graveyard, epitaphs, _load
    return {"status": "ok", "report": format_graveyard(), "epitaphs": epitaphs(),
            "items": _load()[-15:]}


@router.get("/brain/replication-target")
async def brain_replication_target(request: Request):
    """THE REPLICATION UNIT — the next sourced claim awaiting a minimal computational re-run."""
    from agora.execution.replication import pick_target
    return {"status": "ok", "target": await pick_target(request.app.state.db)}


@router.post("/brain/replication-record")
async def brain_replication_record(request: Request):
    """Ledger one replication attempt: REPRODUCED | FAILED | NOT_COMPUTABLE."""
    from agora.execution.replication import record
    b = await request.json()
    r = record(b.get("claim") or "", b.get("source") or "", b.get("outcome") or "",
               b.get("lab_id") or "", b.get("note") or "",
               by_construction_checked=bool(b.get("by_construction_checked")))
    gated = bool(r and r.get("auto_gated"))
    return {"status": "ok" if r else "invalid", "record": r,
            "gated": gated,
            "note": ("Auto-gated to NOT_COMPUTABLE: this REPRODUCED read as by-construction. If it is a "
                     "genuine replication on independent/real data, re-POST with by_construction_checked=true."
                     if gated else None)}


@router.get("/brain/replications")
async def brain_replications():
    from agora.execution.replication import format_replications, _load
    return {"status": "ok", "report": format_replications(), "items": _load()[-12:]}


@router.get("/brain/frontier-seed")
async def brain_frontier_seed():
    """THE FRONTIER — an under-explored vault target (thin domain or structural hole) to aim
    research at the EDGE, breaking the agents' churn on dense clusters."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.frontier import frontier_target, record_seeded
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    t = await _aio.to_thread(frontier_target, vault)
    if t:
        record_seeded(t["target"], t.get("kind", ""))
    return {"status": "ok", "target": t}


@router.get("/brain/frontier")
async def brain_frontier():
    from agora.execution.frontier import format_frontier, _load
    return {"status": "ok", "report": format_frontier(), "items": _load()[-12:]}


@router.get("/brain/cartography-hole")
async def brain_cartography_hole():
    """THE CARTOGRAPHER — the widest un-charted structural hole between vault domains."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.cartography import find_hole
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", "hole": await _aio.to_thread(find_hole, vault)}


@router.post("/brain/cartography-record")
async def brain_cartography_record(request: Request):
    """Ledger one charted hole (and its bridge note, when one was honestly possible)."""
    from agora.execution.cartography import record_charted
    b = await request.json()
    return {"status": "ok", **record_charted(b.get("a") or "", b.get("b") or "",
                                             int(b.get("bridges_then") or 0),
                                             b.get("note") or "", b.get("outcome") or "")}


@router.post("/brain/academy/tick")
async def brain_academy_tick():
    """THE ACADEMY — enroll the weakest verifier with the strongest mentor, or measure the
    active mentee for graduation (+0.10 verification-rate on >=4 new attempts)."""
    from agora.execution.academy import tick
    return {"status": "ok", **tick()}


@router.get("/brain/academy")
async def brain_academy(agent: str = ""):
    """The academy report; with ?agent= returns that agent's active mentor lesson (or '')."""
    from agora.execution.academy import format_academy, lesson_for, _load
    out = {"status": "ok", "report": format_academy(), "items": _load()[-8:]}
    if agent:
        out["lesson"] = lesson_for(agent)
    return out


@router.get("/brain/portfolio")
async def brain_portfolio():
    """THE PORTFOLIO — Agora's public scientific track record (preview + credibility gate)."""
    import asyncio as _aio
    from agora.execution.portfolio import format_portfolio, record
    return {"status": "ok", "report": await _aio.to_thread(format_portfolio),
            **await _aio.to_thread(record)}


@router.post("/brain/portfolio/propose")
async def brain_portfolio_propose(request: Request):
    """Compose the track record; if credible, propose the GATED publish (owner approves)."""
    import asyncio as _aio
    from agora.execution.portfolio import compose
    from agora.execution.hands import propose_action, pending_approvals
    r = await _aio.to_thread(compose)
    if not r.get("credible"):
        return {"status": "too_thin", "resolved_total": r["resolved_total"]}
    if any(x.get("kind") == "portfolio" for x in pending_approvals()):
        return {"status": "already_pending"}
    act = propose_action("portfolio", "Publish public track record",
                         f"{r['resolved_total']} resolved accountability items", {})
    await _send_telegram(f"📊 Track-record proposal `{act['id']}`: publish the public scientific "
                         f"track record ({r['resolved_total']} resolved items).\n"
                         f"Reply `approve {act['id']}` or `reject {act['id']}`.")
    return {"status": "proposed", "action": act}


@router.get("/brain/scout-target")
async def brain_scout_target():
    """THE OPPORTUNITY SCOUT — the best-fit open GitHub issue Agora's vault could answer."""
    import asyncio as _aio
    from agora.execution.scout import find_opportunity
    return {"status": "ok", "target": await _aio.to_thread(find_opportunity)}


@router.post("/brain/scout-record")
async def brain_scout_record(request: Request):
    """Ledger a contacted issue so the Scout never pitches the same one twice."""
    from agora.execution.scout import record_contacted
    b = await request.json()
    r = record_contacted(b.get("url") or "", b.get("repo") or "", int(b.get("issue") or 0),
                         b.get("outcome") or "drafted")
    return {"status": "ok" if r else "duplicate", "record": r}


@router.get("/brain/contribute/shortlist")
async def brain_contribute_shortlist(limit: int = 25):
    """WHERE WE CAN ACTUALLY HELP — the external library filtered down to threads where something we
    have SHIPPED answers what is being asked, ranked by liveness and fit.

    Conservative on purpose: a thread has to be about memory at all before any offer of ours counts,
    and the offer has to point at working code rather than an intention. A bad pitch in a busy thread
    costs more than silence.
    """
    import asyncio as _aio
    from agora.execution.contribution_finder import find
    return {"status": "ok", **await _aio.to_thread(find, limit)}


@router.post("/brain/library/external/harvest")
async def brain_external_harvest(request: Request):
    """Pull the next slice of the query bank from GitHub + Reddit into the external library."""
    import asyncio as _aio
    from agora.execution.external_library import harvest
    b = await request.json() if await request.body() else {}
    return {"status": "ok", **await _aio.to_thread(harvest, int(b.get("batch", 6)))}


@router.get("/brain/library/external/search")
async def brain_external_search(q: str, k: int = 12):
    """Dig into what the outside world has said — the reason the library is kept, not just reported."""
    import asyncio as _aio
    from agora.execution.external_library import search
    return {"status": "ok", "query": q, "hits": await _aio.to_thread(search, q, k)}


@router.get("/brain/library/external/map")
async def brain_external_map():
    """THE CARTOGRAPHER'S MAP, redrawn on the outside world.

    Wren's old objective — the two vault domains with the fewest bridges — guaranteed an off-mission
    answer, because in a vault of physics and category theory the widest hole is always between two
    things unrelated to agent memory. Same instinct, honest map: which needs recur across how many
    UNRELATED projects, and which ones nobody answers. A hole here is a market gap.
    """
    import asyncio as _aio
    from agora.execution.external_library import map_external, stats
    m = await _aio.to_thread(map_external)
    return {"status": "ok", "stats": await _aio.to_thread(stats), **m}


@router.get("/brain/watch/competitors")
async def brain_watch_competitors():
    """EYES OUTSIDE THE POT — what the competition actually shipped since the last check.

    Every other intake this system has is the vault (what we already thought) or arXiv (what academics
    publish). Neither would tell us that a competitor shipped a revert command last week, which is the
    news that would make three of our public claims false while we kept repeating them. Reports DELTAS
    only, and flags loudly when a release touches our own axis (correction, revert, erasure,
    provenance, determinism).
    """
    import asyncio as _aio
    import subprocess
    from agora.execution.competitor_watch import format_report, scan
    try:
        tok = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                             timeout=10).stdout.strip()
    except Exception:
        tok = ""
    res = await _aio.to_thread(scan, tok)
    return {"status": "ok", "report": format_report(res), **res}


@router.get("/brain/scout/box")
async def brain_scout_box():
    """THE SCOUT BOX — leads collected but not yet triaged, capped so it cannot grow into a landfill.

    Discovery is cheap and perishable; triage is the scarce thing. The scan fills this and never waits
    for the inbox to clear (it used to skip entirely while one outreach task sat pending, which read as
    a dead scanner for 23h). `contribute` = an issue we could answer with evidence; `learn` = a merged
    PR in our problem space worth reading.
    """
    from agora.execution.scout import box_load, box_stats
    items = box_load()
    return {"status": "ok", "stats": box_stats(),
            "open": [x for x in items if x.get("status") == "open"][-40:]}


@router.post("/brain/scout/box/add")
async def brain_scout_box_add(request: Request):
    """Scan once and file what it finds. Returns added=null when the lead is a duplicate or the box is
    full — full is reported, never silently overwritten, because a dropped lead is indistinguishable
    from one that was never found."""
    import asyncio as _aio
    from agora.execution.scout import box_add, box_stats, find_learning, find_opportunity
    b = await request.json() if await request.body() else {}
    kind = (b.get("kind") or "contribute").strip()
    finder = find_learning if kind == "learn" else find_opportunity
    lead = await _aio.to_thread(finder)
    if not lead or lead.get("error"):
        return {"status": "ok", "added": None, "reason": (lead or {}).get("error") or "nothing found",
                "stats": box_stats()}
    return {"status": "ok", "added": box_add(lead, kind=kind), "stats": box_stats()}


@router.post("/brain/scout/box/mark")
async def brain_scout_box_mark(request: Request):
    """Close a lead: done | no_fit | dropped."""
    from agora.execution.scout import box_mark, box_stats
    b = await request.json()
    ok = box_mark(b.get("url") or "", b.get("status") or "done")
    return {"status": "ok" if ok else "not_found", "stats": box_stats()}


@router.get("/brain/scout/box/take")
async def brain_scout_box_take(kind: str = "contribute", n: int = 1):
    """Hand out the top `n` open leads for triage, highest score first.

    Batched on purpose: judging "does our vault actually answer this?" takes seconds per lead and most
    answers are no. Promoting one lead per cycle capped throughput at ~10/day and made the whole box
    pointless; promoting them as separate inbox tasks would flood the inbox instead. One task carrying
    several leads is the shape that matches the work.
    """
    from agora.execution.scout import box_stats, box_take
    leads = [x for x in (box_take(kind) for _ in range(max(1, min(int(n), 10)))) if x]
    return {"status": "ok", "leads": leads, "lead": leads[0] if leads else None,
            "stats": box_stats()}


@router.get("/brain/scout")
async def brain_scout():
    from agora.execution.scout import format_scout, _load
    return {"status": "ok", "report": format_scout(), "items": _load()[-12:]}


@router.get("/brain/scout/status")
async def brain_scout_status():
    """VISIBILITY for the GitHub Opportunity Scout: what was DISCOVERED, what was TRIAGED, and the
    live candidate. The scan runs autonomously from the dungeon (~2.4h); this is the read-only
    surface so the owner can SEE it without typing /scout.

    THE TWO ARE NOT THE SAME NUMBER, and reporting one of them as both hid a six-day stall. This
    endpoint derived `last_scan` from the OUTCOME ledger, which is written by triage — so when
    triage stopped and discovery kept running, it read "last scan 2026-07-21", the digest announced
    an idle scanner, and its advice was to check a supervisor that is not even the mechanism in use.
    Discovery was fine the whole time: 7 leads in the box, the oldest 2.2 days old. Both timestamps
    are reported now, and the blocked stage is named.
    """
    import asyncio as _aio
    from datetime import datetime, timezone
    from agora.execution.scout import _load, _STORE, find_opportunity, _THEMES, box_load, box_stats
    import time as _t
    items = _load()
    # last-scan time: newest recorded item ts, falling back to the ledger file's mtime (the file is
    # rewritten on every recorded outcome, so mtime ~= last recorded scan even on a no-fit cycle).
    last_ts = max((x.get("ts", 0) for x in items), default=0.0)
    try:
        file_mtime = _STORE.stat().st_mtime
    except Exception:
        file_mtime = 0.0
    last_scan = max(last_ts, file_mtime)

    def _iso(ts: float) -> str:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else ""

    def _bucket(o: str) -> str:
        return "no_fit" if "no real fit" in (o or "").lower() else "drafted"
    outcomes = {"drafted": 0, "no_fit": 0}
    for x in items:
        outcomes[_bucket(x.get("outcome", ""))] += 1
    recent = [{"repo": x.get("repo", ""), "issue": x.get("issue", 0),
               "outcome": x.get("outcome", ""), "url": x.get("url", ""),
               "ts": x.get("ts", 0), "iso": _iso(x.get("ts", 0))} for x in items[-12:][::-1]]
    cur_theme = _THEMES[int(_t.time() // 3600) % len(_THEMES)]
    try:
        target = await _aio.to_thread(find_opportunity)
    except Exception as e:
        target = {"error": str(e)[:120]}
    # DISCOVERY, measured where discovery actually lands: the box. `last_scan*` keeps its old name and
    # old meaning for existing callers, but it is TRIAGE time and is now labelled as such beside it.
    try:
        bstats = box_stats()
        # `found_ts`, not `ts` -- the box records when a lead was FOUND, the outcome ledger records
        # when one was judged. Reading the wrong key returned 0 for every lead, so the freshness
        # number came back empty and the discovery_stalled branch could never fire: a second
        # can't-fail check inside the fix for the first one. Verified against a real box record.
        last_disc = max((x.get("found_ts") or x.get("ts") or 0 for x in box_load()), default=0.0)
    except Exception:
        bstats, last_disc = {}, 0.0
    hrs = lambda ts: round((_t.time() - ts) / 3600.0, 1) if ts else None    # noqa: E731
    stage = "ok"
    if bstats.get("open") and (hrs(last_scan) or 0) > 24:
        stage = "triage_blocked"          # discovery is filling the box; nobody is draining it
    elif (hrs(last_disc) or 999) > 6:
        stage = "discovery_stalled"       # the dungeon is not scanning — THAT is a process problem
    return {"status": "ok", "scanned_count": len(items),
            "last_scan_unix": last_scan, "last_scan_iso": _iso(last_scan),
            "last_triage_unix": last_scan, "last_triage_iso": _iso(last_scan),
            "hours_since_triage": hrs(last_scan),
            "last_discovery_iso": _iso(last_disc), "hours_since_discovery": hrs(last_disc),
            "box": bstats, "stage": stage,
            "outcomes": outcomes, "current_theme": cur_theme,
            "current_target": target, "recent": recent}


@router.get("/brain/agent-activity")
async def brain_agent_activity(n: int = 8):
    """Recent agent-attributed work across all organ ledgers — for the dungeon build log so every
    agent's real output is visible, not just the vault-graph curator."""
    import asyncio as _aio
    from agora.execution.agent_activity import recent
    return {"status": "ok", "events": await _aio.to_thread(recent, n)}


@router.get("/brain/envoy")
async def brain_envoy():
    """THE ENVOY — current outward engagement on every posted thread (read-only)."""
    import asyncio as _aio
    from agora.execution.envoy import format_envoy, engagement_status
    status = await _aio.to_thread(engagement_status)
    return {"status": "ok", "report": await _aio.to_thread(format_envoy), "threads": status}


@router.post("/brain/envoy/sweep")
async def brain_envoy_sweep():
    """One Envoy pass: harvest new replies + engagement, return only events new since last sweep."""
    import asyncio as _aio
    from agora.execution.envoy import sweep
    return {"status": "ok", **await _aio.to_thread(sweep)}


@router.post("/brain/press/draft")
async def brain_press_draft(request: Request):
    """THE PRESS — store Claude's polished piece and propose the GATED publish action.
    Nothing reaches public/posts/ until the owner approves from Telegram."""
    from agora.execution.press import save_piece
    from agora.execution.hands import propose_action, pending_approvals
    b = await request.json()
    title, body = (b.get("title") or "").strip(), (b.get("body") or "").strip()
    if len(title) < 10 or len(body) < 300:
        return {"status": "too_short"}
    if any(x.get("kind") == "press" for x in pending_approvals()):
        return {"status": "already_pending"}
    rec = save_piece(title, body, b.get("source") or "",
                     body_sk=(b.get("body_sk") or "").strip(),
                     desc=(b.get("desc") or "").strip(),
                     desc_sk=(b.get("desc_sk") or "").strip(),
                     title_sk=(b.get("title_sk") or "").strip())
    act = propose_action("press", f"Publish press piece: {title[:60]}",
                         body[:300], {"press_id": rec["id"]})
    await _send_telegram(f"📰 Press proposal `{act['id']}`: standalone public post\n"
                         f"*{title[:80]}*\n_{body[:180]}…_\n"
                         f"Reply `approve {act['id']}` or `reject {act['id']}`.")
    return {"status": "proposed", "piece": rec, "action": act}


@router.get("/brain/press-target")
async def brain_press_target():
    """The strongest unpublished artifact awaiting a press draft."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.press import pick_target
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", "target": await _aio.to_thread(pick_target, vault)}


@router.get("/brain/press")
async def brain_press():
    from agora.execution.press import format_press, _load
    return {"status": "ok", "report": format_press(), "items": _load()[-10:]}


@router.get("/brain/distribution/inputs")
async def brain_distribution_inputs(n: int = 6):
    """THE DISTRIBUTION DESK — our strongest public posts matched to venues where the
    audience already gathers. Raw material for Claude to draft a venue-tailored share."""
    import asyncio as _aio
    from agora.execution.distribution import distribution_inputs
    return await _aio.to_thread(distribution_inputs, n)


@router.post("/brain/distribution/draft")
async def brain_distribution_draft(request: Request):
    """Store Claude's venue-tailored share and propose the GATED post. Nothing leaves the
    machine: on approval the owner gets a prefilled submit URL for the final one click."""
    from agora.execution.distribution import draft_distribution
    b = await request.json()
    slug = (b.get("slug") or "").strip()
    venue = (b.get("venue") or "").strip()
    title = (b.get("title") or "").strip()
    pitch = (b.get("pitch") or "").strip()
    if not slug or not venue or len(pitch) < 20:
        return {"status": "too_short"}
    rec = draft_distribution(slug, venue, title, pitch,
                             url=(b.get("url") or "").strip(), body=(b.get("body") or "").strip())
    if rec.get("error"):
        return {"status": "error", "error": rec["error"]}
    await _send_telegram(f"📣 Distribution proposal `{rec['id']}`: share to *{rec['payload']['venue_name']}*\n"
                         f"*{title[:80]}*\n_{pitch[:160]}…_\n"
                         f"Reply `approve {rec['id']}` or `reject {rec['id']}`.")
    return {"status": "proposed", "action": rec}


@router.get("/brain/roadmap-inputs")
async def brain_roadmap_inputs():
    """THE ROADMAP — Aldric's organ instrument panel for a data-backed next-move synthesis."""
    import asyncio as _aio
    from agora.execution.roadmap import gather, format_roadmap
    g = await _aio.to_thread(gather)
    return {"status": "ok", "report": await _aio.to_thread(format_roadmap), **g}


@router.get("/brain/synthesis-signals")
async def brain_synthesis_signals():
    """THE SYNTHESIS DETECTOR — phase-transition precursors on Agora's own knowledge dynamics."""
    from agora.execution.synthesis_detector import signals, format_synthesis
    return {"status": "ok", "report": format_synthesis(), **signals()}


@router.get("/brain/cartography")
async def brain_cartography():
    """The map ledger — with the Cartographer's yield refreshed (charted holes since bridged)."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.cartography import format_cartography, measure_yield
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    items = await _aio.to_thread(measure_yield, vault)
    return {"status": "ok", "report": format_cartography(), "items": items[-12:]}


@router.get("/brain/analogies")
async def brain_analogies():
    from agora.execution.analogy_forge import format_analogies, _load
    return {"status": "ok", "report": format_analogies(), "items": _load()[-10:]}


@router.get("/brain/beliefs")
async def brain_beliefs():
    from agora.config import settings
    from agora.execution.belief_revision import format_beliefs, list_beliefs
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", "report": format_beliefs(vault), "beliefs": list_beliefs(vault)}


@router.post("/brain/campaign/start")
async def brain_campaign_start(request: Request):
    """CAMPAIGNS — open a multi-day research campaign: decompose the goal, register the
    sub-questions as standing priorities, harvest findings over days."""
    from agora.execution.campaigns import start_campaign
    b = await request.json()
    q = (b.get("question") or "").strip()
    if not q:
        return {"status": "empty"}
    return {"status": "ok", "campaign": await start_campaign(q, int(b.get("horizon_days", 5)))}


@router.post("/brain/campaign/tick")
async def brain_campaign_tick(request: Request):
    """One harvest pass — update per-sub-question coverage for EVERY running campaign
    (or a single one when an id is given). Campaigns advance in parallel."""
    from agora.execution.campaigns import harvest_tick, list_campaigns
    b = await request.json()
    ids = [b["id"]] if b.get("id") else \
        [c["id"] for c in list_campaigns() if c["status"] == "running"]
    if not ids:
        return {"status": "none_running"}
    results = [await harvest_tick(cid, request.app.state.db) for cid in ids]
    return {"status": "ok", "results": results, **results[0]}


@router.get("/brain/campaign/dossier-inputs")
async def brain_campaign_dossier_inputs(id: str):
    """The evidence for a campaign's final dossier (per sub-question literature + coverage)."""
    from agora.execution.campaigns import gather_dossier_inputs
    return {"status": "ok", **await gather_dossier_inputs(id)}


@router.post("/brain/campaign/complete")
async def brain_campaign_complete(request: Request):
    """Mark a campaign complete (dossier written)."""
    from agora.execution.campaigns import mark_complete
    b = await request.json()
    mark_complete(b.get("id") or "", b.get("dossier") or "")
    return {"status": "ok"}


@router.get("/brain/campaigns")
async def brain_campaigns():
    from agora.execution.campaigns import format_campaigns, list_campaigns
    return {"status": "ok", "report": format_campaigns(), "campaigns": list_campaigns()}


@router.get("/brain/library-inputs")
async def brain_library_inputs(q: str = ""):
    """THE LIBRARY — one unread paper's full text (ar5iv) for Claude to digest into a
    structured paper note (claims, evidence strength, limitations, links to the vault)."""
    from agora.execution.library import gather_paper_inputs
    return {"status": "ok", **await gather_paper_inputs(q)}


@router.get("/brain/recall")
async def brain_recall(q: str, k: int = 6, fmt: str = "json"):
    """RECALL — Agora's curated, value-ranked, connected memory for external agents (a memory
    provider primitive: Hermes / any MCP client queries the librarian's best notes)."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.recall import recall, format_recall
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    d = await _aio.to_thread(recall, q, vault, max(1, min(12, k)))
    if fmt == "text":
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(format_recall(d))
    return {"status": "ok", **d}


@router.post("/brain/library/queue")
async def brain_library_queue(request: Request):
    """Add curated arXiv IDs to the Library's priority reading list."""
    from agora.execution.library import queue_reading
    b = await request.json()
    return {"status": "ok", **queue_reading(b.get("arxiv_ids") or [], b.get("source") or "")}


@router.post("/brain/frontier/harvest")
async def brain_frontier_harvest(per_topic: int = 5):
    """FRONTIER HARVEST — pull fresh arXiv papers in the standing-frontier domains and stock the
    reading list, so the OS always has new external material to digest (unbounded, on-frontier)."""
    import asyncio as _aio
    from agora.execution.frontier_harvest import harvest
    return {"status": "ok", **await _aio.to_thread(harvest, per_topic)}


@router.post("/brain/library-record")
async def brain_library_record(request: Request):
    """Mark a paper read in the bibliography ledger."""
    from agora.execution.library import record_paper
    b = await request.json()
    return {"status": "ok", "record": record_paper(
        b.get("arxiv_id", ""), b.get("title", ""), b.get("url", ""), b.get("note", ""))}


@router.get("/brain/library")
async def brain_library():
    from agora.execution.library import format_library, _load
    return {"status": "ok", "report": format_library(), "papers": _load()[-12:]}


@router.get("/brain/experiments")
async def brain_experiments():
    """CAUSAL SELF-EXPERIMENTS — variant arms, sample sizes, means, decided winners."""
    from agora.execution.experiments import _load, format_experiments
    return {"status": "ok", "experiments": _load(), "report": format_experiments()}


@router.post("/brain/interview/ask")
async def brain_interview_ask(request: Request):
    """THE INTERVIEW — compose today's one highest-value question and ask the owner on
    Telegram. Skips if an unanswered question is still fresh (no nagging)."""
    import time as _t
    from agora.config import settings
    from agora.execution.interview import compose_question, open_question
    oq = open_question()
    if oq and _t.time() - oq.get("ts", 0) < 3 * 86400:
        return {"status": "already_open", "question": oq}
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    rec = await compose_question(vault)
    await _send_telegram(f"💬 Agora asks ({rec['why']}):\n\n{rec['question']}\n\n"
                         f"_reply:_ `answer <your answer>`")
    return {"status": "asked", "question": rec}


@router.post("/brain/interview/answer")
async def brain_interview_answer(request: Request):
    """Record the owner's answer and persist it as a first-class vault note — owner knowledge
    flows back into the system (user model, semantic search, future syntheses)."""
    from agora.execution.interview import record_answer
    b = await request.json()
    rec = record_answer(b.get("text") or "")
    if not rec:
        return {"status": "no_open_question"}
    writer = getattr(request.app.state, "vault_writer", None)
    path = None
    if writer:
        try:
            path = await writer.write_note(
                title=f"Interview: {rec['question'][:64]}",
                content=(f"## Question (Agora)\n{rec['question']}\n\n## Answer (Rasto)\n"
                         f"{rec['answer']}\n\n_Asked because: {rec.get('why', '')}_"),
                tags=["agora", "interview", "owner-knowledge"], agent_name="Agora")
        except Exception:
            pass
    return {"status": "answered", "question": rec, "note": path}


@router.get("/brain/interview")
async def brain_interview():
    from agora.execution.interview import format_interview, _load
    return {"status": "ok", "report": format_interview(), "items": _load()[-10:]}


@router.post("/brain/vitals/snapshot")
async def brain_vitals_snapshot(request: Request):
    """THE OBSERVATORY — take one vital-signs reading (dead-weight, link density, flywheel
    latency, exam, hit-rate, findings). Agora's own falsifiers demanded this ledger."""
    from agora.config import settings
    from agora.execution.observatory import take_snapshot
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", "snapshot": await take_snapshot(request.app.state.db, vault)}


@router.get("/brain/vitals")
async def brain_vitals(n: int = 12):
    """The vital-signs time series + a formatted report."""
    from agora.execution.observatory import series, format_vitals
    return {"status": "ok", "series": series(n), "report": format_vitals()}


@router.get("/brain/hypothesis-inputs")
async def brain_hypothesis_inputs(request: Request):
    """HYPOTHESIS INDUCTION — one coherent cross-agent cluster of recent findings, as raw
    material for Claude to unify into a falsifiable hypothesis (whose falsifier the flywheel
    auto-registers, so the agents then test it)."""
    from agora.execution.hypothesis_induction import gather_hypothesis_inputs
    return {"status": "ok", **await gather_hypothesis_inputs(request.app.state.db)}


@router.post("/brain/hypothesize/run")
async def brain_hypothesize_run(request: Request):
    """Fire the hypothesis trigger once on demand: bridge a ripe cross-domain finding cluster into a
    tested, RECORDED hypothesis (knowledge_type='hypothesis') with its falsifier registered for the
    agents to test. Same path the ~6h hypothesis_loop runs autonomously."""
    from agora.config import settings
    from agora.execution.hypothesis_induction import synthesize_and_record_hypothesis
    return {"status": "ok", **await synthesize_and_record_hypothesis(request.app.state.db,
                                                                     settings.vault_path)}


@router.get("/brain/ideation/inputs")
async def brain_ideation_inputs(request: Request):
    """THE IDEA FORGE — the brain's WHOLE rigorous cross-section (canon, beliefs, lessons,
    reproduced+failed replications, analogies, theory, synthesis precursors, frontier, what the
    Library read, freshest findings) as raw material for Claude to generate GROUNDBREAKING ideas
    across four standing targets (OS, Agora, MCP memory, real-world product). Agora gathers."""
    from agora.config import settings
    from agora.execution.ideation import gather_ideation_inputs
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await gather_ideation_inputs(request.app.state.db, vault)}


@router.post("/brain/ideation/record")
async def brain_ideation_record(request: Request):
    """Append one generated idea to the forge ledger (dedup substrate + public trail)."""
    from agora.execution.ideation import record_idea
    b = await request.json()
    if not (b.get("title") and b.get("target")):
        return {"status": "empty"}
    return {"status": "ok", **record_idea(
        b.get("title", ""), b.get("target", ""), b.get("mechanism", ""), b.get("test", ""),
        b.get("first_step", ""), b.get("grounding", ""), b.get("note", ""))}


@router.get("/brain/ideation")
async def brain_ideation():
    """The Idea Forge ledger — recent groundbreaking ideas the forge generated."""
    from agora.execution.ideation import format_ideas, _load
    return {"status": "ok", "report": format_ideas(12), "items": _load()[-15:]}


@router.get("/brain/exaptation/supply")
async def brain_exaptation_supply():
    """THE EXAPTATION SCANNER (outward turn) — the SUPPLY side: our proven mechanisms abstracted
    to their structural invariant + ready-made world-search queries. Claude takes these OUT to the
    live world (forums/Reddit/HN/YouTube) to harvest matching real unmet need."""
    from agora.execution.exaptation import supply_registry
    return {"status": "ok", **supply_registry()}


@router.post("/brain/exaptation/record")
async def brain_exaptation_record(request: Request):
    """Record one discovered DEMAND->SUPPLY match (discovery only — NOT outreach; any outreach
    still goes through the gated correspondent/draft flow)."""
    from agora.execution.exaptation import record_match
    b = await request.json()
    if not b.get("mechanism_id") or not b.get("pain_title"):
        return {"status": "empty"}
    return {"status": "ok", **record_match(
        b.get("mechanism_id", ""), b.get("pain_title", ""), b.get("url", ""),
        b.get("community", ""), b.get("score", 0), b.get("note", ""))}


@router.get("/brain/exaptation")
async def brain_exaptation():
    """The Exaptation Scanner ledger — real-world pain matched to our proven mechanisms."""
    from agora.execution.exaptation import format_pipeline, _load
    return {"status": "ok", "report": format_pipeline(15), "items": _load()[-20:]}


@router.post("/brain/exchange/propose")
async def brain_exchange_propose(request: Request):
    """RESEARCH EXCHANGE — compose the public digest (preview on disk) and propose publishing
    it as a GATED action. Nothing leaves the machine until Rasto approves from Telegram."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.research_exchange import compose_digest, PUBLIC_URL
    from agora.execution.hands import propose_action, pending_approvals
    if any(x.get("kind") == "publish" for x in pending_approvals()):
        return {"status": "already_pending"}
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    d = await _aio.to_thread(compose_digest, vault)
    if not d.get("insights"):
        return {"status": "nothing_to_publish"}
    rec = propose_action(
        "publish", f"Publish the research digest ({d['insights']} insights) to the public repo",
        f"Composed at {d['path']} ({d['chars']} bytes) → {PUBLIC_URL}", {})
    await _send_telegram(
        f"📡 Research Exchange proposal `{rec['id']}`: publish {d['insights']} insights as a "
        f"public digest.\nPreview: {d['path']}\nTarget: {PUBLIC_URL}\n"
        f"Reply `approve {rec['id']}` or `reject {rec['id']}`.")
    return {"status": "proposed", "action": rec, **d}


@router.post("/brain/memory-economy/propose")
async def brain_memory_economy_propose(request: Request):
    """Propose archiving the current dead weight as a GATED curate action (runs only after
    Rasto approves from Telegram; notes are quarantined reversibly, never deleted)."""
    import asyncio as _aio
    from agora.config import settings
    from agora.execution.memory_economy import prune_candidates
    from agora.execution.hands import propose_action, pending_approvals
    b = await request.json()
    if any(x.get("kind") == "curate" for x in pending_approvals()):
        return {"status": "already_pending"}
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    cands = await _aio.to_thread(prune_candidates, vault, int(b.get("n", 12)))
    if not cands:
        return {"status": "nothing_to_prune"}
    titles = ", ".join(c["title"][:30] for c in cands[:5])
    rec = propose_action(
        "curate", f"Archive {len(cands)} dead-weight notes (quarantine, reversible)",
        f"Old, unlinked, never-retrieved stubs: {titles}…",
        {"paths": [c["path"] for c in cands]})
    await _send_telegram(
        f"🏛 Memory Economy proposal `{rec['id']}`: archive {len(cands)} dead-weight notes "
        f"(old+unlinked+unretrieved stubs) to quarantine (reversible).\n"
        f"e.g. {titles}\nReply `approve {rec['id']}` or `reject {rec['id']}`.")
    return {"status": "proposed", "action": rec, "candidates": len(cands)}


@router.get("/brain/flywheel/questions")
async def brain_flywheel_questions(n: int = 8):
    """COMPOUNDING FLYWHEEL — the open research questions Agora derived from its own insights'
    falsifiers (its claims' weak points), which the agents go investigate so knowledge deepens."""
    from agora.execution.flywheel import open_questions, stats
    return {"status": "ok", "open": open_questions(n), "stats": stats()}


@router.post("/brain/flywheel/mark-deepened")
async def brain_flywheel_mark_deepened(request: Request):
    """Close the flywheel turn: Claude marks a question deepened after shipping the sharper v2.
    Without this the question stays open forever and gets re-queued infinitely."""
    from agora.execution.flywheel import mark_deepened, stats
    body = await request.json()
    mark_deepened((body.get("id") or "").strip())
    return {"status": "ok", **stats()}


@router.get("/brain/flywheel/deepen-inputs")
async def brain_flywheel_deepen_inputs(title: str, falsifier: str = ""):
    """Test an insight's falsifier against fresh research + reality — the evidence Claude uses to
    DEEPEN the insight (the second half of the flywheel: outputs come back as sharper outputs)."""
    from agora.config import settings
    from agora.execution.flywheel import gather_deepening_inputs
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await gather_deepening_inputs(title, falsifier, vault)}


@router.get("/brain/socratic")
async def brain_socratic(q: str):
    """SOCRATIC AGORA — the vault as a tutor: probing questions drawn from the learner's own notes
    that test depth, expose assumptions, and reveal the frontier of what they don't yet know."""
    from agora.config import settings
    from agora.execution.socratic import socratic_questions
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await socratic_questions(q, vault)}


@router.get("/brain/learn-next")
async def brain_learn_next():
    """The single highest-value thing to learn next, from the vault's real gaps."""
    from agora.config import settings
    from agora.execution.socratic import what_to_learn_next
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await what_to_learn_next(vault)}


@router.get("/brain/action-inputs")
async def brain_action_inputs(q: str, kind: str = "brief"):
    """ACTION ENGINE — gather grounded material (vault notes + Agora's insights) on a theme so Claude
    can DRAFT a usable artifact of the requested kind (brief / essay / plan / spec). Knowledge → leverage."""
    from agora.config import settings
    from agora.execution.action_engine import gather_action_inputs
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await gather_action_inputs(q, kind, vault)}


@router.get("/brain/dialectic")
async def brain_dialectic(q: str):
    """DIALECTIC ENGINE — thesis → antithesis → synthesis on a claim. Truth through opposition."""
    from agora.config import settings
    from agora.execution.dialectic import run_dialectic
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await run_dialectic(q, vault)}


@router.get("/brain/dialectic-inputs")
async def brain_dialectic_inputs(q: str):
    """Gather vault + literature on a claim so CLAUDE produces the dialectic (quality, not flash)."""
    from agora.config import settings
    from agora.execution.dialectic import gather_dialectic_inputs
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await gather_dialectic_inputs(q, vault)}


@router.get("/brain/predict-baseline")
async def brain_predict_baseline(q: str):
    """Current real-world metrics for a theme so CLAUDE makes the reasoned prediction (quality)."""
    from agora.execution.prediction_ledger import gather_prediction_baseline
    from agora.execution.learning import lessons_text
    from agora.execution.board import priorities_text
    return {"status": "ok", "lessons": lessons_text(), "owner_priorities": priorities_text(),
            **await gather_prediction_baseline(q)}


@router.post("/brain/predict-record")
async def brain_predict_record(request: Request):
    """Record a CLAUDE-made prediction (reasoned, high-quality) into the ledger."""
    from agora.execution.prediction_ledger import record_prediction
    b = await request.json()
    return {"status": "ok", **record_prediction(
        b.get("theme", ""), b.get("metric", "hackernews_stories"), int(b.get("baseline", 0)),
        b.get("direction", "FLAT"), float(b.get("confidence", 0.6)), b.get("why", ""),
        int(b.get("horizon_days", 14)))}


@router.get("/brain/program/start")
async def brain_program_start(q: str):
    """RESEARCH PROGRAMS — decompose a big question into sub-questions the agents pursue (directed science)."""
    from agora.execution.research_program import start_program
    return {"status": "ok", **await start_program(q)}


@router.get("/brain/program/list")
async def brain_program_list():
    from agora.execution.research_program import programs
    return {"status": "ok", "programs": programs()}


@router.get("/brain/program/findings")
async def brain_program_findings(pid: str):
    """Gather a program's evidence for Claude to synthesize an answer to the main question."""
    from agora.config import settings
    from agora.execution.research_program import gather_program_findings
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await gather_program_findings(pid, vault)}


@router.get("/brain/user-model")
async def brain_user_model(force: bool = False):
    """PERSONAL CONTEXT MODEL — who the vault's owner is (domains / projects / style), to personalize."""
    from agora.config import settings
    from agora.execution.user_model import build_user_model
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await build_user_model(vault, force)}


@router.get("/brain/mind-inputs")
async def brain_mind_inputs():
    """THE AGORA MIND — Agora's entire current cognitive state (beliefs, predictions, tensions, gaps),
    for Claude to synthesize a coherent worldview + decide what to think about next. Metacognition."""
    from agora.config import settings
    from agora.execution.mind import gather_mind_state
    from agora.execution.learning import lessons_text
    from agora.execution.board import priorities_text
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", "lessons": lessons_text(), "owner_priorities": priorities_text(),
            **await gather_mind_state(vault)}


@router.get("/brain/worldview")
async def brain_worldview():
    """Agora's current synthesized worldview (what it believes + is uncertain about)."""
    from agora.execution.mind import get_worldview
    return {"status": "ok", "worldview": get_worldview()}


@router.post("/brain/worldview-record")
async def brain_worldview_record(request: Request):
    """Store the worldview Claude synthesized (the Agora Mind's current state)."""
    from agora.execution.mind import record_worldview
    b = await request.json()
    return {"status": "ok", "path": record_worldview(b.get("content", ""))}


@router.get("/brain/learning-inputs")
async def brain_learning_inputs():
    """THE LEARNING LOOP — the measurable outcomes of Agora's own judgments (prediction calibration,
    resolved calls, funnel/flywheel shape), for Claude to derive applied LESSONS. Agora improves itself."""
    from agora.execution.learning import gather_outcomes
    return {"status": "ok", **await gather_outcomes()}


@router.get("/brain/lessons")
async def brain_lessons():
    """The lessons Agora has learned about itself (read by future predictions / insights / reflections)."""
    from agora.execution.learning import get_lessons
    return {"status": "ok", "lessons": get_lessons()}


@router.post("/brain/lessons-record")
async def brain_lessons_record(request: Request):
    """Store the lessons Claude derived from Agora's track record."""
    from agora.execution.learning import record_lessons
    b = await request.json()
    return {"status": "ok", **record_lessons(b.get("lessons", []))}


@router.get("/brain/actions")
async def brain_actions():
    """AGORA'S HANDS — the action queue. Safe actions auto-approve; outward ones await Rasto."""
    from agora.execution.hands import list_actions, ready_to_execute, pending_approvals
    return {"status": "ok", "actions": list_actions(), "ready": ready_to_execute(),
            "awaiting_approval": pending_approvals()}


@router.post("/brain/action-propose")
async def brain_action_propose(request: Request):
    """Propose an action (safe kinds run; gated kinds wait for approval)."""
    from agora.execution.hands import propose_action
    b = await request.json()
    return {"status": "ok", **propose_action(b.get("kind", "build_tool"), b.get("title", ""),
                                             b.get("spec", ""), b.get("payload"))}


@router.post("/brain/action-decide")
async def brain_action_decide(request: Request):
    """Rasto approves or rejects a gated action."""
    from agora.execution.hands import approve_action, reject_action
    b = await request.json()
    fn = approve_action if b.get("approve") else reject_action
    r = fn(b.get("id", ""))
    return {"status": "ok", "action": r}


@router.post("/brain/action-result")
async def brain_action_result(request: Request):
    """Record the outcome of an executed action."""
    from agora.execution.hands import set_status
    b = await request.json()
    return {"status": "ok", "action": set_status(b.get("id", ""),
                                                  "done" if b.get("ok") else "failed", b.get("result", ""))}


@router.post("/brain/action-execute")
async def brain_action_execute(request: Request):
    """Carry out an approved deterministic safe action (export_insights / digest)."""
    import asyncio
    from agora.config import settings
    from agora.execution.hands import execute_action
    b = await request.json()
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return {"status": "ok", **await asyncio.to_thread(execute_action, b.get("id", ""), vault)}


@router.get("/brain/now")
async def brain_now():
    """AGORA'S SENSES — perceive the live present in the user's own domains (current discussion + fresh
    research). The vault is the past; this is the now."""
    from agora.config import settings
    from agora.execution.senses import sense_now, hottest_topic
    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    r = await sense_now(vault)
    return {"status": "ok", "hottest": hottest_topic(r), **r}


@router.get("/brain/bridges")
async def brain_bridges(n: int = 6, rationale: bool = True):
    """Pairs of the user's notes that are deeply related yet UNLINKED — missing connections.
    Turns the vault from islands into a connected graph."""
    global _SEM_INDEX
    import asyncio
    from agora.execution.semantic_index import SemanticIndex
    from agora.config import settings
    if _SEM_INDEX is None or not _SEM_INDEX.ready:
        _SEM_INDEX = SemanticIndex()
    bridges = (await asyncio.to_thread(_SEM_INDEX.find_bridges, settings.vault_path, n)
               if _SEM_INDEX.ready else [])
    if rationale and bridges:
        from agora.execution.llm_client import call_llm
        for b in bridges:
            b["why"] = (await asyncio.to_thread(
                call_llm,
                "In ONE concise sentence, why are these two note topics deeply related and worth "
                "linking? Be specific, no preamble.",
                f"Note A: {b['a']}\nNote B: {b['b']}", "cheap", 0.3, 90) or "").strip()
    return {"status": "ok", "bridges": bridges}


def _add_link(root: str, rel: str, target: str, why: str) -> int:
    from pathlib import Path
    f = Path(root) / rel
    try:
        txt = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return 0
    if f"[[{target}]]" in txt:
        return 0                                            # already linked
    marker = "## Related (Agora bridges)"
    add = f"- [[{target}]]" + (f" — {why}" if why else "")
    txt = txt.rstrip() + (f"\n{add}\n" if marker in txt else f"\n\n{marker}\n{add}\n")
    f.write_text(txt, encoding="utf-8")
    return 1


@router.post("/brain/bridges/apply")
async def apply_bridges(request: Request):
    """Apply chosen bridges — add a [[wikilink]] (with rationale) to BOTH notes so the vault
    becomes more connected. Reversible: a clearly-marked '## Related (Agora bridges)' section."""
    from agora.config import settings
    body = await request.json()
    added = 0
    for b in body.get("bridges", []):
        added += _add_link(settings.vault_path, b.get("a_path", ""), b.get("b", ""), b.get("why", ""))
        added += _add_link(settings.vault_path, b.get("b_path", ""), b.get("a", ""), b.get("why", ""))
    return {"status": "ok", "links_added": added}


async def _send_telegram(text: str) -> bool:
    """Send a message to the user via Telegram (HERMES_TELEGRAM_* env). No-op if unset."""
    import asyncio
    import json
    import os
    import subprocess
    from agora.execution.claude_inbox import feed_append
    feed_append(text)                               # so Claude Code reads the same feed the user sees
    token, chat = os.getenv("HERMES_TELEGRAM_BOT_TOKEN", ""), os.getenv("HERMES_TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        return False

    def _s():
        payload = json.dumps({"chat_id": chat, "text": text[:4000], "parse_mode": "Markdown"})
        r = subprocess.run(
            ["curl", "-s", "--max-time", "12", "-X", "POST",
             f"https://api.telegram.org/bot{token}/sendMessage",
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=15)
        return '"ok":true' in (r.stdout or "")
    return await asyncio.to_thread(_s)


@router.get("/brain/telegram-feed")
async def telegram_feed(n: int = 20):
    """The recent messages sent to the user's Telegram — so Claude Code can read what they see."""
    from agora.execution.claude_inbox import feed_recent
    return {"feed": feed_recent(n)}


_PLAN_META = ("build ", "together we", "draft ", "create a collaborative", "design and",
              "no real papers", "your vault contains no", "begin by", "we will", "let's",
              "i will", "propose to", "no paper", "the closest are", "no relevant",
              "cannot cite", "does not support", "no source", "compose ", "collaborate with",
              "co-author", "integrating ", "evergreen note", "let us ", "i propose")


async def _build_morning_report(app) -> str:
    """Build the morning digest — only REAL grounded findings (plans/meta filtered) + gaps."""
    from datetime import datetime, timezone, timedelta
    db = app.state.db
    cur = await db.execute(
        "SELECT content, created_at FROM collective_knowledge WHERE knowledge_type='discovery' "
        "ORDER BY created_at DESC LIMIT 20")
    rows = await cur.fetchall()
    findings = []
    for r in rows:
        c = (r["content"] or "").strip()
        if len(c) < 60:
            continue
        if any(b in c.lower()[:45] for b in _PLAN_META):     # drop plans / meta-statements
            continue
        try:                                                 # created_at is UTC; show local (UTC+2)
            hhmm = (datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M:%S")
                    + timedelta(hours=2)).strftime("%H:%M")
        except Exception:
            hhmm = "--:--"
        findings.append((hhmm, c))
        if len(findings) >= 5:
            break
    from agora.execution.semantic_index import SemanticIndex
    global _SEM_INDEX
    if _SEM_INDEX is None or not _SEM_INDEX.ready:
        _SEM_INDEX = SemanticIndex()
    gaps = _SEM_INDEX.rotated_gaps(4) if _SEM_INDEX.ready else []

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"☀️ *Agora — morning report* ({day})", ""]
    if findings:
        lines.append("🔬 *Overnight — grounded findings (newest first, local time):*")
        for hhmm, f in findings:
            lines.append(f"`{hhmm}` {f[:190]}")
        lines.append("")
    if gaps:
        lines.append("🎯 *Your gaps (the agents are aiming here):*")
        for g in gaps:
            lines.append(f"• {g['title']}")
        lines.append("")
    # Harvested NEXT DIRECTIONS — what the research points to (esp. upgrades, for you to act on).
    dirs = _DIRECTIONS.get("directions", [])
    if dirs:
        lines.append("🧭 *Next directions (from overnight findings):*")
        for x in dirs:
            icon = "🛠️" if x.get("kind") == "upgrade" else "🔬"
            lines.append(f"{icon} {x['title']}")
        lines.append("")
    # How often the dungeon had questions — for you (escalations) and for Claude (inbox tasks), 24h.
    import time
    from agora.execution.claude_inbox import _load
    day_ago = time.time() - 86400
    esc_24h = sum(1 for e in _ESCALATIONS.values() if e.get("ts", 0) > day_ago)
    open_esc = sum(1 for e in _ESCALATIONS.values() if not e.get("resolved") and e.get("ts", 0) > day_ago)
    inbox_24h = sum(1 for t in _load() if t.get("ts", 0) > day_ago)
    lines.append(f"❓ *Questions (24h):* you {esc_24h} (escalations, {open_esc} open) · "
                 f"Claude {inbox_24h} (tasks)")
    lines.append("\n_Text a question · `directions` · `upgrades` · `status` · reply a number to build an upgrade_")
    return "\n".join(lines)


@router.post("/brain/morning-report")
async def morning_report(request: Request, send: bool = True):
    """Build a morning digest (real grounded findings + targeted gaps) and Telegram it."""
    text = await _build_morning_report(request.app)
    sent = await _send_telegram(text) if send else False
    return {"status": "ok", "sent": sent, "report": text}


# ── Agent escalation: an agent raises a SIGNIFICANT blocker to the user via Telegram,
#    and the user resolves it back through the same channel. ──
_ESCALATIONS: dict = {}     # agent -> {"problem", "ts", "resolved"}
_GUIDANCE: dict = {}        # agent -> guidance text the user left (consumed by the agent)
_ESC_COOLDOWN = 1800        # don't re-nag about the same stuck agent within 30 min


@router.post("/brain/escalate")
async def escalate(request: Request):
    """An agent reports it is genuinely stuck. Throttled per agent, then pushed to Telegram."""
    import time
    body = await request.json()
    agent = (body.get("agent") or "Agent").strip()
    problem = (body.get("problem") or "").strip()
    if not problem:
        return {"status": "empty"}
    now = time.time()
    prev = _ESCALATIONS.get(agent)
    if prev and not prev.get("resolved") and now - prev["ts"] < _ESC_COOLDOWN:
        return {"status": "throttled"}                  # already waiting on the user
    _ESCALATIONS[agent] = {"problem": problem, "ts": now, "resolved": False}
    sent = await _send_telegram(
        f"⚠️ *{agent} is stuck*\n\n{problem}\n\n→ Reply `fix <guidance>` to unblock it (or `status`).")
    return {"status": "sent" if sent else "no-telegram"}


@router.post("/brain/resolve")
async def resolve_escalation(request: Request):
    """The user's guidance for the most-recently stuck agent (or a named one)."""
    body = await request.json()
    guidance = (body.get("guidance") or "").strip()
    agent = body.get("agent")
    if not agent:
        pend = [(a, e) for a, e in _ESCALATIONS.items() if not e.get("resolved")]
        if not pend:
            return {"status": "none"}
        agent = max(pend, key=lambda ae: ae[1]["ts"])[0]
    _GUIDANCE[agent] = guidance
    if agent in _ESCALATIONS:
        _ESCALATIONS[agent]["resolved"] = True
    return {"status": "ok", "agent": agent}


@router.get("/brain/guidance")
async def get_guidance(agent: str):
    """An agent consumes any pending guidance the user left for it (once)."""
    return {"guidance": _GUIDANCE.pop(agent, None)}


@router.get("/brain/escalations")
async def list_escalations():
    import time
    now = time.time()
    return {"escalations": [
        {"agent": a, "problem": e["problem"], "resolved": e["resolved"],
         "mins_ago": round((now - e["ts"]) / 60)}
        for a, e in sorted(_ESCALATIONS.items(), key=lambda kv: -kv[1]["ts"])]}


# ── Remote control: the user hands Claude Code build/implementation tasks via Telegram ──
@router.post("/brain/claude-inbox")
async def claude_inbox_add(request: Request):
    """Queue a task the user texted to Claude Code (the brain poller routes it here)."""
    from agora.execution.claude_inbox import add_task
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        return {"status": "empty"}
    return {"status": "queued", "id": add_task(text)}


@router.get("/brain/claude-inbox")
async def claude_inbox_list():
    """Claude Code reads its pending tasks here on each wake."""
    from agora.execution.claude_inbox import pending
    return {"pending": pending()}


@router.post("/brain/claude-inbox/done")
async def claude_inbox_done(request: Request):
    """Claude Code marks a task done with a short result."""
    from agora.execution.claude_inbox import mark_done
    body = await request.json()
    mark_done(body.get("id") or "", body.get("result") or "")
    return {"status": "ok"}


@router.get("/brain/brainstorm")
async def list_brainstorm(request: Request, limit: int = 10):
    """Recent brainstorm sessions with their top idea."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT session_id, topic, status, created_at FROM agent_brainstorm_sessions "
        "ORDER BY created_at DESC LIMIT ?", (limit,))
    sessions = []
    for s in await cursor.fetchall():
        s = dict(s)
        ic = await db.execute(
            "SELECT bi.idea_content, bi.votes, d.npc_name FROM agent_brainstorm_ideas bi "
            "LEFT JOIN dungeon_npcs d ON d.npc_id=bi.npc_id "
            "WHERE bi.session_id=? ORDER BY bi.votes DESC, bi.impact_score DESC LIMIT 1",
            (s["session_id"],))
        top = await ic.fetchone()
        s["top_idea"] = dict(top) if top else None
        sessions.append(s)
    return {"sessions": sessions}


@router.get("/brain/upgrades")
async def list_upgrades(request: Request, limit: int = 20):
    """List agent-proposed system upgrades."""
    cursor = await request.app.state.db.execute(
        "SELECT proposer_name, title, description, upgrade_type, impact_estimate, "
        "effort_estimate, status, vote_count, created_at FROM system_upgrade_proposals "
        "ORDER BY created_at DESC LIMIT ?", (limit,))
    return {"proposals": [dict(r) for r in await cursor.fetchall()]}


@router.get("/brain/emotional-state")
async def emotional_state(request: Request):
    """Mood map of all agents + their dominant emotional memory tags."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT d.npc_name, s.mood FROM dungeon_npcs d "
        "LEFT JOIN agent_soul s ON s.npc_id=d.npc_id WHERE d.status='active'")
    agents = []
    for r in await cursor.fetchall():
        r = dict(r)
        agents.append({"name": r["npc_name"],
                       "mood": round(r["mood"], 3) if r["mood"] is not None else None})
    return {"agents": agents}


@router.post("/reflect/{npc_name}")
async def reflect(npc_name: str, request: Request):
    """Trigger an agent to reflect and propose a system upgrade."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    os_engine = get_os(request)
    await os_engine._propose_upgrade(npc_id)
    return {"status": "reflected", "npc": npc_name}


@router.get("/{npc_name}/conversations")
async def get_conversations(npc_name: str, request: Request, limit: int = 20):
    """Get an agent's recent conversation turns (as speaker or target)."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    cursor = await request.app.state.db.execute(
        "SELECT session_id, speaker_name, target_name, message, intent, turn_number, created_at "
        "FROM agent_conversations WHERE speaker_id=? OR target_id=? "
        "ORDER BY created_at DESC LIMIT ?", (npc_id, npc_id, limit))
    return {"npc": npc_name, "turns": [dict(r) for r in await cursor.fetchall()]}


@router.post("/{npc_name}/converse")
async def start_converse(npc_name: str, request: Request):
    """Start a conversation from this agent to another. Body: {target, topic, intent?}."""
    body = await request.json()
    if not body.get("target") or not body.get("topic"):
        raise HTTPException(400, "Missing field: target and/or topic")
    speaker_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    target_id = DUNGEON_AGENT_IDS.get(body["target"]) or body["target"]
    os_engine = get_os(request)
    session_id = await os_engine._start_conversation(
        speaker_id, target_id, body["topic"], intent=body.get("intent", "chat"))
    return {"status": "started", "session_id": session_id}
# ═══════════════════════════════════════════════
# AGENTIC OS v3 — Emócie, Vzťahy, Denníky, Sny, Kultúra, Konflikty
# ═══════════════════════════════════════════════

def _get_v3_engine(request: Request, name: str):
    """Get a v3 engine by attribute name, or raise 503."""
    engine = getattr(request.app.state, name, None)
    if not engine:
        raise HTTPException(503, f"Engine '{name}' not initialised")
    return engine


# ── EMOTIONS ──


@router.get("/{npc_name}/emotion")
async def get_emotion(npc_name: str, request: Request):
    """Get current emotional state for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    engine = _get_v3_engine(request, "emotion_engine")
    state = await engine.get_state(npc_id)
    if not state:
        raise HTTPException(404, f"NPC {npc_name} not found")
    return state


@router.get("/emotions")
async def get_all_emotions(request: Request):
    """Get emotional states of all agents."""
    engine = _get_v3_engine(request, "emotion_engine")
    return {"agents": await engine.get_all_states()}


@router.post("/{npc_name}/emotion")
async def trigger_emotion(npc_name: str, request: Request):
    """Manually trigger an emotion for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    engine = _get_v3_engine(request, "emotion_engine")
    body = await request.json()
    emotion = body.get("emotion", "neutral")
    intensity = float(body.get("intensity", 0.5))
    trigger = body.get("trigger", "api")
    from agora.api.dungeon import broadcast
    result = await engine.trigger(npc_id, emotion, intensity, trigger,
                                   broadcast_fn=lambda t, p: None)
    return result or {"error": "not found"}


# ── RELATIONSHIPS ──


@router.get("/{npc_name}/relationships")
async def get_relationships(npc_name: str, request: Request):
    """Get all relationships for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    engine = _get_v3_engine(request, "relationship_web")
    return {"relationships": await engine.get_all_for_agent(npc_id)}


@router.get("/relationships/{npc_a}/{npc_b}")
async def get_relationship_between(npc_a: str, npc_b: str, request: Request):
    """Get relationship between two specific NPCs."""
    id_a = DUNGEON_AGENT_IDS.get(npc_a) or npc_a
    id_b = DUNGEON_AGENT_IDS.get(npc_b) or npc_b
    engine = _get_v3_engine(request, "relationship_web")
    rel = await engine.get_relationship(id_a, id_b)
    if not rel:
        raise HTTPException(404, f"No relationship data between {npc_a} and {npc_b}")
    return rel


# ── DIARIES ──


@router.get("/{npc_name}/diary")
async def get_diary(npc_name: str, request: Request, limit: int = 20):
    """Get diary entries for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    engine = _get_v3_engine(request, "diary_engine")
    return {"entries": await engine.get_entries(npc_id, limit)}


# ── DREAMS ──


@router.get("/{npc_name}/dreams")
async def get_dreams(npc_name: str, request: Request):
    """Get dreams for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT * FROM agent_dreams WHERE npc_id=? ORDER BY created_at DESC LIMIT 20",
        (npc_id,),
    )
    return {"dreams": [dict(r) for r in await cursor.fetchall()]}


# ── CULTURE ──


@router.get("/culture")
async def get_culture(request: Request):
    """Get all active culture items."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT * FROM agent_culture WHERE is_active=1 ORDER BY spread_count DESC"
    )
    return {"culture": [dict(r) for r in await cursor.fetchall()]}


# ── CONFLICTS ──


@router.get("/{npc_name}/conflicts")
async def get_conflicts(npc_name: str, request: Request):
    """Get active conflicts for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    engine = _get_v3_engine(request, "conflict_engine")
    return {"conflicts": await engine.get_active(npc_id)}


@router.get("/conflicts")
async def get_all_conflicts(request: Request):
    """Get all conflicts."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT c.*, a1.npc_name as name_a, a2.npc_name as name_b "
        "FROM agent_conflicts c "
        "JOIN dungeon_npcs a1 ON a1.npc_id = c.agent_a_id "
        "JOIN dungeon_npcs a2 ON a2.npc_id = c.agent_b_id "
        "WHERE c.status IN ('active', 'mediated') ORDER BY c.severity DESC"
    )
    return {"conflicts": [dict(r) for r in await cursor.fetchall()]}


# ── METAMEMORY ──


@router.get("/{npc_name}/metamemory")
async def get_metamemory(npc_name: str, request: Request):
    """Get meta-memory (belief changes) for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    engine = _get_v3_engine(request, "meta_memory")
    return {"belief_changes": await engine.get_recent_changes(npc_id)}


# ── LIFECYCLE ──


@router.get("/{npc_name}/lifecycle")
async def get_lifecycle(npc_name: str, request: Request):
    """Get lifecycle info for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT * FROM agent_lifecycles WHERE npc_id=?", (npc_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(404, f"NPC {npc_name} not found")
    return dict(row)


# ── FULL V3 STATUS ──


@router.get("/{npc_name}/v3")
async def get_v3_status(npc_name: str, request: Request):
    """Get complete v3 status for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    emotion = None
    ee = getattr(request.app.state, "emotion_engine", None)
    if ee:
        emotion = await ee.get_state(npc_id)

    relationships = []
    rw = getattr(request.app.state, "relationship_web", None)
    if rw:
        relationships = await rw.get_all_for_agent(npc_id)

    cursor = await db.execute(
        "SELECT * FROM agent_lifecycles WHERE npc_id=?", (npc_id,)
    )
    lifecycle = await cursor.fetchone()
    lifecycle = dict(lifecycle) if lifecycle else None

    cursor = await db.execute(
        "SELECT * FROM agent_diaries WHERE npc_id=? ORDER BY created_at DESC LIMIT 5",
        (npc_id,),
    )
    diary = [dict(r) for r in await cursor.fetchall()]

    cursor = await db.execute(
        "SELECT COUNT(*) as c FROM agent_dreams WHERE npc_id=?", (npc_id,)
    )
    dream_count = (await cursor.fetchone())["c"]

    conflicts = []
    ce = getattr(request.app.state, "conflict_engine", None)
    if ce:
        conflicts = await ce.get_active(npc_id)

    metamemory = []
    mm = getattr(request.app.state, "meta_memory", None)
    if mm:
        metamemory = await mm.get_recent_changes(npc_id)

    return {
        "name": npc_name,
        "emotion": emotion,
        "relationships": relationships,
        "lifecycle": lifecycle,
        "diary_entries": diary,
        "total_dreams": dream_count,
        "active_conflicts": len(conflicts),
        "conflicts": conflicts,
        "belief_changes": metamemory,
    }


# ── Bridge endpoints (used by the dungeon to feed experiences in + read the vault) ──

@router.post("/{npc_name}/memories")
async def add_memory(npc_name: str, request: Request):
    """Store a memory for an agent (the dungeon feeds lived experiences back here)."""
    from agora.agent_os.memory_agent import MemoryAgent
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content:
        raise HTTPException(400, "Missing field: content")
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    mem = MemoryAgent(request.app.state.db, npc_id)
    mem_id = await mem.store_memory(
        content,
        memory_type=body.get("memory_type", "episodic"),
        importance=float(body.get("importance", 0.5)),
        emotional_tag=body.get("emotional_tag", "neutral"),
        source=body.get("source", "experience"),
        related_npc_id=body.get("related_npc_id"),
    )
    return {"status": "stored", "id": mem_id}


@router.post("/brain/upgrade")
async def add_upgrade(request: Request):
    """Record a system-upgrade proposal (agents recursively improving the OS)."""
    body = await request.json()
    title = (body.get("title") or "").strip()
    desc = (body.get("description") or body.get("action") or "").strip()
    if not title:
        raise HTTPException(400, "Missing field: title")
    npc_name = body.get("npc", "")
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    await request.app.state.db.execute(
        "INSERT INTO system_upgrade_proposals (proposer_id, proposer_name, title, "
        "description, upgrade_type, impact_estimate, effort_estimate) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (npc_id, npc_name, title[:100], desc[:500],
         body.get("upgrade_type", "feature"),
         body.get("impact", "medium"), body.get("effort", "medium")),
    )
    await request.app.state.db.commit()
    return {"status": "proposed", "title": title}


@router.get("/brain/vault")
async def query_vault(request: Request, q: str = "", k: int = 3):
    """Query the Obsidian vault (the agents' shared knowledge base)."""
    reader = getattr(request.app.state, "vault_reader", None)
    if not reader:
        return {"results": [], "vault": "unavailable"}
    results = await reader.query(q, top_k=k) if q else [await reader.get_random_insight()]
    results = [r for r in results if r]
    return {"results": results, "real_vault": reader.is_real()}


# ── Bare single-segment catch-all — MUST be registered LAST so specific static
#    routes (/emotions, /culture, /conflicts, /brain/*) are matched first. ──
@router.get("/{npc_name}")
async def get_agent_os(npc_name: str, request: Request):
    """Get full OS status for an NPC by name or UUID."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    os_engine = get_os(request)
    status = await os_engine.get_full_status(npc_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"NPC {npc_name} not found")
    return status
# ═══════════════════════════════════════════════
# REAL ACTIONS
# ═══════════════════════════════════════════════


@router.post("/{npc_name}/action")
async def execute_action(npc_name: str, request: Request):
    """Execute a real action on behalf of an agent.
    
    Body: {"action": "send_telegram|write_note|write_article|run_script",
           "params": {...}}
    """
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    engine = getattr(request.app.state, "real_action_engine", None)
    if not engine:
        raise HTTPException(503, "Real action engine not initialised")
    
    body = await request.json()
    action = body.get("action", "")
    params = body.get("params", {})
    
    if not action:
        raise HTTPException(400, "Missing 'action' field")
    
    result = await engine.execute(action, params, agent_name=npc_name)
    return result


@router.post("/actions/send-telegram")
async def send_telegram(request: Request):
    """Send a Telegram message as an agent.
    
    Body: {"agent": "Shadow Kael", "message": "Hello!", "params": {}}
    """
    body = await request.json()
    agent = body.get("agent", "System")
    message = body.get("message", "")
    engine = getattr(request.app.state, "real_action_engine", None)
    if not engine:
        raise HTTPException(503, "Real action engine not initialised")
    result = await engine.execute("send_telegram", {"message": message}, agent_name=agent)
    return result


@router.post("/actions/write-note")
async def write_note(request: Request):
    """Write a .md note to the vault as an agent.
    
    Body: {"agent": "Shadow Kael", "title": "...", "content": "...", "tags": [...]}
    """
    body = await request.json()
    agent = body.get("agent", "System")
    engine = getattr(request.app.state, "real_action_engine", None)
    if not engine:
        raise HTTPException(503, "Real action engine not initialised")
    result = await engine.execute("write_note", {
        "title": body.get("title", "Note"),
        "content": body.get("content", ""),
        "tags": body.get("tags", []),
    }, agent_name=agent)
    return result


@router.get("/brain/repair-ledger")
async def brain_repair_ledger(days: float = 14.0):
    """THE SECOND BOOK — repair output per agent, beside the creation (note-count) view.

    Counting vault notes made four agents read as zero and one as 64%. On this ledger over 60 days
    Artificer Rooke is the most productive member in the organization (58 repairs, 33 of them
    decisive) and scored zero on the note count, while the top note-writer has 7. A creation metric
    applied to repairers reports idleness that is not there.
    """
    from agora.execution.repair_ledger import repair_ledger, starvation_report, format_repair_ledger
    return {"status": "ok", "ledger": repair_ledger(days),
            "starvation": starvation_report(), "report": format_repair_ledger(days)}
