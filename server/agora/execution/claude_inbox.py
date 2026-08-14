"""
Remote-control channel for Claude Code.

The brain's Telegram poller is the single reader of the chat. When the user texts a task addressed
to Claude Code (prefix cc/claude/build/task/implement), the poller drops it here. Claude Code reads
this inbox on its next wake (via /brain/claude-inbox), works the task, posts the result back to
Telegram, and marks it done. So the user can hand Claude Code build/implementation work from their
phone, from anywhere, and get answers.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

INBOX = Path(__file__).resolve().parents[2] / ".claude_inbox.json"   # server/.claude_inbox.json
FEED = Path(__file__).resolve().parents[2] / ".telegram_feed.json"   # everything sent to Telegram

# Dedup gate — agents kept re-queuing the SAME target (challenge unit-economics 3x, the
# synthetic-control dialectic 3x), because the old check only looked at PENDING tasks, so once a
# task was done it could be re-picked forever. We now reject a new task whose normalized signature
# matches one already handled (pending OR done) inside the window.
_DEDUP_WINDOW_S = 36 * 3600
_DEDUP_JACCARD = 0.82
_STOPWORDS = frozenset(
    "the a an of for to in on and or is are with this that which from into our we us it its as be "
    "by at insight hypothesis pipeline campaign falsifier path source via how what when where why".split())


def _signature(text: str) -> frozenset:
    """Normalised token set of a task's CORE intent. Strips only NOISE (file paths, bracketed/
    campaign/market ids, bridge counts) — NOT the distinguishing content like a deepen's falsifier
    text — so genuine duplicates collide while different targets stay distinct."""
    s = (text or "").lower()
    s = re.sub(r"\[[0-9a-f]{4,}\]", " ", s)                    # bracketed ids [20156b19]
    s = re.sub(r"campaign\s+[0-9a-f]{6,}", " ", s)             # campaign ids
    s = re.sub(r"\|\|\s*path:\s*[^|]+", " ", s)                # '|| path: C:\…' metadata
    s = re.sub(r"[a-z]:\\[^\s|]+", " ", s)                     # stray windows paths
    s = re.sub(r"market_id:\s*\d+|market_prob:[^|]*|ends:\s*[\d-]+|bridges now:\s*\d+", " ", s)
    toks = [w for w in re.findall(r"[a-z][a-z\-]{2,}", s) if w not in _STOPWORDS]
    return frozenset(toks)


def _is_duplicate(sig: frozenset, items: list, now: float) -> str:
    if not sig:
        return ""
    for t in items:
        if now - t.get("ts", 0) > _DEDUP_WINDOW_S:
            continue
        other = _signature(t.get("text", ""))
        if not other:
            continue
        inter = len(sig & other)
        union = len(sig | other)
        if union and inter / union >= _DEDUP_JACCARD:
            return t.get("id", "")
    return ""


def feed_append(text: str) -> None:
    """Record an outgoing Telegram message so Claude Code can read the same feed the user sees."""
    try:
        items = json.loads(FEED.read_text(encoding="utf-8"))
    except Exception:
        items = []
    items.append({"ts": time.time(), "text": (text or "")[:1500]})
    try:
        FEED.write_text(json.dumps(items[-80:], ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def feed_recent(n: int = 20) -> list:
    try:
        return json.loads(FEED.read_text(encoding="utf-8"))[-n:]
    except Exception:
        return []


def _load() -> list:
    try:
        return json.loads(INBOX.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    INBOX.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def add_task(text: str, untrusted: str = "", source: str = "") -> str:
    """Queue a task for Claude Code.

    `text` is OUR instruction. `untrusted` is third-party content — a stranger's GitHub issue body,
    a harvested reply, a web-search snippet, a paper abstract — and it is sanitized and enveloped
    HERE rather than by the caller.

    WHY THE SIGNATURE CHANGED. `input_shield.wrap_as_data` exists precisely for this flow; its own
    docstring says "The Correspondent harvests replies from strangers on the public web straight
    toward Claude's task inbox." A repo-wide grep on 2026-08-14 found it called at exactly ONE site,
    while three others fed the same class of text in raw:

      * server/agora/main.py — the envoy loop, which is the one that actually fires (registered in
        lifespan, every 30 min), while the guarded copy was the on-demand endpoint. Same data, two
        doors, one guard, and the guard was on the door used less.
      * agora-game-server/mcp_server.py — Scout triage, interpolating a stranger's issue title and
        body[:320] into a task whose next instruction is "draft a gated reply".
      * server/agora/execution/web_search.py — third-party title and snippet.

    Sanitizing the WHOLE string here would be wrong: a task mixes our operational instructions with
    the third-party span, and defanging our own text would corrupt legitimate tasks. So the split is
    the fix — the caller cannot concatenate untrusted content into `text` without going out of its
    way, and every caller added later inherits the envelope for free. That is the difference between
    closing a class and patching three instances; the sibling gate `_inbox_theme_allowed` records
    the same drift in its own docstring (31 queueing functions, 5 gate calls).

    This does NOT make injection impossible. The mechanical half of the shield (zero-width and bidi
    stripping, control chars, collapsing code fences that could re-open an instruction block) is a
    real and deterministic win; the prose envelope is weaker and a determined injection walks past
    it. The point is that the mechanical half now runs on every path.
    """
    if untrusted:
        from agora.execution.input_shield import wrap_as_data
        text = (text or "").rstrip() + "\n\n" + wrap_as_data(source or "an external source",
                                                             untrusted)
    items = _load()
    now = time.time()
    dup = _is_duplicate(_signature(text), items, now)
    if dup:
        return dup                      # already handled (pending or recently done) — don't re-queue
    tid = uuid.uuid4().hex[:6]
    items.append({"id": tid, "text": text, "ts": now,
                  "status": "pending", "result": ""})
    _save(items[-100:])
    return tid


def pending() -> list:
    return [t for t in _load() if t.get("status") == "pending"]


def recent_texts(window_s: float = _DEDUP_WINDOW_S) -> list[str]:
    """Texts of every task (pending or done) handled inside the window — so target SELECTORS can
    avoid re-picking what was just worked, broadening coverage instead of cycling on one target."""
    now = time.time()
    return [t.get("text", "") for t in _load() if now - t.get("ts", 0) <= window_s]


def mark_done(task_id: str, result: str) -> None:
    items = _load()
    for t in items:
        if t.get("id") == task_id:
            t["status"] = "done"
            t["result"] = (result or "")[:800]
            t["done_ts"] = time.time()
    _save(items)
