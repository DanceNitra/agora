"""Where can we actually HELP — the contribution shortlist, mined from the external library.

The library collects everything the outside world says about our problem. This is the filter that
turns it into a work queue: which of those threads is a place where inspeximus/Agora has something real to
offer, ranked so the best one is obvious at 3am.

Deliberately conservative about "we can help". A thread scores only when the need it voices maps onto
something we have SHIPPED and can point at — supersession, revert, receipted erasure, the
determinism/no-LLM-write property, the poison work, or a measured benchmark. Wanting to be relevant is
not the same as being relevant, and a bad pitch in a busy thread costs more than silence.
"""
from __future__ import annotations

import re
import time

# what we can actually put on the table, and the words that signal someone needs it
OFFERS = {
    "supersession / corrections that stick": (
        ("stale", "outdated", "old value", "overwrite", "update memory", "conflicting", "contradict",
         "wrong fact", "keeps remembering"),
        "keyed supersession + echo_guard, deterministic, no model call on the write path"),
    "receipted erasure / GDPR delete": (
        ("gdpr", "right to be forgotten", "delete user", "erase", "purge", "hard delete", "wipe",
         "data retention", "forget everything"),
        "forget_subject() erases through derived_from lineage and emits a hash-chained, content-free "
        "receipt; audited by governance_audit.py across 3 scenarios x 3 repeats"),
    "revert to predecessor": (
        ("revert", "undo", "rollback", "restore previous", "go back to"),
        "revert(key) restores the superseded value without the caller knowing it"),
    "no LLM on the write path / cost": (
        ("expensive", "cost", "token usage", "latency", "slow ingest", "rate limit", "extraction cost",
         "non-deterministic", "nondeterministic", "inconsistent results"),
        "zero model calls at write; measured 519-917s of extraction per scenario for an LLM-on-write "
        "pipeline against none, with answer accuracy statistically indistinguishable"),
    "memory poisoning / trust": (
        ("poison", "injection", "malicious", "untrusted", "provenance", "trust level", "attribution",
         "tamper"),
        "attestation + trusted_only (fails closed), echo_guard, and the honest scope: a provenance "
        "gate is authorization, NOT truth — trust_is_not_truth.py demonstrates it"),
    "measurement / benchmark": (
        ("benchmark", "evaluate", "how do i measure", "comparison", "which memory", "vs mem0",
         "locomo", "recall@"),
        "published pre-registered harness with the null included (benchmarks/memops), plus RAMR"),
    "drop-in store for a framework": (
        ("langgraph", "basestore", "checkpointer", "llamaindex", "crewai", "autogen", "mcp server",
         "memory backend", "swap"),
        "InspeximusStore passes an operation-by-operation parity audit against LangGraph's own InMemoryStore; "
        "CrewAI adapter and an MCP server ship in the package"),
}

_NOISE_REPOS = ("revvel-standards", "awesome-", "-notes", "learning-", "tutorial")


# The thread has to be ABOUT memory before any offer of ours is relevant. Without this the keyword
# match alone dragged in a ternary-model benchmark and a crypto wallet, because both say "state" and
# "verify" — the same too-loose matching that let churn through the task gate an hour earlier.
_SUBJECT = ("memory", "memories", "remember", "recall", "retrieval", "rag", "context window",
            "embedding", "vector store", "knowledge base", "mem0", "zep", "letta", "cognee",
            "langmem", "checkpointer", "basestore", "conversation history", "long-term", "long term")


def _is_about_memory(blob: str) -> bool:
    return any(s in blob for s in _SUBJECT)


def _score(item: dict, offers: list) -> int:
    s = 0
    s += 4 * len(offers)                                  # how many of our offers the thread needs
    s += min(int(item.get("comments") or 0), 10)          # a live conversation beats a dead one
    if item.get("kind") == "issue":
        s += 3                                            # an open question invites an answer
    if item.get("source") == "reddit":
        s += 2                                            # public, and the owner can answer as himself
    try:
        age_d = (time.time() - time.mktime(time.strptime(item.get("updated", "")[:10], "%Y-%m-%d"))) / 86400
        s += 5 if age_d <= 14 else 2 if age_d <= 45 else -3
    except Exception:
        pass
    if any(n in (item.get("repo") or "").lower() for n in _NOISE_REPOS):
        s -= 8
    return s


def find(limit: int = 25) -> dict:
    from agora.execution.external_library import _inspeximus
    m = _inspeximus()
    out = []
    for r in m.items:
        meta = r.get("meta") or {}
        blob = ((r.get("text") or "") + " " + str(meta.get("title") or "")).lower()
        if not _is_about_memory(blob):
            continue
        offers = [name for name, (words, _) in OFFERS.items() if any(w in blob for w in words)]
        if not offers:
            continue
        item = {"title": (meta.get("title") or "")[:140], "url": meta.get("url", ""),
                "repo": meta.get("repo", ""), "kind": meta.get("kind", ""),
                "source": meta.get("source", ""), "comments": meta.get("comments", 0),
                "updated": meta.get("updated", ""), "offers": offers,
                "what_we_bring": [OFFERS[o][1] for o in offers][:2],
                "excerpt": re.sub(r"\s+", " ", (r.get("text") or ""))[:220]}
        item["score"] = _score(item, offers)
        out.append(item)
    out.sort(key=lambda x: -x["score"])
    by_offer: dict = {}
    for it in out:
        for o in it["offers"]:
            by_offer[o] = by_offer.get(o, 0) + 1
    return {"candidates": out[:limit], "total_matching": len(out), "library_scanned": len(m.items),
            "demand_by_offer": dict(sorted(by_offer.items(), key=lambda kv: -kv[1]))}
