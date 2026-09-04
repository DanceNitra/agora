"""
The Frontier — push research toward the EDGE of the vault, not its dense centre.

Agents churn: they re-derive the same already-dense clusters because their seeds are static gaps
and recent (themselves-churned) findings. The dedup correctly rejects the duplicates, but the
fix is upstream — aim the agents at what is UNDER-explored. This reuses the Cartographer's vault
scan to surface a frontier target: a thin (barely-developed) knowledge domain to grow, or a
structural hole between two domains to bridge. A small ledger rotates targets so the frontier
itself doesn't churn. Novelty becomes the default direction of research.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".frontier.json"
_COOL = 6 * 3600          # don't re-seed the same frontier target within 6h


def _json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    try:
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    try:
        _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _recent_targets(now: float) -> set:
    return {x["target"] for x in _load() if now - x.get("ts", 0) < _COOL}


def _candidate_pool(vault: str):
    """Gather a DIVERSE pool of raw research directions for the intelligent selector to rank:
    thin domains (underdeveloped corners) + structural holes (unbridged domain pairs)."""
    from agora.execution.cartography import _scan
    note_domain, domain_notes, bridges = _scan(vault)
    real = {d: len(ns) for d, ns in domain_notes.items() if d not in ("(unfiled)", "(root)")}
    thin = sorted([(c, d) for d, c in real.items() if 1 <= c <= 8])[:8]
    big = {d: c for d, c in real.items() if c >= 8}
    doms = sorted(big)
    holes = []
    for i, a in enumerate(doms):
        for b in doms[i + 1:]:
            if bridges.get(tuple(sorted((a, b))), 0) == 0:
                holes.append((big[a] + big[b], a, b))
    holes.sort(reverse=True)
    return thin, holes[:8], len(real)


def _smart_frontier(vault: str, explore: bool) -> dict | None:
    """INTELLIGENT target selection (owner 2026-07-16): a reasoning-tier CRO picks the SINGLE next research
    direction that moves the whole org forward the most — scoring impact / novelty / buildability /
    compounding / alignment over a diverse candidate pool, COMPOUNDING on our moat (agent memory, inspeximus,
    the Crucible) by default, with a ~30% bold broad-frontier exploration slice. Replaces the hourly
    thin/hole rotation. Reversible: AGORA_SMART_FRONTIER=0 falls back to _rotation_target."""
    from agora.execution.llm_client import call_llm
    thin, holes, ndoms = _candidate_pool(vault)
    if ndoms < 2:
        return None
    recent = _recent_targets(time.time())
    # MOAT VEIN (owner 2026-07-18): the vault candidate pool is dominated by abstract complexity/network toy
    # gaps that pass the Lab gate but re-derive textbook results (Condorcet, Griffiths) and never touch the
    # product. Seed the pool with the CONCRETE, business-critical agent-memory vein validated by hand this
    # session — measurable competitor-weakness probes + inspeximus-capability questions. Each is a runnable head-to-
    # head that builds the #1 product, not an isolated toy fact. In COMPOUND MODE the CRO must PREFER these.
    moat_vein = (
        "MOAT VEIN — concrete, runnable agent-memory / inspeximus product questions (PREFER these in compound mode; "
        "each competitor weakness is a fair, measurable head-to-head vs inspeximus):\n"
        "- Run-to-run NONDETERMINISM: fraction of subjects whose stored/returned value flips across identical "
        "re-ingests, for mem0/Zep/Letta/Cognee (LLM on write path) vs inspeximus's deterministic core (=0).\n"
        "- CORRECTION-UNDER-POISON (FAIR contract: raw text for all, each extracts, shared LLM judge): after a "
        "genuine correction, an adversarial re-assertion of the retired value as the newest write — measure "
        "poison-rejection AND legit-new-value-adoption, inspeximus vs mem0.\n"
        "- WRITE-COMPLETION across LLM backends: silent fact-drop rate of mem0/Letta extraction on "
        "Qwen/Ollama/Mistral vs inspeximus's backend-agnostic write.\n"
        "- INGEST COST/LATENCY per write: LLM calls + tokens + ms for Graphiti/Cognee (cognify) vs inspeximus ~0.\n"
        "- MEMORY-POISONING ASR reduction of inspeximus's warrant-gate on an ASB/MINJA-style attack vs an "
        "undefended vector store, fair identical stream.\n"
        "- REPRODUCE a published agent-memory benchmark (LoCoMo / LongMemEval / MemoryAgentBench) with a "
        "runnable fixed-seed harness that shows WHERE each system loses, honestly scoped.\n"
        "- inspeximus SEMANTIC-KEYING: does embedding-resolved keys let deterministic supersession survive "
        "paraphrased conflicts where exact-key match fails? measure vs a plain-extractor baseline.\n")
    pool = (moat_vein
            + "\n\nTHIN vault domains (underdeveloped — deprioritize abstract complexity/network toys here):\n"
            + ("\n".join(f"- {d} ({c} notes)" for c, d in thin) or "- (none)")
            + "\n\nSTRUCTURAL HOLES (substantial domains with no bridge):\n"
            + ("\n".join(f"- {a} <-> {b}" for _s, a, b in holes) or "- (none)"))
    recent_txt = "; ".join(list(recent)[:12]) or "(none)"
    mode = ("EXPLORE MODE: pick a BOLD broad-frontier bet — a high-novelty, high-impact question that "
            "could open a whole new field for us, even if it is not yet on our edge."
            if explore else
            "COMPOUND MODE: pick a MOAT-VEIN question (a concrete, runnable competitor-weakness head-to-head or "
            "an inspeximus-capability measurement from the MOAT VEIN list) — one that directly builds the inspeximus #1 "
            "product and earns credibility/income. STRONGLY prefer the MOAT VEIN over abstract vault toy-gaps; "
            "only pick a vault domain if it is genuinely more product-critical than every moat-vein item.")
    sys = (
        "You are the Chief Research Officer of Agora, an autonomous research organization. Our MOAT is "
        "agent memory, the inspeximus open-source memory library, and the Crucible replication ledger; our "
        "frontier is the Science of Better Thinking and the Future of Work & Society. Choose the SINGLE "
        "best NEXT research direction to move the whole organization forward the most — think exponential "
        "leverage, not one isolated fact. Judge candidates on IMPACT (would answering it matter 10x?), "
        "NOVELTY (genuinely open, not a textbook/named-law re-derivation), BUILDABILITY (settleable with a "
        "small computational model or real data + a falsifier), COMPOUNDING (builds on our moat, opens more "
        "doors, creates leverage), and ALIGNMENT. " + mode + " Do NOT pick anything close to these "
        f"recently-seeded targets: {recent_txt}. You may pick from the vault candidates below, or propose a "
        "SHARPER direction they inspire. Reply ONLY JSON: {\"target\":\"<short name>\",\"kind\":\""
        "<thin_domain|hole|moat|frontier>\",\"prompt\":\"<one sharp directive: exactly what a researcher "
        "should produce, with a measurable result + falsifier>\",\"why\":\"<one line: why this moves us "
        "the most>\"}.")
    raw = call_llm(sys, pool, "medium", 0.6, 1500)
    d = _json(raw)
    tgt = str(d.get("target", "")).strip()
    if not tgt:
        return None
    # PRIOR-ART GATE on the SELECTION (owner 2026-07-16, flag AGORA_NOVELTY_GATE): the selector optimizes
    # for compelling + on-moat but NOT for "already published" — it can (and did: 'Memory as Causal
    # Laboratory' = CausalFlow/CMI) propose an occupied field. Check the literature; if occupied, re-select
    # ONCE toward a genuinely-open angle OR an explicit Crucible REPLICATION / stress-test of a recent claim
    # (finding where it breaks is also our moat). Fail-open.
    if os.getenv("AGORA_NOVELTY_GATE", "1") != "0":
        occ, ref = _direction_occupied(tgt, str(d.get("prompt", "")))
        if occ:
            raw2 = call_llm(
                sys + f"\n\nIMPORTANT: your pick '{tgt}' is ALREADY an active published field ({ref}). Do "
                "NOT propose to invent it. Instead pick a GENUINELY OPEN direction, OR propose a Crucible "
                "REPLICATION / adversarial stress-test of a SPECIFIC recent claim (name it; find the regime "
                "where it BREAKS) — independent replication is our moat and nobody has done it.",
                pool, "medium", 0.7, 1500)
            d2 = _json(raw2)
            if str(d2.get("target", "")).strip():
                d = d2
                tgt = str(d.get("target", "")).strip()
    return {"kind": str(d.get("kind", "frontier"))[:20], "target": tgt[:120],
            "prompt": str(d.get("prompt", ""))[:1000], "why": str(d.get("why", ""))[:300]}


def _direction_occupied(target: str, prompt: str):
    """Prior-art check for a chosen research direction: is it already an active, published field (someone
    has built essentially this)? Returns (occupied: bool, reference: str). Fail-open (False) on error so the
    frontier never starves.

    HARDENED (owner 2026-07-16): the old single-query, 2-arXiv-result, cheap-judge version repeatedly PASSED
    already-occupied fields (missed Prism 2604.19795 for 'evolutionary memory' and Forensic 2606.30566 for
    'poison-detection') because the closest prior art is recent arXiv preprints under DIFFERENT terminology.
    Fixes: (1) THREE query angles — the target name, the mechanism phrase, and their join — so a paper is
    caught even if it renames the idea; (2) deeper arXiv (6/query, where 2026 preprints live) + OpenAlex for
    breadth; (3) a stricter medium-tier judge told a CLOSE/differently-worded match counts and to ERR TOWARD
    OCCUPIED (a false-positive only costs a re-pick; a miss wastes a whole research cycle)."""
    try:
        from agora.execution.research_tool import (arxiv_search, openalex_search, format_for_prompt,
                                                    distill_query)
        from agora.execution.llm_client import call_llm
        mech = re.sub(r"\s+", " ", prompt or "").strip()[:140]          # the "what to produce" core
        queries = [target[:120], mech, (target + " " + mech)[:160]]
        seen, papers = set(), []
        for q in queries:
            if not q.strip():
                continue
            kw = distill_query(q)
            for p in arxiv_search(kw, 6) + openalex_search(kw, 4):
                if p.get("error"):
                    continue
                key = (p.get("title") or "")[:80].lower()
                if key and key not in seen:
                    seen.add(key); papers.append(p)
            if len(papers) >= 18:
                break
        # ALSO hit the broad web (Semantic Scholar / Tavily / Crossref / HF / DDG) — the arXiv+OpenAlex
        # keyword APIs are brittle and miss recent preprints under renamed terminology (they missed Prism
        # 2604.19795 entirely; web_search found it via Tavily). This is the retrieval half of the fix.
        web_block = ""
        try:
            from agora.execution.web_search import web_search
            wr = web_search((target + " " + mech)[:180], 5).get("results", [])
            web_block = "\n".join(f"- {w.get('title','')}: {(w.get('snippet') or '')[:180]}" for w in wr[:10])
        except Exception:
            pass
        if not papers and not web_block:
            return (False, "")
        raw = call_llm(
            "You are a PRIOR-ART GATE for an autonomous research org. Given the RESEARCH DIRECTION and REAL "
            "abstracts + web hits, decide if the direction is ALREADY OCCUPIED: does any listed work already "
            "do essentially this, OR publish its core mechanism/framing — EVEN under different terminology or "
            "in an adjacent domain? A CLOSE match counts. ERR TOWARD OCCUPIED: a false 'occupied' only costs a "
            "re-pick, but a missed one wastes an entire research cycle. Reply ONLY JSON: "
            "{\"occupied\":true|false,\"ref\":\"<closest work: author/short-title/year + arxiv-id, or empty>\"}.",
            f"RESEARCH DIRECTION: {target} — {prompt[:400]}\n\nREAL ABSTRACTS:\n{format_for_prompt(papers)}"
            + (f"\n\nWEB HITS:\n{web_block}" if web_block else ""),
            "medium", 0.0, 250)
        dd = _json(raw)
        return (bool(dd.get("occupied")), str(dd.get("ref", ""))[:120])
    except Exception:
        return (False, "")


def frontier_target(vault: str) -> dict | None:
    """Intelligent CRO selection (default) with the hourly thin/hole rotation as fallback."""
    if os.getenv("AGORA_SMART_FRONTIER", "1") != "0":
        try:
            explore = int(time.time()) % 10 < 1          # ~10% explore (was 30%): retarget to the moat vein,
            #                                              the 90% compound slice now mines agent-memory product Qs
            r = _smart_frontier(vault, explore)
            if r:
                return r
        except Exception as e:
            print(f"[frontier] smart-select failed, falling back to rotation: {e}")
    return _rotation_target(vault)


def _rotation_target(vault: str) -> dict | None:
    """An under-explored target: a THIN domain to develop or a structural HOLE to bridge.
    Alternates by the hour and skips targets seeded in the last 6h (so the frontier rotates)."""
    from agora.execution.cartography import _scan
    now = time.time()
    recent = _recent_targets(now)
    try:
        note_domain, domain_notes, bridges = _scan(vault)
    except Exception:
        return None

    real = {d: ns for d, ns in domain_notes.items() if d not in ("(unfiled)", "(root)")}
    if len(real) < 2:
        return None

    # alternate: even hours hunt a THIN domain, odd hours a structural HOLE
    if int(now // 3600) % 2 == 0:
        # thin = a real domain with the FEWEST notes (a barely-developed corner), not yet seeded
        thin = sorted(((len(ns), d) for d, ns in real.items() if 1 <= len(ns) <= 8),
                      key=lambda x: x[0])
        for cnt, d in thin:
            if d not in recent:
                return {"kind": "thin_domain", "target": d, "size": cnt,
                        "prompt": f"The '{d}' area of the vault is thin ({cnt} notes) — develop it "
                                  f"with a NEW, specific finding that deepens it, not a restatement."}
    # the widest structural hole between two substantial domains with no bridge
    big = {d: len(ns) for d, ns in real.items() if len(ns) >= 8}
    doms = sorted(big)
    holes = []
    for i, a in enumerate(doms):
        for b in doms[i + 1:]:
            nb = bridges.get(tuple(sorted((a, b))), 0)
            if nb == 0:
                holes.append((big[a] + big[b], a, b))
    holes.sort(reverse=True)
    for _sz, a, b in holes:
        key = f"{a} <-> {b}"
        if key not in recent:
            return {"kind": "hole", "target": key, "a": a, "b": b,
                    "prompt": f"'{a}' and '{b}' are both substantial vault domains with NO link "
                              f"between them — produce a finding that genuinely bridges them via a "
                              f"shared mechanism (not surface similarity)."}
    return None


# The window this ledger keeps. It used to be 80 rows, which on a busy day is a few hours: the
# organ that selects our research direction is the second largest spender in the brain, 3.47M
# tokens over 794 calls, and its entire history was 80 lines long, all of them from the same day.
# A selector whose choices cannot be reviewed cannot be judged, and the cap was silently deciding
# that. 4,000 rows is roughly a year at the observed rate and costs a few hundred kilobytes.
_KEEP = 4000


def record_seeded(target: str, kind: str = "") -> None:
    items = _load()
    items.append({"target": (target or "")[:120], "kind": kind[:20], "ts": time.time()})
    _save(items[-_KEEP:])


def format_frontier() -> str:
    items = _load()
    if not items:
        return "🧭 _No frontier target seeded yet._"
    lines = [f"🧭 *The Frontier* — {len(items)} edge-targets seeded"]
    for x in items[-6:][::-1]:
        lines.append(f"• [{x.get('kind','?')}] {x['target'][:60]}")
    return "\n".join(lines)
