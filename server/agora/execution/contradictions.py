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


def _same_note(ma: dict, mb: dict) -> bool:
    """Are these two index entries the SAME note filed under two different dates?

    The agents re-write a note into a fresh `Agora Agents/YYYY-MM-DD/` folder every time they
    revisit it, so one title is worn by up to ten distinct files. Measured 2026-07-31 on the live
    index: 4,200 of 10,955 entries (38%) share a title with at least one sibling, and because a
    copy is a near-perfect neighbour of its original, the top-2 shortlist fills up with them --
    **59 of Dame Elara's 96 judgements in 24h were a note against its own copy** (a == b in the
    ledger). Asking the model whether a note contradicts itself costs a call, cannot return
    CONTRADICT, and then banks the guaranteed COMPATIBLE as a decisive coherence verdict. Her
    ledger read as the busiest in the keep while two thirds of it was tautology.

    Compared on the file's basename rather than the title alone, so a re-titled copy at the same
    path is caught too.
    """
    if (ma.get("title") or "\x00A") == (mb.get("title") or "\x00B"):
        return True
    pa, pb = str(ma.get("path") or "\x00A"), str(mb.get("path") or "\x00B")
    return pa.rsplit("/", 1)[-1].lower() == pb.rsplit("/", 1)[-1].lower()


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


#: Two notes whose bodies agree this closely are one note stored twice, whatever their filenames say.
#: Set at 0.90 token-overlap because that is where the measured population splits: on the 120 highest
#: -similarity candidates left after the title filter, 39 pairs were byte-identical or one contained
#: the other, 36 more sat above 0.90, and the remaining 45 were genuinely different documents.
_DUP_JACCARD = 0.90

#: How many candidate pairs a sweep may OPEN to find its `max_judged` real ones. The duplicate check
#: costs two file reads and no tokens, so it is cheap to skip past copies -- but not free, and an
#: unbounded scan over ~6,900 candidates would stall the organ if the tail were all copies.
_MAX_SCAN = 200


def _norm_body(text: str) -> str:
    return re.sub(r"\s+", " ", text.split("---", 2)[-1]).strip().lower()


def _is_duplicate_body(a: str, b: str) -> bool:
    """Is this pair the same document twice, judged on CONTENT rather than on its filename?

    The title check catches a note re-filed under a new date. It cannot catch the vault's other copy
    habit: the same note under an operational prefix (`backup_`, `pwback_`, `orphan_`, `r2_`,
    `bridge1_`, ...), which 754 files carry. Stripping such a prefix by pattern was the tempting fix
    and it is wrong -- it would also merge `python_decorators` with `rust_decorators`, two different
    notes that differ only by a leading token. The bodies are already read a line later for the
    judge, so the honest test is the one that reads them.

    Measured 2026-07-31 on the 120 top candidates that survived the title filter: 62% were copies
    (39 byte-identical or contained). Judging those asks the model whether a document contradicts
    itself; the answer cannot be CONTRADICT, and banking the guaranteed COMPATIBLE is what made this
    organ look like the busiest in the keep.
    """
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    ta, tb = set(a.split()), set(b.split())
    union = len(ta | tb)
    return bool(union) and len(ta & tb) / union >= _DUP_JACCARD


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
            if not (_is_artifact(meta[k[0]]) or _is_artifact(meta[k[1]]))
            and not _same_note(meta[k[0]], meta[k[1]])}
    known = _known_pairs()
    root = Path(vault_path)
    judged = found = scanned = dup_skipped = 0
    items = _load()
    for (a, b), s in sorted(cand.items(), key=lambda kv: -kv[1]):
        if judged >= max_judged or scanned >= _MAX_SCAN:
            break
        ta, tb = meta[a]["title"], meta[b]["title"]
        if tuple(sorted((ta, tb))) in known:
            continue
        try:
            sa = (root / meta[a]["path"]).read_text(encoding="utf-8", errors="replace")
            sb = (root / meta[b]["path"]).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        scanned += 1
        # Spend the read, not the tokens, on a copy. Skipped WITHOUT recording: a duplicate is a
        # fact about the vault's filing, not a coherence verdict, and banking it as "compatible"
        # is exactly the churn this organ was accused of.
        if _is_duplicate_body(_norm_body(sa), _norm_body(sb)):
            dup_skipped += 1
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
        # CARRY THE PATHS (2026-07-31). The record named the two notes by TITLE only, and a title in
        # this vault points at up to ten files. A verdict nobody can trace back to the exact two
        # documents it judged is not a checkable verdict -- and this ledger is the whole evidence
        # Elara produces. With the paths and the measured similarity, a reader can re-open both
        # notes and re-derive the judgement; that is the receipt a coherence organ can honestly
        # offer, in place of the lab id a computational organ would carry.
        rec = {"id": uuid.uuid4().hex[:6], "a": ta, "b": tb, "sim": round(s, 3),
               "path_a": meta[a].get("path", ""), "path_b": meta[b].get("path", ""),
               "contradict": bool(r), "claim": (r or {}).get("claim", ""),
               "by": OWNER,
               "status": "open" if r else "compatible", "ts": time.time()}
        items.append(rec)
        # And remember it NOW. `known` was read once before the loop and never updated, so when
        # several distinct index pairs mapped to one title pair the sweep judged that same pair
        # again and again -- measured 26 of 96 judgements in 24h were repeats, one title pair
        # judged five times inside a single window.
        known.add(tuple(sorted((ta, tb))))
        if r:
            found += 1
    _save(items[-300:])
    return {"status": "ok", "judged": judged, "found": found,
            "dup_skipped": dup_skipped, "scanned": scanned}


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
