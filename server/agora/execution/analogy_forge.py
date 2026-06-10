"""
The Analogy Forge — bisociation as a scheduled habit, not an accident.

The system's strongest idea to date (detection thresholds as critical points) was born from one
cognitive move: lifting the STRUCTURE of a mechanism out of its home domain and forcing it onto
a foreign one. Embedding-similarity bridges can't make that move — they find surface resemblance,
not shared skeletons. The Forge makes the move routine: pick the vault's most mechanism-dense
concept note that hasn't been forged yet, pair it with a board-priority domain, and demand a
structural mapping WITH a runnable Lab test (severe-test rule). Most forgings will die in the
Lab — that's the point; the ones that survive are the mind-blowers.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".analogies.json"

# Markers of transferable MECHANISM (dynamics, not topic). A note rich in these describes a
# skeleton that can wear different flesh.
_MARKERS = (
    "feedback", "threshold", "equilibrium", "phase transition", "scaling", "diffusion",
    "selection pressure", "cascade", "hysteresis", "saturation", "bottleneck", "attractor",
    "bifurcation", "percolation", "critical", "homeostasis", "oscillat", "arbitrage",
    "compound", "network effect", "amplif", "damping", "resonance", "load balanc",
    "entropy", "gradient", "immune", "epidemi", "queue", "carrying capacity",
)


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


def _note_title(text: str, fallback: str) -> str:
    m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", text[:600], re.MULTILINE)
    return (m.group(1) if m else fallback).strip()


def pick_mechanism(vault: str) -> dict | None:
    """The most mechanism-dense concept note not yet forged — title, path, excerpt, score.
    Owner concepts only (the Agora Agents subtree is the system's own output)."""
    base = Path(vault) / "04 Resources" / "Concepts"
    if not base.is_dir():
        return None
    used = {(x.get("mechanism") or "").lower() for x in _load()}
    best = None
    for p in base.rglob("*.md"):
        if "Agora Agents" in str(p):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")[:5000]
        except Exception:
            continue
        title = _note_title(text, p.stem)
        if title.lower() in used:
            continue
        low = text.lower()
        score = sum(low.count(m) for m in _MARKERS)
        if score >= 4 and (best is None or score > best["score"]):
            body = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)
            best = {"title": title[:120], "path": str(p), "score": score,
                    "excerpt": body[:700]}
    return best


def record_forged(mechanism: str, target: str, note: str = "", outcome: str = "") -> dict:
    rec = {"mechanism": (mechanism or "")[:120], "target": (target or "")[:120],
           "note": (note or "")[:200], "outcome": (outcome or "")[:200], "ts": time.time()}
    items = _load()
    items.append(rec)
    _save(items[-100:])
    return rec


def format_analogies() -> str:
    items = _load()
    if not items:
        return "⚒ _The forge is cold — no mechanism has been hammered into a new domain yet._"
    lines = [f"⚒ *The Analogy Forge* — {len(items)} forgings"]
    for r in items[-6:][::-1]:
        lines.append(f"• '{r['mechanism'][:40]}' → {r['target'][:40]}")
        if r.get("outcome"):
            lines.append(f"   {r['outcome'][:80]}")
    return "\n".join(lines)
