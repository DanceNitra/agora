"""
The Press — the company's storefront.

The engine produces results that die in the vault: a measured phase-diagram for causal
inference, a graded AI×biology bridge, failed replications when they come. The Press turns the
best of them into polished standalone posts in the public repo's `public/posts/` — every piece
carries its falsifier and its accountability line, because publishing claims without exposure
is marketing, and we are not a marketing department. Strictly gated: Claude drafts, the owner
approves from Telegram, only then does anything leave the machine.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".press.json"
AGORA_REPO = Path(__file__).resolve().parents[3]
POSTS_REL = "public/posts"
_REPO_URL = "https://github.com/DanceNitra/agora/blob/main"


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


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9 -]", "", (text or "")).strip().lower()
    return re.sub(r"[ _]+", "-", s)[:60] or "post"


def save_piece(title: str, body: str, source_note: str = "") -> dict:
    """Store Claude's polished piece; the caller proposes the gated 'press' action around it."""
    rec = {"id": uuid.uuid4().hex[:6], "title": (title or "")[:160], "body": (body or "")[:12000],
           "source": (source_note or "")[:160], "status": "draft", "ts": time.time()}
    items = _load()
    items.append(rec)
    _save(items[-60:])
    return rec


def covered_titles() -> list[str]:
    return [x.get("title", "") for x in _load()]


def publish_piece(pid: str) -> dict:
    """PUBLISH (call only from an approved gated action): write the piece into public/posts/,
    commit ONLY that file, push. Returns the public URL."""
    items = _load()
    rec = next((x for x in items if x.get("id") == pid), None)
    if not rec or rec.get("status") not in ("draft", "proposed"):
        return {"error": "no publishable piece"}
    fname = f"{time.strftime('%Y-%m-%d')}-{_slug(rec['title'])}.md"
    rel = f"{POSTS_REL}/{fname}"
    dst = AGORA_REPO / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    footer = ("\n\n---\n*Published by [Agora](https://github.com/DanceNitra/agora), an "
              "autonomous research OS, with its owner's review and approval. Every claim above "
              "ships with the test that would kill it.*\n")
    dst.write_text(rec["body"] + footer, encoding="utf-8")

    def _git(*args):
        return subprocess.run(["git", "-C", str(AGORA_REPO), *args],
                              capture_output=True, text=True, timeout=60)
    _git("add", rel)
    c = _git("commit", "-m", f"Press: {rec['title'][:60]}")
    if "nothing to commit" in (c.stdout + c.stderr):
        return {"error": "nothing to commit (identical piece already published?)"}
    p = _git("push", "origin", "main")
    if p.returncode != 0:
        return {"error": ("push failed: " + (p.stderr or p.stdout))[:200]}
    rec["status"] = "published"
    rec["url"] = f"{_REPO_URL}/{rel}"
    rec["published_ts"] = time.time()
    _save(items)
    return {"url": rec["url"]}


def pick_target(vault: str) -> dict | None:
    """The strongest unpublished artifact: a recent agora note of a press-worthy kind
    (lab/bridge/analogy/dossier/dialectic), preferring ones with measured numbers."""
    src = Path(vault) / "04 Resources" / "Concepts" / "Agora Agents"
    if not src.is_dir():
        return None
    covered = {t[:50].lower() for t in covered_titles()}
    week_ago = time.time() - 7 * 86400
    best = None
    for p in src.rglob("*.md"):
        stem = p.stem.lower()
        if not stem.startswith(("lab-", "bridge-", "analogy-", "dossier-", "dialectic-")):
            continue
        try:
            if p.stat().st_mtime < week_ago:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")[:4000]
        except Exception:
            continue
        tm = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", text[:500], re.MULTILINE)
        title = (tm.group(1) if tm else p.stem).strip()
        if title[:50].lower() in covered:
            continue
        # measured numbers make a piece publishable, not just readable
        score = (3 * len(re.findall(r"\d+(?:\.\d+)?\s*%", text))
                 + 2 * text.lower().count("measured")
                 + 2 * text.lower().count("lab ")
                 + text.lower().count("falsifier"))
        if best is None or score > best["score"]:
            best = {"title": title[:140], "path": str(p), "score": score}
    return best


def format_press() -> str:
    items = _load()
    if not items:
        return "📰 _The press is quiet — no piece has been drafted yet._"
    pub = sum(1 for x in items if x.get("status") == "published")
    lines = [f"📰 *The Press* — {pub} published / {len(items)} drafted"]
    icon = {"draft": "📝", "proposed": "⏸️", "published": "📣"}
    for x in items[-6:][::-1]:
        lines.append(f"{icon.get(x['status'], '•')} [{x['status']}] {x['title'][:58]}")
        if x.get("url"):
            lines.append(f"    {x['url']}")
    return "\n".join(lines)
