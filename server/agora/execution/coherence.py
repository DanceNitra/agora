"""
The Coherence Audit — the belief set stays a system, not a pile.

The contradiction sweep guards the OWNER's notes; nothing guards whether AGORA contradicts
ITSELF. Each audit takes the newest unaudited belief (insight/hypothesis note), embeds its
core claim, finds its closest sibling beliefs, and has the light model judge incompatibility
(the same labeled-text judge the contradiction sweep uses). Real tensions auto-queue an
internal dialectic; audited pairs are remembered so the work never repeats. Convergence —
like the identification-premium spine — is then a measured fact, not an impression.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".coherence.json"


def _load() -> dict:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {"audited": [], "tensions": []}


def _save(d: dict) -> None:
    try:
        _STORE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _core_claim(path: str) -> str:
    """The belief's central section (Insight/Hypothesis heading), title as fallback."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    m = re.search(r"##\s*(?:The insight|Hypothesis)\s*\n(.+?)(?=\n##|\Z)", text,
                  re.DOTALL | re.IGNORECASE)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:800]
    t = re.search(r"^title:\s*(.+)$", text[:600], re.M)
    return (t.group(1).strip().strip('"') if t else Path(path).stem)[:200]


async def audit_once(vault_path: str) -> dict:
    """Audit ONE new belief against its closest siblings; queue dialectics for real tensions."""
    import asyncio
    import numpy as np
    from agora.execution.belief_revision import list_beliefs
    from agora.execution.semantic_index import _embed_batch
    from agora.execution.contradictions import _judge_pair, _is_duplicate_body, _norm_body

    d = _load()
    audited = set(d.get("audited", []))
    beliefs = [b for b in list_beliefs(vault_path)
               if b["belief_status"] in ("active", "survived")]
    target = next((b for b in reversed(beliefs) if b["title"] not in audited), None)
    if not target or len(beliefs) < 3:
        return {"status": "nothing_to_audit", "beliefs": len(beliefs)}

    others = [b for b in beliefs if b["title"] != target["title"]]
    claims = {b["title"]: _core_claim(b["path"]) for b in [target] + others}
    texts = [claims[target["title"]]] + [claims[o["title"]] for o in others]
    embs = await asyncio.to_thread(_embed_batch, texts)
    tensions_found = 0
    if embs and len(embs) == len(texts):
        v = np.array(embs, dtype=np.float32)
        v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
        sims = v[1:] @ v[0]
        order = np.argsort(-sims)[:3]
        for i in order:
            if float(sims[i]) < 0.5:
                continue
            other = others[int(i)]
            # Same guard as the vault sweep, for the same reason. This audit excludes a sibling by
            # TITLE, which misses the copy filed under a different one -- and a belief cannot be in
            # tension with itself, so the call can only come back COMPATIBLE. The core claims are
            # already extracted here, so the check costs nothing but the comparison.
            if _is_duplicate_body(_norm_body(claims[target["title"]]),
                                  _norm_body(claims[other["title"]])):
                continue
            r = await asyncio.to_thread(_judge_pair, target["title"], claims[target["title"]],
                                        other["title"], claims[other["title"]])
            if r:
                tensions_found += 1
                d.setdefault("tensions", []).append(
                    {"a": target["title"], "b": other["title"],
                     "claim": r["claim"], "status": "queued", "ts": time.time()})
                from agora.execution.claude_inbox import add_task
                add_task(f"Dialectic: {r['claim'][:130]} (internal coherence: "
                         f"{target['title'][:40]} vs {other['title'][:40]})")
    d["audited"] = (list(audited) + [target["title"]])[-200:]
    d["tensions"] = d.get("tensions", [])[-50:]
    _save(d)
    return {"status": "ok", "audited": target["title"], "compared": len(others),
            "tensions_found": tensions_found}


def format_coherence() -> str:
    d = _load()
    tensions = d.get("tensions", [])
    lines = [f"🧩 *Coherence* — {len(d.get('audited', []))} beliefs audited, "
             f"{len(tensions)} internal tensions found"]
    for t in tensions[-5:]:
        lines.append(f"⚡ {t['a'][:34]} ⇄ {t['b'][:34]}")
        if t.get("claim"):
            lines.append(f"   _{t['claim'][:80]}_")
    if not tensions:
        lines.append("_The belief set is mutually consistent so far._")
    return "\n".join(lines)
