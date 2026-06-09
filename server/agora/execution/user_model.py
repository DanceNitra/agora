"""
Personal Context Model — Agora knows YOU.

A generic engine treats every topic the same. This builds a concise, evolving model of the vault's
owner — their domains, the projects/goals they seem to be building toward, and their intellectual
style — inferred from their own notes. Other parts of Agora read it to personalise: bias research and
gaps toward the user's actual focus, tailor insights and teaching to who they are. The second-brain
becomes YOUR partner, not a generic engine.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import random
from pathlib import Path

_MODEL = Path(__file__).resolve().parents[2] / ".user_model.json"


def get_model() -> dict:
    try:
        return json.loads(_MODEL.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(m: dict) -> None:
    try:
        _MODEL.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


async def build_user_model(vault_path: str, force: bool = False) -> dict:
    """Infer the owner's domains / projects / style from their vault. Cached ~daily."""
    cached = get_model()
    if cached and not force and (time.time() - cached.get("ts", 0)) < 86400:
        return cached

    from agora.execution.semantic_index import SemanticIndex
    from agora.execution.llm_client import call_llm
    si = SemanticIndex()
    titles = [m.get("title", "") for m in getattr(si, "meta", [])] if si.ready else []
    titles = [t for t in titles if t and "Agora Agents" not in t]
    sample = random.sample(titles, min(140, len(titles))) if titles else []
    raw = await asyncio.to_thread(
        call_llm,
        "Below are titles of notes from a person's personal knowledge vault. Infer a concise, specific "
        "MODEL of this person. Reply EXACTLY:\nDOMAINS: <their main fields, comma-separated>\n"
        "PROJECTS: <the concrete goals/things they seem to be building toward>\n"
        "STYLE: <how they think — one sentence>",
        "\n".join(sample), "cheap", 0.4, 320) or ""
    dm = re.search(r"DOMAINS:\s*(.+)", raw, re.I)
    pm = re.search(r"PROJECTS:\s*(.+)", raw, re.I)
    sm = re.search(r"STYLE:\s*(.+)", raw, re.DOTALL | re.I)
    model = {"domains": (dm.group(1).strip()[:240] if dm else ""),
             "projects": (pm.group(1).strip()[:240] if pm else ""),
             "style": (re.sub(r"\s+", " ", sm.group(1)).strip()[:240] if sm else ""),
             "n_notes": len(titles), "ts": time.time()}
    if model["domains"] or model["projects"]:
        _save(model)
    return model


def format_model(m: dict) -> str:
    if not m.get("domains") and not m.get("projects"):
        return "🧭 No user model yet."
    return "\n".join([
        "🧭 *What Agora knows about you*\n",
        f"*Domains:* {m.get('domains', '')}",
        f"*Projects:* {m.get('projects', '')}",
        f"*Style:* {m.get('style', '')}",
        f"\n_inferred from {m.get('n_notes', 0)} of your notes_",
    ])
