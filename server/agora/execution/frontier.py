"""
The Frontier — push research toward the EDGE of the vault, not its dense centre.

Agents churn: they re-derive the same already-dense clusters because their seeds are static gaps
and recent (themselves-churned) findings. The dedup correctly rejects the duplicates, but the
fix is upstream — aim the agents at what is UNDER-explored. This reuses the Cartographer's vault
scan to surface a frontier target: a thin (barely-developed) knowledge domain to grow, or a
structural hole between two domains to bridge. A small ledger rotates targets so the frontier
itself doesn't churn. Novelty becomes the default direction of research.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".frontier.json"
_COOL = 6 * 3600          # don't re-seed the same frontier target within 6h


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


def _recent_targets(now: float) -> set:
    return {x["target"] for x in _load() if now - x.get("ts", 0) < _COOL}


def frontier_target(vault: str) -> dict | None:
    """An under-explored target: a THIN domain to develop or a structural HOLE to bridge.
    Alternates by the hour and skips targets seeded in the last 6h (so the frontier rotates)."""
    from agora.execution.cartography import _scan
    now = time.time()
    recent = _recent_targets(now)
    try:
        note_domain, domain_notes, bridges = _scan(vault)
    except Exception:
        return None

    real = {d: ns for d, ns in domain_notes.items() if d not in ("(unfiled)", "(root)")}
    if len(real) < 2:
        return None

    # alternate: even hours hunt a THIN domain, odd hours a structural HOLE
    if int(now // 3600) % 2 == 0:
        # thin = a real domain with the FEWEST notes (a barely-developed corner), not yet seeded
        thin = sorted(((len(ns), d) for d, ns in real.items() if 1 <= len(ns) <= 8),
                      key=lambda x: x[0])
        for cnt, d in thin:
            if d not in recent:
                return {"kind": "thin_domain", "target": d, "size": cnt,
                        "prompt": f"The '{d}' area of the vault is thin ({cnt} notes) — develop it "
                                  f"with a NEW, specific finding that deepens it, not a restatement."}
    # the widest structural hole between two substantial domains with no bridge
    big = {d: len(ns) for d, ns in real.items() if len(ns) >= 8}
    doms = sorted(big)
    holes = []
    for i, a in enumerate(doms):
        for b in doms[i + 1:]:
            nb = bridges.get(tuple(sorted((a, b))), 0)
            if nb == 0:
                holes.append((big[a] + big[b], a, b))
    holes.sort(reverse=True)
    for _sz, a, b in holes:
        key = f"{a} <-> {b}"
        if key not in recent:
            return {"kind": "hole", "target": key, "a": a, "b": b,
                    "prompt": f"'{a}' and '{b}' are both substantial vault domains with NO link "
                              f"between them — produce a finding that genuinely bridges them via a "
                              f"shared mechanism (not surface similarity)."}
    return None


def record_seeded(target: str, kind: str = "") -> None:
    items = _load()
    items.append({"target": (target or "")[:120], "kind": kind[:20], "ts": time.time()})
    _save(items[-80:])


def format_frontier() -> str:
    items = _load()
    if not items:
        return "🧭 _No frontier target seeded yet._"
    lines = [f"🧭 *The Frontier* — {len(items)} edge-targets seeded"]
    for x in items[-6:][::-1]:
        lines.append(f"• [{x.get('kind','?')}] {x['target'][:60]}")
    return "\n".join(lines)
