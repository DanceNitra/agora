"""
The Seminar — agent conversation & brainstorm turned into topic-anchored research.

The leak this closes: the tick loop ran a 2-turn agent conversation ~60% of EVERY tick and a
group brainstorm every 30 ticks, both on HARDCODED dungeon-fiction topics ("ancient artifacts",
"a threat in the dungeon", intent='chat'). They wrote conversation/brainstorm rows and burned
~2.36M tokens (organ 'agent-dialogue') for ZERO recorded research value — agents literally
chatting about dungeon secrets.

The Seminar implements the owner's actual intent: agents collaborate on NAMED open research
questions, and every exchange must terminate in a recorded CONTRIBUTION — a falsifiable claim
grounded in real literature, with what would refute it and what it connects to. Talk is the
means; the contribution is the product. Contributions accumulate into per-topic THREADS (a living
dossier) and are valued, so the funnel's ROI for dialogue climbs off the floor.

Four layers, one module:
  1. Value contract — a cycle counts only if it yields a Contribution (else nothing is recorded).
  2. Structured exchange — pick_topic + extract_contribution turn a transcript into a claim.
  3. Topics as the unit of value — contributions append to a topic thread that advances.
  4. Measurement — value_points()/seminar_stats() feed the Metabolism and the funnel.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[2]
_TOPICS = _SERVER / ".topics.json"
_CONTRIB = _SERVER / ".contributions.json"

_MAX_PER_TOPIC = 4          # contributions before a topic is ripe for synthesis/press
_MAX_ATTEMPTS = 8           # rounds before a topic retires even if it never produced enough — stops
#                            the seminar livelocking on a saturated topic (every new claim is a
#                            near-duplicate the anti-repeat gate rejects, so n_contrib never advances)
# folder/structure artifacts that masquerade as "domains" — never a real research topic
_JUNK = re.compile(r"\b(meta|root|unfiled|system|inbox|daily|templates?|fleeting|sessions?|"
                   r"backups?|attachments?|untitled)\b", re.I)


def _is_real_topic(headline: str) -> bool:
    return bool(headline) and len(headline) > 3 and not _JUNK.search(headline)


# Board-aligned open research questions — the priorities the seminar should advance (finance &
# causal inference PREMIUM; Science of Better Thinking; Future of Work). These ground reliably in
# real literature (unlike the thinnest vault gaps), so the dialogue reliably produces a
# Contribution instead of stalling. Rotated deterministically; deepened across many sessions.
_TOPIC_BANK = [
    ("difference-in-differences parallel trends robustness",
     "Under what realistic violations is a difference-in-differences estimate most biased, and "
     "how powerful are the standard pre-trends and sensitivity checks at catching them?"),
    ("instrumental variables weak instrument bias",
     "When does a plausibly-valid instrument still give badly biased causal estimates, and what "
     "diagnostic would reveal it before the estimate is trusted?"),
    ("regression discontinuity bandwidth sensitivity",
     "How sensitive are regression-discontinuity effect estimates to bandwidth and functional-form "
     "choices, and what would falsify a claimed discontinuity?"),
    ("volatility drag geometric vs arithmetic returns",
     "How large is the gap between arithmetic and geometric (compounded) returns under realistic "
     "volatility, and when does it dominate a strategy's expected growth?"),
    ("factor investing out-of-sample decay",
     "How much of a published equity factor's premium survives out of sample after costs, and what "
     "evidence would mark a factor as data-mined rather than real?"),
    ("Kelly criterion fractional betting drawdown",
     "What fraction of full-Kelly best trades off long-run growth against drawdown risk, and what "
     "observation would refute the chosen fraction?"),
    ("spaced repetition forgetting curve optimal interval",
     "What review schedule maximizes long-run retention per unit study time, and what result would "
     "overturn the spacing effect's optimality?"),
    ("calibration of expert probability forecasts",
     "Do structured forecasting practices measurably improve calibration over base rates, and what "
     "would show the improvement is illusory?"),
    ("retrieval interference in large memory stores",
     "How does retrieval precision degrade as a memory store grows, and does value-curation recover "
     "it — i.e. is interference, not capacity, the binding constraint?"),
    ("automation labor displacement task-level exposure",
     "Which job tasks are most exposed to current AI, and what evidence distinguishes augmentation "
     "from displacement in the data so far?"),
    ("collective intelligence team size diminishing returns",
     "At what point does adding members stop improving a group's problem-solving, and what would "
     "falsify a claimed collective-intelligence factor?"),
    ("survivorship bias in performance studies",
     "How much does survivorship bias inflate measured performance in fund/startup studies, and "
     "what correction would change the headline conclusion?"),
]
_REFUSAL = re.compile(
    r"\b(i cannot|i can't|unable to|no (?:real |specific )?source|please provide|"
    r"as an ai|i need a|does not (?:fit|apply)|no paper (?:fits|matches))\b", re.I)


def _load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(p: Path, data) -> None:
    try:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _id(seed: str) -> str:
    # stable-ish short id without random (deterministic on content+len of ledger)
    base = f"{seed}{len(_load(_CONTRIB, []))}{int(time.time())}"
    h = 0
    for ch in base:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return f"{h:08x}"


# ── Layer 3: topics as the unit of value ────────────────────────────────────
def pick_topic(vault: str) -> dict:
    """A REAL open research question to collaborate on. Prefers deepening an existing open
    thread (fewest contributions first) so topics actually advance; otherwise opens a fresh one
    from the Frontier (a thin domain or an unbridged structural hole). Never returns dungeon
    fiction."""
    topics = _load(_TOPICS, [])
    # board/claude topics are curated research questions — trust them; only frontier/gap topics
    # (raw folder/domain names) need the junk filter. (Without this, 'meta-prediction' etc. were
    # wrongly dropped because the junk word 'meta' is a substring of a real topic.)
    live = [t for t in topics if t.get("status") in ("open", "advancing")
            and t.get("n_contrib", 0) < _MAX_PER_TOPIC and t.get("attempts", 0) < _MAX_ATTEMPTS
            and (t.get("source") in ("board", "claude") or _is_real_topic(t.get("headline", "")))]
    # 1) deepen the least-advanced live thread most of the time
    if live and (len(live) >= 3 or (int(time.time()) % 3) != 0):
        # fewest contributions first, then fewest attempts → rotate across live topics instead of
        # spinning on one (a rejected round doesn't bump last_advanced, so without attempts the same
        # saturated topic would stay first forever).
        live.sort(key=lambda t: (t.get("n_contrib", 0), t.get("attempts", 0), t.get("last_advanced", 0)))
        return live[0]
    # 2) open a fresh topic from the board-aligned bank (reliably groundable), rotating through
    #    it before repeating. This is the primary fresh source — the priorities to advance.
    seen = {t.get("headline", "").lower() for t in topics}
    for headline, prompt in _TOPIC_BANK:
        if headline.lower() not in seen:
            t = {"id": _id(headline), "topic": prompt, "headline": headline,
                 "source": "board", "status": "open", "n_contrib": 0, "contribution_ids": [],
                 "opened": time.time(), "last_advanced": 0.0}
            topics.append(t)
            _save(_TOPICS, topics)
            return t
    # 3) a substantive vault gap, framed as a synthesis to connect/extend (secondary)
    try:
        from agora.execution.semantic_index import SemanticIndex
        for g in SemanticIndex().rotated_gaps(10):
            title = g.get("title", "")
            if _is_real_topic(title) and title.lower() not in seen:
                t = {"id": _id(title), "topic": f"Develop or stress-test the vault idea "
                     f"'{title}' with a NEW finding — extend it, connect it to related work, "
                     f"or state what evidence would refute it.", "headline": title,
                     "source": "gap", "status": "open", "n_contrib": 0, "contribution_ids": [],
                     "opened": time.time(), "last_advanced": 0.0}
                topics.append(t)
                _save(_TOPICS, topics)
                return t
    except Exception:
        pass
    # 4) frontier fallback (thin domain / structural hole), junk-filtered
    try:
        from agora.execution.frontier import frontier_target, record_seeded
        ft = frontier_target(vault)
        if ft and ft.get("prompt") and _is_real_topic(ft.get("target", "")):
            t = {"id": _id(ft["target"]), "topic": ft["prompt"], "headline": ft["target"],
                 "source": ft.get("kind", "frontier"), "status": "open",
                 "n_contrib": 0, "contribution_ids": [],
                 "opened": time.time(), "last_advanced": 0.0}
            topics.append(t)
            _save(_TOPICS, topics)
            try:
                record_seeded(ft["target"], ft.get("kind", ""))
            except Exception:
                pass
            return t
    except Exception:
        pass
    # 3) fallback: reuse any live thread, else a generic-but-real research prompt
    if live:
        return live[0]
    tid = _id("open-inquiry")
    t = {"id": tid, "topic": "Identify one unsupported assumption in the vault's strongest "
         "current claim and state what evidence would test it.", "headline": "self-audit",
         "source": "fallback", "status": "open", "n_contrib": 0, "contribution_ids": [],
         "opened": time.time(), "last_advanced": 0.0}
    topics.append(t)
    _save(_TOPICS, topics)
    return t


def _advance_topic(topic_id: str, contrib_id: str) -> None:
    topics = _load(_TOPICS, [])
    for t in topics:
        if t.get("id") == topic_id:
            t.setdefault("contribution_ids", []).append(contrib_id)
            t["n_contrib"] = t.get("n_contrib", 0) + 1
            t["last_advanced"] = time.time()
            t["status"] = "synthesized" if t["n_contrib"] >= _MAX_PER_TOPIC else "advancing"
            break
    _save(_TOPICS, topics)


def _record_attempt(topic_id: str) -> None:
    """Count every round on a topic (success or not) and retire it once it has had too many
    tries — otherwise a saturated topic, whose every new claim the anti-repeat gate rejects,
    would trap the seminar deepening it forever."""
    if not topic_id:
        return
    topics = _load(_TOPICS, [])
    for t in topics:
        if t.get("id") == topic_id:
            t["attempts"] = t.get("attempts", 0) + 1
            if t["attempts"] >= _MAX_ATTEMPTS and t.get("status") in ("open", "advancing"):
                t["status"] = "synthesized"      # exhausted — move the seminar on to fresh ground
            break
    _save(_TOPICS, topics)


# ── Layer 1+2: the value contract + structured extraction ────────────────────
def _parse_json(text: str) -> dict | None:
    """Parse the rapporteur's JSON, tolerating truncation. The model often hits the token cap
    mid-string, leaving the JSON unclosed — so on a strict-parse failure we salvage the completed
    string fields by key (a finished claim is still usable even if evidence got cut off)."""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    out: dict = {}
    for key in ("claim", "evidence", "falsifier"):
        km = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.S)
        if km:
            out[key] = km.group(1).replace('\\"', '"').replace("\\n", " ").strip()
    lm = re.search(r'"links"\s*:\s*\[([^\]]*)\]', text, re.S)
    if lm:
        out["links"] = [s.strip().strip('"') for s in lm.group(1).split(",") if s.strip().strip('"')]
    return out or None


_WORD = re.compile(r"[a-z0-9]+")


def _prior_claims(topic_id: str) -> list[str]:
    """Claims already recorded for this topic — so deepening ADVANCES instead of restating."""
    if not topic_id:
        return []
    return [c.get("claim", "") for c in _load(_CONTRIB, []) if c.get("topic_id") == topic_id]


def _too_similar(claim: str, priors: list[str], thr: float = 0.55) -> bool:
    """True if the claim near-duplicates an existing one (token overlap-coefficient)."""
    a = set(_WORD.findall((claim or "").lower()))
    if len(a) < 4:
        return False
    for p in priors:
        b = set(_WORD.findall((p or "").lower()))
        if b and len(a & b) / min(len(a), len(b)) > thr:
            return True
    return False


def extract_contribution(topic: dict, transcript: str, partners: list[str]) -> dict | None:
    """Turn a real exchange into a recorded Contribution grounded in literature, or return None.

    The value contract: no grounded, falsifiable claim → no contribution → nothing recorded
    (the cycle was activity, not knowledge). Deepening a topic must ADD a distinct angle, not
    restate prior contributions. NEVER invents sources. Sync; call via to_thread.
    """
    from agora.execution import research_tool
    from agora.execution.llm_client import call_llm

    q = topic.get("headline") or topic.get("topic", "")[:80]
    try:
        papers = research_tool.research(research_tool.distill_query(q), n=4)
        if not papers:                                # second angle: terms from the full prompt
            papers = research_tool.research(research_tool.distill_query(topic.get("topic", q)), n=4)
    except Exception:
        papers = []
    # Grounding is EITHER external literature OR the user's own vault notes (a synthesis that
    # connects/extends real notes is valuable too). Require at least one real anchor.
    vault_notes = []
    try:
        from agora.execution.semantic_index import SemanticIndex
        vault_notes = [h for h in SemanticIndex().search(q, top_k=4) if h.get("score", 0) > 0.4]
    except Exception:
        vault_notes = []
    if not papers and not vault_notes:
        return None                                   # nothing real to stand on → honest skip
    src_block = research_tool.format_for_prompt(papers) if papers else "(no external paper found)"
    note_block = "; ".join(f"[[{n['title']}]]" for n in vault_notes[:4]) or "(no close vault note)"
    has_paper = bool(papers)
    priors = _prior_claims(topic.get("id"))
    prior_block = ""
    if priors:
        prior_block = ("\n\nALREADY ESTABLISHED for this topic (do NOT restate these — your finding "
                       "must ADD a DISTINCT new angle: a different mechanism, a boundary condition, "
                       "an edge case, a quantitative bound, or a counter-result):\n- "
                       + "\n- ".join(c[:140] for c in priors[-6:]))
    sys = (
        "You are a research seminar's rapporteur. From the colleagues' exchange, any RELEVANT "
        "papers, and the user's own vault notes below, state ONE substantive, falsifiable finding "
        "the discussion reached. Ground it by CONNECTING or EXTENDING the named vault notes into a "
        "new claim; if a paper is directly on-topic, also paraphrase its result and name it "
        "(Author Year) — but IGNORE any listed paper that is off-topic. If the topic already has "
        "established claims (listed below), your finding MUST advance beyond them, not rephrase "
        "them. Never invent sources or over-generalize. Reply ONLY JSON: "
        '{"claim":"<one falsifiable sentence>","evidence":"<how the vault notes combine, plus '
        '(Author Year) if a paper truly applies>","falsifier":"<what observation would refute the '
        'claim>","links":["<vault concept it connects/contradicts>"]}')
    usr = (f"Topic: {topic.get('topic','')}\n\nExchange:\n{transcript[:1000]}\n\n"
           f"Possibly-relevant papers (use only if on-topic):\n{src_block[:1100]}\n\n"
           f"User's related vault notes: {note_block}{prior_block}")
    out = call_llm(sys, usr, tier="cheap", max_tokens=700, temperature=0.4)
    if not (out or "").strip():                       # transient empty (GPU contention) → one retry
        out = call_llm(sys, usr, tier="medium", max_tokens=700, temperature=0.4)
    d = _parse_json(out)
    if not d:
        return None
    claim = (d.get("claim") or "").strip()
    if len(claim) < 25 or _REFUSAL.search(claim) or _REFUSAL.search(d.get("evidence", "")):
        return None                                   # vacuous / refusal → not a contribution
    if _too_similar(claim, priors):
        return None                                   # near-duplicate of an existing contribution
    return record_contribution(topic, partners, claim, d.get("evidence", ""),
                               d.get("falsifier", ""), d.get("links") or [],
                               basis="literature" if has_paper else "synthesis")


def record_contribution(topic: dict, partners: list[str], claim: str, evidence: str,
                        falsifier: str, links: list, basis: str = "literature") -> dict:
    """Append a Contribution to the ledger and its topic thread; advance the topic."""
    contribs = _load(_CONTRIB, [])
    cid = _id(claim)
    c = {"id": cid, "ts": time.time(), "topic_id": topic.get("id"),
         "topic": topic.get("headline") or topic.get("topic", "")[:80],
         "partners": partners[:4], "claim": claim[:400], "evidence": evidence[:300],
         "falsifier": falsifier[:300], "links": [str(x)[:80] for x in links][:5],
         "basis": basis,
         "grounded": bool(evidence and not _REFUSAL.search(evidence)), "verified": False}
    contribs.append(c)
    _save(_CONTRIB, contribs)
    if topic.get("id"):
        _advance_topic(topic["id"], cid)
    return c


# ── Layer 4 support + measurement ────────────────────────────────────────────
_SOURCE_RE = re.compile(r"\[\[.+?\]\]|\(\s*[A-Z][A-Za-z\-]+.{0,40}\d{4}\s*\)|doi:|https?://|arXiv|et al\.", re.I)


def verify_contributions(limit: int = 500) -> dict:
    """Promote grounded contributions to VERIFIED when they meet the full evidence bar: a falsifier
    AND a checkable source — a cited paper ('(Author, 2024)'/arXiv/doi/url) or a [[vault note]].
    Here 'verified' means *independently checkable + falsifiable* (a stricter tier than 'grounded',
    which only requires some evidence text) — the higher-trust QA layer that value_points() already
    rewards (+2) but that nothing ever wrote back. Deterministic, idempotent; never un-verifies."""
    contribs = _load(_CONTRIB, [])
    changed = checked = 0
    for c in contribs:
        if c.get("verified") or not c.get("grounded"):
            continue
        checked += 1
        if checked > limit:
            break
        has_fals = bool((c.get("falsifier") or "").strip())
        has_src = bool(_SOURCE_RE.search((c.get("evidence") or "") + " " + (c.get("claim") or "")))
        if has_fals and has_src:
            c["verified"] = True
            changed += 1
    if changed:
        _save(_CONTRIB, contribs)
    return {"checked": checked, "newly_verified": changed,
            "total_verified": sum(1 for c in contribs if c.get("verified")), "total": len(contribs)}


def value_points() -> float:
    """Seminar value for the Metabolism: 1 per grounded contribution, +2 if later verified."""
    contribs = _load(_CONTRIB, [])
    return float(sum(1 for c in contribs if c.get("grounded"))
                 + 2 * sum(1 for c in contribs if c.get("verified")))


def seminar_stats() -> dict:
    contribs = _load(_CONTRIB, [])
    topics = _load(_TOPICS, [])
    grounded = sum(1 for c in contribs if c.get("grounded"))
    return {"contributions": len(contribs), "grounded": grounded,
            "verified": sum(1 for c in contribs if c.get("verified")),
            "topics_open": sum(1 for t in topics if t.get("status") in ("open", "advancing")),
            "topics_synthesized": sum(1 for t in topics if t.get("status") == "synthesized")}


_SEMLOG = _SERVER / ".seminar_log.json"
_running = False        # in-flight guard: one group seminar at a time (a round is network+LLM heavy)


def inject_topic(headline: str, prompt: str = "", source: str = "claude") -> dict:
    """Push a topic into the seminar pool — used when Claude (or the owner) hands the team a
    question to research. It jumps the queue as an open thread the agents will pick up."""
    headline = (headline or "").strip()
    if not headline:
        return {"error": "empty"}
    topics = _load(_TOPICS, [])
    if any(t.get("headline", "").lower() == headline.lower() for t in topics):
        return {"status": "exists", "headline": headline}
    t = {"id": _id(headline), "topic": prompt or f"Investigate and stress-test: {headline}. "
         f"Produce a falsifiable claim grounded in literature or the vault, and what would refute it.",
         "headline": headline, "source": source, "status": "open", "n_contrib": 0,
         "contribution_ids": [], "opened": time.time(), "last_advanced": 0.0}
    topics.append(t)
    _save(_TOPICS, topics)
    return {"status": "ok", "headline": headline, "id": t["id"]}


def log_round(topic: dict, contributors: list, passed: list, contribution: dict | None) -> None:
    """Record one group-seminar round (who contributed, who passed and why) for the report."""
    log = _load(_SEMLOG, [])
    log.append({"ts": time.time(), "topic": topic.get("headline", "")[:80],
                "contributors": contributors[:8], "passed": passed[:8],
                "claim": (contribution or {}).get("claim", "")[:160] if contribution else ""})
    _save(_SEMLOG, log[-200:])                       # rolling


def run_group_seminar(npcs: list[dict], vault: str) -> dict:
    """ALL agents work ONE topic together. Each agent brings the relevant KNOWLEDGE its memory
    surfaces (MNEMO recall) — not decorative chatter — and only if it genuinely has something;
    the rest pass (honestly logged). ONE rapporteur then synthesizes the team's combined knowledge
    into a single grounded Contribution. One synthesis LLM call per round (fast on a shared GPU,
    and 'work not chat'). Sync (network + LLM); call via to_thread. Returns a round summary."""
    global _running
    if _running:
        return {"topic": "", "contributors": [], "passed": [], "contribution": None,
                "skipped": "a round is already running"}
    _running = True
    try:
        return _run_group_seminar_inner(npcs, vault)
    finally:
        _running = False


def _run_group_seminar_inner(npcs: list[dict], vault: str) -> dict:
    from agora.execution import mnemo_bridge

    topic = pick_topic(vault)
    contributors, passed, brought = [], [], []
    for n in npcs[:8]:
        name = n.get("npc_name") or n.get("npc_id", "agent")
        role = n.get("role") or name
        can, ctx = mnemo_bridge.agent_can_contribute(role, topic.get("headline", ""))
        if can and ctx:
            contributors.append({"id": n.get("npc_id"), "name": name})
            brought.append(f"{name} brings: {ctx[:200]}")
        else:
            passed.append({"agent": name, "why": "no relevant memory"})
    contribution = None
    if contributors:
        # the "exchange" is the team's pooled knowledge; the rapporteur synthesizes one claim
        transcript = "\n".join(brought)
        contribution = extract_contribution(topic, transcript, [c["name"] for c in contributors])
        if contribution:
            mnemo_bridge.remember_contribution(contribution["claim"], contribution.get("evidence", ""),
                                               tags=[topic.get("headline", "")[:40]])
    log_round(topic, [c["name"] for c in contributors], passed, contribution)
    _record_attempt(topic.get("id"))      # count the round so a saturated topic eventually retires
    return {"topic": topic.get("headline", ""), "contributors": contributors,
            "passed": passed, "contribution": contribution}


def research_report(hours: int = 3) -> str:
    """A Telegram-ready digest of what the team researched: topics advanced, contributions made,
    what was skipped and WHY, and what is ripe for synthesis. For the owner while away."""
    now = time.time()
    cutoff = now - hours * 3600
    contribs = [c for c in _load(_CONTRIB, []) if c.get("ts", 0) >= cutoff]
    rounds = [r for r in _load(_SEMLOG, []) if r.get("ts", 0) >= cutoff]
    topics = _load(_TOPICS, [])
    ripe = [t["headline"] for t in topics if t.get("status") == "synthesized"]
    passed_counts: dict = {}
    for r in rounds:
        for p in r.get("passed", []):
            passed_counts[p.get("why", "?")] = passed_counts.get(p.get("why", "?"), 0) + 1
    lines = [f"[RESEARCH REPORT] last {hours}h — team seminar"]
    lines.append(f"Rounds: {len(rounds)} | Contributions: {len(contribs)} "
                 f"(grounded {sum(1 for c in contribs if c.get('grounded'))})")
    for c in contribs[-5:]:
        who = "+".join(c.get("partners", [])[:3])
        lines.append(f"+ [{c.get('topic','')[:32]}] {c['claim'][:90]}  ({who})")
    if not contribs:
        lines.append("(no new contributions — topics too thin or memory had nothing relevant)")
    skipped = "; ".join(f"{v}x {k}" for k, v in sorted(passed_counts.items(), key=lambda x: -x[1]))
    if skipped:
        lines.append(f"Skipped turns: {skipped}")
    if ripe:
        lines.append(f"Ripe for synthesis: {', '.join(ripe[:4])}")
    return "\n".join(lines)[:3900]


def topic_threads(n: int = 8) -> list[dict]:
    topics = _load(_TOPICS, [])
    topics.sort(key=lambda t: -t.get("last_advanced", t.get("opened", 0)))
    return [{"headline": t.get("headline", t.get("topic", "")[:60]),
             "status": t.get("status"), "n_contrib": t.get("n_contrib", 0),
             "source": t.get("source")} for t in topics[:n]]
