"""Agent OS API — soul, brain, body, abilities, skills, help requests."""
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


def _garbage_finding(title: str, content: str):
    """Conservative quality filter — reject only CLEARLY broken findings (self-upgrade: completion
    filter). Returns a reason string if garbage, else None."""
    t, c = (title or "").strip(), (content or "").strip()
    cl, tl = c.lower(), t.lower()
    for p in ("hypothesize on:", "pursue direction:", "develop the gap:", "deepen:"):
        if cl.count(p) >= 2 or tl.count(p) >= 2:          # nested quest prefixes
            return "nested quest prefix"
    body = cl.split("source:")[0].strip()
    if len(body) < 50:
        return "too short"
    if body.strip(". ") == tl.strip(". "):               # content merely restates the title
        return "content restates title (no real finding)"
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
            return {"status": "rejected", "reason": g}
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
    return {"status": "written", "path": path, "score": q["score"]}


_VERIFIED: set = set()   # finding titles already fact-checked (so we work through the backlog)


@router.post("/brain/verify-findings")
async def verify_findings(request: Request, n: int = 4, incorporate: bool = True):
    """Fact-check recent UN-checked findings against real sources; incorporate the VERIFIED ones
    into the vault as validated notes. Run repeatedly to work through the backlog gradually."""
    from agora.execution.verifier import verify_finding
    db = request.app.state.db
    cur = await db.execute(
        "SELECT title, content FROM collective_knowledge WHERE knowledge_type='discovery' "
        "ORDER BY created_at DESC LIMIT 25")
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
    so agents can do GAP-DRIVEN research aimed at what the user actually lacks."""
    global _SEM_INDEX
    from agora.execution.semantic_index import SemanticIndex
    if _SEM_INDEX is None or not _SEM_INDEX.ready:
        _SEM_INDEX = SemanticIndex()
    return {"status": "ok", "gaps": _SEM_INDEX.find_gaps(n) if _SEM_INDEX.ready else []}


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
    """The latest harvested directions — agents pull these to pursue them (closing the loop)."""
    return {"directions": _DIRECTIONS.get("directions", []), "themes": _DIRECTIONS.get("themes", [])}


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
    gaps = _SEM_INDEX.find_gaps(4) if _SEM_INDEX.ready else []

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
