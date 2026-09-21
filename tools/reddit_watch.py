#!/usr/bin/env python3
"""Read-only Reddit watch for u/Danculus (app-only OAuth, never posts).

  python tools/reddit_watch.py threads            # every submission: walk the full reply tree,
                                                  # report the comments whose last word is not ours
  python tools/reddit_watch.py sub LocalLLaMA     # recent threads in a subreddit, ranked for a
                                                  # comment we could add (keyword overlap with our work)

The tree walk matters: our replies are nested children, and a flat top-level listing reports an
unanswered thread that we answered a level down.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
UA = "agora-research-radar/0.3 (by u/Danculus)"
US = "Danculus"
OUR_TOPICS = ["memory", "rag", "retrieval", "delete", "erasure", "gdpr", "vector", "embedding", "bm25",
              "hallucinat", "poison", "provenance", "agent", "benchmark", "eval", "context", "forget",
              "supersede", "chroma", "qdrant", "faiss", "sqlite", "locomo", "mem0", "letta", "zep"]


def token() -> str:
    env = dict(l.strip().split("=", 1) for l in open(ROOT / "server" / ".env", encoding="utf-8")
               if "=" in l and not l.startswith("#"))
    r = requests.post("https://www.reddit.com/api/v1/access_token",
                      auth=(env["AGORA_REDDIT_CLIENT_ID"], env["AGORA_REDDIT_CLIENT_SECRET"]),
                      data={"grant_type": "client_credentials"}, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def get(path: str, tok: str, **params):
    r = requests.get("https://oauth.reddit.com" + path, params=params,
                     headers={"Authorization": "bearer " + tok, "User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.json()


def walk(children, depth=0):
    """Yield (depth, comment data) for every t1 node, recursively."""
    for c in children:
        if c.get("kind") != "t1":
            continue
        d = c["data"]
        yield depth, d
        rep = d.get("replies")
        if isinstance(rep, dict):
            yield from walk(rep["data"]["children"], depth + 1)


def when(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, dt.UTC).strftime("%m-%d %H:%M")


def cmd_threads(tok: str, max_age_days: int) -> int:
    """Report comments addressed to us with no reply from us below them, at most max_age_days old.
    Older silences were deliberate (June and July 2026 jabs), so a daily brief must not resurface them."""
    subs = get(f"/user/{US}/submitted", tok, limit=100)["data"]["children"]
    open_items = 0
    for s in subs:
        d = s["data"]
        tree = get(f"/comments/{d['id']}", tok, limit=500, depth=10)[1]["data"]["children"]
        nodes = list(walk(tree))
        # a thread branch is answered when its deepest-latest node is ours, or when the last node
        # is another person's reply to someone who is not us
        waiting = []
        for depth, c in nodes:
            if c.get("author") == US:
                continue
            rep = c.get("replies")
            kids = rep["data"]["children"] if isinstance(rep, dict) else []
            ours_below = any(k.get("kind") == "t1" and k["data"].get("author") == US for k in kids)
            parent_is_us = c.get("parent_id", "").startswith("t3_") or any(
                p.get("name") == c.get("parent_id") and p.get("author") == US for _, p in nodes)
            fresh = (time.time() - c["created_utc"]) / 86400 <= max_age_days
            if not ours_below and parent_is_us and fresh and c.get("author") != "AutoModerator":
                waiting.append((depth, c))
        print(f"r/{d['subreddit']:12s} {d['score']:3d}pts {len(nodes):3d}c  {d['title'][:70]}")
        for depth, c in waiting:
            open_items += 1
            print(f"    WAITING {when(c['created_utc'])} u/{c['author']} (depth {depth}): "
                  f"{c['body'][:160].replace(chr(10), ' ')}")
        time.sleep(0.7)
    print(f"\n{open_items} comment(s) addressed to us without a reply from us (last {max_age_days} days)")
    return 0


def cmd_sub(tok: str, sub: str, limit: int) -> int:
    seen = {}
    for listing in ("new", "hot"):
        for c in get(f"/r/{sub}/{listing}", tok, limit=limit)["data"]["children"]:
            d = c["data"]
            seen[d["id"]] = d
    rows = []
    for d in seen.values():
        text = (d["title"] + " " + (d.get("selftext") or "")).lower()
        hits = sorted({k for k in OUR_TOPICS if k in text})
        age_h = (time.time() - d["created_utc"]) / 3600
        if not hits or age_h > 72:
            continue
        rows.append((len(hits) * 3 + d["num_comments"] * 0.2 + d["score"] * 0.1, age_h, d, hits))
    rows.sort(key=lambda r: -r[0])
    for score, age_h, d, hits in rows[:15]:
        print(f"{score:5.1f} {age_h:4.0f}h {d['score']:4d}pts {d['num_comments']:3d}c  {d['title'][:80]}")
        print(f"      https://www.reddit.com{d['permalink']}  [{', '.join(hits)}]")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("threads")
    t.add_argument("--days", type=int, default=14)
    p = sp.add_parser("sub")
    p.add_argument("name")
    p.add_argument("--limit", type=int, default=100)
    a = ap.parse_args()
    tok = token()
    if a.cmd == "threads":
        return cmd_threads(tok, a.days)
    return cmd_sub(tok, a.name, a.limit)


if __name__ == "__main__":
    sys.exit(main())
