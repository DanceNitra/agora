"""
The Memory Economy — the Custodian actually governs.

Agora's own grand insight (the Custodian Principle) says intelligence is the governance of a
scarce memory under challenge. Until now the vault only GROWS. This module is the missing prune
half: every note gets a value account (substance, connectivity, retrieval demand, freshness,
verification), and the lowest-value dead weight — old, unlinked, never-retrieved stubs — is
proposed for archival as a GATED action. Nothing moves until Rasto approves from Telegram, and
even then notes are QUARANTINED (reversible move + manifest), never deleted.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

QUARANTINE = Path("C:/Users/Danculus/_vault_quarantine")
_SKIP_DIRS = (".obsidian", ".git", ".trash", "06 System", "System", "Templates", "templates",
              "Agora Agents", "Daily", "Backups", ".meta", "Sessions")
_WIKILINK = re.compile(r"\[\[([^\]|#]+)")
_FM_DATE = re.compile(r"^(created|updated):\s*[\"']?(\d{4})-(\d{2})-(\d{2})", re.M)


def _note_age_ts(head: str, mtime: float) -> float:
    """Last-touched timestamp from frontmatter (updated > created) — git checkouts reset every
    file mtime, so mtime alone calls the whole vault 'fresh'. Falls back to mtime."""
    best = None
    for kind, y, mo, d in _FM_DATE.findall(head):
        try:
            ts = time.mktime((int(y), int(mo), int(d), 12, 0, 0, 0, 0, -1))
        except Exception:
            continue
        if kind == "updated":
            return ts
        best = ts if best is None else max(best, ts)
    return best if best is not None else mtime


def _retrieval_counts() -> dict:
    from agora.execution.semantic_index import retrieval_counts
    try:
        return retrieval_counts()
    except Exception:
        return {}


def score_notes(vault_path: str) -> list[dict]:
    """One pass over the vault: per-note value account. Higher = earning its keep.
    Components: substance (length), connectivity (in+out wikilinks), retrieval demand
    (semantic-search hits), freshness (recent edit), settledness (evergreen status)."""
    root = Path(vault_path)
    notes, outlinks, titles = [], {}, set()
    for p in root.rglob("*.md"):
        sp = str(p)
        if any(s in sp for s in _SKIP_DIRS):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
            st = p.stat()
        except Exception:
            continue
        title = p.stem.lower().strip()
        titles.add(title)
        outlinks[title] = {t.strip().lower() for t in _WIKILINK.findall(txt)}
        head = txt[:1200]
        notes.append({"path": str(p.relative_to(root)), "title": p.stem,
                      "chars": len(txt), "mtime": _note_age_ts(head, st.st_mtime),
                      "evergreen": "status: evergreen" in head})
    inlinks: dict[str, int] = {}
    for src, outs in outlinks.items():
        for t in outs:
            if t in titles:
                inlinks[t] = inlinks.get(t, 0) + 1
    hits = _retrieval_counts()
    now = time.time()
    for n in notes:
        t = n["title"].lower().strip()
        n["inlinks"] = inlinks.get(t, 0)
        n["outlinks"] = len(outlinks.get(t, set()))
        n["retrievals"] = int((hits.get(n["path"]) or {}).get("n", 0))
        n["age_days"] = round((now - n["mtime"]) / 86400, 1)
        value = 0
        value += 2 if n["chars"] >= 900 else (1 if n["chars"] >= 400 else 0)
        links = n["inlinks"] + n["outlinks"]
        value += 2 if links >= 3 else (1 if links >= 1 else 0)
        value += 2 if n["retrievals"] >= 3 else (1 if n["retrievals"] >= 1 else 0)
        value += 2 if n["age_days"] <= 30 else (1 if n["age_days"] <= 90 else 0)
        value += 2 if n["evergreen"] else 0
        n["value"] = value
    return notes


def prune_candidates(vault_path: str, n: int = 12) -> list[dict]:
    """The dead weight, conservatively: old, small, unlinked, never-retrieved, NOT evergreen,
    NOT recently edited. These are the notes the Custodian proposes to archive."""
    out = [x for x in score_notes(vault_path)
           if not x["evergreen"] and x["age_days"] > 30 and x["chars"] < 700
           and x["inlinks"] == 0 and x["retrievals"] == 0 and x["value"] <= 2]
    return sorted(out, key=lambda x: (x["value"], -x["age_days"]))[:n]


def quarantine_notes(vault_path: str, rel_paths: list[str]) -> dict:
    """Reversibly move notes out of the vault into a timestamped quarantine batch with a
    manifest. Never deletes; restore_batch() undoes the whole batch."""
    root = Path(vault_path)
    batch = QUARANTINE / time.strftime("%Y%m%d-%H%M%S")
    moved = []
    for rel in rel_paths:
        src = root / rel
        if not src.is_file() or any(s in str(src) for s in _SKIP_DIRS):
            continue
        dst = batch / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved.append({"from": str(src), "to": str(dst)})
    if moved:
        (batch / "manifest.json").write_text(
            json.dumps({"vault": str(root), "ts": time.time(), "moved": moved},
                       ensure_ascii=False, indent=1), encoding="utf-8")
    return {"batch": str(batch) if moved else "", "moved": len(moved)}


def restore_batch(batch_dir: str) -> dict:
    """Undo a quarantine batch — move every note back where it came from."""
    manifest = Path(batch_dir) / "manifest.json"
    if not manifest.is_file():
        return {"restored": 0, "error": "no manifest"}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    restored = 0
    for m in data.get("moved", []):
        src, dst = Path(m["to"]), Path(m["from"])
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            restored += 1
    return {"restored": restored}


def format_economy(notes: list[dict], candidates: list[dict]) -> str:
    """One-screen Telegram view of the memory economy."""
    if not notes:
        return "🏛 _The memory economy has no data yet._"
    total = len(notes)
    dead = len(candidates)
    avg = round(sum(x["value"] for x in notes) / total, 2)
    lines = [f"🏛 *Memory economy* — {total} notes, avg value {avg}/10",
             f"Dead weight (old+unlinked+unretrieved stubs): *{dead}*"]
    for c in candidates[:8]:
        lines.append(f"  • {c['title'][:44]} _(v{c['value']}, {c['chars']}ch, {c['age_days']:.0f}d)_")
    return "\n".join(lines)
