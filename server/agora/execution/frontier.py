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
import os
import re
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".frontier.json"
_COOL = 6 * 3600          # don't re-seed the same frontier target within 6h


def _json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    try:
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}


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


def _candidate_pool(vault: str):
    """Gather a DIVERSE pool of raw research directions for the intelligent selector to rank:
    thin domains (underdeveloped corners) + structural holes (unbridged domain pairs)."""
    from agora.execution.cartography import _scan
    note_domain, domain_notes, bridges = _scan(vault)
    real = {d: len(ns) for d, ns in domain_notes.items() if d not in ("(unfiled)", "(root)")}
    thin = sorted([(c, d) for d, c in real.items() if 1 <= c <= 8])[:8]
    big = {d: c for d, c in real.items() if c >= 8}
    doms = sorted(big)
    holes = []
    for i, a in enumerate(doms):
        for b in doms[i + 1:]:
            if bridges.get(tuple(sorted((a, b))), 0) == 0:
                holes.append((big[a] + big[b], a, b))
    holes.sort(reverse=True)
    return thin, holes[:8], len(real)


def _smart_frontier(vault: str, explore: bool) -> dict | None:
    """INTELLIGENT target selection (owner 2026-07-16): a reasoning-tier CRO picks the SINGLE next research
    direction that moves the whole org forward the most — scoring impact / novelty / buildability /
    compounding / alignment over a diverse candidate pool, COMPOUNDING on our moat (agent memory, mnemo,
    the Crucible) by default, with a ~30% bold broad-frontier exploration slice. Replaces the hourly
    thin/hole rotation. Reversible: AGORA_SMART_FRONTIER=0 falls back to _rotation_target."""
    from agora.execution.llm_client import call_llm
    thin, holes, ndoms = _candidate_pool(vault)
    if ndoms < 2:
        return None
    recent = _recent_targets(time.time())
    pool = ("THIN vault domains (underdeveloped):\n"
            + ("\n".join(f"- {d} ({c} notes)" for c, d in thin) or "- (none)")
            + "\n\nSTRUCTURAL HOLES (substantial domains with no bridge):\n"
            + ("\n".join(f"- {a} <-> {b}" for _s, a, b in holes) or "- (none)"))
    recent_txt = "; ".join(list(recent)[:12]) or "(none)"
    mode = ("EXPLORE MODE: pick a BOLD broad-frontier bet — a high-novelty, high-impact question that "
            "could open a whole new field for us, even if it is not yet on our edge."
            if explore else
            "COMPOUND MODE: pick the direction that most COMPOUNDS our moat (agent memory + the mnemo "
            "library + the Crucible replication ledger + memory/reasoning integrity) — one that builds on "
            "what we already lead and makes that lead harder to catch.")
    sys = (
        "You are the Chief Research Officer of Agora, an autonomous research organization. Our MOAT is "
        "agent memory, the mnemo open-source memory library, and the Crucible replication ledger; our "
        "frontier is the Science of Better Thinking and the Future of Work & Society. Choose the SINGLE "
        "best NEXT research direction to move the whole organization forward the most — think exponential "
        "leverage, not one isolated fact. Judge candidates on IMPACT (would answering it matter 10x?), "
        "NOVELTY (genuinely open, not a textbook/named-law re-derivation), BUILDABILITY (settleable with a "
        "small computational model or real data + a falsifier), COMPOUNDING (builds on our moat, opens more "
        "doors, creates leverage), and ALIGNMENT. " + mode + " Do NOT pick anything close to these "
        f"recently-seeded targets: {recent_txt}. You may pick from the vault candidates below, or propose a "
        "SHARPER direction they inspire. Reply ONLY JSON: {\"target\":\"<short name>\",\"kind\":\""
        "<thin_domain|hole|moat|frontier>\",\"prompt\":\"<one sharp directive: exactly what a researcher "
        "should produce, with a measurable result + falsifier>\",\"why\":\"<one line: why this moves us "
        "the most>\"}.")
    raw = call_llm(sys, pool, "medium", 0.6, 1500)
    d = _json(raw)
    tgt = str(d.get("target", "")).strip()
    if not tgt:
        return None
    return {"kind": str(d.get("kind", "frontier"))[:20], "target": tgt[:120],
            "prompt": str(d.get("prompt", ""))[:1000], "why": str(d.get("why", ""))[:300]}


def frontier_target(vault: str) -> dict | None:
    """Intelligent CRO selection (default) with the hourly thin/hole rotation as fallback."""
    if os.getenv("AGORA_SMART_FRONTIER", "1") != "0":
        try:
            explore = int(time.time()) % 10 < 3          # ~30% bold-exploration slice
            r = _smart_frontier(vault, explore)
            if r:
                return r
        except Exception as e:
            print(f"[frontier] smart-select failed, falling back to rotation: {e}")
    return _rotation_target(vault)


def _rotation_target(vault: str) -> dict | None:
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
