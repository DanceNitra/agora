"""
The Distribution Desk — credibility is the moat, distribution is the bottleneck.

We publish a lot (19+ posts, FAILED replications) but almost no one sees it: 0 stars,
~5 unique human readers in 14 days. This organ matches our strongest public output to
the venues where the relevant audience already gathers (Hacker News, topic subreddits,
X), scores shareability, and supplies Claude the raw material to draft a venue-tailored
share.

Like every outward action it is GATED. Nothing is posted automatically. On approval we
hand the owner a ready-to-paste packet: the canonical link plus a PREFILLED submission
URL for the chosen venue, so the final human click keeps us inside each venue's ToS and
nothing leaves the machine behind the owner's back.
"""
from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SITE = "https://dancenitra.github.io/agora/public"
MANIFEST = ROOT / "public" / "posts" / "posts.json"
PACKET_DIR = ROOT / "agora_output" / "distribution"

# Venues people who care about our topics actually read. kind drives the prefilled submit URL.
VENUES: dict[str, dict] = {
    "hn":               {"name": "Hacker News",     "kind": "hn"},
    "x":                {"name": "X / Twitter",     "kind": "x"},
    # some subs auto-remove posts whose title lacks a category flair tag -> prepend one
    "r/statistics":     {"name": "r/statistics",     "kind": "reddit", "sub": "statistics", "flair": "[D]"},
    "r/econometrics":   {"name": "r/econometrics",   "kind": "reddit", "sub": "econometrics"},
    "r/datascience":    {"name": "r/datascience",    "kind": "reddit", "sub": "datascience"},
    "r/MachineLearning": {"name": "r/MachineLearning", "kind": "reddit", "sub": "MachineLearning", "flair": "[D]"},
    "r/LocalLLaMA":     {"name": "r/LocalLLaMA",     "kind": "reddit", "sub": "LocalLLaMA"},
    "r/slatestarcodex": {"name": "r/slatestarcodex", "kind": "reddit", "sub": "slatestarcodex"},
    "r/longevity":      {"name": "r/longevity",      "kind": "reddit", "sub": "longevity"},
    "r/QuantifiedSelf": {"name": "r/QuantifiedSelf", "kind": "reddit", "sub": "QuantifiedSelf"},
}

# topic keyword groups -> ordered venue keys (most-relevant first)
TOPIC_VENUES: list[tuple[tuple[str, ...], list[str]]] = [
    (("causal", "did", "difference-in-differences", "difference in differences", "pre-trend",
      "pretrend", "econometr", "regression", "confound", "instrumental", "collider"),
     ["hn", "r/econometrics", "r/statistics", "r/datascience"]),
    (("bayes", "frequentist", "confidence interval", "credible interval", "calibrat", "p-value",
      "null", "replicat", "robustness", "meta-analysis", "significance"),
     ["hn", "r/statistics", "r/slatestarcodex", "r/datascience"]),
    (("ai", "llm", "model collapse", "agent", "reasoning", "rag", "retrieval", "embedding",
      "transformer", "self-training", "self training", "fine-tun"),
     ["hn", "r/MachineLearning", "r/LocalLLaMA"]),
    (("memory", "second brain", "note-taking", "consolidation", "forgetting", "knowledge graph"),
     ["hn", "r/LocalLLaMA", "r/MachineLearning"]),
    (("forecast", "prediction", "brier", "overconfid", "dunning", "hot hand", "wisdom of crowds"),
     ["hn", "r/slatestarcodex", "r/statistics"]),
    (("aging", "longevity", "anti-aging", "healthspan", "mice", "intervention", "lifespan"),
     ["hn", "r/longevity", "r/QuantifiedSelf"]),
    (("network", "metcalfe", "percolation", "emergence", "complexity", "lock-in", "herding",
      "crowd", "phase transition", "criticality"),
     ["hn", "r/slatestarcodex", "r/MachineLearning"]),
]
FALLBACK_VENUES = ["hn", "x"]

# title/desc signals that a piece is contrarian / a measured failure -> high shareability
SHARE_SIGNALS = (
    "fail", "artifact", "myth", "weak evidence", "wrong", "we measured", "measured", "zero",
    "reverse", "trap", "dying", "rotting", "fallacy", "couldn't", "could not", "isn't", "aren't",
    "not cov", "more wrong", "least grounded", "more confident", "no ", "debunk", "overrated",
)


def _q(s: str) -> str:
    return urllib.parse.quote(s or "", safe="")


def _load_manifest() -> list:
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return []


def post_url(slug: str) -> str:
    return f"{SITE}/posts/{slug}.html"


