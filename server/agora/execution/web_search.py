"""
Multi-source web-scout — the widest free external reach (owner 2026-06-27): surface fresh external
signal (papers, practitioner folklore, products, discussions) to bridge into our vault + feed the
Crucible with testable claims.

FREE-first design with graceful degradation:
  - NO-KEY sources always run: HuggingFace papers, Hacker News (Algolia), Crossref, Wikipedia,
    Semantic Scholar, DuckDuckGo (lite HTML). (arXiv + OpenAlex are already covered by research_tool.)
  - KEY-GATED sources run only when their API key is set AND under the FREE monthly quota, then
    auto-skip until the month resets: Tavily (~1000/mo free), Brave (~2000/mo free), Reddit (our
    existing OAuth creds). Keys live in gitignored server/.env: TAVILY_API_KEY, BRAVE_API_KEY.
  - X/Twitter is intentionally OMITTED: its API is no longer free (~$100/mo+) and scraping is
    flaky/ToS-risky — adding it would break the "mainly free" constraint.

Every source is wrapped fail-soft so one broken endpoint never kills the rest. Pure stdlib (urllib)
— no new dependencies. This is DATA fetch (not LLM), so it is fine under the cloud-free LLM policy.
"""
import json, os, re, time, urllib.request, urllib.parse
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[2]          # .../server
_QUOTA = _SERVER / ".web_search_quota.json"
_FREE_LIMIT = {"tavily": 1000, "brave": 2000}          # conservative free monthly caps


