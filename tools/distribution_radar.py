"""
distribution_radar.py - automated DISCOVERY of live conversations where Agora has something real to
contribute, so the owner never has to manually trawl Reddit/HN/GitHub. Complements the push-only
Distribution Desk (which submits OUR posts to venues): the Radar PULLS live threads, ranks them by
fit x recency x engagement, and drafts an angle + which of our assets to bring. The owner reviews and
posts (GATED - this never posts anything).

Sources: Hacker News (free Algolia API, no auth) + GitHub issues (via gh, already authed here) +
Reddit (app-only OAuth read, free tier, creds in server/.env). X deferred (no free search API).
Reddit is READ-ONLY discovery; we never post (the owner posts manually) - ToS-compliant.

Usage:  python tools/distribution_radar.py            # last 30 days, top opportunities
"""
import json, os, re, sys, time, subprocess, urllib.request, urllib.parse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console is cp1250; titles carry unicode
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "agora_output", "distribution_radar")
WINDOW_DAYS = 30
CRUCIBLE = "https://dancenitra.github.io/agora/public/crucible/"
# actionability gates (a weak/old/closed thread is not worth a comment)
HN_MAX_AGE_DAYS = 5      # HN threads die within days; commenting later = nobody sees it
HN_MIN_POINTS = 15       # real audience
GH_MIN_COMMENTS = 1      # a genuine discussion, not a solo dump
JUNK_REPO_RE = re.compile(r"(intern|bootcamp|camp|playbook|test-|-test|demo|tutorial|course|assignment|homework|study|sandbox|practice|example)", re.I)
REDDIT_MAX_AGE_DAYS = 14   # subreddit threads stay active longer than HN (days, not hours)
REDDIT_MIN_UPS = 5         # a real thread, not a 1-upvote drop
REDDIT_MIN_COMMENTS = 3    # OR this many comments = a live discussion
ENV_PATH = os.path.join(ROOT, "server", ".env")

# our real, defensible assets mapped to the conversations they speak to
TOPICS = [
    {"q": "RAG chunk size retrieval", "kw": ["chunk", "rag", "retriev", "context window"],
     "asset": "Folklore Index: 'smaller chunks are better for RAG' = FAILED",
     "hook": "we ran it - under a fixed top-k budget the SMALLEST chunk is the worst (recovery 0.75 vs 1.0); optimum sits at/above the span scale"},
    {"q": "RAG hallucination grounding retrieval poisoning", "kw": ["hallucinat", "grounding", "poison", "rag"],
     "asset": "Poison-Deference Index + Grounding Firewall",
     "hook": "measured: frontier models adopt a planted-false retrieved doc ~92% of the time even when they knew the right answer; a drop-sensitivity gate ships 0% wrong at 70% coverage"},
    {"q": "LLM as a judge evaluation reliability", "kw": ["llm as judge", "llm-as-judge", "eval", "judge"],
     "asset": "Crucible / Eval-Eval angle",
     "hook": "the judge layer everyone evaluates ON is rarely audited itself (test-retest, position/verbosity bias) - we publish runnable receipts"},
    {"q": "multi-agent vs single agent", "kw": ["multi-agent", "multi agent", "agent", "orchestrat"],
     "asset": "Folklore Index: multi-agent > single at fixed cost = NOT_COMPUTABLE",
     "hook": "at fixed token cost the comparison is dominated by run-to-run noise (same config swings 0.15-0.20 on identical tasks); the loud folklore rests on under-powered evals"},
    {"q": "benchmark leaderboard contamination overfitting", "kw": ["benchmark", "leaderboard", "sota", "contaminat"],
     "asset": "Folklore Index: leaderboard winner's score is reliable = FAILED (winner's curse)",
     "hook": "selection-on-the-max inflates the reported top score and the winner is the truly-best model only ~17% of the time at N=50 noisy evals"},
    {"q": "AI agent reliability long tasks time horizon", "kw": ["agent", "reliab", "time horizon", "metr"],
     "asset": "Folklore Index: agent-success half-life REPRODUCED; time-horizon headline FAILED",
     "hook": "a constant-hazard half-life fits METR's anchors, but the headline horizon swings 2.8x just from the 50%-vs-80% success threshold"},
]

UA = {"User-Agent": "agora-distribution-radar/0.1"}


