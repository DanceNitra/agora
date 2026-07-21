"""
THE IDEA FORGE — turn EVERYTHING the brain knows into groundbreaking, buildable ideas.

Agora already has narrow idea engines: the insight engine (one new claim from vault+lit+data),
the synthesis organ (unify >=3 findings), hypothesis induction, the analogy forge. They each
look at a SLICE. This organ is the wide-angle complement: it gathers the brain's WHOLE rigorous
cross-section — the canon laws, the strongest beliefs, the lessons learned, the reproduced AND
failed replications, the analogies and theory runs, the frontier targets, what the Library has
actually read, and the freshest findings — and hands the lot to the strong model (Claude) to
generate GROUNDBREAKING, non-obvious ideas aimed at four standing targets:

    - SYSTEM / OS    : the agent operating system & dungeon substrate
    - AGORA          : the epistemic engine itself (organs, loops, quality)
    - MCP MEMORY     : the memory product (inspeximus / second-brain-as-a-service)
    - REAL-WORLD     : a shippable product the outside world would pay for

The established division of labour holds: AGORA GATHERS, CLAUDE CREATES. This module is the
gather half — read-only over every existing ledger, defensively wrapped so a single missing
source can never break the payload. The only state it writes is its own idea ledger
(.ideation.json), used to dedup so the forge never repeats itself.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_STORE = _ROOT / ".ideation.json"

# The four standing targets the forge aims at. Stable IDs so the ledger and the skill agree.
TARGETS = [
    {"id": "os", "name": "System / OS",
     "framing": "the agent operating system & dungeon substrate that runs the agents — "
                "scheduling, memory, coordination, the loop, robustness, observability"},
    {"id": "agora", "name": "Agora epistemic engine",
     "framing": "Agora itself as a knowledge-creating organism — new organs, sharper loops, "
                "higher-yield research, better quality firewalls, compounding mechanisms"},
    {"id": "mcp_memory", "name": "MCP memory product",
     "framing": "the memory product (inspeximus / second-brain-as-a-service over MCP) — how an "
                "external user's notes become a thinking partner; retrieval, consolidation, recall"},
    {"id": "realworld", "name": "Real-world product",
     "framing": "a shippable product the outside world would pay for, grounded in what the vault "
                "has actually proven — a tool, a service, a method someone outside Agora needs"},
]


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


def record_idea(title: str, target: str, mechanism: str = "", test: str = "",
                first_step: str = "", grounding: str = "", note: str = "") -> dict:
    """Append one generated idea to the ledger (dedup substrate + public trail)."""
    items = _load()
    rec = {
        "title": (title or "").strip()[:160],
        "target": (target or "").strip(),
        "mechanism": (mechanism or "").strip()[:600],
        "test": (test or "").strip()[:400],
        "first_step": (first_step or "").strip()[:400],
        "grounding": (grounding or "").strip()[:400],
        "note": (note or "").strip()[:240],
        "ts": time.time(),
    }
    items.append(rec)
    _save(items)
    return {"recorded": rec["title"], "target": rec["target"], "total": len(items)}


def recent_idea_titles(days: int = 30) -> list[str]:
    """Titles generated within the window — the anti-repeat set handed to the skill."""
    cut = time.time() - days * 86400
    return [x.get("title", "") for x in _load() if x.get("ts", 0) >= cut and x.get("title")]


def format_ideas(n: int = 12) -> str:
    items = _load()[-n:]
    if not items:
        return "🧠 Idea Forge — no ideas generated yet."
    lines = ["🧠 *Idea Forge* — recent groundbreaking ideas:"]
    for it in reversed(items):
        tgt = it.get("target", "?")
        lines.append(f"• [{tgt}] {it.get('title','')}")
    return "\n".join(lines)


def _safe(fn, default):
    """Run a gather closure; never let one source's failure poison the whole payload."""
    try:
        return fn()
    except Exception as e:  # pragma: no cover - defensive
        return {"_error": str(e)[:120]} if isinstance(default, dict) else default


