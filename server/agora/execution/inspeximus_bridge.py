"""
INSPEXIMUS <-> brain bridge — the agents' shared memory, and the gate on who may contribute.

The owner's rule: any of the 8 agents may join a group seminar, but only if it GENUINELY has
something to add — and "genuinely" means its memory surfaces relevant knowledge. So INSPEXIMUS is wired
into the brain as the team's shared store: a contribution is remembered back into it, so the
memory compounds as the team works, and the next "can you contribute?" check is richer.

Uses the open-source inspeximus package (single-file, lexical recall at this scale — fast, no GPU). The
vault's semantic index is a bootstrap backstop so domain-relevant agents can contribute before the
shared store has warmed up. Dogfoods the mcp_memory product inside Agora's own loop.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[2]
_REPO = _SERVER.parent
_STORE_PATH = _SERVER / ".inspeximus_brain.json"
_SEED_FLAG = _SERVER / ".inspeximus_seeded.flag"

_store = None


def _inspeximus():
    """The shared brain store (lexical mode — no embedder, instant at a few hundred memories)."""
    global _store
    if _store is None:
        if str(_REPO) not in sys.path:
            sys.path.insert(0, str(_REPO))
        try:
            from inspeximus import Inspeximus
        except ImportError:                   # pre-1.25 install still under the old name
            from inspeximus import Inspeximus
        _store = Inspeximus(path=str(_STORE_PATH), embed=None)
    return _store


def seed_recent(db_path: str | None = None, cap: int = 250) -> int:
    """One-time-ish: seed the shared store from recent GROUNDED discoveries so it isn't empty at
    start. Idempotent via a flag file. Returns how many memories were added."""
    if _SEED_FLAG.exists():
        return 0
    import sqlite3
    m = _inspeximus()
    added = 0
    try:
        con = sqlite3.connect(f"file:{(_SERVER / 'agora.db').as_posix()}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT title, content, contributor_name FROM collective_knowledge "
            "WHERE knowledge_type='discovery' "
            "AND content LIKE '%Source%' ORDER BY rowid DESC LIMIT ?", (cap,)).fetchall()
        con.close()
        for title, content, who in rows:
            # NAME THE WRITER. Seeded without a source, every one of these is unreachable by
            # slash(scope='source') -- the default scope -- so a discovery later found to be poison
            # could not have its standing forfeited by the agent that produced it.
            txt = f"{(title or '').strip()}: {(content or '').strip()}"[:_CONTRIB_MAX_CHARS]
            if len(txt) > 30:
                m.remember(txt, tags=["seed", "discovery"], value=1.0,
                           source={"doc": "agent:%s" % who} if who else None)
                added += 1
    except Exception:
        pass
    try:
        _SEED_FLAG.write_text(str(added), encoding="utf-8")
    except Exception:
        pass
    return added


_CONTRIB_MAX_CHARS = 8000


def remember_contribution(claim: str, evidence: str = "", tags=None,
                          derived_from=None, source_doc: str = "") -> None:
    """Fold a fresh seminar Contribution back into the shared memory so it compounds.

    THREE things this used to drop, all measured on the live store 2026-07-31:

    * `derived_from` -- a Contribution is by construction a synthesis of the memories the contributing
      agents recalled, and those ids were available at the call site and thrown away. Coverage was
      0.00% of 3,228 records, so `slash()` had nothing to propagate along and the accountability lever
      could not reach a single derived conclusion.
    * `source` -- also 0.00%, which is worse: `slash(scope='source')`, the DEFAULT scope, resolves on
      exactly this field, so on our own deployment it matched nothing at all. A retraction lever that
      selects on a field no writer populates reports success and forfeits nothing.
    * the text past 500 characters. This is the third copy of that truncation found today (the others
      were in agent_os and mcp_server); it cut every contribution mid-sentence, and a claim cut before
      its falsifier is a claim that can no longer be tested.
    """
    try:
        txt = (claim + (" - " + evidence if evidence else "")).strip()
        if len(txt) > 25:
            _inspeximus().remember(
                txt[:_CONTRIB_MAX_CHARS], tags=list(tags or []) + ["contribution"], value=1.5,
                derived_from=list(derived_from) if derived_from else None,
                source={"doc": source_doc} if source_doc else None)
    except Exception:
        pass


def credit_outcome(subject: str, good: bool, k: int = 5, min_rel: float = 0.30,
                   warrant: str | None = None) -> dict:
    """Stage 3 of the accuracy loop (the one big bet): when an EXTERNAL verdict lands — a forecast
    resolves correct/wrong, a replication is ruled REPRODUCED/FAILED — credit the brain-memories most
    relevant to that subject by the outcome, so the substrate re-ranks by WAS-IT-RIGHT (knowledge tied
    to verified results rises; knowledge tied to debunked claims fades). Recall-at-resolution with a
    STRONG relevance floor (0.30, above the contribution gate) so only clearly-on-subject memories take
    the signal — a defensible proxy for the exact grounding without creation-time recall-set stamping.

    `warrant` NAMES THE EXOGENOUS ARTIFACT that produced the verdict — `prediction:<id>` for a resolved
    ledger entry, `lab:<lab_id>` for a Lab run. It is what separates a verdict the world handed us from
    a grade we handed ourselves, and it is the sole input to `good_warranted`, which
    `credit_requires_warrant` reads to block the MINJA self-graded-outcome loop.

    Measured 2026-08-09 and the reason this parameter now exists: across 220,213 records in this
    deployment, `good` was populated on 470 and `good_warranted` on **0**. The credit loop was live and
    every single good credit was unwarranted — not because our verdicts are self-graded (these two are
    genuinely external) but because no caller could say so. A guard whose input no caller can supply
    reports SAFE forever.

    PASS A WARRANT ONLY FOR A RE-CHECKABLE ARTIFACT. `None` is the correct value when the outcome was
    graded by our own heuristics; forging a token to make coverage non-zero would fake the exact signal
    the guard exists to test, and would be worse than the 0% it replaces.
    """
    try:
        m = _inspeximus()
        hits = m.recall(subject or "", k=k)
        ids = [h["id"] for h in hits if h.get("relevance", 0) >= min_rel]
        if not ids:
            return {"updated": [], "reason": "no strongly-relevant memory"}
        return m.credit(ids, "good" if good else "bad", warrant=warrant)
    except Exception as e:
        return {"error": str(e)[:100]}


def consolidate_brain_memory() -> dict:
    """The dream pass on the shared brain store: link near-duplicate memories + state-toggle
    contradictions. Raw text is immutable and nothing is dropped (keep=None) — it only ADDS links /
    supersede markers. The dungeon agents already run this on their stores; this brings the brain's
    store the same hygiene so links compound as it grows. Returns the consolidation stats."""
    try:
        return _inspeximus().consolidate()      # keep=None -> never drops; links + state-toggles only
    except Exception as e:
        return {"error": str(e)[:120]}


def agent_can_contribute(role_hint: str, topic: str, min_rel: float = 0.22) -> tuple[bool, str, list]:
    """Can this agent genuinely add to the topic? True only if its memory (shared INSPEXIMUS, or the
    vault as a bootstrap backstop) surfaces relevant knowledge.

    Returns (can, context_snippets, recalled_ids). The third element is the LINEAGE: the memories this
    agent actually read to form its contribution. It used to be dropped on the floor, and dropping it is
    why `derived_from` coverage measured 0.00% across all 3,228 records in the live store on 2026-07-31 --
    every contribution was written as a fresh primary observation with no parents, so `slash()` had no
    edges to walk and a retraction could not reach a single conclusion built on the retracted memory.
    The lever we describe as the moat was inert on our own data because nothing upstream declared what
    it was built from."""
    query = f"{role_hint} {topic}".strip()
    # 1) shared INSPEXIMUS recall (the team's accumulated knowledge)
    try:
        hits = _inspeximus().recall(query, k=3)
        strong = [h for h in hits if h.get("relevance", 0) >= min_rel]
        if strong:
            ctx = " | ".join(h["text"][:160] for h in strong[:2])
            return True, ctx, [h["id"] for h in strong if h.get("id")]
    except Exception:
        pass
    # 2) bootstrap backstop: the user's vault (semantic) — so domain-relevant agents can start.
    # A vault note is NOT an inspeximus record, so it cannot be a `derived_from` parent; it is named as
    # the SOURCE instead, which is the field slash(scope='source') resolves on.
    try:
        from agora.execution.semantic_index import SemanticIndex
        notes = [h for h in SemanticIndex().search(query, top_k=3) if h.get("score", 0) >= 0.52]
        if notes:
            ctx = "relevant notes: " + "; ".join(f"[[{n['title']}]]" for n in notes[:3])
            return True, ctx, []
    except Exception:
        pass
    return False, "", []
