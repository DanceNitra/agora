"""Rebuild the front page's Writing list from posts.json, and fail loudly when it drifts.

WHY. Measured 2026-08-26: 63 essays are published and 14 were reachable from the front page. The
newest one linked was 2026-07-11; six weeks of work, including both posts a live Reddit thread was
pointing 4,200 readers at, existed on the site and could not be found from its front door. One of
the 14 links pointed at a slug that is not in posts.json at all.

Nothing was broken. The list is hand-written markup, and hand-written markup does not know when
something new is published, so it decays silently and passes every check that looks at the page
itself. The archive at public/posts/ was correct the whole time and listed all 63; only the curated
front-page list was stale, which is the harder case to notice because the page looks fine.

So the list is generated, and `--check` makes staleness a failing exit code rather than something
somebody has to remember. That is the actual fix: the instance is 50 missing links, the class is a
derived surface maintained by hand.

  python tools/render_writing_index.py            # rewrite index.html and sk/index.html
  python tools/render_writing_index.py --check    # exit 1 if either is stale (for CI)

BOTH HALVES OR NEITHER. The site is bilingual and the Slovak mirror is a separate file, so a post
appears in the Slovak list only when its Slovak page actually exists on disk. A link to a missing
page is worse than no link, and the sk/ tree has been the half that silently lags before.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "public", "posts", "posts.json")
NBH = "‑"          # the non-breaking hyphen the existing rows use in dates
SHOW = 12               # the front page is a shopfront, not the archive; public/posts/ holds all
BLOCK = re.compile(r'(<div class="windex" data-reveal="">)(.*?)(</div>)', re.S)


def rows(posts: list, lang: str) -> str:
    out = []
    for n, p in enumerate(posts, 1):
        # Escape even though nothing in posts.json needs it today: measured, 0 of 48 fields carry
        # &, < or >. A future title with an ampersand would otherwise break the page silently, and
        # a generator is exactly where that has to be handled once rather than per post.
        title = html.escape(p["title_sk"] if lang == "sk" else p["title"], quote=False)
        desc = html.escape(p["desc_sk"] if lang == "sk" else p["desc"], quote=False)
        href = (f'/agora/sk/public/posts/{p["slug"]}.html' if lang == "sk"
                else f'public/posts/{p["slug"]}.html')
        date = p["date"].replace("-", NBH)
        read = f'{p.get("read", 5)} min'
        out.append(
            f'<a class="wrow" href="{href}">\n'
            f'<span class="wno">{n:02d}</span>\n'
            f'<span class="wtitle"><span class="{lang}">{title}</span></span>\n'
            f'<span class="wdek"><span class="{lang}">{desc}</span></span>\n'
            f'<span class="wmeta">{date} · <span class="{lang}">{read}</span></span>\n'
            f'</a>')
    return "\n" + "\n".join(out) + "\n"


def selected(posts: list, lang: str) -> list:
    """Newest first, and for Slovak only what actually has a Slovak page on disk."""
    live = []
    for p in sorted(posts, key=lambda x: x["date"], reverse=True):
        page = os.path.join(ROOT, *(("sk", "public", "posts") if lang == "sk"
                                    else ("public", "posts")), p["slug"] + ".html")
        if os.path.exists(page):
            live.append(p)
        elif lang == "en":
            print(f"  WARNING: {p['slug']} is in posts.json with no page at {page}; skipped")
    return live[:SHOW]


def main() -> int:
    check = "--check" in sys.argv
    posts = json.load(io.open(POSTS, encoding="utf-8"))
    stale = []
    for lang, path in (("en", os.path.join(ROOT, "index.html")),
                       ("sk", os.path.join(ROOT, "sk", "index.html"))):
        if not os.path.exists(path):
            raise SystemExit(f"REFUSED: {path} is absent")
        # NOT named `html`: that is the module this file imports for escaping, and a
        # local of the same name works only because rows() resolves it from globals.
        doc = io.open(path, encoding="utf-8").read()
        m = BLOCK.search(doc)
        if not m:
            raise SystemExit(f"REFUSED: no windex block in {path}; the markup moved and this tool "
                             f"would have silently written nothing")
        chosen = selected(posts, lang)
        if not chosen:
            raise SystemExit(f"REFUSED: no {lang} posts resolved to a page on disk")
        new = rows(chosen, lang)
        before = len(re.findall(r'class="wrow"', m.group(2)))
        after = len(chosen)
        if m.group(2) == new:
            print(f"  {lang}: current ({after} rows, newest {chosen[0]['date']})")
            continue
        stale.append(path)
        if check:
            print(f"  {lang}: STALE -- {before} rows now, {after} after a rebuild; "
                  f"newest listed would be {chosen[0]['date']}")
            continue
        io.open(path, "w", encoding="utf-8").write(doc[:m.start(2)] + new + doc[m.end(2):])
        print(f"  {lang}: rewrote {before} -> {after} rows, newest {chosen[0]['date']}")

    if check and stale:
        print(f"\n  STALE: {len(stale)} file(s). Run: python tools/render_writing_index.py")
        return 1
    print(f"\n  {len(posts)} essays published; the front page shows the newest {SHOW}, "
          f"public/posts/ holds them all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