def _recency_weight(age_days):
    return max(0.1, 1.0 - age_days / float(WINDOW_DAYS))   # 1.0 today -> 0.1 at the window edge


def hn_search(topic, since_ts):
    """Hacker News via Algolia (free, no auth): recent stories matching the query."""
    url = ("http://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode({
        "query": topic["q"], "tags": "story",
        "numericFilters": "created_at_i>%d" % since_ts, "hitsPerPage": 8}))
    out = []
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read())
    except Exception as e:
        return out, "hn error: %s" % e
    for h in r.get("hits", []):
        title = h.get("title") or ""
        if not title:
            continue
        text = (title + " " + (h.get("story_text") or "")).lower()
        if not any(k in text for k in topic["kw"]):
            continue
        age = (time.time() - h.get("created_at_i", time.time())) / 86400.0
        points = h.get("points", 0) or 0
        ncom = h.get("num_comments", 0) or 0
        if age > HN_MAX_AGE_DAYS or points < HN_MIN_POINTS:   # stale or no audience -> not actionable
            continue
        score = (points + 2 * ncom) * _recency_weight(age)
        out.append({"src": "HN", "title": title[:140],
                    "url": "https://news.ycombinator.com/item?id=%s" % h.get("objectID"),
                    "engagement": "%d pts / %d comments" % (points, ncom),
                    "age_days": round(age, 1), "score": round(score, 1)})
    return out, None


def gh_search(topic, since_date):
    """GitHub open issues via gh (already authed), recent + matching."""
    out = []
    try:
        q = '%s in:title,body state:open created:>%s' % (topic["q"], since_date)
        p = subprocess.run(["gh", "search", "issues", q, "--limit", "12",
                            "--json", "title,url,repository,createdAt,commentsCount,state,isPullRequest"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40)
        hits = json.loads(p.stdout) if p.stdout.strip() else []
    except Exception as e:
        return out, "gh error: %s" % e
    for h in hits:
        title = h.get("title") or ""
        text = title.lower()
        if not any(k in text for k in topic["kw"]):
            continue
        if (h.get("state") or "open").lower() != "open" or h.get("isPullRequest"):  # re-verify open, no PRs
            continue
        ncom = h.get("commentsCount", 0) or 0
        repo = (h.get("repository") or {}).get("nameWithOwner", "")
        if ncom < GH_MIN_COMMENTS or JUNK_REPO_RE.search(repo):   # solo dump or personal/learning repo
            continue
        try:
            created = time.mktime(time.strptime(h.get("createdAt", "")[:10], "%Y-%m-%d"))
            age = (time.time() - created) / 86400.0
        except Exception:
            age = WINDOW_DAYS
        score = (3 + 2 * ncom) * _recency_weight(age)
        out.append({"src": "GitHub", "title": ("%s: %s" % (repo, title))[:140],
                    "url": h.get("url"), "engagement": "%d comments" % ncom,
                    "age_days": round(age, 1), "score": round(score, 1)})
    return out, None


_REDDIT_TOKEN = None


def _load_reddit_creds():
    cid = os.environ.get("AGORA_REDDIT_CLIENT_ID")
    csec = os.environ.get("AGORA_REDDIT_CLIENT_SECRET")
    if cid and csec:
        return cid, csec
    try:                                          # read from gitignored server/.env (append-safe, no echo)
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("AGORA_REDDIT_CLIENT_ID="):
                    cid = line.split("=", 1)[1].strip()
                elif line.startswith("AGORA_REDDIT_CLIENT_SECRET="):
                    csec = line.split("=", 1)[1].strip()
    except Exception:
        pass
    return cid, csec


def _reddit_token():
    """App-only OAuth (client_credentials) for a confidential 'script' app -> read-only bearer token."""
    global _REDDIT_TOKEN
    if _REDDIT_TOKEN:
        return _REDDIT_TOKEN
    cid, csec = _load_reddit_creds()
    if not (cid and csec):
        return None
    import base64
    auth = base64.b64encode(("%s:%s" % (cid, csec)).encode()).decode()
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request("https://www.reddit.com/api/v1/access_token", data=data,
                                 headers={"Authorization": "Basic %s" % auth, "User-Agent": UA["User-Agent"]})
    try:
        res = json.loads(urllib.request.urlopen(req, timeout=20).read())
        _REDDIT_TOKEN = res.get("access_token")
    except Exception:
        _REDDIT_TOKEN = None
    return _REDDIT_TOKEN


def reddit_search(topic, since_ts):
    """Reddit via app-only OAuth (read-only): recent posts matching the query, gated by engagement+recency.
    Read-only discovery only - we NEVER post here (the owner posts manually); ToS-compliant per the
    Responsible Builder Policy (low-volume, non-commercial, no automated posting/voting)."""
    out = []
    tok = _reddit_token()
    if not tok:
        return out, "reddit: no token (set AGORA_REDDIT_CLIENT_ID/SECRET in server/.env)"
    url = ("https://oauth.reddit.com/search?" + urllib.parse.urlencode({
        "q": topic["q"], "sort": "relevance", "t": "month", "limit": 12, "type": "link"}))
    hdr = {"Authorization": "bearer %s" % tok, "User-Agent": UA["User-Agent"]}
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=20).read())
    except Exception as e:
        return out, "reddit error: %s" % e
    for c in r.get("data", {}).get("children", []):
        d = c.get("data", {})
        title = d.get("title") or ""
        if not title:
            continue
        text = (title + " " + (d.get("selftext") or "")).lower()
        if not any(k in text for k in topic["kw"]):
            continue
        age = (time.time() - d.get("created_utc", time.time())) / 86400.0
        ups = d.get("ups", 0) or 0
        ncom = d.get("num_comments", 0) or 0
        if age > REDDIT_MAX_AGE_DAYS or (ups < REDDIT_MIN_UPS and ncom < REDDIT_MIN_COMMENTS):
            continue                              # stale or no audience -> not actionable
        score = (ups + 2 * ncom) * _recency_weight(age)
        out.append({"src": "Reddit", "title": ("r/%s: %s" % (d.get("subreddit"), title))[:140],
                    "url": "https://www.reddit.com" + (d.get("permalink") or ""),
                    "engagement": "%d ups / %d comments" % (ups, ncom),
                    "age_days": round(age, 1), "score": round(score, 1)})
    return out, None