def _get(url, headers=None, timeout=12, data=None):
    req = urllib.request.Request(url, data=data,
                                 headers=headers or {"User-Agent": "agora-webscout/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _json(url, headers=None, timeout=12, data=None):
    return json.loads(_get(url, headers, timeout, data))


def _q(s):
    return urllib.parse.quote(s)


def _env(name):
    """Read a secret key: os.environ first, else parse gitignored server/.env directly (the repo's
    pattern for non-AGORA_ secrets — pydantic loads .env into Settings, not os.environ)."""
    v = os.environ.get(name)
    if v:
        return v.strip()
    try:
        m = re.search(rf'^{name}=(.+)$', (_SERVER / ".env").read_text(encoding="utf-8"), re.M)
        return m.group(1).strip().strip('"').strip("'") if m else None
    except Exception:
        return None


# ── monthly free-quota tracking (auto-reset on month change) ──────────────────
def _load_quota():
    try:
        d = json.loads(_QUOTA.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    mon = time.strftime("%Y-%m", time.gmtime())
    if d.get("month") != mon:
        d = {"month": mon}                              # new month → reset all counters
    return d


def _quota_ok(src):
    return _load_quota().get(src, 0) < _FREE_LIMIT.get(src, 0)


def _quota_inc(src):
    d = _load_quota(); d[src] = d.get(src, 0) + 1
    try:
        _QUOTA.write_text(json.dumps(d), encoding="utf-8")
    except Exception:
        pass


# ── NO-KEY sources ────────────────────────────────────────────────────────────
def _hf(q, n):
    d = _json(f"https://huggingface.co/api/papers/search?q={_q(q)}")
    out = []
    for p in (d if isinstance(d, list) else [])[:n]:
        pp = p.get("paper", p)
        t = pp.get("title", "")
        if t:
            out.append({"title": t, "url": f"https://huggingface.co/papers/{pp.get('id', '')}",
                        "snippet": (pp.get("summary") or "")[:240], "source": "hf"})
    return out


def _hn(q, n):
    d = _json(f"https://hn.algolia.com/api/v1/search?query={_q(q)}&tags=story&hitsPerPage={n}")
    out = []
    for h in d.get("hits", []):
        if h.get("title"):
            out.append({"title": h["title"],
                        "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                        "snippet": f"{h.get('points', 0)} pts · {h.get('num_comments', 0)} comments",
                        "source": "hn"})
    return out


def _crossref(q, n):
    d = _json(f"https://api.crossref.org/works?query={_q(q)}&rows={n}&select=title,DOI,abstract")
    out = []
    for it in d.get("message", {}).get("items", []):
        t = (it.get("title") or [""])[0]
        if t:
            out.append({"title": t, "url": f"https://doi.org/{it.get('DOI', '')}",
                        "snippet": re.sub(r"<[^>]+>", "", it.get("abstract", "") or "")[:240],
                        "source": "crossref"})
    return out


def _wikipedia(q, n):
    d = _json(f"https://en.wikipedia.org/w/api.php?action=opensearch&search={_q(q)}&limit={n}&format=json")
    return [{"title": t, "url": u, "snippet": "", "source": "wikipedia"}
            for t, u in zip(d[1], d[3])]


def _semanticscholar(q, n):
    d = _json(f"https://api.semanticscholar.org/graph/v1/paper/search?query={_q(q)}&limit={n}&fields=title,abstract,url")
    return [{"title": p.get("title", ""), "url": p.get("url", ""),
             "snippet": (p.get("abstract") or "")[:240], "source": "s2"}
            for p in d.get("data", []) if p.get("title")]


def _ddg(q, n):
    html = _get(f"https://lite.duckduckgo.com/lite/?q={_q(q)}", headers={"User-Agent": "Mozilla/5.0"})
    out = []
    # quote-/order-agnostic: any <a> tag whose attributes contain result-link, then pull href + text
    for tag in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.S):
        attrs, inner = tag.group(1), tag.group(2)
        if "result-link" not in attrs:
            continue
        m = re.search(r'href=["\'](https?://[^"\']+)["\']', attrs)
        title = re.sub(r"<[^>]+>", "", inner).strip()
        if m and title:
            out.append({"title": title, "url": m.group(1), "snippet": "", "source": "ddg"})
        if len(out) >= n:
            break
    return out


# ── KEY-GATED sources (free tier; auto-skip when over quota or no key) ─────────
def _tavily(q, n):
    key = _env("TAVILY_API_KEY")
    if not key or not _quota_ok("tavily"):
        return []
    body = json.dumps({"api_key": key, "query": q, "max_results": n}).encode()
    d = _json("https://api.tavily.com/search", headers={"Content-Type": "application/json"},
              data=body, timeout=18)
    _quota_inc("tavily")
    return [{"title": r.get("title", ""), "url": r.get("url", ""),
             "snippet": (r.get("content") or "")[:240], "source": "tavily"} for r in d.get("results", [])]


def _brave(q, n):
    key = _env("BRAVE_API_KEY")
    if not key or not _quota_ok("brave"):
        return []
    d = _json(f"https://api.search.brave.com/res/v1/web/search?q={_q(q)}&count={n}",
              headers={"X-Subscription-Token": key, "Accept": "application/json"})
    _quota_inc("brave")
    return [{"title": r.get("title", ""), "url": r.get("url", ""),
             "snippet": (r.get("description") or "")[:240], "source": "brave"}
            for r in d.get("web", {}).get("results", [])]


def _reddit(q, n):
    import sys
    sys.path.insert(0, str(_SERVER.parent / "tools"))
    import distribution_radar as R
    tok = R._reddit_token()
    if not tok:
        return []
    d = _json(f"https://oauth.reddit.com/search?q={_q(q)}&limit={n}&sort=relevance&t=year",
              headers={"User-Agent": "agora-webscout/0.1", "Authorization": "bearer " + tok})
    out = []
    for c in d.get("data", {}).get("children", []):
        x = c.get("data", {})
        if x.get("title"):
            out.append({"title": x["title"], "url": "https://reddit.com" + x.get("permalink", ""),
                        "snippet": (x.get("selftext") or "")[:240], "source": "reddit"})
    return out


_SOURCES = [_hf, _hn, _crossref, _wikipedia, _semanticscholar, _ddg, _tavily, _brave, _reddit]


def web_search(query: str, n_per: int = 6) -> dict:
    """Aggregate across every enabled source, dedup by URL/title, return {results, by_source, errors}.
    Fail-soft: a broken source is skipped and noted in `errors`, never raised."""
    results, seen, by_source, errors = [], set(), {}, {}
    for fn in _SOURCES:
        name = fn.__name__.lstrip("_")
        try:
            hits = fn(query, n_per) or []
            kept = 0
            for r in hits:
                key = (r.get("url") or r.get("title", "")).lower().rstrip("/")
                if key and key not in seen:
                    seen.add(key); results.append(r); kept += 1
            by_source[name] = kept
        except Exception as e:
            errors[name] = f"{type(e).__name__}: {str(e)[:80]}"
    return {"query": query, "count": len(results), "by_source": by_source,
            "errors": errors, "results": results}


if __name__ == "__main__":
    import sys
    out = web_search(sys.argv[1] if len(sys.argv) > 1 else "agent memory benchmark", 5)
    print("count:", out["count"], "| by_source:", out["by_source"], "| errors:", out["errors"])
    for r in out["results"][:12]:
        print(f"  [{r['source']:>9}] {r['title'][:70]}")
