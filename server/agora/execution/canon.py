"""
The Canon — one living book of what Agora currently believes.

Artifacts pile up (insights, hypotheses, dialectics, dossiers, papers, worldviews) and the
owner needs ONE place that holds the current best understanding. The Canon is a single vault
document that Claude MERGES (never appends) whenever enough new artifacts have landed: each
belief gets one paragraph with its status and links, organized by domain cluster. The
worldview note is a snapshot; the Canon is the textbook that keeps being rewritten — and its
history lives in git.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

_CANON_REL = "04 Resources/Concepts/Agora Agents/Canon — What Agora Currently Believes.md"
_ARTIFACT_GLOBS = ("insight*.md", "hypothesis*.md", "dialectic*.md", "dossier*.md",
                   "paper*.md", "post-mortem*.md")


def canon_path(vault_path: str) -> Path:
    return Path(vault_path) / _CANON_REL


def read_canon(vault_path: str) -> str:
    p = canon_path(vault_path)
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def write_canon(vault_path: str, content: str) -> str:
    """Replace the Canon wholesale (Claude supplies the merged text). Stamps updated:."""
    p = canon_path(vault_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    today = time.strftime("%Y-%m-%d %H:%M")
    if not content.lstrip().startswith("---"):
        content = (f"---\ntitle: Canon — What Agora Currently Believes\n"
                   f"tags: [agora, canon, claude-synthesis]\nupdated: {today}\n---\n\n" + content)
    elif re.search(r"^updated:", content[:600], re.M):
        content = re.sub(r"^updated:.*$", f"updated: {today}", content, count=1, flags=re.M)
    else:
        content = re.sub(r"^---\s*$", f"---\nupdated: {today}", content, count=1, flags=re.M)
    p.write_text(content, encoding="utf-8")
    return str(p)


def _canon_updated_ts(vault_path: str) -> float:
    text = read_canon(vault_path)
    m = re.search(r"^updated:\s*(\d{4})-(\d{2})-(\d{2})", text[:600], re.M)
    if not m:
        return 0.0
    return time.mktime((int(m.group(1)), int(m.group(2)), int(m.group(3)), 23, 59, 0, 0, 0, -1))


def new_artifacts_since_canon(vault_path: str) -> list[dict]:
    """Artifacts created after the Canon's last update (by frontmatter created:, mtime fallback)."""
    root = Path(vault_path) / "04 Resources/Concepts/Agora Agents"
    cutoff = _canon_updated_ts(vault_path)
    out = []
    if not root.is_dir():
        return out
    for pattern in _ARTIFACT_GLOBS:
        for p in root.rglob(pattern):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            m = re.search(r"^created:\s*(\d{4})-(\d{2})-(\d{2})", text[:800], re.M)
            ts = (time.mktime((int(m.group(1)), int(m.group(2)), int(m.group(3)), 12, 0, 0, 0, 0, -1))
                  if m else p.stat().st_mtime)
            if ts > cutoff:
                tm = re.search(r"^title:\s*(.+)$", text[:600], re.M)
                core = ""
                sm = re.search(r"##\s*(The insight|Hypothesis|Answer)\s*\n(.+?)(?=\n##|\Z)",
                               text, re.DOTALL | re.IGNORECASE)
                if sm:
                    core = re.sub(r"\s+", " ", sm.group(2)).strip()[:500]
                out.append({"title": (tm.group(1).strip().strip('"') if tm else p.stem),
                            "kind": p.name.split("-")[0], "core": core})
    return out


def gather_canon_inputs(vault_path: str) -> dict:
    """Everything Claude needs to rewrite the Canon: its current text + the new artifacts."""
    return {"canon": read_canon(vault_path)[:9000],
            "new_artifacts": new_artifacts_since_canon(vault_path)[:14]}