def main():
    since_ts = int(time.time() - WINDOW_DAYS * 86400)
    since_date = time.strftime("%Y-%m-%d", time.localtime(since_ts))
    opportunities, errors = [], []
    for topic in TOPICS:
        for fn, arg in ((hn_search, since_ts), (gh_search, since_date), (reddit_search, since_ts)):
            hits, err = fn(topic, arg)
            if err:
                errors.append(err)
            for h in hits:
                h["asset"] = topic["asset"]
                h["draft_angle"] = topic["hook"]
                opportunities.append(h)
    # dedup by url, keep best score; rank
    best = {}
    for o in opportunities:
        u = o["url"]
        if u not in best or o["score"] > best[u]["score"]:
            best[u] = o
    ranked = sorted(best.values(), key=lambda o: o["score"], reverse=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    payload = {"generated_window_days": WINDOW_DAYS, "crucible": CRUCIBLE,
               "note": "GATED - draft angles for the owner to review and post; this tool never posts. "
                       "Sources: HN + GitHub + Reddit (app-only OAuth, read-only). X deferred (no free API).",
               "errors": errors, "opportunities": ranked}
    with open(os.path.join(OUT_DIR, "radar_opportunities.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)

    print("=" * 70)
    print("DISTRIBUTION RADAR - live conversations to join (last %d days)" % WINDOW_DAYS)
    print("GATED: draft angles only; the owner posts. Sources: HN + GitHub + Reddit.")
    print("=" * 70)
    if not ranked:
        print("No fitting live threads found in the window (try widening WINDOW_DAYS or topics).")
    for i, o in enumerate(ranked[:12], 1):
        print("\n%d. [%s | score %.1f | %s | %sd old] %s" %
              (i, o["src"], o["score"], o["engagement"], o["age_days"], o["title"]))
        print("   %s" % o["url"])
        print("   BRING: %s" % o["asset"])
        print("   ANGLE: %s" % o["draft_angle"])
    if errors:
        print("\n(notes: %s)" % "; ".join(errors[:4]))
    print("\nwrote: agora_output/distribution_radar/radar_opportunities.json")


if __name__ == "__main__":
    main()
