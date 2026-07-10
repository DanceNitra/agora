"""Generate sitemap.xml for the Agora storefront from the posts manifest. Run after render_post.
Lists the homepage, the posts index, the Crucible, and every post (with <lastmod> from posts.json).
Deployed to https://dancenitra.github.io/agora/sitemap.xml (submit this URL to GSC + Bing)."""
import json
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://dancenitra.github.io/agora"

_DATEMOD = re.compile(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})')


def _lastmod_for(slug, published):
    """Prefer the post's JSON-LD dateModified (so an audited/edited post signals freshness for
    re-crawl); fall back to the posts.json publish date."""
    html_path = ROOT / "public" / "posts" / f"{slug}.html"
    try:
        m = _DATEMOD.search(html_path.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    except Exception:
        pass
    return published

# Slugs that canonicalize to another post (near-duplicates) — omit from the sitemap so only the
# canonical URL is listed. The page still exists; its <link rel="canonical"> points to the survivor.
CANONICALIZED = {
    "passing-a-pre-trends-test-is-weak-evidence-which-difference-",  # -> pre-trends-test-weak-evidence
}


def build():
    urls = [(f"{SITE}/", None)]
    if (ROOT / "public" / "posts" / "index.html").exists():
        urls.append((f"{SITE}/public/posts/index.html", None))
    if (ROOT / "public" / "crucible" / "index.html").exists():
        urls.append((f"{SITE}/public/crucible/index.html", None))
    if (ROOT / "public" / "track-record.html").exists():
        urls.append((f"{SITE}/public/track-record.html", None))
    if (ROOT / "public" / "research-digest.html").exists():
        urls.append((f"{SITE}/public/research-digest.html", None))
    if (ROOT / "public" / "forecast.html").exists():
        urls.append((f"{SITE}/public/forecast.html", None))
    try:
        posts = json.loads((ROOT / "public" / "posts" / "posts.json").read_text(encoding="utf-8"))
    except Exception:
        posts = []
    for p in posts:
        slug = p.get("slug")
        if slug and slug not in CANONICALIZED:
            urls.append((f"{SITE}/public/posts/{slug}.html", _lastmod_for(slug, p.get("date"))))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in urls:
        lm = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        out.append(f"  <url><loc>{html.escape(loc)}</loc>{lm}</url>")
    out.append("</urlset>\n")
    (ROOT / "sitemap.xml").write_text("\n".join(out), encoding="utf-8")
    return len(urls)


if __name__ == "__main__":
    n = build()
    print(f"wrote sitemap.xml with {n} urls")
