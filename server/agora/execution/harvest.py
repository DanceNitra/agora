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


def _board_frame() -> tuple[str, set]:
    """The board's AIM and its REFUSALS as prose, plus the on-priority term set.

    THE DIRECTIONS GENERATOR HAD NEVER HEARD OF THE BOARD. Measured 2026-08-17: this module contained
    zero references to it, so it synthesised directions purely from findings, and the dungeon's quest
    gate -- which DOES gate on `board_priority_terms` -- then dropped 5 of the 6 it published. The
    harvest is described elsewhere in this repo as "the ONLY RENEWABLE source of research themes", and
    83% of it was discarded by construction, one layer downstream, every cycle.

    The five dropped ones were not junk. They were sharp questions on the recall/retrieval-accuracy
    axis -- and that axis is the one the owner's board explicitly deprioritises as "a measured dead end
    for us [that] must never admit work on their own". So the gate was right and the generator was
    blind: it kept proposing good work on a closed axis. Telling it the frame is the fix; loosening the
    gate would have re-opened a door the owner deliberately shut.
    """
    from agora.execution.board import priorities_text
    from agora.execution.methods import _REFUSAL, board_priority_terms
    text = priorities_text() or ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    aim = " ".join(s for s in sentences if s and not _REFUSAL.search(s))
    refused = " ".join(s for s in sentences if s and _REFUSAL.search(s))
    frame = ""
    if aim:
        frame += "\n\nAIM AT THIS (the owner's standing frontier): " + aim[:700]
    if refused:
        frame += ("\n\nNEVER PROPOSE WORK ON THESE -- they are explicitly deprioritised, and a "
                  "direction on them is discarded downstream: " + refused[:700])
    return frame, board_priority_terms(text)


async def synthesize_directions(findings: list[str]) -> dict:
    """findings: recent finding contents → {themes, insight, directions:[{title,kind,why}]}."""
    from agora.execution.llm_client import call_llm
    from agora.execution.methods import _theme_tokens, light_stem
    if not findings:
        return {"themes": [], "insight": "", "directions": []}
    block = "\n".join(f"- {f[:160]}" for f in findings[:16])
    frame, prio = _board_frame()
    raw = await asyncio.to_thread(
        call_llm,
        "You are Agora's research director. From the agents' recent findings below, produce ONLY "
        'JSON: {"themes":["..."],"insight":"the single strongest thing we now know",'
        '"directions":[{"title":"<short>","kind":"research|upgrade","why":"<one sentence>"}]}. '
        "Give 2-3 emerging THEMES and EXACTLY 3 concrete, ACTIONABLE next directions that BUILD ON "
        "these findings — each either a sharp research question to pursue or a concrete system/tool "
        "upgrade to make. Be specific and non-generic; no vague 'explore further'. Keep each 'why' "
        "to one short sentence." + frame,
        block, "cheap", 0.4, 1100) or ""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    out = {"themes": [], "insight": "", "directions": [], "off_board_dropped": 0,
           "off_board_titles": []}
    if m:
        try:
            d = json.loads(m.group(0))
            out["themes"] = [str(t)[:90] for t in (d.get("themes") or [])][:3]
            out["insight"] = str(d.get("insight", ""))[:300]
            for x in (d.get("directions") or [])[:3]:
                if not x.get("title"):
                    continue
                title = str(x["title"])[:90]
                kind = "upgrade" if "upgrade" in str(x.get("kind", "")).lower() else "research"
                # A RESEARCH direction must be admissible by the same gate that will judge it. Upgrades
                # are exempt: they go to the owner, not to the swarm's quest board, so the frontier
                # vocabulary does not apply to them. And the drop is COUNTED, never silent -- a supply
                # that quietly empties itself is the failure this repo keeps re-finding, so the caller
                # can see "3 proposed, 2 kept, 1 off-board" instead of an unexplained short list.
                if kind == "research" and prio and not (
                        {light_stem(w) for w in _theme_tokens(title)} & prio):
                    out["off_board_dropped"] += 1
                    out["off_board_titles"].append(title)
                    continue
                out["directions"].append({"title": title, "kind": kind,
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
