"""
The Contradiction Sweep — the vault finds its own disagreements.

Bridges connect islands; nothing yet looks for places where the library claims A and ¬A.
The owner's own insight says knowledge debt is measurable as non-confluence — contradictory
reasoning paths. This sweep shortlists semantically close note pairs (the embeddings are
already there), has the light model judge INCOMPATIBILITY (a cheap labeled-text call per
pair), stores real contradictions, and feeds each into the existing dialectic pipeline so it
gets resolved — thesis, antithesis, synthesis — instead of festering.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".contradictions.json"

#: The agent this organ belongs to. Declared here and asserted against repair_ledger._ORGANS in
#: tests, so the ledger and the organ map cannot drift into naming different owners.
OWNER = "Dame Elara"


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


#: Notes the SYSTEM generated about its own contents. A contradiction between two of these is a
#: contradiction between two retellings of the same material, not between two beliefs — and judging one
#: costs an LLM call and produces an inbox task nobody can act on. Measured 2026-07-29: the only open
#: contradiction Dame Elara held was `vault-digest-2026-06-20-1821` against another vault-digest. Her
#: organ was running, spending tokens, and finding disagreements inside our own summaries.
_ARTIFACT_MARKERS = ("vault-digest", "autolinker", "vault digest", "daily-digest",
                     "agora-agents-index", "seminar-report", "weekly-retrospective")


def _is_artifact(m: dict) -> bool:
    blob = f"{m.get('title', '')} {m.get('path', '')}".lower().replace("_", "-")
    return any(k in blob for k in _ARTIFACT_MARKERS)


def _known_pairs() -> set[tuple]:
    return {tuple(sorted((c["a"], c["b"]))) for c in _load()}


def _judge_pair(a_title: str, a_snip: str, b_title: str, b_snip: str) -> dict | None:
    """One cheap labeled-text call: do these notes make INCOMPATIBLE claims?"""
    from agora.execution.llm_client import call_llm
    raw = call_llm(
        "Two notes from one knowledge vault. Decide if they make INCOMPATIBLE claims — both "
        "cannot be true as stated (genuine contradiction, not just different topics or "
        "emphasis). Reply EXACTLY:\nVERDICT: CONTRADICT or COMPATIBLE\nCLAIM: <if CONTRADICT, "
        "the disputed claim as ONE neutral sentence>",
        f"NOTE A ({a_title}):\n{a_snip[:700]}\n\nNOTE B ({b_title}):\n{b_snip[:700]}",
        "cheap", 0.2, 200) or ""
    if not re.search(r"VERDICT:\s*CONTRADICT", raw, re.I):
        return None
    m = re.search(r"CLAIM:\s*(.+)", raw, re.I | re.DOTALL)
    claim = re.sub(r"\s+", " ", m.group(1)).strip()[:200] if m else ""
    return {"claim": claim} if len(claim) > 20 else {"claim": f"{a_title} vs {b_title}"}


async def sweep(vault_path: str, max_judged: int = 8) -> dict:
    """Shortlist close pairs, judge them sequentially (flash rate-limits on concurrency),
    store the genuine contradictions."""
    from agora.execution.semantic_index import SemanticIndex
    import numpy as np

    si = SemanticIndex()
    if not si.ready:
        return {"status": "no_index", "judged": 0, "found": 0}
    v, meta = si.vecs, si.meta
    sims = v @ v.T
    np.fill_diagonal(sims, -1.0)
    top2 = np.argpartition(-sims, 2, axis=1)[:, :2]
    cand = {}
    for i in range(len(meta)):
        for j in top2[i]:
            j = int(j)
            s = float(sims[i, j])
            if 0.78 < s < 0.97 and si._is_knowledge(meta[i]) and si._is_knowledge(meta[j]):
                cand[(min(i, j), max(i, j))] = s
    cand = {k: s for k, s in cand.items()
            if not (_is_artifact(meta[k[0]]) or _is_artifact(meta[k[1]]))}
    known = _known_pairs()
    root = Path(vault_path)
    judged = found = 0
    items = _load()
    for (a, b), s in sorted(cand.items(), key=lambda kv: -kv[1]):
        if judged >= max_judged:
            break
        ta, tb = meta[a]["title"], meta[b]["title"]
        if tuple(sorted((ta, tb))) in known:
            continue
        try:
            sa = (root / meta[a]["path"]).read_text(encoding="utf-8", errors="replace")
            sb = (root / meta[b]["path"]).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        judged += 1
        r = await asyncio.to_thread(_judge_pair, ta, sa.split("---", 2)[-1], tb, sb.split("---", 2)[-1])
        # NAME THE AGENT WHO DID THE WORK (2026-07-31). This ledger recorded a, b, sim, contradict,
        # claim, status and ts -- everything except WHO. Dame Elara owns the coherence organ and this
        # is its ledger (repair_ledger._ORGANS), so every record here is hers, but nothing said so.
        # Measured consequence: the swarm acceptance gate scored her 94 decisive outcomes in 24h as
        # "no named actor" and FAILED her, while an earlier vault-side count reported her as idle.
        # She was the busiest agent in the keep and invisible, for the same reason Rooke and Wren were
        # invisible: attribution, not absence. An organ that closes work anonymously cannot be credited,
        # and an agent that cannot be credited reads as one that does nothing.
        rec = {"id": uuid.uuid4().hex[:6], "a": ta, "b": tb, "sim": round(s, 3),
               "contradict": bool(r), "claim": (r or {}).get("claim", ""),
               "by": OWNER,
               "status": "open" if r else "compatible", "ts": time.time()}
        items.append(rec)
        if r:
            found += 1
    _save(items[-300:])
    return {"status": "ok", "judged": judged, "found": found}


def open_contradictions(n: int = 5) -> list:
    return [c for c in _load() if c.get("status") == "open"][:n]


def set_status(cid: str, status: str) -> None:
    items = _load()
    for c in items:
        if c.get("id") == cid:
            c["status"] = status
    _save(items)


def format_contradictions(n: int = 8) -> str:
    items = [c for c in _load() if c.get("contradict")][-n:]
    if not items:
        return "⚡ _No contradictions found in the vault (yet)._"
    icon = {"open": "⚡", "queued": "⏳", "resolved": "✅"}
    lines = ["⚡ *Vault contradictions* — places where your library disagrees with itself"]
    for c in items:
        lines.append(f"{icon.get(c['status'], '•')} {c['a'][:34]} ⇄ {c['b'][:34]}")
        if c.get("claim"):
            lines.append(f"   _{c['claim'][:90]}_")
    return "\n".join(lines)
