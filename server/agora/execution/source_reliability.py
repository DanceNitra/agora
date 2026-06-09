"""
Source Reliability — not all of Agora's eyes see equally well.

Every source (arXiv, OpenAlex, Hacker News, World Bank, PubMed, Wikipedia…) has been treated
as equally credible. This ledger attributes every verification and reality-check verdict to
the source that delivered it: a decisive verdict (VERIFIED/OVERSTATED/SUPPORTED/REFUTED/MIXED)
counts as a hit, a non-answer (INCONCLUSIVE/INSUFFICIENT) as a miss. Over time each source
earns a reliability weight that is surfaced to the synthesis layer — so Claude reads "World
Bank: strong, HN traction: weak" alongside the evidence itself.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".source_reliability.json"
_HIT = {"VERIFIED", "OVERSTATED", "SUPPORTED", "REFUTED", "MIXED"}
_MISS = {"INCONCLUSIVE", "INSUFFICIENT", "UNSUPPORTED"}


def _load() -> dict:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d: dict) -> None:
    try:
        _STORE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _norm(source: str) -> str:
    s = (source or "").strip()
    s = re.sub(r"\s*\(.*?\)", "", s)            # "Hacker News (traction)" -> "Hacker News"
    return s[:40] or "unknown"


def record(source: str, verdict: str) -> None:
    """Attribute one verdict to the source that delivered it."""
    v = (verdict or "").strip().upper()
    if v not in _HIT and v not in _MISS:
        return
    d = _load()
    e = d.setdefault(_norm(source), {"hits": 0, "misses": 0})
    if v in _HIT:
        e["hits"] += 1
    else:
        e["misses"] += 1
    e["ts"] = time.time()
    _save(d)


def weights() -> dict:
    """source -> reliability in [0,1] (Laplace-smoothed so tiny samples stay humble)."""
    return {name: round((e["hits"] + 1) / (e["hits"] + e["misses"] + 2), 3)
            for name, e in _load().items()}


def reliability_text() -> str:
    """One line for synthesis prompts: which eyes to trust."""
    w = weights()
    if not w:
        return ""
    ranked = sorted(w.items(), key=lambda kv: -kv[1])
    return "Source reliability (observed): " + ", ".join(
        f"{n} {v:.2f}" for n, v in ranked[:7])


def format_sources() -> str:
    d = _load()
    if not d:
        return "🔭 _No source track record yet._"
    w = weights()
    lines = ["🔭 *Source reliability* — how often each eye delivers a verdict"]
    for name, e in sorted(d.items(), key=lambda kv: -w[kv[0]]):
        n = e["hits"] + e["misses"]
        lines.append(f"• {name}: *{w[name]:.2f}* ({e['hits']}/{n} decisive)")
    return "\n".join(lines)
