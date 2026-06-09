"""
Belief Revision — Agora can kill its own ideas.

The vault only ever ACCUMULATES beliefs; nothing retires them. Science is not adding truths,
it is burying errors. This gives every belief (insight / hypothesis note) a lifecycle:

    active → challenged → survived | revised | retired

A periodic CHALLENGE SWEEP picks the belief that has gone longest without being tested and
queues it for Claude, who gathers disconfirming evidence and rules: survived (stamped, with a
survival count), revised (a sharper v2 supersedes it), or retired (a post-mortem buries it).
Superseded notes stay in the vault — stamped and bannered, never deleted — so the graveyard
itself is part of the record.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

_AGENTS_DIR = "04 Resources/Concepts/Agora Agents"
_BELIEF_GLOBS = ("insight*.md", "hypothesis*.md")


def _beliefs_dir(vault_path: str) -> Path:
    return Path(vault_path) / _AGENTS_DIR


def _frontmatter_get(text: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.+)$", text[:1500], re.M)
    return m.group(1).strip().strip('"') if m else ""


def list_beliefs(vault_path: str) -> list[dict]:
    """Every active belief note with its challenge history."""
    out = []
    root = _beliefs_dir(vault_path)
    if not root.is_dir():
        return out
    for pattern in _BELIEF_GLOBS:
        for p in root.rglob(pattern):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            status = _frontmatter_get(text, "belief_status") or "active"
            last = _frontmatter_get(text, "last_challenged")
            out.append({"path": str(p), "title": _frontmatter_get(text, "title") or p.stem,
                        "type": "hypothesis" if p.name.startswith("hypothesis") else "insight",
                        "belief_status": status, "last_challenged": last,
                        "survived": int(_frontmatter_get(text, "challenges_survived") or 0)})
    return out


def pick_challenge_target(vault_path: str) -> dict | None:
    """The belief longest without a test: never-challenged first (oldest file), then the
    stalest last_challenged. Superseded notes are out of the game."""
    alive = [b for b in list_beliefs(vault_path)
             if b["belief_status"] in ("active", "survived")]
    if not alive:
        return None
    never = [b for b in alive if not b["last_challenged"]]
    if never:
        return sorted(never, key=lambda b: Path(b["path"]).stat().st_mtime)[0]
    return sorted(alive, key=lambda b: b["last_challenged"])[0]


def stamp_belief(path: str, verdict: str, by_note: str = "", reason: str = "") -> dict:
    """Record a challenge outcome on the note itself.
    survived  -> belief_status: survived, challenges_survived += 1
    revised   -> belief_status: superseded + banner linking the v2
    retired   -> belief_status: retired  + post-mortem banner"""
    p = Path(path)
    if not p.is_file():
        return {"error": "no such note"}
    text = p.read_text(encoding="utf-8", errors="replace")
    today = time.strftime("%Y-%m-%d")
    survived = int(_frontmatter_get(text, "challenges_survived") or 0)

    def _set(key: str, value: str, t: str) -> str:
        if re.search(rf"^{key}:", t[:1500], re.M):
            return re.sub(rf"^{key}:.*$", f"{key}: {value}", t, count=1, flags=re.M)
        return re.sub(r"^---\s*$", f"---\n{key}: {value}", t, count=1, flags=re.M)

    if verdict == "survived":
        text = _set("belief_status", "survived", text)
        text = _set("challenges_survived", str(survived + 1), text)
    elif verdict in ("revised", "retired"):
        text = _set("belief_status", "superseded" if verdict == "revised" else "retired", text)
        link = f" by [[{by_note}]]" if by_note else ""
        banner = (f"\n> ⚠️ **{'SUPERSEDED' if verdict == 'revised' else 'RETIRED'}** "
                  f"({today}){link} — {reason[:200]}\n")
        # banner goes right after the frontmatter block
        m = re.search(r"^---.*?^---\s*$", text, re.M | re.DOTALL)
        text = (text[:m.end()] + banner + text[m.end():]) if m else banner + text
    else:
        return {"error": f"unknown verdict '{verdict}'"}
    text = _set("last_challenged", today, text)
    p.write_text(text, encoding="utf-8")
    return {"status": "ok", "verdict": verdict, "title": _frontmatter_get(text, "title")}


def format_beliefs(vault_path: str) -> str:
    bs = list_beliefs(vault_path)
    if not bs:
        return "⚖️ _No beliefs on record._"
    icon = {"active": "•", "survived": "🛡", "superseded": "♻️", "retired": "🪦"}
    lines = [f"⚖️ *Agora's beliefs* — {len(bs)} on record"]
    for b in sorted(bs, key=lambda x: x["belief_status"]):
        tail = f" (survived ×{b['survived']})" if b["survived"] else ""
        lines.append(f"{icon.get(b['belief_status'], '•')} {b['title'][:62]}{tail}")
    return "\n".join(lines)
