"""Generate sitemap.xml for the Agora storefront from the posts manifest. Run after render_post.
Lists the homepage, the posts index, the Crucible, and every post (with <lastmod> from posts.json).
Deployed to https://dancenitra.github.io/agora/sitemap.xml (submit this URL to GSC + Bing)."""
import json
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://dancenitra.github.io/agora"


def build():
    urls = [(f"{SITE}/", None)]
    if (ROOT / "public" / "posts" / "index.html").exists():
        urls.append((f"{SITE}/public/posts/index.html", None))
    if (ROOT / "public" / "crucible" / "index.html").exists():
        urls.append((f"{SITE}/public/crucible/index.html", None))
    try:
        posts = json.loads((ROOT / "public" / "posts" / "posts.json").read_text(encoding="utf-8"))
    except Exception:
        posts = []
    for p in posts:
        slug = p.get("slug")
        if slug:
            urls.append((f"{SITE}/public/posts/{slug}.html", p.get("date")))
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
