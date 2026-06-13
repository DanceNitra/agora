"""
MNEMO ↔ brain bridge — the agents' shared memory, and the gate on who may contribute.

The owner's rule: any of the 8 agents may join a group seminar, but only if it GENUINELY has
something to add — and "genuinely" means its memory surfaces relevant knowledge. So MNEMO is wired
into the brain as the team's shared store: a contribution is remembered back into it, so the
memory compounds as the team works, and the next "can you contribute?" check is richer.

Uses the open-source mnemo module (single-file, lexical recall at this scale — fast, no GPU). The
vault's semantic index is a bootstrap backstop so domain-relevant agents can contribute before the
shared store has warmed up. Dogfoods the mcp_memory product inside Agora's own loop.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[2]
_REPO = _SERVER.parent
_STORE_PATH = _SERVER / ".mnemo_brain.json"
_SEED_FLAG = _SERVER / ".mnemo_seeded.flag"

_store = None


def _mnemo():
    """The shared brain store (lexical mode — no embedder, instant at a few hundred memories)."""
    global _store
    if _store is None:
        if str(_REPO) not in sys.path:
            sys.path.insert(0, str(_REPO))
        from mnemo.mnemo import Mnemo
        _store = Mnemo(path=str(_STORE_PATH), embed=None)
    return _store


def seed_recent(db_path: str | None = None, cap: int = 250) -> int:
    """One-time-ish: seed the shared store from recent GROUNDED discoveries so it isn't empty at
    start. Idempotent via a flag file. Returns how many memories were added."""
    if _SEED_FLAG.exists():
        return 0
    import sqlite3
    m = _mnemo()
    added = 0
    try:
        con = sqlite3.connect(f"file:{(_SERVER / 'agora.db').as_posix()}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT title, content FROM collective_knowledge WHERE knowledge_type='discovery' "
            "AND content LIKE '%Source%' ORDER BY rowid DESC LIMIT ?", (cap,)).fetchall()
        con.close()
        for title, content in rows:
            txt = f"{(title or '').strip()}: {(content or '').strip()}"[:500]
            if len(txt) > 30:
                m.remember(txt, tags=["seed", "discovery"], value=1.0)
                added += 1
    except Exception:
        pass
    try:
        _SEED_FLAG.write_text(str(added), encoding="utf-8")
    except Exception:
        pass
    return added


def remember_contribution(claim: str, evidence: str = "", tags=None) -> None:
    """Fold a fresh seminar Contribution back into the shared memory so it compounds."""
    try:
        txt = (claim + (" — " + evidence if evidence else "")).strip()
        if len(txt) > 25:
            _mnemo().remember(txt[:500], tags=list(tags or []) + ["contribution"], value=1.5)
    except Exception:
        pass


def agent_can_contribute(role_hint: str, topic: str, min_rel: float = 0.22) -> tuple[bool, str]:
    """Can this agent genuinely add to the topic? True only if its memory (shared MNEMO, or the
    vault as a bootstrap backstop) surfaces relevant knowledge. Returns (can, context_snippets)."""
    query = f"{role_hint} {topic}".strip()
    # 1) shared MNEMO recall (the team's accumulated knowledge)
    try:
        hits = _mnemo().recall(query, k=3)
        strong = [h for h in hits if h.get("relevance", 0) >= min_rel]
        if strong:
            ctx = " | ".join(h["text"][:160] for h in strong[:2])
            return True, ctx
    except Exception:
        pass
    # 2) bootstrap backstop: the user's vault (semantic) — so domain-relevant agents can start
    try:
        from agora.execution.semantic_index import SemanticIndex
        notes = [h for h in SemanticIndex().search(query, top_k=3) if h.get("score", 0) >= 0.52]
        if notes:
            ctx = "relevant notes: " + "; ".join(f"[[{n['title']}]]" for n in notes[:3])
            return True, ctx
    except Exception:
        pass
    return False, ""
