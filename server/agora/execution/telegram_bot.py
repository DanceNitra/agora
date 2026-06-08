"""
Two-way Telegram — turns the morning report into a research COMMAND CENTER. The user texts a
question or command from their phone; the agents do a grounded research brief (real OpenAlex/arXiv
sources + the user's own semantic notes) and reply right in Telegram.

Commands:
  research <topic>  /  <any question>  → grounded research brief
  gaps                                  → the user's current knowledge gaps
  report                                → send the morning report now
"""
from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
import urllib.request


def _tok() -> str:
    return os.getenv("HERMES_TELEGRAM_BOT_TOKEN", "")


def _chat() -> str:
    return os.getenv("HERMES_TELEGRAM_CHAT_ID", "")


def _api(method: str, params: dict) -> dict:
    url = f"https://api.telegram.org/bot{_tok()}/{method}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=70) as r:
        return json.loads(r.read())


async def send(text: str) -> None:
    if not _tok() or not _chat():
        return
    try:
        await asyncio.to_thread(_api, "sendMessage",
                                {"chat_id": _chat(), "text": text[:4000], "parse_mode": "Markdown"})
    except Exception:
        try:  # retry without markdown (in case of parse errors)
            await asyncio.to_thread(_api, "sendMessage", {"chat_id": _chat(), "text": text[:4000]})
        except Exception:
            pass


async def research_brief(query: str) -> str:
    """Grounded research brief on demand: real cross-field sources + the user's own notes."""
    from agora.execution.research_tool import research, format_for_prompt
    from agora.execution.semantic_index import SemanticIndex
    from agora.execution.llm_client import call_llm
    papers = await asyncio.to_thread(research, query, 4)
    sources = format_for_prompt(papers)
    si = SemanticIndex()
    related = si.search(query, 4) if si.ready else []
    rel = "; ".join(f"[[{r['title']}]]" for r in related[:3]) or "(your vault is thin here — a gap)"
    brief = await asyncio.to_thread(
        call_llm,
        "You are a rigorous research assistant. Using the REAL papers and the user's own notes "
        "below, write a tight grounded brief (4-6 sentences): the key finding(s), citing real "
        "papers by author/year, and connect it to the user's notes. NEVER invent sources.",
        f"Question: {query}\n\nReal papers:\n{sources}\n\nUser's relevant notes: {rel}",
        "cheap", 0.3, 700) or "(no answer)"
    src1 = sources.splitlines()[0][:90] if sources and "(no external" not in sources else "—"
    return f"🔬 *{query[:80]}*\n\n{brief.strip()}\n\n📎 {src1}\n🔗 your notes: {rel}"


async def _handle(app, text: str) -> None:
    low = text.lower().strip()
    if low in ("/gaps", "gaps", "medzery"):
        from agora.execution.semantic_index import SemanticIndex
        si = SemanticIndex()
        gaps = si.find_gaps(8) if si.ready else []
        await send("🎯 *Tvoje medzery:*\n" + "\n".join(f"• {g['title']}" for g in gaps))
    elif low in ("/report", "report"):
        from agora.api.agent_os_api import _build_morning_report
        await send(await _build_morning_report(app, send_it=False))
    elif low in ("/start", "/help", "help"):
        await send("🏰 *Agora research assistant*\nNapíš otázku → grounded brief.\n"
                   "`research <téma>` · `gaps` · `report`")
    else:
        q = text.split(" ", 1)[1] if low.startswith(("research ", "/research ", "skumaj ")) else text
        await send("🔬 _skúmam… pár sekúnd_")
        await send(await research_brief(q))


async def poll_loop(app) -> None:
    """Long-poll Telegram for the user's commands (no public URL needed)."""
    if not _tok() or not _chat():
        print("[Telegram] no token/chat — two-way command center disabled")
        return
    print("[Telegram] two-way command center started")
    offset = 0
    # skip backlog: start from the latest update
    try:
        init = await asyncio.to_thread(_api, "getUpdates", {"timeout": 0, "offset": -1})
        for u in init.get("result", []):
            offset = u["update_id"] + 1
    except Exception:
        pass
    while True:
        try:
            upd = await asyncio.to_thread(_api, "getUpdates", {"offset": offset, "timeout": 50})
            for u in upd.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message", {})
                if str(msg.get("chat", {}).get("id")) != str(_chat()):
                    continue
                txt = (msg.get("text") or "").strip()
                if txt:
                    try:
                        await _handle(app, txt)
                    except Exception as e:
                        await send(f"⚠️ {str(e)[:200]}")
        except Exception:
            await asyncio.sleep(5)
        await asyncio.sleep(1)
