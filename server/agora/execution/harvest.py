"""
Harvest — the missing layer between research and action.

Agent findings used to just pile up in /brain/collective and become notes. Harvest reads the
recent findings and synthesizes them into (a) the emerging THEMES, (b) the single strongest
INSIGHT we now hold, and (c) THREE concrete NEXT DIRECTIONS — each a research direction or a
system/tool upgrade — that BUILD ON the findings. Those directions are surfaced to the user AND
fed back as high-priority quests, so each batch of research points somewhere and the work compounds.
"""
from __future__ import annotations

import asyncio
import json
import re


async def synthesize_directions(findings: list[str]) -> dict:
    """findings: recent finding contents → {themes, insight, directions:[{title,kind,why}]}."""
    from agora.execution.llm_client import call_llm
    if not findings:
        return {"themes": [], "insight": "", "directions": []}
    block = "\n".join(f"- {f[:160]}" for f in findings[:16])
    raw = await asyncio.to_thread(
        call_llm,
        "You are Agora's research director. From the agents' recent findings below, produce ONLY "
        'JSON: {"themes":["..."],"insight":"the single strongest thing we now know",'
        '"directions":[{"title":"<short>","kind":"research|upgrade","why":"<one sentence>"}]}. '
        "Give 2-3 emerging THEMES and EXACTLY 3 concrete, ACTIONABLE next directions that BUILD ON "
        "these findings — each either a sharp research question to pursue or a concrete system/tool "
        "upgrade to make. Be specific and non-generic; no vague 'explore further'. Keep each 'why' "
        "to one short sentence.",
        block, "cheap", 0.4, 1100) or ""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    out = {"themes": [], "insight": "", "directions": []}
    if m:
        try:
            d = json.loads(m.group(0))
            out["themes"] = [str(t)[:90] for t in (d.get("themes") or [])][:3]
            out["insight"] = str(d.get("insight", ""))[:300]
            for x in (d.get("directions") or [])[:3]:
                if x.get("title"):
                    out["directions"].append({
                        "title": str(x["title"])[:90],
                        "kind": "upgrade" if "upgrade" in str(x.get("kind", "")).lower() else "research",
                        "why": str(x.get("why", ""))[:200]})
        except Exception:
            pass
    return out


def format_directions(d: dict) -> str:
    if not d.get("directions"):
        return "🧭 Not enough recent findings to chart directions yet."
    lines = ["🧭 *Where the research points next*\n"]
    if d.get("themes"):
        lines.append("*Themes:* " + " · ".join(d["themes"]))
    if d.get("insight"):
        lines.append(f"*Insight:* {d['insight']}")
    lines.append("\n*Next directions:*")
    for x in d["directions"]:
        icon = "🛠️" if x["kind"] == "upgrade" else "🔬"
        lines.append(f"{icon} *{x['title']}* — _{x['why']}_")
    return "\n".join(lines)
