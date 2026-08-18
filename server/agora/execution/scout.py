"""
The Opportunity Scout — Shadow Kael turns the keep outward.

The first public win (a substantive comment on a 189k-star repo's open issue, answered with running
architecture + simulation numbers) was a one-off. The Scout makes it a pipeline: search GitHub for
OPEN issues that are genuine questions Agora's vault can answer with evidence, score the fit, and
surface the best as a candidate for a gated outreach reply. Reputation compounds when you answer
other people's open problems, not when you announce your own — so the Scout hunts other people's
problems. Contacted issues are ledgered; nothing is posted without the owner's approval.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from agora.execution.competitor_watch import is_competitor_repo

_STORE = Path(__file__).resolve().parents[2] / ".scout.json"

# Agora's areas of genuine, evidenced strength — the Scout only pitches where we have real notes.
# Mix of the proven memory/causal themes (landed the zeroclaw win) + frontier-aligned themes
# (Science of Better Thinking + Future of Work) where our vault can still answer with EVIDENCE.
# CONCENTRATED on the inspeximus mission (2026-07-18, owner-locked frontier): every theme must be one where
# inspeximus can answer a real open GitHub issue with EVIDENCE (a measured receipt or a competitor-gap the
# vault documents). Off-mission themes (generic causal-inference, forecasting, KG-completion, CSD, multi-
# agent orchestration) were removed — they diluted the hourly rotation onto low-fit, off-inspeximus repos.
# THE BOARD DEPRIORITISES THE RETRIEVAL AXIS IN ITS OWN WORDS: "RAG chunking, reranking,
# long-context comparisons and multi-hop retrieval quality are a measured dead end for us and must
# never admit work on their own." Two themes here contradicted that -- "RAG memory retrieval
# forgetting" and "multi-hop retrieval memory" -- and this rotation is hourly, so 2 of 18 meant
# ~11% of every day's scanning fed the dead end. Measured 2026-08-18: 13 of one inbox's 59 tasks
# were external leads on that axis, every one triaged away again at the far end. Removed here,
# which is where they were produced.
_THEMES = [
    # core agent-memory
    "agent memory consolidation",
    "LLM long-term memory",
    "vector store memory pruning",
    "personal knowledge management note decay",
    "experience replay catastrophic forgetting",
    # memory-INTEGRITY (our measured moat: echo_guard, revert, supersession, provable erasure) +
    # the open cross-system benchmark (github.com/DanceNitra/agent-memory-integrity)
    "knowledge base contradiction detection",
    "agent memory stale facts correction",
    "memory update supersede outdated fact",
    "agent memory undo revert correction",
    "temporal validity bitemporal agent memory",
    "agent memory poisoning defense",
    # ecosystem / product wedge (where an inspeximus adapter or the MCP server is a concrete fit)
    "LangChain agent memory",
    "CrewAI agent memory",
    "LlamaIndex memory",
    "MCP memory server",
    "mem0 memory alternative",
]
_STOP = frozenset("the a an of for to in on and or is are how do does can with this that your you "
                  "what when where why who which from into our we us it its as be by at".split())



def _live_themes() -> list[str]:
    """`_THEMES` minus any theme the gatekeeper has explicitly refused.

    The skip list was consumed only by the dungeon's quest filter (dungeon_os/agent_worker.py:1186);
    the Scout rotated a hard-coded list and never read it. Measured 2026-08-18: two skips were
    recorded for the retrieval axis that morning and the Scout was still sitting on
    "multi-hop retrieval memory" that evening.

    EXACT match, deliberately. The skip store holds free text -- whole hypothesis sentences among
    them -- and a fuzzy matcher between that and a fixed theme list is the "criterion wider than the
    property" trap: it would silently refuse themes nobody skipped. An exact skip is a precise
    instruction and is honoured precisely; anything else is left alone and stays visible in the list.

    FAILS OPEN. If the store is unreadable, or if every theme were somehow refused, the rotation is
    returned unchanged rather than empty -- a scout scanning nothing looks identical to a dead organ,
    and is worse than one scanning the wrong thing.
    """
    try:
        from agora.execution.gatekeeper import skipped_themes
        refused = {str(t).strip().lower() for t in (skipped_themes() or [])}
    except Exception:                                                   # noqa: BLE001
        return list(_THEMES)
    live = [t for t in _THEMES if t.strip().lower() not in refused]
    return live or list(_THEMES)


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


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z\-]{2,}", (text or "").lower()) if w not in _STOP}


def _iso_to_ts(iso: str) -> float:
    try:
        from datetime import datetime, timezone
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return 0.0


MIN_STARS = 3   # a real-community bar: drop solo/0-star repos (keyword match != engagement target)


THEME_TRIES = 5   # how many themes one firing may try before giving up (see find_opportunity)


def find_opportunity(theme: str | None = None, tries: int | None = None) -> dict | None:
    """Search GitHub open issues across a rotating strength-theme; return the best-fit candidate
    not already contacted, with a fit score and its text for Claude to judge. Quality-gated: skip
    self-authored 'issues-as-notebook' entries and require a real-community repo (stars/forks), so a
    mere keyword match on a solo personal project is not surfaced as an outreach target.

    ONE DRY THEME NO LONGER WASTES A WHOLE FIRING. The theme used to be a single hourly rotation, so
    if that theme happened to have nothing, the firing found nothing and the next one was 2.5 hours
    away. Measured 2026-08-18: 6 of the 16 live themes had an offerable lead at that moment, so
    roughly three firings in five were guaranteed to come back empty while leads were sitting there.
    The rotation still decides where to START -- so the themes stay evenly covered over time -- and a
    firing now walks forward until one yields or `tries` themes are spent.

    `tries=1` restores the old single-theme cost, and READ-ONLY CALLERS MUST USE IT. /scout/status
    calls this to show a live candidate, so walking five themes turned a status read into five
    GitHub searches and hung it past any sane timeout -- measured immediately after this change went
    in. A visibility surface may not pay for discovery."""
    if theme is None:
        live = _live_themes()
        if not live:
            return None
        start = int(time.time() // 3600) % len(live)
        err = None
        for k in range(min(tries or THEME_TRIES, len(live))):
            r = find_opportunity(live[(start + k) % len(live)])
            if r and not r.get("error"):
                return r
            if r and r.get("error"):
                err = r          # remember an API failure; an empty theme is not one
        return err
    from agora.execution.correspondent import _api
    # SKIP WHAT THE BOX HAS SEEN, NOT ONLY WHAT THE LEDGER HAS. box_add() dedups against the box AND
    # the ledger; this used to read the ledger alone, so 93 URLs the box already held were re-findable
    # forever. Measured 2026-08-18 during a 30.8-hour discovery stall.
    seen = {x.get("url") for x in _load()} | {x.get("url") for x in box_load()}
    theme_words = _words(theme)
    q = urllib.parse.quote(f'{theme} is:issue is:open')
    try:
        res = _api("GET", f"/search/issues?q={q}&sort=updated&order=desc&per_page=15")
    except Exception as e:
        return {"error": str(e)[:120], "theme": theme}
    now = time.time()
    cands = []
    for it in res.get("items", []):
        url = it.get("html_url", "")
        if not url or url in seen or it.get("pull_request"):
            continue
        m = re.match(r"https://github\.com/([^/]+/[^/]+)/issues/(\d+)", url)
        if not m:
            continue
        repo = m.group(1)
        # never pitch our own repo (no audience there) — that is announcing, not engaging
        if repo.lower().startswith("dancenitra/"):
            continue
        # and never pitch a COMPETITOR's repo (owner's rule, 2026-08-07). Our strength themes are
        # their issue trackers' subject matter, so a theme search ranks them high by construction.
        # find_learning() below is deliberately NOT filtered — reading them is how we stay honest.
        if is_competitor_repo(repo):
            continue
        title, body = it.get("title", ""), (it.get("body") or "")[:1200]
        reactions = (it.get("reactions") or {}).get("total_count", 0)
        comments = it.get("comments", 0)
        author = (it.get("user") or {}).get("login", "").lower()
        owner = repo.split("/")[0].lower()
        # SKIP solo 'issues-as-notebook': the repo owner filing their own issue with NO community
        # response (0 comments + 0 reactions) is a private planning note, not a question to engage.
        if author == owner and comments == 0 and reactions == 0:
            continue
        # FRESHNESS — a reply only lands if the participants are still present. Skip cold threads.
        upd = it.get("updated_at") or ""
        age_d = (now - _iso_to_ts(upd)) / 86400 if upd else 999
        if age_d > 45:                      # cold thread — engaging it is shouting into a void
            continue
        # fit = how much the issue overlaps our strength theme + is it actually a question
        overlap = len(theme_words & _words(title + " " + body))
        asks = 1 if ("?" in title or "?" in body[:400]
                     or re.search(r"\bhow\b|\bwhy\b|\bbest way\b", (title + body[:200]).lower())) else 0
        fresh = 3 if age_d <= 7 else 2 if age_d <= 21 else 0
        score = overlap * 2 + asks * 3 + min(reactions, 5) + min(comments, 5) + fresh
        if score >= 5:
            cands.append({"url": url, "repo": repo, "issue_number": int(m.group(2)),
                          "title": title[:160], "body": body[:900], "theme": theme,
                          "score": score, "reactions": reactions, "comments": comments,
                          "age_days": round(age_d, 1)})
    # COMMUNITY GATE: check the top-scoring candidates' repos (bounded API calls) and return the first
    # that clears the real-community bar (stars/forks). Drops 0-star/0-fork solo projects entirely.
    #
    # AUDIENCE GATE (added 2026-07-30, after a measured miss): the repo bar is not enough, because it
    # asks whether the PROJECT is alive, not whether THIS THREAD is reachable. run-llama/llama_index#21666
    # scored fit 12 and sailed through on the repo's stars -- and the thread turned out to be ten
    # outsiders talking to each other: 26 comments over 2.5 months, every participant
    # author_association NONE, no maintainer having touched it once, and the accounts 4-8 months old with
    # 1-25 followers each while all linking their own projects. A full validate/storm/audit/verify cycle
    # was spent on a comment nobody would have read. The topic fit was real; the audience did not exist.
    for c in sorted(cands, key=lambda z: -z["score"])[:6]:
        # SUBJECT GATE, and it must be the SAME test box_add() applies. The fit score measures overlap
        # with a rotating theme; box_add() asks whether the thread is about memory at all. They can
        # disagree, and when they do the finder proposes a lead the box will always refuse, learns
        # nothing from the refusal, and offers it again on the next firing. Measured 2026-08-18:
        # langchain-ai/langgraph#5672 scored 15 and failed _about_memory, and the contribute half of
        # the Scout had been a silent no-op for 30.8 hours across roughly twelve firings. Checked here
        # because it is free, before the two API calls below.
        if not _about_memory(c):
            continue
        try:
            rp = _api("GET", f"/repos/{c['repo']}")
            stars = int(rp.get("stargazers_count", 0) or 0)
            forks = int(rp.get("forks_count", 0) or 0)
        except Exception:
            continue
        if not (stars >= MIN_STARS or forks >= 1):
            continue

        # Is anyone with authority actually in this thread? One extra call per candidate, same budget
        # shape as the repo check above.
        AUTHORITY = {"OWNER", "MEMBER", "COLLABORATOR", "CONTRIBUTOR"}
        maint = None
        try:
            cs = _api("GET", f"/repos/{c['repo']}/issues/{c['issue_number']}/comments?per_page=100")
            if isinstance(cs, list):
                maint = sum(1 for x in cs
                            if (x.get("author_association") or "").upper() in AUTHORITY)
        except Exception:
            maint = None          # unknown, not zero -- an API failure must not read as "dead thread"

        # Only judge a thread that has HAD a real discussion. Under 5 comments, no maintainer yet is
        # normal (nobody has answered, and being first is exactly the opening we want). At 5+ comments
        # with still nobody from the project, it is a side-conversation, not a place to be heard.
        if maint == 0 and c["comments"] >= 5:
            c["rejected"] = f"no maintainer in {c['comments']} comments"
            continue

        c["stars"] = stars
        c["forks"] = forks
        c["maintainer_comments"] = maint
        return c
    return None


def record_contacted(url: str, repo: str, issue: int, outcome: str = "drafted") -> dict | None:
    if not url:
        return None
    items = _load()
    if any(x.get("url") == url for x in items):
        return None
    rec = {"url": url, "repo": (repo or "")[:80], "issue": int(issue or 0),
           "outcome": (outcome or "")[:60], "ts": time.time()}
    items.append(rec)
    _save(items[-120:])
    return rec


def format_scout() -> str:
    items = _load()
    if not items:
        return "🔭 _The scout has logged no opportunities yet._"
    lines = [f"🔭 *The Opportunity Scout* — {len(items)} issues engaged"]
    for x in items[-6:][::-1]:
        lines.append(f"• [{x.get('outcome', '?')}] {x['repo']}#{x['issue']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------
# THE SCOUT BOX — the Scout collects; Claude drains. Separately.
#
# Until 2026-07-20 the dungeon's _queue_scout() returned early whenever a "Scout outreach" task was
# still pending in the Claude inbox, so ONE unprocessed task stopped every subsequent scan: the
# status read "last scan 23h ago" while the loop was firing on schedule and finding nothing to do.
# Discovery is cheap and perishable (a 45-day-old thread is already cold); triage is what is scarce.
# So scanning now fills a capped box and never waits, and exactly one lead is promoted into the inbox
# at a time — the outreach gate is unchanged, only the queueing is.
#
# Two kinds of lead, because not every useful find is something to answer:
#   contribute — an open issue where inspeximus/Agora can answer with evidence (the outreach path)
#   learn      — a PR or issue in the same problem space worth READING: how others solved what we are
#                solving, or a design decision we should not have to rediscover
_BOX = Path(__file__).resolve().parents[2] / ".scout_box.json"
BOX_CAP = 30

#: The agent this organ belongs to. Declared here and asserted against repair_ledger._ORGANS in tests,
#: so the ledger and the organ map cannot drift into naming different owners.
OWNER = "Shadow Kael"


def box_load() -> list:
    try:
        return json.loads(_BOX.read_text(encoding="utf-8"))
    except Exception:
        return []


def _box_save(items: list) -> None:
    try:
        _BOX.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


# The lead has to be ABOUT memory, not merely score well on a theme. Third time tonight this exact
# class of bug appeared: the task gate matched any board token, the contribution finder matched any
# offer keyword, and the scout matched any theme — each time dragging in something unrelated. Here it
# surfaced "[BOUNTY] Implement Device-Age Oracle Fields (fingerprint check)" from a bounty repo the
# July audit had already flagged as off-mission. Scout tasks bypass the inbox gate by design (they are
# machinery, not research themes), so the subject check has to live at the point of collection.
_SUBJECT = ("memory", "memories", "remember", "recall", "retrieval", "rag", "context window",
            "embedding", "vector store", "knowledge base", "mem0", "zep", "letta", "cognee",
            "langmem", "checkpointer", "basestore", "conversation history", "long-term memory",
            "long term memory", "agent memory", "supersede", "provenance", "forget")


def _about_memory(lead: dict) -> bool:
    blob = ((lead.get("title") or "") + " " + (lead.get("body") or "") + " " +
            (lead.get("repo") or "")).lower()
    return any(s in blob for s in _SUBJECT)


def box_add(lead: dict, kind: str = "contribute") -> dict | None:
    """Add a lead if it is new and there is room. Returns None when duplicate or full.

    Full means full: the cap is a signal that triage has stopped, not a buffer to silently overwrite.
    A dropped lead would be indistinguishable from one that was never found.
    """
    url = (lead or {}).get("url")
    if not url:
        return None
    if not _about_memory(lead):
        return None
    # Chokepoint backstop for the no-competitors rule: every path that offers help drains through
    # this box, so a future finder that forgets the filter still cannot queue a competitor lead.
    # Scoped to "contribute" — a "learn" lead from a competitor repo is intel, not support.
    if kind == "contribute" and is_competitor_repo(lead.get("repo") or ""):
        return None
    items = box_load()
    if any(x.get("url") == url for x in items):
        return None
    if any(x.get("url") == url for x in _load()):      # already engaged in the ledger
        return None
    if len([x for x in items if x.get("status") == "open"]) >= BOX_CAP:
        return None
    rec = dict(lead)
    # NAME THE AGENT WHO DID THE WORK (2026-07-31). This box recorded repo, url, score, theme, status
    # and timestamps -- everything except WHO found and ruled on the lead. Shadow Kael owns the scout
    # organ and this is its ledger (repair_ledger._ORGANS), so every record is his. Measured: the swarm
    # acceptance gate scored his 3 decisive rulings in 24h as "no named actor" and FAILED him. An organ
    # that closes work anonymously cannot be credited, and an uncredited agent reads as an idle one --
    # which is exactly how two of the busiest agents in the keep came to be reported as doing nothing.
    rec.update({"kind": kind, "status": "open", "by": OWNER, "found_ts": time.time()})
    items.append(rec)
    _box_save(items[-200:])
    return rec


def box_take(kind: str = "contribute") -> dict | None:
    """Highest-scoring open lead of a kind, marked as taken. This is what gets promoted to the inbox."""
    items = box_load()
    open_ = [x for x in items if x.get("status") == "open" and x.get("kind") == kind]
    if not open_:
        return None
    best = max(open_, key=lambda z: (z.get("score", 0), z.get("found_ts", 0)))
    for x in items:
        if x.get("url") == best.get("url"):
            x["status"] = "taken"
            x["taken_ts"] = time.time()
    _box_save(items)
    return best


def box_mark(url: str, status: str = "done") -> bool:
    items = box_load()
    hit = False
    for x in items:
        if x.get("url") == url:
            x["status"] = (status or "done")[:20]
            x["closed_ts"] = time.time()
            x.setdefault("by", OWNER)      # a record closed before `by` existed still names its owner
            hit = True
    if hit:
        _box_save(items)
    return hit


def box_rule(url: str, verdict: str, by: str = "") -> bool:
    """Record the Scout's RULING on a lead without touching where the pipeline stands.

    `status` tracks the GATED pipeline -- open -> drafted -> posted -- and a real fit must stay
    `open` until the owner approves, because nothing goes outward unapproved. `verdict` records what
    Shadow Kael DECIDED, which is finished work the moment he decides it.

    They were one field, and that made his ledger incoherent: a `no_fit` was marked and counted as a
    decisive outcome, while a FIT -- strictly more work, measured against the board, the vault and
    the thread's reachability, and grounded by a Lab run -- was left `open` and scored as nothing.
    Measured 2026-07-31: 9 box records in the window, every one `open`, and the acceptance gate
    reported Shadow Kael with 0 decisive outcomes on the same cycle his contribution landed as a
    grounded discovery. The instrument was crediting him for finding nothing and not for finding
    something.
    """
    v = (verdict or "").strip()[:20]
    if not url or not v:
        return False
    items = box_load()
    hit = False
    for x in items:
        if x.get("url") == url:
            x["verdict"] = v
            x["ruled_ts"] = time.time()
            x.setdefault("by", by or OWNER)
            hit = True
    if hit:
        _box_save(items)
    return hit


def box_stats() -> dict:
    items = box_load()
    open_ = [x for x in items if x.get("status") == "open"]
    return {"open": len(open_), "cap": BOX_CAP, "full": len(open_) >= BOX_CAP,
            "by_kind": {k: len([x for x in open_ if x.get("kind") == k])
                        for k in ("contribute", "learn")},
            "total_seen": len(items),
            "oldest_open_days": round((time.time() - min((x.get("found_ts", time.time())
                                                          for x in open_), default=time.time())) / 86400, 1)}


def find_learning() -> dict | None:
    """A merged PR in our problem space worth READING — not something to answer.

    The outreach scan deliberately skips pull requests: you do not pitch a PR. But a merged PR in an
    agent-memory project is the most concentrated form of "how somebody else solved the thing we are
    solving", and reading one costs nothing and cannot embarrass us. Scored for substance (files and
    review discussion) rather than for fit with our strengths — the point is what we do NOT know.
    """
    from agora.execution.correspondent import _api
    seen = {x.get("url") for x in box_load()} | {x.get("url") for x in _load()}
    _live = _live_themes()
    rot = int(time.time() // 3600) % len(_live)
    theme = _live[rot]
    q = urllib.parse.quote(f"{theme} is:pr is:merged")
    try:
        res = _api("GET", f"/search/issues?q={q}&sort=updated&order=desc&per_page=15")
    except Exception as e:
        return {"error": str(e)[:120], "theme": theme}
    now = time.time()
    best = None
    for it in res.get("items", []):
        url = it.get("html_url", "")
        if not url or url in seen:
            continue
        m = re.match(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)", url)
        if not m:
            continue
        repo = m.group(1)
        if repo.lower().startswith("dancenitra/"):        # our own work teaches us nothing new
            continue
        upd = it.get("updated_at") or ""
        age_d = (now - _iso_to_ts(upd)) / 86400 if upd else 999
        if age_d > 120:                                   # older than that and the code has moved on
            continue
        comments = it.get("comments", 0)
        body = (it.get("body") or "")[:900]
        # substance: a reviewed PR with a written rationale teaches more than a one-line fix
        score = min(comments, 8) + (3 if len(body) > 400 else 0) + (2 if age_d <= 30 else 0)
        cand = {"url": url, "repo": repo, "issue_number": int(m.group(2)),
                "title": it.get("title", "")[:160], "body": body, "theme": theme,
                "score": score, "comments": comments, "age_days": round(age_d, 1)}
        if best is None or cand["score"] > best["score"]:
            best = cand
    return best
