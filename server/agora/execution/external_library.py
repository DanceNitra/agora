"""The EXTERNAL LIBRARY — everything the outside world says about our problem, kept and searchable.

The system's whole intake was its own vault plus arXiv: what we already thought, and what academics
publish. Neither surfaces the issue somebody filed yesterday asking for exactly what we built, or the
Reddit thread where three people compare the libraries we compete with.

So: harvest GitHub and Reddit continuously against a rotating query bank, keep everything (deduped) in
a mnemo store, and expose search over it. Items accumulate — the point is not a report that scrolls
past, it is a corpus that gets deeper the longer it runs and that we can interrogate later
("who has asked for erasure?", "what did people say about mem0 in June?").

Stored in mnemo on purpose: it is our own product doing the job it exists for, it deduplicates by key,
and a re-harvest of the same thread supersedes rather than duplicates.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

_STORE_PATH = Path(__file__).resolve().parents[2] / ".external_library.jsonl"
_STATE = Path(__file__).resolve().parents[2] / ".external_library_state.json"

# The query bank. Rotated a few per cycle so a night of harvesting sweeps the whole space without
# burning rate limits. Written as things a PERSON would ask, because that is what lands in issues.
GH_QUERIES = [
    "agent memory correction is:issue", "agent memory forget is:issue",
    "memory poisoning agent is:issue", "conversational memory stale is:issue",
    "mem0 alternative is:issue", "vector store delete user data gdpr is:issue",
    "langgraph store memory is:issue", "llm memory dedupe is:issue",
    "agent memory benchmark is:issue", "rag memory update outdated is:issue",
    "memory provenance trust is:issue", "right to be forgotten embeddings is:issue",
    "agent memory revert undo is:issue", "long term memory agent framework is:issue",
    "memory layer mcp server is:issue", "semantic memory contradiction is:issue",
]
GH_PR_QUERIES = [
    "agent memory is:pr is:merged", "memory store langchain is:pr is:merged",
    "mem0 integration is:pr", "memory backend is:pr is:open",
    "checkpointer store is:pr is:merged",
]
REDDIT = [
    ("LocalLLaMA", "agent memory"), ("LocalLLaMA", "mem0"), ("LocalLLaMA", "long term memory"),
    ("RAG", "memory"), ("RAG", "mem0 zep"), ("RAG", "chunking"),
    ("LangChain", "memory store"), ("AI_Agents", "memory"),
    ("MachineLearning", "agent memory"), ("ClaudeAI", "memory mcp"),
]


def _mnemo():
    from mnemo import Mnemo
    m = Mnemo(path=str(_STORE_PATH))
    m.echo_guard = True
    return m


def _state() -> dict:
    try:
        return json.loads(_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"cursor": 0, "harvested": 0}


def _save_state(s: dict) -> None:
    try:
        _STATE.write_text(json.dumps(s), encoding="utf-8")
    except Exception:
        pass


def _gh(path: str) -> dict:
    # encoding is explicit: `text=True` decodes with the locale codec, which on this box is cp1250 and
    # dies on the first non-Latin character in an issue body — silently costing whole queries.
    try:
        out = subprocess.run(["gh", "api", path], capture_output=True, timeout=45,
                             encoding="utf-8", errors="replace")
        return json.loads(out.stdout) if out.returncode == 0 and out.stdout else {}
    except Exception:
        return {}


def _reddit(sub: str, query: str, limit: int = 15) -> list:
    """Read-only, through the OAuth token the distribution radar already holds.

    The anonymous www.reddit.com/*.json route now answers 403 Blocked, so the token is not optional.
    Read-only by construction: this module has no write path and never posts — the owner posts.
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
        import distribution_radar as R
        tok = R._reddit_token()
        if not tok:
            return []
        url = (f"https://oauth.reddit.com/r/{sub}/search?q={urllib.parse.quote(query)}"
               f"&restrict_sr=1&sort=new&limit={limit}&t=year")
        req = urllib.request.Request(url, headers={"User-Agent": "agora-external-library/1.0",
                                                   "Authorization": "bearer " + tok})
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read())
        return [c["data"] for c in d.get("data", {}).get("children", [])]
    except Exception:
        return []


def _store(m, *, key: str, text: str, meta: dict) -> bool:
    """One item. Returns True if it was new to the library."""
    if any((r.get("meta") or {}).get("url") == meta.get("url") for r in m.items):
        return False
    m.remember(text[:4000], key=key, meta=meta, tags=[meta.get("source", "web"), meta.get("kind", "")])
    return True


def harvest(batch: int = 6) -> dict:
    """Run one rotating slice of the query bank. Designed to be called on a loop, not once."""
    st = _state()
    cur = int(st.get("cursor", 0))
    m = _mnemo()
    added = {"gh_issues": 0, "gh_prs": 0, "reddit": 0}
    touched = []

    for i in range(batch):
        idx = (cur + i) % (len(GH_QUERIES) + len(GH_PR_QUERIES) + len(REDDIT))
        if idx < len(GH_QUERIES):
            q = GH_QUERIES[idx]
            touched.append(q)
            res = _gh(f"search/issues?q={urllib.parse.quote(q)}&sort=updated&per_page=12")
            for it in res.get("items", []):
                url = it.get("html_url", "")
                repo = re.sub(r"https://github\.com/([^/]+/[^/]+)/.*", r"\1", url)
                if repo.lower().startswith("dancenitra/"):
                    continue
                txt = (f"[github issue] {repo}: {it.get('title','')}\n"
                       f"{(it.get('body') or '')[:1500]}")
                if _store(m, key=f"gh::{url}", text=txt,
                          meta={"url": url, "source": "github", "kind": "issue", "repo": repo,
                                "title": it.get("title", "")[:200], "comments": it.get("comments", 0),
                                "updated": (it.get("updated_at") or "")[:10], "query": q}):
                    added["gh_issues"] += 1
        elif idx < len(GH_QUERIES) + len(GH_PR_QUERIES):
            q = GH_PR_QUERIES[idx - len(GH_QUERIES)]
            touched.append(q)
            res = _gh(f"search/issues?q={urllib.parse.quote(q)}&sort=updated&per_page=10")
            for it in res.get("items", []):
                url = it.get("html_url", "")
                repo = re.sub(r"https://github\.com/([^/]+/[^/]+)/.*", r"\1", url)
                if repo.lower().startswith("dancenitra/"):
                    continue
                txt = f"[github pr] {repo}: {it.get('title','')}\n{(it.get('body') or '')[:1500]}"
                if _store(m, key=f"gh::{url}", text=txt,
                          meta={"url": url, "source": "github", "kind": "pr", "repo": repo,
                                "title": it.get("title", "")[:200], "comments": it.get("comments", 0),
                                "updated": (it.get("updated_at") or "")[:10], "query": q}):
                    added["gh_prs"] += 1
        else:
            sub, q = REDDIT[idx - len(GH_QUERIES) - len(GH_PR_QUERIES)]
            touched.append(f"r/{sub}:{q}")
            for p in _reddit(sub, q):
                url = "https://reddit.com" + (p.get("permalink") or "")
                txt = (f"[reddit r/{sub}] {p.get('title','')}\n{(p.get('selftext') or '')[:1500]}")
                if _store(m, key=f"rd::{url}", text=txt,
                          meta={"url": url, "source": "reddit", "kind": "thread", "repo": f"r/{sub}",
                                "title": (p.get("title") or "")[:200],
                                "comments": p.get("num_comments", 0),
                                "score": p.get("score", 0),
                                "updated": time.strftime("%Y-%m-%d",
                                                         time.gmtime(p.get("created_utc") or 0)),
                                "query": q}):
                    added["reddit"] += 1
        time.sleep(1.2)                                  # be a polite citizen of both APIs

    m.flush() if hasattr(m, "flush") else m._save(force=True)
    st["cursor"] = cur + batch
    st["harvested"] = int(st.get("harvested", 0)) + sum(added.values())
    _save_state(st)
    return {"added": added, "new_total": sum(added.values()), "queries": touched,
            "library_size": len(m.items), "cursor": st["cursor"]}


def search(q: str, k: int = 12) -> list:
    """Dig into what has accumulated. This is the point of keeping it rather than reporting it."""
    m = _mnemo()
    out = []
    for h in (m.recall(q, k=k, mode="lexical", reinforce=False) or []):
        meta = h.get("meta") or {}
        out.append({"title": meta.get("title", "")[:160], "url": meta.get("url", ""),
                    "source": meta.get("source", ""), "kind": meta.get("kind", ""),
                    "repo": meta.get("repo", ""), "comments": meta.get("comments", 0),
                    "updated": meta.get("updated", ""), "excerpt": (h.get("text") or "")[:280]})
    return out


def stats() -> dict:
    m = _mnemo()
    by = {}
    repos = {}
    for r in m.items:
        meta = r.get("meta") or {}
        key = f"{meta.get('source','?')}/{meta.get('kind','?')}"
        by[key] = by.get(key, 0) + 1
        if meta.get("repo"):
            repos[meta["repo"]] = repos.get(meta["repo"], 0) + 1
    st = _state()
    return {"items": len(m.items), "by_kind": by, "harvest_cursor": st.get("cursor", 0),
            "top_repos": sorted(repos.items(), key=lambda kv: -kv[1])[:12]}


# --------------------------------------------------------------------------------------------
# THE CARTOGRAPHER'S NEW MAP
#
# Wren used to look for the two vault domains with the fewest bridges between them. In a vault holding
# physics, ADHD and category theory that objective function guarantees an off-mission answer: the
# widest hole is always between two things that have nothing to do with agent memory.
#
# Same instinct, honest map: chart the OUTSIDE world instead. Who is asking for what, which needs
# recur across unrelated projects, and which of them nobody has built. A hole in that map is a market
# gap; a hole in the vault map was just a gap in our reading.
AXIS = {
    "correction/update": ("correct", "update", "stale", "outdated", "supersede", "overwrite"),
    "forget/erasure": ("forget", "delete", "erasure", "gdpr", "right to be forgotten", "purge", "wipe"),
    "revert/undo": ("revert", "undo", "rollback", "restore previous"),
    "provenance/trust": ("provenance", "trust", "source", "attribution", "verify", "audit"),
    "poisoning/safety": ("poison", "injection", "malicious", "adversarial", "tamper"),
    "determinism/cost": ("deterministic", "non-deterministic", "llm cost", "expensive", "latency"),
    "dedup/conflict": ("duplicate", "dedupe", "conflict", "contradiction"),
    "retrieval quality": ("recall", "retrieval", "chunk", "rerank", "embedding", "hybrid"),
}


def map_external(min_repos: int = 2) -> dict:
    """Chart the external corpus: which needs recur, across whose projects, and where nobody answers.

    Returns buckets sorted by how many DISTINCT projects raise them — one loud repo is a customer,
    the same need in six unrelated repos is a market.
    """
    m = _mnemo()
    buckets: dict = {k: {"items": [], "repos": set()} for k in AXIS}
    for r in m.items:
        meta = r.get("meta") or {}
        blob = ((r.get("text") or "") + " " + str(meta.get("title") or "")).lower()
        for name, words in AXIS.items():
            if any(w in blob for w in words):
                buckets[name]["items"].append({"title": meta.get("title", "")[:120],
                                               "url": meta.get("url", ""),
                                               "repo": meta.get("repo", ""),
                                               "source": meta.get("source", ""),
                                               "comments": meta.get("comments", 0)})
                if meta.get("repo"):
                    buckets[name]["repos"].add(meta["repo"])

    out = []
    for name, b in buckets.items():
        out.append({"need": name, "mentions": len(b["items"]), "distinct_projects": len(b["repos"]),
                    "projects": sorted(b["repos"])[:12],
                    "loudest": sorted(b["items"], key=lambda x: -(x["comments"] or 0))[:5]})
    out.sort(key=lambda x: (-x["distinct_projects"], -x["mentions"]))

    connectable = [o for o in out if o["distinct_projects"] >= min_repos]
    silent = [o["need"] for o in out if o["mentions"] == 0]
    return {"library_items": len(m.items), "map": out,
            "recurring_needs": [o["need"] for o in connectable],
            "unseen_in_the_wild": silent,
            "note": ("A need raised in several unrelated projects is a market signal; a need we build "
                     "for that appears nowhere is either early or imaginary, and the map does not "
                     "distinguish those two — it only says nobody is asking yet.")}
