"""
The Replication Unit — Artificer Rooke re-runs other people's science.

Reading literature grounds beliefs in what was CLAIMED; replication grounds them in what
actually COMPUTES. The unit picks a sourced finding from the collective knowledge, and Claude
builds the smallest computational model of the claim in the Lab: REPRODUCED (the mechanism
holds in a minimal model), FAILED (it doesn't — which is a publishable result, science's
rarest export), or NOT_COMPUTABLE (an honest pass). The ledger is Rooke's track record — the
first dungeon agent whose standing rests on re-running the work of others, not producing more.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".replications.json"
_OUTCOMES = ("REPRODUCED", "FAILED", "NOT_COMPUTABLE")


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


#: Textbook families. A second entry in one of these is not a new replication -- it is the same known
#: result restated, which the standing bar forbids re-deriving. Kept in sync with the renderer's list
#: (tools/render_crucible.py::_DD_FAMILIES); the agreement is asserted in tests rather than imported, so
#: the brain does not depend on a build tool.
_FAMILIES = ("k-clique", "clique percolation", "epidemic threshold", "finite-size", "branching",
             "linucb", "regret bound", "percolation threshold", "universality class",
             "power law", "power-law", "scale-free", "preferential attach")
_STOP = {"the", "and", "for", "with", "that", "this", "from", "are", "was", "not", "但", "its",
         "than", "when", "which", "into", "under", "over", "per", "has", "have", "been", "can"}
_DUP_THR = 0.5


def _tokens(claim: str) -> set:
    s = re.sub(r"\([^)]*\)", " ", (claim or "").lower())
    s = re.sub(r"[^a-z\s]", " ", s)
    return {t for t in s.split() if len(t) > 2 and t not in _STOP}


def already_covered(claim: str, entries: list | None = None) -> str:
    """Have we already spent a replication on this claim? Returns a reason, or "" if it is genuinely new.

    THE DEFECT THIS REPLACES. The freshness check was `claim[:60].lower() in attempted` -- exact equality
    on a 60-character prefix, standing in for "is this the same claim". Two wordings of one result share
    no prefix, so both read as fresh and both cost a full replication cycle. Measured on the live ledger
    2026-07-28: the LinUCB regret bound of Chu et al. 2011 was replicated THREE times over six weeks under
    three notations, and the public REPRODUCED count read 23 where the truth was 21.

    Three checks, because no single one is sufficient and I measured that rather than assuming it:
      * PREFIX -- the original, kept: catches a literal re-queue.
      * TOKEN OVERLAP -- catches restatements that share vocabulary. Would have stopped the three
        BA-network percolation entries (jaccard 0.89-1.00) the prefix check let through.
      * FAMILY -- catches what neither of the above can. The three LinUCB claims score jaccard 0.26-0.43,
        BELOW the overlap threshold, because a theorem written in three notations shares almost no words.
        All three do contain a family term. Without this the fix would have addressed a different failure
        than the one that actually happened.

    Skipping is cheap here and wrong-accepting is not: the scanner simply takes the next candidate, while
    a false accept costs a full cycle AND inflates a published number.
    """
    entries = _load() if entries is None else entries
    c = (claim or "").strip()
    if not c:
        return "empty claim"
    if c[:60].lower() in {(r.get("claim") or "")[:60].lower() for r in entries}:
        return "identical opening -- already attempted"
    tk = _tokens(c)
    if tk:
        for r in entries:
            rt = _tokens(r.get("claim", ""))
            if rt and len(tk & rt) / len(tk | rt) >= _DUP_THR:
                return f"restates lab {r.get('lab_id') or '?'} ({r.get('outcome')})"
    return ""


def family_prior(claim: str, entries: list | None = None) -> list:
    """Prior ledger entries in the same textbook family. EVIDENCE, deliberately not a block.

    Blocking on family was implemented first and measured before shipping, which is the only reason it is
    not in here. Replaying the live ledger through it showed it would have refused 9 of 58 entries -- and
    one of them was "Real-world networks are scale-free", verdict FAILED. A FAILED is the Crucible's most
    valuable output and the entire reason to hunt claims where failure is a live possibility; a guard that
    discards one because the topic was touched before is working against the thing it protects.

    The three LinUCB entries are the SAME PROPOSITION restated. "scale-free is FALSE" and "the power law
    reproduces" are DIFFERENT propositions in one topical family. Nothing lexical separates those, and at
    queue time the verdict is not yet known -- so this refuses to guess. It reports the prior entries, they
    are stamped onto the record, and tools/render_crucible.py FAILS the render until a human declares them
    duplicate or genuinely distinct. One decision per family, made once, with the evidence attached --
    instead of a silent block or a silent inflation.
    """
    entries = _load() if entries is None else entries
    low = (claim or "").lower()
    out = []
    for fam in _FAMILIES:
        if fam in low:
            out += [r.get("lab_id") or "?" for r in entries
                    if fam in (r.get("claim", "") or "").lower()]
    return sorted(set(out))


_VEC_CACHE = _STORE.parent / ".replication_vectors.json"
#: Conservative. MEASURED on a 10-pair fixture (research/probes/audit_claim_semantic_dedup.py): the
#: weakest restatement of one theorem scores 0.813 and the closest DIFFERENT claim in a shared topic
#: (LinUCB vs Thompson sampling) scores 0.776. Separable, but by 0.037 on ten pairs -- nowhere near enough
#: margin to block on. It flags; a human decides.
_SIM_THR = 0.80


def _embed(text: str) -> list | None:
    """Local embedder, best effort. Never raises: a replication must still be recordable with the
    embedder down, and a missing flag is recoverable while a lost verdict is not."""
    import urllib.request
    try:
        body = json.dumps({"model": "nomic-embed-text",
                           "prompt": "search_document: " + text[:2000]}).encode()
        req = urllib.request.Request("http://localhost:11434/api/embeddings", data=body,
                                     headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=20).read()).get("embedding") or None
    except Exception:
        return None


def semantic_prior(claim: str, entries: list | None = None) -> list:
    """Prior entries whose claim MEANS the same thing. Evidence, like family_prior -- never a block.

    Keyword families miss what they were not told about: a fourth LinUCB wording ("the optimism-based
    bandit algorithm of Chu et al. attains sublinear cumulative regret") contains neither 'linucb' nor
    'regret bound' and sailed past every lexical check, including the family list added to catch exactly
    it. Cosine on the local embedder scores it 0.81-0.84 against the other three.

    Thin margin, so this only ever stamps. See _SIM_THR.
    """
    entries = _load() if entries is None else entries
    v = _embed(claim or "")
    if not v:
        return []
    try:
        cache = json.loads(_VEC_CACHE.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    hits, dirty = [], False
    nv = sum(x * x for x in v) ** 0.5 or 1.0
    for r in entries:
        key = (r.get("lab_id") or "") + "|" + (r.get("claim") or "")[:40]
        pv = cache.get(key)
        if pv is None:
            pv = _embed(r.get("claim", ""))
            if not pv:
                continue
            cache[key], dirty = pv, True
        npv = sum(x * x for x in pv) ** 0.5 or 1.0
        if sum(a * b for a, b in zip(v, pv)) / (nv * npv) >= _SIM_THR:
            hits.append(r.get("lab_id") or "?")
    if dirty:
        try:
            _VEC_CACHE.write_text(json.dumps(cache), encoding="utf-8")
        except Exception:
            pass
    return sorted(set(hits))


def _save(items: list) -> None:
    try:
        _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


# Computational/methods topics where a published claim has a SIMULABLE core (a number, an
# exponent, a threshold, a rate) — the regime where replication can actually REPRODUCE or FAIL,
# instead of NOT_COMPUTABLE on a descriptive claim. Rotated so Rooke covers fresh ground.
_REPLICABLE_TOPICS = [
    "branching process critical exponent survival probability",
    "random graph percolation threshold giant component",
    "epidemic threshold network SIR basic reproduction number",
    "stochastic gradient descent convergence rate convex",
    "multi-armed bandit regret bound logarithmic",
    "directed percolation absorbing state phase transition exponent",
    "preferential attachment power-law degree exponent",
    "reinforcement learning sample complexity bound",
    "Kuramoto model synchronization critical coupling",
    "contagion cascade threshold fraction network",
]
# a sentence carries a REPLICABLE result if it has a number AND a result-signal word
_RESULT = re.compile(
    r"(\d+(?:\.\d+)?\s*%|\bexponent\b|\bthreshold\b|\bcritical\b|\bscal\w+\b|\brate\b|"
    r"\bbound\b|\bprobabilit\w+\b|\bconverge\w*\b|\bregret\b|\bpower[- ]law\b|"
    r"\d+(?:\.\d+)?\s*(?:times|x|fold)|=\s*\d|\bproportional to\b)", re.IGNORECASE)
_NUM = re.compile(r"\d")


def _best_claim(summ: str) -> tuple[str, int]:
    """The abstract sentence with the strongest measurable-result signal, and its score."""
    best, score = "", 0
    for s in re.split(r"(?<=[.!?])\s", summ):
        if len(s) < 50:
            continue
        sc = len(_RESULT.findall(s)) * 2 + (1 if _NUM.search(s) else 0)
        if sc > score:
            best, score = s[:240], sc
    return best, score


# Board-aligned topics for the CORPORATION's lead hunt — tuned to our actual Crucible content
# (the Operating-Point thesis: cognitive biases, statistical artifacts, finance, replication crisis),
# not just the physics-heavy replication rotation. These are where FAMOUS, contested, FAILED-likely
# claims live — the highest-value Crucible candidates.
_CORP_TOPICS = [
    "cognitive bias overconfidence calibration measured effect size",
    "replication crisis effect size psychology meta-analysis",
    "regression to the mean statistical artifact measurement",
    "behavioral finance anomaly return predictability out-of-sample",
    "heuristics and biases reasoning experiment quantitative",
    "wisdom of crowds aggregation accuracy correlation",
    "publication bias p-hacking effect size inflation",
    "forecasting calibration expert prediction accuracy",
    "nudge intervention effect size field experiment",
    "growth mindset intervention effect size meta-analysis",
    "power posing ego depletion replication effect",
    "diversification tail risk portfolio number of stocks",
]


# methods-boilerplate that scores on a bare number but carries NO testable result
_METHODS_NOISE = re.compile(
    r"\b(participants?|we identif\w+|literature search|studies for inclusion|sample of|"
    r"systematic review|inclusion criteria|we (?:perform|conduct|search))\b", re.IGNORECASE)
# a genuine RESULT signal (effect size / direction), not just any digit
_RESULT_STRONG = re.compile(
    r"(\bd\s*=\s*[-\d.]|\br\s*=\s*[-\d.]|\beffect size\b|\bincreas\w+ by\b|\breduc\w+ by\b|"
    r"\bcohen'?s d\b|\bodds ratio\b|\bcorrelat\w+ of\b|\d+(?:\.\d+)?\s*%|\bbeta\s*=|"
    r"\bexponent\b|\bthreshold\b|\bscal\w+\b|\bvanish\w+\b|\bdiverg\w+\b)", re.IGNORECASE)


def _scan_topic(topic: str, attempted: list) -> dict | None:
    """Best fresh measurable-RESULT paper for one topic, or None. Prefers a real effect/exponent
    over a methods sentence that merely contains a number (e.g. 'n = 28 participants')."""
    from agora.execution.research_tool import openalex_search, arxiv_search
    papers = [p for p in (arxiv_search(topic, 6) + openalex_search(topic, 4)) if not p.get("error")]
    best = None
    for p in papers:
        claim, score = _best_claim((p.get("summary") or "").strip())
        if score < 2 or len(claim) < 40:
            continue
        why = already_covered(claim, attempted)
        if why:
            print(f"  [replication] skipping candidate: {why} :: {claim[:70]}")
            continue
        if _METHODS_NOISE.search(claim) and not _RESULT_STRONG.search(claim):
            continue                                   # a methods sentence, not a testable result
        if _RESULT_STRONG.search(claim):
            score += 3                                 # prefer real effect/exponent claims
        if best is None or score > best["score"]:
            src = f"{p.get('title','')[:90]} ({p.get('authors','')[:50]}, {p.get('published','')[:10]})"
            best = {"claim": claim, "source": src[:160], "title": (p.get("title") or "")[:90],
                    "url": p.get("url", ""), "topic": topic, "score": score}
    return best


def pick_paper_target() -> dict | None:
    """A REAL arXiv paper with a quantitative, simulable claim — the input Rooke needs to produce
    a genuine REPRODUCED/FAILED. Tries the hour's physics-replication topic first, then the
    board-aligned corp topics in a rotated order, returning the first fresh measurable claim — so a
    single exhausted topic can no longer starve the pipeline (the corp 'exhausted sources' bug)."""
    attempted = _load()          # the ENTRIES, not a set of prefixes -- already_covered needs the claims
    pool = [_REPLICABLE_TOPICS[int(time.time() // 3600) % len(_REPLICABLE_TOPICS)]]
    r = int(time.time() // 1800) % len(_CORP_TOPICS)
    pool += _CORP_TOPICS[r:] + _CORP_TOPICS[:r]
    for topic in pool:
        hit = _scan_topic(topic, attempted)
        if hit:
            return hit
    return None


#: A negative admission the shared `is_non_finding` filter does not catch. Measured on the live pool:
#: "**Final finding:** None of the provided sources contain any data, analysis, or discussion" passed
#: it, and that is the most explicit statement of having nothing that the swarm produces.
_EMPTY_ADMISSION = re.compile(
    r"none of the (provided|cited|given) (sources?|papers?|abstracts?)|"
    r"contain no (data|analysis|discussion|evidence)|"
    r"(no|zero) substantive (claim|finding|result)", re.I)


def _is_non_finding(title: str, content: str) -> bool:
    """True when there is nothing here to reproduce or refute."""
    try:
        from agora.execution.non_finding import is_non_finding
        if is_non_finding(title, content):
            return True
    except Exception:
        pass                                   # the extra pattern below still applies
    return bool(_EMPTY_ADMISSION.search(content or ""))


async def pick_targets(db, n: int = 8) -> list:
    """SEVERAL replication targets, best first. Rooke's own instrument set decides which it can honestly
    model, so it must be able to walk PAST one it cannot.

    HEAD-OF-LINE BLOCKING, measured 2026-07-31. `pick_target` returned exactly one candidate and the
    endpoint offered no list, so a claim outside Rooke's instrument set wedged him permanently: four
    consecutive calls returned the same untestable claim ("The regrets do not rely on any scalarization
    functions and reflect Pareto optimality...", an empirical statement about an algorithm, not a
    quantity a minimal model can settle). He refused it correctly, got it again, refused it again. Over
    the preceding five days he produced ZERO discoveries, as did High Priest Orin, whose /theory/target
    has the same single-head shape; Shadow Kael, on single-head /scout-target, produced one. The three
    agents on head-only endpoints were the three that produced nothing.

    This is the SAME defect `belief-challenge-target` already fixed, and its comment says what it cost:
    "taking only the head is what wedged the challenge sweep for 42 days". The fix was never carried to
    the other endpoints. Same shape as the standing gate fixed in tools/autolinker.py and left in
    mcp_server.py -- a class repaired at one site and left alive at the others.
    """
    import asyncio as _aio
    out, seen = [], set()
    paper = await _aio.to_thread(pick_paper_target)
    if paper:
        out.append(paper)
        seen.add((paper.get("claim") or "")[:80])
    attempted = _load()
    cur = await db.execute(
        "SELECT title, content FROM collective_knowledge WHERE knowledge_type='discovery' "
        "AND content LIKE '%Source:%' ORDER BY created_at DESC LIMIT 120")
    for r in await cur.fetchall():
        if len(out) >= n:
            break
        content = (r["content"] or "").strip()
        claim = re.split(r"(?<=[.!?])\s", content)[0][:200]
        if len(claim) < 40 or claim[:80] in seen:
            continue
        # DO NOT ASK ROOKE TO REPLICATE OUR OWN NEGATIVE ADMISSIONS. Measured 2026-07-31: of the first
        # eight candidates this query returned, FIVE were the swarm's own non-findings -- "the provided
        # sources do not support the claim", "yields no substantive claim beyond restating", "None of
        # the provided sources contain any data". There is nothing in those to reproduce or refute, so
        # every one burns a cycle and returns an honest idle that looks like Rooke failing. The
        # promotion path already filters this exact shape (is_non_finding, and _NEGATIVE_PROMO in
        # promote_findings); this query read the same table without it.
        if _is_non_finding(r["title"] or "", content):
            continue
        if already_covered(claim, attempted):
            continue
        m = re.search(r"Source:\s*(.+)$", content, re.MULTILINE)
        source = (m.group(1).strip() if m else "")[:160]
        if not source:
            continue
        seen.add(claim[:80])
        out.append({"claim": claim, "source": source, "title": (r["title"] or "")[:90]})
    return out


async def pick_target(db) -> dict | None:
    """The replication target. PREFER a real arXiv paper with a simulable quantitative claim
    (Aldric's roadmap: feed Rooke real papers); fall back to a recent sourced internal finding.

    Kept as the head of `pick_targets` so existing callers keep working. A caller with its OWN gate
    must walk the list instead -- see pick_targets for what taking only the head cost.
    """
    import asyncio as _aio
    paper = await _aio.to_thread(pick_paper_target)
    if paper:
        return paper
    attempted = _load()
    cur = await db.execute(
        "SELECT title, content FROM collective_knowledge WHERE knowledge_type='discovery' "
        "AND content LIKE '%Source:%' ORDER BY created_at DESC LIMIT 60")
    rows = await cur.fetchall()
    for r in rows:
        content = (r["content"] or "").strip()
        claim = re.split(r"(?<=[.!?])\s", content)[0][:200]
        if len(claim) < 40:
            continue
        why = already_covered(claim, attempted)
        if why:
            print(f"  [replication] skipping internal candidate: {why}")
            continue
        m = re.search(r"Source:\s*(.+)$", content, re.MULTILINE)
        source = (m.group(1).strip() if m else "")[:160]
        if not source:
            continue
        return {"claim": claim, "source": source, "title": (r["title"] or "")[:90]}
    return None


# BY-CONSTRUCTION GATE (verdict-logic self-check on REPRODUCED). The Crucible audit (2026-07-05) found
# ~8 REPRODUCED verdicts that were not replications at all: a synthetic model that PLANTS the very
# structure the mechanism detects, re-derives a TAUTOLOGICAL identity, or otherwise GUARANTEES its own
# answer — so a FAILED was never a live possibility. A REPRODUCED whose note trips this (and carries no
# independent/real-data counter-signal) is auto-downgraded to NOT_COMPUTABLE — the honest bucket for
# "no genuinely-falsifiable computational replication was performed". Reversible: pass
# by_construction_checked=True to attest you verified it stands on independent evidence and record it as-is.
_BY_CONSTRUCTION = re.compile(
    r"(by[- ]construction|\bplanted\b|baked[- ]in|tautolog\w*|guaranteed by (?:design|construction|the)|"
    r"we (?:planted|built the interaction)|manufactur\w+ (?:the )?(?:ratio|result|answer)|"
    r"(?:reproduces?|manufactures?) (?:its|the) own (?:conclusion|answer|assumption)|"
    r"never (?:a )?live possibilit|impossible by (?:design|construction))", re.IGNORECASE)
# the reproduction rests on INDEPENDENT / REAL evidence, not a rigged synthetic setup → do not gate
_INDEPENDENT = re.compile(
    r"(real[- ]data|real \w+ (?:data|corpus|network|graph|votes)|\bSNAP\b|\bLoCoMo\b|held identical|"
    r"off[- ]critical|contrast class|not by[- ]construction|out[- ]of[- ]sample|independent\w*|"
    r"measured \w+ vs|on the (?:original|released|public) (?:data|dataset|votes))", re.IGNORECASE)


def by_construction_suspect(outcome: str, note: str) -> bool:
    """True when a REPRODUCED note reads as guaranteed-by-construction with no independent-data signal."""
    return ((outcome or "").strip().upper() == "REPRODUCED"
            and bool(_BY_CONSTRUCTION.search(note or "")) and not _INDEPENDENT.search(note or ""))


def record(claim: str, source: str, outcome: str, lab_id: str = "", note: str = "",
           by_construction_checked: bool = False) -> dict | None:
    o = (outcome or "").strip().upper()
    if o not in _OUTCOMES or len((claim or "").strip()) < 10:
        return None
    gated = False
    if not by_construction_checked and by_construction_suspect(o, note):
        o = "NOT_COMPUTABLE"
        note = ("[AUTO-GATED: verdict-logic self-check — reads as by-construction (planted/tautological/"
                "guaranteed), not a falsifiable replication; re-record with by_construction_checked=True if "
                "it stands on independent/real data] " + (note or ""))
        gated = True
    rec = {"claim": (claim or "")[:200], "source": (source or "")[:160], "outcome": o,
           "lab_id": (lab_id or "")[:12], "note": (note or "")[:300], "ts": time.time()}
    if gated:
        rec["auto_gated"] = "by_construction"
    items = _load()
    # Stamp prior entries in the same textbook family onto the record. Not a block -- see family_prior --
    # but the evidence the renderer's fatal duplicate check and the human declaration both need, computed
    # once, at the moment we actually know what was recorded.
    prior = family_prior(rec["claim"], items)
    if prior:
        rec["family_prior"] = prior[:8]
    sim = semantic_prior(rec["claim"], items)
    if sim:
        rec["similar_prior"] = sim[:8]
    items.append(rec)
    _save(items[-120:])
    # Stage 3 (accuracy loop): a hard external verdict credits the brain-memories about this claim —
    # REPRODUCED rewards knowledge consistent with verified results, FAILED debits knowledge tied to a
    # debunked claim. NOT_COMPUTABLE carries no signal (skip).
    if o in ("REPRODUCED", "FAILED"):
        try:
            from agora.execution.inspeximus_bridge import credit_outcome
            credit_outcome(claim, good=(o == "REPRODUCED"))
        except Exception:
            pass
    return rec


def format_replications() -> str:
    items = _load()
    if not items:
        return "⚗️ _No replication has been attempted yet — Rooke's bench is clean._"
    by = {o: sum(1 for x in items if x["outcome"] == o) for o in _OUTCOMES}
    lines = [f"⚗️ *The Replication Unit* — {by['REPRODUCED']} reproduced · "
             f"{by['FAILED']} failed · {by['NOT_COMPUTABLE']} passed"]
    icon = {"REPRODUCED": "✅", "FAILED": "💥", "NOT_COMPUTABLE": "⏭"}
    for r in items[-6:][::-1]:
        lines.append(f"{icon[r['outcome']]} {r['claim'][:64]}")
        if r.get("note"):
            lines.append(f"    {r['note'][:76]}")
    return "\n".join(lines)
