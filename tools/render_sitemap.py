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
    # DIRECTORY form, not index.html. These two pages canonicalise to ".../posts/" and ".../crucible/",
    # so listing ".../index.html" submitted Google a URL the page itself disavows -- a sitemap arguing
    # with its own canonical tag. Both forms serve byte-identical bodies; the canonical is the one that
    # counts. (The homepage already did this correctly.)
    for d in ("posts", "crucible"):
        if (ROOT / "public" / d / "index.html").exists():
            urls.append((f"{SITE}/public/{d}/", None))
    # Hub pages. `inspeximus` and `leaderboard` were live (HTTP 200) and absent from the sitemap
    # entirely -- inspeximus is the flagship product page, linked twice from the homepage hero.
    for f in ("track-record.html", "research-digest.html", "forecast.html"):
        if (ROOT / "public" / f).exists():
            urls.append((f"{SITE}/public/{f}", None))
    # `inspeximus` is deliberately NOT here. /public/inspeximus/ canonicalises CROSS-SITE to
    # https://dancenitra.github.io/inspeximus/ -- the product's own Pages site, which is live and holds
    # near-identical content (measured: 88% 5-gram overlap). A sitemap must not submit a URL the page
    # itself disavows. I added it as a "missing page" earlier today and rewrote its canonical to match,
    # on the untested assumption that the target was dead because the DOMAIN ROOT 404s; it is not, and
    # the cross-site canonical was correct all along. Both changes reverted.
    for d in ("leaderboard", "compare"):
        if (ROOT / "public" / d / "index.html").exists():
            urls.append((f"{SITE}/public/{d}/", None))
    try:
        posts = json.loads((ROOT / "public" / "posts" / "posts.json").read_text(encoding="utf-8"))
    except Exception:
        posts = []
    for p in posts:
        slug = p.get("slug")
        if slug and slug not in CANONICALIZED:
            urls.append((f"{SITE}/public/posts/{slug}.html", _lastmod_for(slug, p.get("date"))))
    # The Slovak half. Since 2026-07-28 each page exists once per language -- EN at its original URL, SK
    # mirrored under /agora/sk/ -- so the Slovak URLs need listing too or they are discoverable only by
    # following the on-page toggle. Listed only where the mirrored file actually exists, so a page that
    # was never bilingual does not get a phantom entry. lastmod is inherited from the English twin.
    sk_root = ROOT / "sk"
    if sk_root.exists():
        for loc, lastmod in list(urls):
            rel = loc[len(SITE):].lstrip("/")                      # "" | "public/posts/" | "a/b.html"
            # The FILE to test for existence, and separately the URL to publish. Deriving the URL from
            # the file path emitted ".../sk/index.html" and ".../sk/public/posts/index.html" while those
            # pages canonicalise to the directory form -- reintroducing on the Slovak side the exact
            # sitemap-vs-canonical contradiction fixed on the English side hours earlier. The EN entry
            # already decided the correct shape; mirror THAT, and use the path only to check the file is
            # really there.
            cand = sk_root / (rel if rel.endswith(".html") else rel + "index.html")
            if cand.exists():
                urls.append((f"{SITE}/sk/{rel}", lastmod))

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in urls:
        lm = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        out.append(f"  <url><loc>{html.escape(loc)}</loc>{lm}</url>")
    out.append("</urlset>\n")
    (ROOT / "sitemap.xml").write_text("\n".join(out), encoding="utf-8")

    # A sitemap INDEX at a second URL. Search Console has reported "couldn't fetch" for
    # /agora/sitemap.xml across four submissions in a month, while the file itself is provably fine:
    # HTTP 200 to a Googlebot UA, application/xml, no BOM, no redirect, valid schema, every one of its
    # URLs live. When the artifact is good and the report is bad for a month, the remaining candidate is
    # a cached failure on that exact URL, and re-submitting the same address does not clear it. This
    # gives a path Search Console has never seen, and it is a standard construct rather than a trick --
    # an index is what a growing site is supposed to submit anyway.
    idx = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
           f"  <sitemap><loc>{SITE}/sitemap.xml</loc></sitemap>",
           "</sitemapindex>\n"]
    (ROOT / "sitemap_index.xml").write_text("\n".join(idx), encoding="utf-8")
    return len(urls)


if __name__ == "__main__":
    n = build()
    print(f"wrote sitemap.xml with {n} urls")
