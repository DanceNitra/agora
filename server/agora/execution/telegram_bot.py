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


# the last brief, kept in memory so the user can reply "keep" to save it to their vault
_last = {"query": "", "brief": "", "sources": ""}


async def research_brief(query: str) -> str:
    """Grounded research brief on demand: real cross-field sources + the user's own notes.
    Disambiguates the query in the user's context first (so 'vault' ≠ cryptography)."""
    from agora.execution.research_tool import research, format_for_prompt
    from agora.execution.semantic_index import SemanticIndex
    from agora.execution.llm_client import call_llm

    si = SemanticIndex()
    related = si.search(query, 4) if si.ready else []
    rel_titles = ", ".join(r["title"] for r in related[:4])
    rel = "; ".join(f"[[{r['title']}]]" for r in related[:3]) or "(your vault is thin here — a gap)"

    # reformulate into a precise academic search query, disambiguated to the user's context
    refined = await asyncio.to_thread(
        call_llm,
        "Turn the user's request into a precise 4-8 word academic SEARCH QUERY for finding real "
        "papers. The user keeps a personal research knowledge-vault (a 'second brain') on AI, "
        "complex systems, causal inference, neuroscience, finance, knowledge management. "
        "Disambiguate domain terms to THEIR context — e.g. 'vault' means a personal knowledge "
        "base / second brain, NOT cryptography. Reply with ONLY the search query, nothing else.",
        f"Request: {query}\nTheir related notes: {rel_titles}", "cheap", 0.1, 60)
    refined = (refined or query).strip().strip('"')[:110] or query

    papers = await asyncio.to_thread(research, refined, 4)
    sources = format_for_prompt(papers)
    brief = await asyncio.to_thread(
        call_llm,
        "You are a rigorous research assistant. Using the REAL papers and the user's own notes "
        "below, write a tight grounded brief (4-6 sentences): the key finding(s), citing real "
        "papers by author/year, and connect it to the user's notes. NEVER invent sources, and "
        "stay on the user's actual topic.",
        f"User's question: {query}\nSearch used: {refined}\n\nReal papers:\n{sources}\n\n"
        f"User's relevant notes: {rel}", "cheap", 0.3, 700) or "(no answer)"

    # show the most RELEVANT paper (research() returns by relevance), not the most-cited
    real = [p for p in papers if not p.get("error") and p.get("title")]
    top = real[0] if real else None
    src_line = (f"📎 {top['title'][:75]} ({top.get('citations', 0)} cit.) {top['url']}"
                if top else "📎 (no external source)")
    _last.update(query=query, brief=brief.strip(),
                 sources="\n".join(f"- {p['title']} ({p.get('citations', 0)} cit.) {p['url']}"
                                   for p in real[:3]))
    return f"🔬 *{query[:80]}*\n\n{brief.strip()}\n\n{src_line}\n🔗 your notes: {rel}"


async def _save_to_vault(query: str, brief: str, sources: str) -> dict:
    """Promote a kept brief into the vault (gate bypassed — the user explicitly approved it)."""
    body = json.dumps({
        "title": f"Research — {query[:60]}",
        "content": f"{brief}\n\n## Sources\n{sources}",
        "agent": "Agora (kept by Rasto)",
        "tags": ["research", "kept", "agora"],
        "gate": False,
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/agent-os/brain/vault-note", data=body,
        headers={"Content-Type": "application/json"})

    def _p():
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read())
    return await asyncio.to_thread(_p)


async def _handle(app, text: str) -> None:
    low = text.lower().strip()
    if low in ("keep", "/keep", "uloz", "ulož"):
        if not _last["brief"]:
            await send("_nič na uloženie — najprv sa niečo opýtaj_")
        else:
            r = await _save_to_vault(_last["query"], _last["brief"], _last["sources"])
            if r and r.get("status") == "written":
                await send(f"✅ Uložené do vaultu — *{_last['query'][:60]}*")
            else:
                await send("✗ uloženie zlyhalo")
    elif low in ("/gaps", "gaps", "medzery"):
        from agora.execution.semantic_index import SemanticIndex
        si = SemanticIndex()
        gaps = si.find_gaps(8) if si.ready else []
        await send("🎯 *Tvoje medzery:*\n" + "\n".join(f"• {g['title']}" for g in gaps))
    elif low in ("/report", "report"):
        from agora.api.agent_os_api import _build_morning_report
        await send(await _build_morning_report(app))
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
