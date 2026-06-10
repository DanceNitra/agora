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
import time
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
    from agora.execution.claude_inbox import feed_append
    feed_append(text)                               # Claude Code reads the same feed the user sees
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


def _brain_get(path: str) -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:8000{path}", timeout=70) as r:
        return json.loads(r.read())


def _brain_post(path: str, body: dict) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:8000{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=70) as r:
        return json.loads(r.read())


# the last brief, kept in memory so the user can reply "keep" to save it to their vault
_last = {"query": "", "brief": "", "sources": ""}
_bridges_cache = {"bridges": []}


# ── THE THREAD: rolling multi-turn memory so follow-up questions work like a dialogue ──
from pathlib import Path as _TPath

_THREAD_FILE = _TPath(__file__).resolve().parents[2] / ".thread.json"
_THREAD_TTL = 2 * 3600          # a thread goes stale after 2h of silence


def _thread_load() -> list:
    try:
        import time as _t
        items = json.loads(_THREAD_FILE.read_text(encoding="utf-8"))
        if items and _t.time() - items[-1].get("ts", 0) > _THREAD_TTL:
            return []           # stale thread — start fresh
        return items
    except Exception:
        return []


def _thread_add(q: str, a: str) -> None:
    try:
        import time as _t
        items = _thread_load()
        items.append({"q": (q or "")[:200], "a": (a or "")[:300], "ts": _t.time()})
        _THREAD_FILE.write_text(json.dumps(items[-6:], ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _thread_text() -> str:
    items = _thread_load()
    if not items:
        return ""
    return "RECENT CONVERSATION (use to resolve follow-ups like 'and what about X?'):\n" + \
        "\n".join(f"- They asked: {x['q']} | You answered: {x['a']}" for x in items)


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
        "base / second brain, NOT cryptography. If the request is a FOLLOW-UP, resolve it "
        "against the recent conversation. Reply with ONLY the search query, nothing else.",
        f"Request: {query}\nTheir related notes: {rel_titles}\n{_thread_text()}", "cheap", 0.1, 160)
    refined = (refined or query).strip().strip('"')[:110] or query

    papers = await asyncio.to_thread(research, refined, 4)
    sources = format_for_prompt(papers)
    brief = await asyncio.to_thread(
        call_llm,
        "You are a rigorous research assistant. Using the REAL papers and the user's own notes "
        "below, write a tight grounded brief (4-6 sentences): the key finding(s), citing real "
        "papers by author/year, and connect it to the user's notes. NEVER invent sources, and "
        "stay on the user's actual topic.",
        f"User's question: {query}\nSearch used: {refined}\n{_thread_text()}\n\n"
        f"Real papers:\n{sources}\n\nUser's relevant notes: {rel}", "cheap", 0.3, 700) or "(no answer)"

    # show the most RELEVANT paper (research() returns by relevance), not the most-cited
    real = [p for p in papers if not p.get("error") and p.get("title")]
    top = real[0] if real else None
    src_line = (f"📎 {top['title'][:75]} ({top.get('citations', 0)} cit.) {top['url']}"
                if top else "📎 (no external source)")
    _last.update(query=query, brief=brief.strip(),
                 sources="\n".join(f"- {p['title']} ({p.get('citations', 0)} cit.) {p['url']}"
                                   for p in real[:3]))
    _thread_add(query, brief.strip())          # the Thread: this exchange feeds the next one
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
    if low.startswith(("fix ", "/fix ")):
        guidance = text.split(" ", 1)[1].strip()
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/resolve",
                                    {"guidance": guidance})
        if (d or {}).get("status") == "ok":
            await send(f"✅ Guidance sent to *{d['agent']}* — it will pick it up and unblock.")
        else:
            await send("_No stuck agent is waiting right now._")
    elif low.startswith(("cc ", "claude ", "build ", "task ", "implement ", "hej claude")):
        task = text
        for p in ("hej claude ", "cc ", "claude "):           # strip only the addressing prefix
            if low.startswith(p):
                task = text[len(p):].strip()
                break
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/claude-inbox",
                                    {"text": task})
        await send(f"📥 Task queued for *Claude Code* (#{(d or {}).get('id', '?')}). "
                   f"It'll pick this up on its next check and report back here.")
    elif low.isdigit() and 1 <= int(low) <= 9:
        # a bare number = pick that numbered self-upgrade proposal → Claude implements it
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/self-upgrades/pick",
                                    {"n": int(low)})
        if (d or {}).get("status") == "queued":
            await send(f"✅ Got it — queued for *Claude Code*: implement *{d['title']}* (#{d['id']}). "
                       f"I'll build it and report back here.")
        else:
            await send("_No numbered proposal to pick — run `upgrades` first._")
    elif low in ("status", "/status", "agents"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/escalations")
        open_ = [e for e in (d or {}).get("escalations", []) if not e["resolved"]]
        if not open_:
            await send("✅ *All clear* — no agent is stuck.")
        else:
            lines = ["⚠️ *Agents needing help:*\n"]
            for e in open_:
                lines.append(f"• *{e['agent']}* ({e['mins_ago']}m ago): {e['problem'][:140]}")
            lines.append("\n→ Reply `fix <guidance>` to unblock the latest.")
            await send("\n".join(lines))
    elif low in ("verify", "/verify"):
        await send("🔬 _Fact-checking recent findings against real sources…_")
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/verify-findings", {})
        res = (d or {}).get("results", [])
        if not res:
            await send("_No new findings to verify._")
        else:
            icon = {"VERIFIED": "✅", "OVERSTATED": "⚠️", "UNSUPPORTED": "❌"}
            lines = ["🔬 *Verification vs real sources:*\n"]
            for r in res:
                lines.append(f"{icon.get(r['verdict'], '•')} {r['title'][:42]}\n   _{r['reason'][:90]}_")
            lines.append(f"\n→ *{d.get('incorporated', 0)}/{d.get('total', 0)}* incorporated into "
                         f"the vault ({d.get('verified', 0)} fully verified).")
            await send("\n".join(lines))
    elif low in ("keep", "/keep"):
        if not _last["brief"]:
            await send("_Nothing to save — ask a question first._")
        else:
            r = await _save_to_vault(_last["query"], _last["brief"], _last["sources"])
            await send(f"✅ Saved to your vault — *{_last['query'][:60]}*"
                       if r and r.get("status") == "written" else "✗ Save failed.")
    elif low in ("bridges", "/bridges"):
        await send("🌉 _Finding missing connections in your vault…_")
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/bridges?n=6&rationale=true")
        bridges = (d or {}).get("bridges", [])
        _bridges_cache["bridges"] = bridges
        if not bridges:
            await send("_No new bridges found._")
        else:
            lines = ["🌉 *Missing connections in your vault:*\n"]
            for i, b in enumerate(bridges, 1):
                lines.append(f"{i}. [[{b['a']}]] ↔ [[{b['b']}]]\n   _{b.get('why', '')}_")
            lines.append("\n→ Reply `connect` to add these links to your notes.")
            await send("\n".join(lines))
    elif low in ("connect", "/connect", "apply"):
        bridges = _bridges_cache.get("bridges", [])
        if not bridges:
            await send("_Run `bridges` first._")
        else:
            d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/bridges/apply",
                                        {"bridges": bridges})
            await send(f"✅ Added *{(d or {}).get('links_added', 0)}* links to your notes "
                       f"('## Related (Agora bridges)' section).")
            _bridges_cache["bridges"] = []
    elif low.startswith(("believe ", "/believe ")):
        topic = text.split(" ", 1)[1].strip()
        await send("🧠 _Reading what your vault believes…_")
        from agora.config import settings
        from agora.execution.knowledge_graph import believe, format_belief
        await send(format_belief(await believe(topic, settings.vault_path, 8)))
    elif low.startswith(("hypothesize ", "/hypothesize ", "hypothesis ")):
        topic = text.split(" ", 1)[1].strip()
        await send("🔬 _Forming a hypothesis and testing it against real literature…_")
        from agora.config import settings
        from agora.execution.scientist import hypothesize_and_test, format_hypothesis
        await send(format_hypothesis(await hypothesize_and_test(topic, settings.vault_path)))
    elif low.startswith(("frontier ", "/frontier ")):
        topic = text.split(" ", 1)[1].strip()
        await send("🔭 _Finding your vault's frontier…_")
        from agora.config import settings
        from agora.execution.knowledge_graph import frontier, format_frontier
        await send(format_frontier(await frontier(topic, settings.vault_path, 8)))
    elif low in ("directions", "/directions", "harvest"):
        await send("🧭 _Harvesting findings into next directions…_")
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/directions?n=14")
        from agora.execution.harvest import format_directions
        await send(format_directions(d or {}))
    elif low in ("pulse", "/pulse", "report+"):
        await send("📊 _Reading the system's pulse…_")
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/pulse?hours=4")
        await send((d or {}).get("report", "_No pulse available right now._"))
    elif low.startswith(("reality ", "/reality ", "test ")):
        import urllib.parse
        claim = text.split(" ", 1)[1].strip()
        await send("🌐 _Reality check — testing against real-world data…_")
        d = await asyncio.to_thread(
            _brain_get, "/api/v1/agent-os/brain/empirical-test?q=" + urllib.parse.quote(claim))
        if d and d.get("verdict"):
            from agora.execution.data_tool import format_empirical
            await send(format_empirical(d))
        else:
            await send("_Could not run the reality check right now._")
    elif low.startswith(("insight ", "/insight ", "synthesize ")):
        import urllib.parse
        theme = text.split(" ", 1)[1].strip()
        await send("💡 _Synthesizing a new insight from vault + literature + reality…_")
        d = await asyncio.to_thread(
            _brain_get, "/api/v1/agent-os/brain/insight?q=" + urllib.parse.quote(theme))
        if d and d.get("insight"):
            from agora.execution.insight_engine import format_insight
            await send(format_insight(d))
        else:
            await send("_Couldn't synthesize an insight right now (too little to connect, or LLM hiccup)._")
    elif low.startswith(("predict ", "/predict ")):
        import urllib.parse
        theme = text.split(" ", 1)[1].strip()
        await send("🔮 _Recording a falsifiable prediction…_")
        d = await asyncio.to_thread(
            _brain_get, "/api/v1/agent-os/brain/predict?q=" + urllib.parse.quote(theme))
        if d and d.get("direction"):
            await send(f"🔮 *Prediction:* {d['metric_label']} for _{theme[:50]}_ will go "
                       f"*{d['direction']}* in {d['horizon_days']}d (conf {d['confidence']:.0%})\n"
                       f"_{d.get('why', '')}_\n_baseline {d['baseline']} — resolves automatically_")
        else:
            await send("_Couldn't record a prediction right now._")
    elif low in ("predictions", "/predictions", "ledger"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/predictions")
        await send((d or {}).get("report", "_No predictions yet._"))
    elif low.startswith(("quiz ", "/quiz ", "socratic ")):
        import urllib.parse
        topic = text.split(" ", 1)[1].strip()
        await send("🎓 _Drawing Socratic questions from your notes…_")
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/socratic?q=" + urllib.parse.quote(topic))
        from agora.execution.socratic import format_socratic
        await send(format_socratic(d or {}))
    elif low in ("learn", "/learn", "learn next", "what next"):
        await send("🎓 _Finding your highest-value next topic…_")
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/learn-next")
        from agora.execution.socratic import format_learn_next
        await send(format_learn_next(d or {}))
    elif low.startswith(("draft ", "/draft ")):
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/claude-inbox",
                                    {"text": "Draft " + text.split(" ", 1)[1].strip()})
        await send(f"📝 Queued for Claude to draft (#{(d or {}).get('id', '?')}). I'll produce the "
                   f"artifact on my next check and drop it in your vault.\n_kinds: brief · essay · plan · spec_")
    elif low.startswith(("debate ", "/debate ", "dialectic ")):
        import urllib.parse
        claim = text.split(" ", 1)[1].strip()
        await send("⚖️ _Running the dialectic — thesis vs antithesis…_")
        d = await asyncio.to_thread(
            _brain_get, "/api/v1/agent-os/brain/dialectic?q=" + urllib.parse.quote(claim))
        from agora.execution.dialectic import format_dialectic
        await send(format_dialectic(d or {}))
    elif low.startswith(("program ", "/program ")):
        import urllib.parse
        q = text.split(" ", 1)[1].strip()
        await send("🎯 _Launching a research program — decomposing your question…_")
        d = await asyncio.to_thread(
            _brain_get, "/api/v1/agent-os/brain/program/start?q=" + urllib.parse.quote(q))
        subs = (d or {}).get("subquestions", [])
        await send(f"🎯 *Research program launched* (#{(d or {}).get('id', '?')}):\n"
                   + "\n".join(f"• {s}" for s in subs)
                   + "\n\n_the agents will research these; the synthesis lands later_")
    elif low in ("model", "/model", "about me"):
        await send("🧭 _Building your context model…_")
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/user-model")
        from agora.execution.user_model import format_model
        await send(format_model(d or {}))
    elif low in ("mind", "/mind", "worldview", "state of mind"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/worldview")
        wv = (d or {}).get("worldview", "").strip()
        await send(("🧠 *Agora's state of mind*\n\n" + wv[:3400]) if wv
                   else "🧠 _No worldview synthesized yet — Agora reflects on itself ~daily._")
    elif low in ("lessons", "/lessons", "learnings"):
        from agora.execution.learning import format_lessons
        await send(format_lessons())
    elif low in ("exam", "/exam", "test me"):
        await send("📝 _Composing an exam from your core concepts (a minute)…_")
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/exam/generate", {"n": 6})
        from agora.execution.exam import format_exam_questions
        await send(format_exam_questions(d or {}) if (d or {}).get("status") == "ok"
                   else "_Couldn't compose an exam right now._")
    elif low in ("exams", "/exams", "scores"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/exams")
        rows = [f"• {time.strftime('%m-%d', time.localtime(s['ts']))}: "
                + (f"*{s['score']}/{s['max']}*" if s.get("score") is not None else "_awaiting grade_")
                for s in (d or {}).get("series", [])]
        await send("📊 *Agora's exam scores*\n" + "\n".join(rows) if rows
                   else "_No exams taken yet._")
    elif low in ("actions", "/actions", "hands"):
        from agora.execution.hands import format_actions
        await send(format_actions())
    elif low.startswith(("answer ", "/answer ")):
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/interview/answer",
                                    {"text": text.split(" ", 1)[1].strip()})
        st = (d or {}).get("status")
        await send("✅ _Answer recorded — it's in your vault and feeds the user model._"
                   if st == "answered" else "_No open question right now._")
    elif low in ("interview", "/interview", "questions"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/interview")
        await send((d or {}).get("report", "_No interview yet._"))
    elif low in ("ask me", "/ask"):
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/interview/ask", {})
        if (d or {}).get("status") == "already_open":
            await send("_There's already an open question — see_ `interview`.")
    elif low in ("vitals", "/vitals", "health"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/vitals")
        await send((d or {}).get("report", "_No vitals yet._"))
    elif low in ("experiments", "/experiments", "ab"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/experiments")
        await send((d or {}).get("report", "_No experiments yet._"))
    elif low in ("library", "/library", "papers"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/library")
        await send((d or {}).get("report", "_Library empty._"))
    elif low.startswith(("campaign ", "/campaign ")):
        q = text.split(" ", 1)[1].strip()
        await send("🎯 _Opening a multi-day campaign — decomposing the goal…_")
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/campaign/start",
                                    {"question": q})
        c = (d or {}).get("campaign", {})
        await send(f"🎯 *Campaign launched* `{c.get('id','?')}`:\n"
                   + "\n".join(f"• {s}" for s in c.get("subquestions", []))
                   + "\n\n_the agents pursue these for days; I'll synthesize the dossier when ready_"
                   if c else "_Couldn't start a campaign._")
    elif low.startswith(("got", "forgot")) and len(low.split()) <= 2:
        parts = low.replace("/", "").split()
        idx = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 1
        ok = parts[0] == "got"
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/tutor/grade",
                                    {"idx": idx, "ok": ok})
        if (d or {}).get("status") == "ok":
            await send(f"{'✅' if ok else '🔁'} _{d['concept'][:40]} comes back in "
                       f"{d['next_in_days']}d._")
        else:
            await send("_No quiz card waiting under that number._")
    elif low in ("quiz me", "/tutor", "tutor"):
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/tutor/daily", {})
        if not (d or {}).get("n"):
            await send("_Nothing due — your memory is ahead of schedule._")
    elif low.startswith(("gap ", "/gap ")):
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/forge/add",
                                    {"description": text.split(" ", 1)[1].strip()})
        g = (d or {}).get("gap")
        await send(f"🔨 Gap registered `{g['id']}` — the Forge will queue it for a build."
                   if g else "_Already on record (or too short)._")
    elif low.startswith(("desk ", "/desk ")) or low in ("desk", "/desk"):
        import urllib.parse as _up
        topic = text.split(" ", 1)[1].strip() if " " in text else ""
        await send("🗂 _Laying out your desk…_")
        d = await asyncio.to_thread(_brain_get,
                                    "/api/v1/agent-os/brain/desk?q=" + _up.quote(topic))
        await send((d or {}).get("report", "_Couldn't lay out the desk._"))
    elif low in ("attention", "/attention"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/attention")
        await send((d or {}).get("report", "_No attention data._"))
    elif low in ("forge", "/forge"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/forge")
        await send((d or {}).get("report", "_Forge empty._"))
    elif low in ("canon", "/canon"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/canon")
        c = (d or {}).get("canon", "").strip()
        await send(("📖 " + c[:3400]) if c else "_No canon written yet._")
    elif low.startswith(("board ", "/board ")):
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/board/decide",
                                    {"text": text.split(" ", 1)[1].strip()})
        await send("🏛 _Directives recorded — they now steer every synthesis until the next board._"
                   if (d or {}).get("agenda") else "_Couldn't record directives._")
    elif low in ("board", "/board"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/board")
        await send((d or {}).get("report", "_No board yet._"))
    elif low.startswith(("recall ", "/recall ")):
        import urllib.parse as _up
        q = text.split(" ", 1)[1].strip()
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/recall?q=" + _up.quote(q))
        from agora.execution.recall import format_recall
        await send(format_recall(d or {}))
    elif low in ("correspondence", "/correspondence", "letters"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/correspondence")
        await send((d or {}).get("report", "_No correspondence._"))
    elif low in ("theory", "/theory"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/theory")
        await send((d or {}).get("report", "_No theory runs._"))
    elif low in ("counterfactual", "/counterfactual", "whatif"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/counterfactual")
        await send((d or {}).get("report", "_No counterfactual data._"))
    elif low in ("metabolism", "/metabolism", "roi"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/metabolism")
        await send((d or {}).get("report", "_No metabolic data._"))
    elif low in ("oracle", "/oracle"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/oracle")
        await send((d or {}).get("report", "_No oracle data._"))
    elif low in ("coherence", "/coherence"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/coherence")
        await send((d or {}).get("report", "_No coherence data._"))
    elif low in ("dashboard", "/dashboard", "gauges"):
        await send("📟 Gauges: http://127.0.0.1:8000/api/v1/agent-os/dashboard "
                   "(open on the machine running Agora)")
    elif low in ("atlas", "/atlas"):
        await send("🗺 _Rebuilding the domain maps (a minute)…_")
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/atlas/build", {})
        await send((d or {}).get("report", "_Atlas build failed._"))
    elif low in ("salon", "/salon"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/salon")
        await send((d or {}).get("report", "_Salon quiet._"))
    elif low in ("annals", "/annals", "diary"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/annals")
        await send((d or {}).get("report", "_No annals._"))
    elif low in ("lab", "/lab", "experiments lab"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/lab")
        await send((d or {}).get("report", "_Lab dark._"))
    elif low in ("mastery", "/mastery"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/agent-mastery")
        await send((d or {}).get("report", "_No mastery data._"))
    elif low in ("sources", "/sources"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/source-reliability")
        await send((d or {}).get("report", "_No source data._"))
    elif low in ("contradictions", "/contradictions"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/contradictions")
        await send((d or {}).get("report", "_No contradictions._"))
    elif low in ("beliefs", "/beliefs"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/beliefs")
        await send((d or {}).get("report", "_No beliefs._"))
    elif low in ("campaigns", "/campaigns"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/campaigns")
        await send((d or {}).get("report", "_No campaigns._"))
    elif low in ("graveyard", "/graveyard", "graves"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/graveyard")
        await send((d or {}).get("report", "_The graveyard is empty._"))
    elif low in ("bounty", "/bounty", "kills"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/bounty")
        await send((d or {}).get("report", "_The bounty board is empty._"))
    elif low in ("analogies", "/analogies", "forge log"):
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/analogies")
        await send((d or {}).get("report", "_The forge is cold._"))
    elif low in ("economy", "/economy", "memory economy"):
        await send("🏛 _Auditing the memory economy (a minute)…_")
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/memory-economy")
        await send((d or {}).get("report", "_No economy data._"))
    elif low.startswith(("approve ", "/approve ", "reject ", "/reject ")):
        approve = low.startswith(("approve", "/approve"))
        aid = text.split(" ", 1)[1].strip()
        d = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/action-decide",
                                    {"id": aid, "approve": approve})
        a = (d or {}).get("action")
        if not a:
            await send(f"_No action {aid}._")
        elif not approve:
            await send(f"🚫 Rejected `{aid}`.")
        elif a.get("kind") in ("export_insights", "digest", "curate", "gist", "publish", "outreach"):
            # deterministic executor kinds run immediately on approval
            r = await asyncio.to_thread(_brain_post, "/api/v1/agent-os/brain/action-execute",
                                        {"id": aid})
            await send(f"✅ Approved `{aid}` — executed: {(r or {}).get('result', (r or {}).get('error', '?'))}")
        else:
            await send(f"✅ Approved `{aid}` — Agora will carry it out.")
    elif low in ("now", "/now", "pulse", "world"):
        await send("🌐 _Sensing what's live in your world…_")
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/now")
        from agora.execution.senses import format_now
        await send(format_now(d or {}))
    elif low in ("upgrades", "/upgrades", "self-upgrades"):
        await send("🔧 _Agora reflecting on its own mechanisms…_")
        d = await asyncio.to_thread(_brain_get, "/api/v1/agent-os/brain/self-upgrades")
        ups = (d or {}).get("upgrades", [])
        if not ups:
            await send("_No upgrade proposals right now._")
        else:
            lines = ["🔧 *Agora proposes upgrades to itself — reply a number to build it:*\n"]
            for i, u in enumerate(ups, 1):
                lines.append(f"*{i}.* {u['title']}\n   _{u.get('why', '')[:90]}_")
            await send("\n".join(lines))
    elif low in ("/gaps", "gaps"):
        from agora.execution.semantic_index import SemanticIndex
        si = SemanticIndex()
        gaps = si.find_gaps(8) if si.ready else []
        await send("🎯 *Your knowledge gaps:*\n" + "\n".join(f"• {g['title']}" for g in gaps))
    elif low in ("/report", "report"):
        from agora.api.agent_os_api import _build_morning_report
        await send(await _build_morning_report(app))
    elif low in ("/start", "/help", "help"):
        await send("🏰 *Agora — research + control*\n\n"
                   "*Research (agents):*\n"
                   "`<question>` → grounded brief, then `keep`\n"
                   "`believe <topic>` → what your vault claims (+contradictions)\n"
                   "`hypothesize <topic>` → form + test a new hypothesis (AGORA 2.0)\n"
                   "`verify` · `bridges`/`connect` · `gaps` · `report` · `status` · `fix <g>`\n\n"
                   "*Control Claude Code:*\n"
                   "`build <task>` / `cc <task>` → hand me a build/implementation task; "
                   "I pick it up and report back here.")
    else:
        q = text.split(" ", 1)[1] if low.startswith(("research ", "/research ")) else text
        await send("🔬 _Researching… a few seconds._")
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
