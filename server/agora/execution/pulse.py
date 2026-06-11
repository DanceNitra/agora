"""
Pulse — a human-readable heartbeat of the autonomous system.

The user can't watch the Quest log. Pulse answers, in plain language: what is being researched and
WHY, how much of it is meaningful vs churn, what actually reached the Obsidian vault (second-brain),
and whether it was pushed to GitHub. It is the tracking layer that turns "the vault spins infinitely"
into a story a human can read in 20 seconds.
"""
from __future__ import annotations

import subprocess
import time
from datetime import datetime, timedelta, timezone


def _git(vault: str, *args: str) -> str:
    try:
        return subprocess.run(["git", "-C", vault, *args],
                              capture_output=True, text=True, timeout=12, encoding="utf-8").stdout
    except Exception:
        return ""


def vault_status(vault: str) -> dict:
    """Is the second-brain actually being updated on GitHub? Last push, note count, unpushed work."""
    last = _git(vault, "log", "-1", "--format=%ct").strip()
    last_ts = int(last) if last.isdigit() else 0
    # Count from the COMMITTED tree (ls-tree HEAD), NOT the index (ls-files): on Windows the vault's
    # ':'-named files break the index so ls-files undercounts and shows fresh notes as deleted. The
    # committed tree is the truth of what's actually on GitHub.
    notes = _git(vault, "ls-tree", "-r", "--name-only", "HEAD", "04 Resources/Concepts/Agora Agents/")
    note_lines = [l for l in notes.splitlines() if l.endswith(".md")]
    note_count = len(note_lines)
    today = datetime.now().strftime("%Y-%m-%d")          # local date (matches the writer's folders)
    new_today = sum(1 for l in note_lines if f"/{today}/" in l)
    unpushed = _git(vault, "rev-list", "--count", "origin/main..main").strip()
    return {"last_push_ts": last_ts, "note_count": note_count, "new_today": new_today,
            "unpushed": int(unpushed) if unpushed.isdigit() else 0}


async def build_pulse(db, vault_path: str, hours: int = 4) -> dict:
    """Gather the period's activity + value + vault outcomes into one structure."""
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    cur = await db.execute(
        "SELECT title, content, created_at FROM collective_knowledge "
        "WHERE knowledge_type='discovery' AND created_at > ? ORDER BY created_at DESC", (since,))
    rows = await cur.fetchall()
    findings = [(r["title"] or "", r["content"] or "") for r in rows]
    hyp = [f for f in findings if f[0].startswith("Hypothesis:")]
    frontier = [f for f in findings if f[0].startswith("Frontier:")]

    # "meaningful" = a substantive finding that cites a real source (not an echo / stub)
    def meaningful(f):
        c = f[1]
        return len(c) > 120 and "Source:" in c and not f[0].lower().count("hypothesize on:") >= 2
    best = next((f for f in findings if meaningful(f)), None)
    a_frontier = frontier[0] if frontier else None

    # focus = the most common multi-word topic across recent titles (what they're working on)
    topics: dict[str, int] = {}
    for t, _ in findings:
        key = t.split(":")[-1].strip()[:48]
        if len(key) > 8:
            topics[key] = topics.get(key, 0) + 1
    focus = sorted(topics, key=lambda k: -topics[k])[:3]

    vault = vault_status(vault_path)
    try:
        from agora.execution.llm_client import llm_cache_stats
        cache = llm_cache_stats()
    except Exception:
        cache = {"hits": 0, "misses": 0}
    # churn signal: fraction of THIS period's raw findings with a near-duplicate (containment >= 0.6)
    try:
        from agora.execution.finding_diversity import _tokens, _containment, _claim
        _tk = [_tokens((t or "") + " " + _claim(c or "")) for t, c in findings]
        _near = sum(1 for i in range(len(_tk))
                    if any(i != j and _containment(_tk[i], _tk[j]) >= 0.6 for j in range(len(_tk))))
        near_dup_rate = round(_near / len(_tk), 3) if _tk else 0.0
    except Exception:
        near_dup_rate = None
    return {
        "hours": hours,
        "findings": len(findings), "hypotheses": len(hyp), "frontiers": len(frontier),
        "meaningful": sum(1 for f in findings if meaningful(f)),
        "best": {"title": best[0], "content": best[1][:200]} if best else None,
        "a_frontier": {"title": a_frontier[0], "content": a_frontier[1][:160]} if a_frontier else None,
        "focus": focus, "vault": vault, "cache": cache, "near_dup_rate": near_dup_rate,
    }


