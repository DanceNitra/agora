"""
distribution_radar.py - automated DISCOVERY of live conversations where Agora has something real to
contribute, so the owner never has to manually trawl Reddit/HN/GitHub. Complements the push-only
Distribution Desk (which submits OUR posts to venues): the Radar PULLS live threads, ranks them by
fit x recency x engagement, and drafts an angle + which of our assets to bring. The owner reviews and
posts (GATED - this never posts anything).

Sources in v0.1: Hacker News (free Algolia API, no auth) + GitHub issues (via gh, already authed here).
Reddit/X are deferred (Reddit 403s our env; X has no free API) - flagged honestly in the output.

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
        p = subprocess.run(["gh", "search", "issues", q, "--limit", "8",
                            "--json", "title,url,repository,createdAt,commentsCount"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40)
        hits = json.loads(p.stdout) if p.stdout.strip() else []
    except Exception as e:
        return out, "gh error: %s" % e
    for h in hits:
        title = h.get("title") or ""
        text = title.lower()
        if not any(k in text for k in topic["kw"]):
            continue
        try:
            created = time.mktime(time.strptime(h.get("createdAt", "")[:10], "%Y-%m-%d"))
            age = (time.time() - created) / 86400.0
        except Exception:
            age = WINDOW_DAYS
        ncom = h.get("commentsCount", 0) or 0
        score = (3 + 2 * ncom) * _recency_weight(age)
        repo = (h.get("repository") or {}).get("nameWithOwner", "")
        out.append({"src": "GitHub", "title": ("%s: %s" % (repo, title))[:140],
                    "url": h.get("url"), "engagement": "%d comments" % ncom,
                    "age_days": round(age, 1), "score": round(score, 1)})
    return out, None


def main():
    since_ts = int(time.time() - WINDOW_DAYS * 86400)
    since_date = time.strftime("%Y-%m-%d", time.localtime(since_ts))
    opportunities, errors = [], []
    for topic in TOPICS:
        for fn, arg in ((hn_search, since_ts), (gh_search, since_date)):
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
                       "Reddit/X deferred (Reddit 403s our env; X has no free API).",
               "errors": errors, "opportunities": ranked}
    with open(os.path.join(OUT_DIR, "radar_opportunities.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)

    print("=" * 70)
    print("DISTRIBUTION RADAR - live conversations to join (last %d days)" % WINDOW_DAYS)
    print("GATED: draft angles only; the owner posts. Reddit/X deferred (auth).")
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
