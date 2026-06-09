"""
Action Engine — knowledge into LEVERAGE.

Agora knows a lot, creates insights, predicts, and teaches — but produces no usable OUTPUT. This turns
its accumulated knowledge (vault notes, Claude insights, recent findings) on a theme into an artifact
a person can actually use: a decision/project brief, an essay draft, an action plan, or a technical
spec. Agora GATHERS the grounded material; Claude Opus DRAFTS the artifact (the flash model is too weak
for real writing). The leap from "knows things" to "PRODUCES things you use".
"""
from __future__ import annotations

import asyncio
from pathlib import Path

ARTIFACT_KINDS = {
    "brief": "a crisp DECISION / PROJECT BRIEF — the opportunity, why now, the proposed approach, "
             "the key risks, and the next 3 concrete steps",
    "essay": "a structured ESSAY draft — a sharp hook, 3-4 argued sections each with evidence from the "
             "material, and a conclusion that lands a point",
    "plan": "a concrete step-by-step ACTION PLAN — ordered milestones, what each one unlocks, and the "
            "first action to take this week",
    "spec": "a technical SPEC — the goal, the design, the components + interfaces, and a sensible "
            "build order",
}


async def gather_action_inputs(theme: str, kind: str, vault_path: str) -> dict:
    """Gather the grounded material (vault notes incl. Agora's insights + recent findings) for Claude
    to draft a usable artifact of the requested kind."""
    from agora.execution.semantic_index import SemanticIndex

    kind = (kind or "brief").lower().strip()
    si = SemanticIndex()
    hits = si.search(theme, 6) if si.ready else []
    root = Path(vault_path)
    vault = []
    for h in hits:
        try:
            txt = (root / h["path"]).read_text(encoding="utf-8", errors="replace")
            vault.append({"title": h["title"], "snippet": txt[:380]})
        except Exception:
            pass
    return {"theme": theme, "kind": kind,
            "kind_spec": ARTIFACT_KINDS.get(kind, ARTIFACT_KINDS["brief"]),
            "vault": vault, "kinds_available": list(ARTIFACT_KINDS)}


def parse_draft_request(text: str) -> tuple[str, str]:
    """Parse 'Draft <kind>: <theme>' / 'draft <kind>: <theme>' → (kind, theme)."""
    body = text.split(":", 1)
    head = body[0].lower().replace("draft", "").strip()
    kind = next((k for k in ARTIFACT_KINDS if k in head), "brief")
    theme = (body[1].strip() if len(body) > 1 else "").strip()
    return kind, theme