def _ago(ts: int) -> str:
    if not ts:
        return "never"
    mins = int((time.time() - ts) / 60)
    if mins < 60:
        return f"{mins}m ago"
    return f"{mins // 60}h{mins % 60:02d}m ago"


def format_pulse(p: dict, gaps: list | None = None, directions: list | None = None) -> str:
    """The plain-language report — vault outcome first (what the user most wants to know)."""
    v = p["vault"]
    lines = [f"📊 *Agora Pulse* — last {p['hours']}h\n"]

    # 1. What actually reached the second-brain (the user's #1 question)
    lines.append("📚 *Your second-brain (Obsidian → GitHub):*")
    lines.append(f"• {v['note_count']} agent notes total · {v['new_today']} added today")
    push = _ago(v["last_push_ts"])
    if v["unpushed"] > 0:
        lines.append(f"• ⚠️ last GitHub sync {push} — *{v['unpushed']} commits waiting* to push")
    else:
        lines.append(f"• ✅ synced to GitHub {push} (nothing waiting)")
    lines.append("")

    # 2. What was researched + why
    lines.append("🔬 *What's being researched:*")
    if p["focus"]:
        lines.append("• Focus: " + " · ".join(p["focus"]))
    why = []
    for g in (gaps or [])[:2]:
        why.append(g.get("title", "") if isinstance(g, dict) else str(g))
    for d in (directions or [])[:1]:
        why.append(d.get("title", "") if isinstance(d, dict) else str(d))
    if why:
        lines.append("• Why: filling your gaps — " + "; ".join(w[:40] for w in why if w))
    lines.append(f"• {p['findings']} findings this period · {p['meaningful']} substantive "
                 f"({p['hypotheses']} tested hypotheses, {p['frontiers']} open frontiers)")
    if p.get("near_dup_rate") is not None and p.get("findings"):
        lines.append(f"• ♻️ finding overlap: *{p['near_dup_rate']:.0%}* near-duplicates this period "
                     f"(lower = more diverse research)")
    lines.append("")

    # 3. The single most meaningful thing (signal, not noise)
    if p["best"]:
        lines.append("💡 *Most meaningful finding:*")
        lines.append(f"_{p['best']['content']}_")
        lines.append("")
    if p["a_frontier"]:
        lines.append("🔭 *Open question discovered:*")
        lines.append(f"_{p['a_frontier']['content']}_")
        lines.append("")

    # 4. Honest verdict — did anything actually LAND in the vault, or is it just churn in the brain?
    #    (the user's real question: is this meaningful, and is it reaching my second-brain?)
    if v["new_today"] == 0 and v["unpushed"] == 0:
        lines.append(f"🟠 *Churning, not landing* — {p['findings']} findings this period, but "
                     f"*0 new notes reached your vault today*. Research → vault is the bottleneck "
                     f"(most findings don't pass the quality gate).")
    elif v["new_today"] >= 2:
        lines.append(f"🟢 *Productive* — {v['new_today']} new notes reached your second-brain.")
    else:
        lines.append("🟡 *Modest* — a little landed; mostly groundwork.")
    c = p.get("cache", {})
    # Research ROI — value (notes that survived the quality gate into the vault) vs effort.
    pr = p.get("promote", {})
    if pr.get("checked", 0):
        land = round(100 * pr.get("promoted", 0) / pr["checked"])
        calls = c.get("misses", 0) + c.get("skipped", 0)
        lines.append(f"🎯 *Research ROI:* {pr.get('promoted', 0)} notes landed / {pr['checked']} vetted "
                     f"({land}% land rate)" + (f" · ~{calls} LLM calls" if calls else ""))
    total = c.get("hits", 0) + c.get("misses", 0)
    if c.get("hits", 0):
        pct = round(100 * c["hits"] / total) if total else 0
        lines.append(f"♻️ *Policy reuse:* {c['hits']} LLM calls skipped via cache ({pct}% of decisions)")
    lines.append("\n_`pulse` anytime · `directions` · `upgrades` · reply a number to build_")
    return "\n".join(lines)
