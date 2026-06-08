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
import time
import uuid
from pathlib import Path

INBOX = Path(__file__).resolve().parents[2] / ".claude_inbox.json"   # server/.claude_inbox.json


def _load() -> list:
    try:
        return json.loads(INBOX.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    INBOX.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def add_task(text: str) -> str:
    items = _load()
    tid = uuid.uuid4().hex[:6]
    items.append({"id": tid, "text": text, "ts": time.time(),
                  "status": "pending", "result": ""})
    _save(items[-100:])
    return tid


def pending() -> list:
    return [t for t in _load() if t.get("status") == "pending"]


def mark_done(task_id: str, result: str) -> None:
    items = _load()
    for t in items:
        if t.get("id") == task_id:
            t["status"] = "done"
            t["result"] = (result or "")[:800]
            t["done_ts"] = time.time()
    _save(items)