def submit_url(venue_key: str, url: str, title: str, blurb: str = "") -> str:
    """A prefilled submission URL for the venue (the owner's final one-click)."""
    v = VENUES.get(venue_key, {})
    kind = v.get("kind", "hn")
    if kind == "hn":
        return f"https://news.ycombinator.com/submitlink?u={_q(url)}&t={_q(title)}"
    if kind == "reddit":
        flair = v.get("flair", "")
        t = f"{flair} {title}".strip() if flair else title
        return (f"https://www.reddit.com/r/{v.get('sub','')}/submit"
                f"?url={_q(url)}&title={_q(t)}")
    if kind == "x":
        text = (blurb or title)[:240]
        return f"https://twitter.com/intent/tweet?text={_q(text)}&url={_q(url)}"
    return url


def _signals(text: str) -> list[str]:
    t = text.lower()
    return [s.strip() for s in SHARE_SIGNALS if s in t]


def match_venues(text: str) -> list[str]:
    t = text.lower()
    out: list[str] = []
    for kws, venues in TOPIC_VENUES:
        if any(k in t for k in kws):
            for vk in venues:
                if vk not in out:
                    out.append(vk)
    if not out:
        out = list(FALLBACK_VENUES)
    return out[:4]


def _recency_bonus(date: str) -> float:
    try:
        y, m, d = (int(x) for x in date.split("-"))
        age_days = (time.time() - time.mktime((y, m, d, 12, 0, 0, 0, 0, -1))) / 86400.0
        return max(0.0, 1.0 - age_days / 30.0)  # full credit today, 0 after ~30 days
    except Exception:
        return 0.0


def gather_distributable(n: int = 6) -> list[dict]:
    items = []
    for p in _load_manifest():
        slug = p.get("slug", "")
        if not slug:
            continue
        title = p.get("title", "")
        desc = p.get("desc", "") or ""
        tags = p.get("tags", "") or ""
        text = f"{title} {desc} {tags}"
        sig = _signals(text)
        score = 1.0 + 0.5 * len(sig) + _recency_bonus(p.get("date", ""))
        vkeys = match_venues(text)
        items.append({
            "slug": slug, "title": title, "desc": desc, "date": p.get("date", ""),
            "url": post_url(slug), "score": round(score, 2), "signals": sig,
            "suggested_venues": [{"key": k, "name": VENUES[k]["name"]} for k in vkeys],
        })
    items.sort(key=lambda x: -x["score"])
    return items[:n]


def distribution_inputs(n: int = 6) -> dict:
    """Raw material for Claude to draft a venue-tailored share (the creative leap stays with Claude)."""
    items = gather_distributable(n)
    return {"status": "ok", "site": SITE, "n": len(items), "items": items,
            "venues": {k: v["name"] for k, v in VENUES.items()}}


def draft_distribution(slug: str, venue: str, title: str, pitch: str,
                       url: str = "", body: str = "") -> dict:
    """Store a GATED distribution proposal (mirrors press/correspondent)."""
    from agora.execution.hands import propose_action
    v = VENUES.get(venue)
    if not v:
        return {"error": f"unknown venue '{venue}'"}
    url = url or post_url(slug)
    title = (title or slug).strip()
    pitch = (pitch or "").strip()
    rec = propose_action(
        "distribute",
        f"Share: {title[:55]} -> {v['name']}",
        pitch[:300],
        {"slug": slug, "venue": venue, "venue_name": v["name"],
         "title": title, "pitch": pitch, "body": (body or pitch), "url": url},
    )
    return rec


def execute_distribution(payload: dict) -> str:
    """On approval: write a ready-to-paste packet + return the prefilled submit URL.
    We do NOT auto-post to third-party venues (accounts/ToS); the owner's one click does."""
    venue = payload.get("venue", "")
    v = VENUES.get(venue, {})
    title = payload.get("title", "")
    url = payload.get("url", "")
    pitch = payload.get("pitch", "")
    body = payload.get("body", pitch)
    link = submit_url(venue, url, title, pitch)
    PACKET_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    safe_slug = (payload.get("slug", "post") or "post")[:40]
    packet = PACKET_DIR / f"{stamp}_{safe_slug}_{venue.replace('/', '-')}.md"
    packet.write_text(
        f"# Distribution packet — {v.get('name', venue)}\n\n"
        f"**Title:** {title}\n\n"
        f"**Canonical link:** {url}\n\n"
        f"**Prefilled submit URL (one click):** {link}\n\n"
        f"**Suggested copy / comment:**\n\n{body}\n",
        encoding="utf-8",
    )
    return f"Ready for {v.get('name', venue)}. Open prefilled: {link}  |  packet: {packet.name}"