async def gather_ideation_inputs(db, vault_path: str) -> dict:
    """Compose the brain's WHOLE rigorous cross-section as raw material for groundbreaking ideas.
    Every source is wrapped: a missing ledger degrades that one field, never the call."""
    out: dict = {"targets": TARGETS}

    # --- owner steering + the laws + metacognition ---------------------------------------
    def _priorities():
        from agora.execution.board import priorities_text
        return priorities_text()
    out["owner_priorities"] = _safe(_priorities, "")

    def _canon():
        from agora.execution.canon import read_canon
        return (read_canon(vault_path) or "")[:3500]
    out["canon"] = _safe(_canon, "")

    def _lessons():
        from agora.execution.learning import lessons_text
        return lessons_text()
    out["lessons"] = _safe(_lessons, "")

    # --- beliefs + calibration (the Agora Mind) ------------------------------------------
    try:
        from agora.execution.mind import gather_mind_state
        ms = await gather_mind_state(vault_path)
        out["beliefs"] = (ms.get("beliefs") or [])[-12:]
        out["calibration"] = ms.get("calibration")
        out["open_tensions"] = (ms.get("tensions") or ms.get("open_tensions") or [])[:6]
    except Exception as e:
        out["beliefs"], out["calibration"] = [], None
        out["_mind_error"] = str(e)[:120]

    # --- the rigorous ledgers: replications (split repro/failed), analogies, theory ------
    def _reps():
        from agora.execution.replication import _load as rl
        items = rl()
        repro = [r for r in items if str(r.get("outcome", "")).upper() == "REPRODUCED"][-8:]
        failed = [r for r in items if str(r.get("outcome", "")).upper() == "FAILED"][-8:]
        slim = lambda r: {"claim": (r.get("claim", "") or "")[:200],
                          "outcome": r.get("outcome", ""), "note": (r.get("note", "") or "")[:160]}
        return {"reproduced": [slim(r) for r in repro], "failed": [slim(r) for r in failed]}
    out["replications"] = _safe(_reps, {"reproduced": [], "failed": []})

    def _analogies():
        from agora.execution.analogy_forge import _load as al
        return [{"mechanism": (a.get("mechanism", "") or "")[:140],
                 "target": (a.get("target", "") or "")[:80],
                 "outcome": a.get("outcome", "")} for a in al()[-8:]]
    out["analogies"] = _safe(_analogies, [])

    def _theory():
        from agora.execution.theory import _load as tl
        return [{"belief": (t.get("belief", t.get("path", "")) or "")[:140],
                 "verdict": t.get("verdict", "")} for t in tl()[-8:]]
    out["theory_runs"] = _safe(_theory, [])

    # --- forward signals: synthesis precursors + the frontier + library reading ----------
    def _synth():
        from agora.execution.synthesis_detector import signals
        return signals()
    out["synthesis_signals"] = _safe(_synth, {})

    def _frontier():
        from agora.execution.frontier import format_frontier
        return format_frontier()
    out["frontier"] = _safe(_frontier, "")

    def _library():
        from agora.execution.library import format_library
        return format_library(8)
    out["library_read"] = _safe(_library, "")

    # --- the freshest raw findings (what the agents just grounded) ------------------------
    try:
        cur = await db.execute(
            "SELECT title, content, contributor_name FROM collective_knowledge "
            "WHERE knowledge_type='discovery' AND length(content) > 80 "
            "ORDER BY created_at DESC LIMIT 40")
        rows = await cur.fetchall()
        out["recent_findings"] = [
            {"title": (r[0] or "")[:120], "snippet": (r[1] or "")[:220], "by": r[2] or ""}
            for r in rows]
    except Exception as e:
        out["recent_findings"] = []
        out["_findings_error"] = str(e)[:120]

    # --- the WHOLE vault corpus: semantic coverage per target (the ~6000 notes) -----------
    # The findings above are what the AGENTS recently grounded; this taps everything the OWNER's
    # second brain holds. For each standing target we pull its most relevant real notes from the
    # full corpus, so the forge stands on the vault's depth, not just the recent stream.
    try:
        import asyncio
        from pathlib import Path as _Path
        from agora.execution.semantic_index import SemanticIndex

        def _vault_coverage() -> dict:
            si = SemanticIndex()
            if not si.ready:
                return {"indexed_notes": 0, "by_target": {}}
            root = _Path(vault_path)
            by_target = {}
            for t in TARGETS:
                hits = si.search(t["framing"], 3)
                snips = []
                for h in hits:
                    try:
                        txt = (root / h["path"]).read_text(encoding="utf-8", errors="replace")
                        snips.append({"title": h.get("title", ""), "snippet": txt[:240]})
                    except Exception:
                        snips.append({"title": h.get("title", ""), "snippet": ""})
                by_target[t["id"]] = snips
            return {"indexed_notes": len(si.meta), "by_target": by_target}

        out["vault_corpus"] = await asyncio.to_thread(_vault_coverage)
    except Exception as e:
        out["vault_corpus"] = {"indexed_notes": 0, "by_target": {}, "_error": str(e)[:120]}

    # --- the anti-repeat set: what the forge already proposed -----------------------------
    out["recent_idea_titles"] = recent_idea_titles(30)
    return out
