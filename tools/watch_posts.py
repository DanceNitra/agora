#!/usr/bin/env python3
"""
watch_posts — track live distribution of our posts and report movement since last check.

Auto-discovers our Hacker News submissions (any story linking dancenitra.github.io) via the
HN Algolia API, plus repo stars via the GitHub API. Stores a small state file so each run prints
deltas (new points / new comments / new stars) and surfaces HN comments that may need a reply.

Reddit is intentionally NOT polled: Reddit 403-blocks server-side API calls, so Reddit numbers
must come from the owner. GitHub's traffic API counts the repo page, not the Pages blog post, so
it is not a reliable readership signal here — HN points/comments are the real signal.
"""
from __future__ import annotations

import gzip
import json
import re
import ssl
import urllib.request
from pathlib import Path

STATE = Path(__file__).resolve().parents[1] / "agora_output" / "distribution" / "_watch_state.json"
UA = {"User-Agent": "agora-metrics/1.0 (research)"}
# CrossValidated answers we've posted (answer_id -> short label) — tracked for score/comments/removal
CV_ANSWERS = {"676295": "Q422027 pre-trends / interaction terms"}
_SECTX = ssl.create_default_context()
_SECTX.check_hostname = False
_SECTX.verify_mode = ssl.CERT_NONE  # SE API cert isn't in the local trust store; read-only public data


def _get(url: str):
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=20).read().decode())


def _se(path: str):
    """Stack Exchange API (gzip, unverified TLS) — site=stats (CrossValidated)."""
    url = "https://api.stackexchange.com/2.3/" + path + "&site=stats&filter=withbody"
    req = urllib.request.Request(url, headers={**UA, "Accept-Encoding": "gzip"})
    raw = urllib.request.urlopen(req, timeout=20, context=_SECTX).read()
    try:
        raw = gzip.decompress(raw)
    except Exception:
        pass
    return json.loads(raw.decode())


def _clean(h: str) -> str:
    return re.sub("<[^>]+>", " ", h or "").strip()


def _load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    prev = _load()
    cur: dict = {"hn": {}, "stars": 0, "cv": {}}
    lines = []

    # --- Hacker News: every story pointing at our site ---
    try:
        hn = _get("http://hn.algolia.com/api/v1/search?query=dancenitra.github.io&tags=story&hitsPerPage=20")
        ours = [h for h in hn.get("hits", []) if "dancenitra.github.io" in (h.get("url") or "")]
        if not ours:
            lines.append("HN: no submissions indexed yet (Algolia lags ~10-30 min on fresh posts).")
        for h in ours:
            oid = h.get("objectID")
            pts, com = h.get("points", 0), h.get("num_comments", 0)
            cur["hn"][oid] = {"points": pts, "comments": com,
                              "title": (h.get("title") or "")[:60]}
            p = prev.get("hn", {}).get(oid, {})
            dp = pts - p.get("points", 0) if p else pts
            dc = com - p.get("comments", 0) if p else com
            tag = f"  (+{dp} pts, +{dc} comments)" if p else "  (NEW)"
            lines.append(f"HN [{pts} pts / {com} comments]{tag}  {cur['hn'][oid]['title']}")
            lines.append(f"    https://news.ycombinator.com/item?id={oid}")
    except Exception as e:
        lines.append(f"HN: lookup error {str(e)[:80]}")

    # --- GitHub stars (downstream conversion signal) ---
    try:
        g = _get("https://api.github.com/repos/DanceNitra/agora")
        cur["stars"] = g.get("stargazers_count", 0)
        ds = cur["stars"] - prev.get("stars", 0)
        lines.append(f"GitHub stars: {cur['stars']}" + (f"  (+{ds})" if prev and ds else ""))
    except Exception as e:
        lines.append(f"GitHub: lookup error {str(e)[:80]}")

    # --- CrossValidated answers we've posted (score / comments / removal) ---
    for aid, label in CV_ANSWERS.items():
        try:
            items = _se(f"answers/{aid}?order=desc&sort=activity").get("items", [])
            if not items:
                lines.append(f"CV {label}: answer {aid} NOT FOUND (deleted/removed?)")
                cur["cv"][aid] = {"score": None, "comments": 0}
                continue
            a = items[0]
            score = a.get("score", 0)
            cm = _se(f"answers/{aid}/comments?order=asc&sort=creation&pagesize=20").get("items", [])
            p = prev.get("cv", {}).get(aid, {})
            ds = score - p.get("score", 0) if p else score
            n_new = len(cm) - p.get("comments", 0) if p else len(cm)
            cur["cv"][aid] = {"score": score, "comments": len(cm)}
            tag = f"  (score {ds:+d}, +{n_new} new comments)" if p else "  (baseline)"
            lines.append(f"CV [{score} score / {len(cm)} comments]{tag}  {label}")
            lines.append(f"    https://stats.stackexchange.com/a/{aid}")
            for c in cm[-3:] if n_new else []:
                lines.append(f"    NEW comment: {_clean(c.get('body'))[:160]}")
        except Exception as e:
            lines.append(f"CV {label}: lookup error {str(e)[:80]}")

    _save(cur)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
