"""Split the bilingual pages into one URL per language: EN stays put, SK mirrors under /agora/sk/.

WHY. Every page carried both languages in one document, CSS-toggled: 204 `span.en` and 204 `span.sk` on
the homepage, and a whole `div.sk` article on each post. Three things followed, all measured 2026-07-28:

  * A text extractor -- which is what an AI crawler and an answer engine ingest -- got the two languages
    glued together with no separator: "An autonomousresearch organizationthatships receipts.Autonomna
    vyskumna organizacia,ktoraprinasa dokazy." Nothing on the homepage was quotable. We explicitly invite
    GPTBot, PerplexityBot and ClaudeBot in robots.txt, to a page whose text is corrupted at the token level.
  * hreflang declared `en` AND `sk` pointing at the SAME URL. hreflang maps one URL per language; three
    annotations to one URL is a no-op that Google ignores, and no Slovak-targeted URL existed to rank.
  * No Slovak element carried lang="sk", so ~900-1900 Slovak words per post were declared English -- to
    search engines and to screen readers alike.

WHAT THIS DOES. For every bilingual page: write an EN-only document at the SAME URL (no existing link
breaks, no redirects needed) and an SK-only document at the mirrored path under sk/. Each gets its own
`lang`, its own canonical, and reciprocal hreflang. The EN/SK toggle stops being a CSS class flip and
becomes a real link to the other language's URL -- which is also what makes the two documents discoverable
from each other.

WHY bs4 AND NOT REGEX. The pages nest markup inside the language wrappers; a regex strip of
`<span class="sk">...</span>` cannot see its own closing tag through a nested element and would silently
eat or keep the wrong span. This walks the DOM.

NO SLOVAK IS LOST. That is the point and the constraint. The verification pass below asserts, per page,
that the SK document's text equals the Slovak text that was in the original, and likewise for EN -- a
split that dropped content would otherwise look like a success.
"""
from __future__ import annotations

import argparse
import io
import pathlib
import re
import sys

from bs4 import BeautifulSoup, Tag

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://dancenitra.github.io/agora"
SK_DIR = ROOT / "sk"
#: never mirrored: the SK tree holds documents, not a second copy of the data files
MIRROR_SUFFIX = ".html"


def bilingual_pages() -> list[pathlib.Path]:
    """Every page that actually carries both languages. A page with only one is left alone."""
    out = []
    for p in [ROOT / "index.html", *sorted((ROOT / "public").rglob("*.html"))]:
        if SK_DIR in p.parents or not p.exists():
            continue
        s = p.read_text(encoding="utf-8", errors="replace")
        if 'class="sk"' in s and 'class="en"' in s:
            out.append(p)
    return out


def rel_url(path: pathlib.Path) -> str:
    """Site-absolute URL path for a source file, e.g. /agora/public/posts/x.html"""
    return "/agora/" + path.relative_to(ROOT).as_posix()


def urls_for(path: pathlib.Path) -> tuple[str, str]:
    """The canonical URL of each language twin.

    DIRECTORY FORM for any index.html, because that is what these pages already declare as their own
    canonical and what the sitemap lists. Building the URL naively from the file path rewrote
    public/posts/ 's canonical to `.../public/posts/index.html` -- reintroducing, inside the pages, the
    exact sitemap-vs-canonical contradiction fixed hours earlier one layer up.
    """
    rel = path.relative_to(ROOT).as_posix()
    pretty = rel[:-len("index.html")] if rel.endswith("index.html") else rel
    return f"{SITE}/{pretty}", f"{SITE}/sk/{pretty}"


def _strip_other_language(soup: BeautifulSoup, keep: str) -> None:
    drop = "sk" if keep == "en" else "en"
    for el in soup.find_all(class_=drop):
        # only language wrappers -- a class list like ["sk","x"] is still a language wrapper, but an
        # element whose class merely CONTAINS these letters is not (find_all(class_=) matches tokens).
        el.decompose()


def _set_head(soup: BeautifulSoup, keep: str, en_url: str, sk_url: str) -> None:
    html = soup.find("html")
    if isinstance(html, Tag):
        html["lang"] = keep
        html["data-lang"] = keep

    self_url = en_url if keep == "en" else sk_url
    for link in soup.find_all("link", rel="canonical"):
        link["href"] = self_url

    # INSERT the alternates when the page never had any. Several bilingual pages (the posts index among
    # them) carried no hreflang at all, so rewriting-in-place left both twins silently unaware of each
    # other -- a split whose whole purpose is the reciprocal declaration, not making it.
    have = {(l.get("hreflang") or "").lower() for l in soup.find_all("link", rel="alternate")}
    head = soup.head
    if head is not None:
        for hl, href in (("en", en_url), ("sk", sk_url), ("x-default", en_url)):
            if hl not in have:
                tag = soup.new_tag("link", rel="alternate", href=href)
                tag["hreflang"] = hl
                head.append(tag)

    for link in soup.find_all("link", rel="alternate"):
        hl = (link.get("hreflang") or "").lower()
        if hl == "en":
            link["href"] = en_url
        elif hl == "sk":
            link["href"] = sk_url
        elif hl == "x-default":
            link["href"] = en_url
    # og:url and og:locale should follow the document, not the other language
    for m in soup.find_all("meta", property="og:url"):
        m["content"] = self_url
    for m in soup.find_all("meta", property="og:locale"):
        m["content"] = "en_US" if keep == "en" else "sk_SK"


#: characters that only appear in Slovak here -- a deterministic "is this actually Slovak" test
_SK_CHARS = set("áäčďéíĺľňóôŕšťúýžÁČĎÉÍĽŇÓŠŤÚÝŽ")
#: below this ratio of Slovak-to-English body text, the page is not translated, only decorated
_SK_MIN_RATIO = 0.5


def sk_is_real(original: str) -> tuple[bool, str]:
    """Is there a Slovak DOCUMENT here, or only Slovak chrome around English content?

    Some posts carry Slovak navigation and a Slovak "Zhrnutie" label while the article itself was never
    translated. Splitting one of those produces a Slovak URL holding 355 characters and an English
    headline -- a thin page, in the wrong language, at a URL we told Google was the Slovak version.
    Measured across the site: 1 of 63 pages. Publishing it would be worse than not having it, so the
    mirror is skipped and the EN page's `hreflang="sk"` is dropped: we claim a Slovak alternate only
    where one exists.
    """
    en_t, sk_t = _text(original, "en"), _text(original, "sk")
    ratio = len(sk_t) / max(1, len(en_t))
    soup = BeautifulSoup(original, "html.parser")
    _strip_other_language(soup, "sk")
    h1 = soup.find("h1")
    h1_sk = bool(set((h1.get_text(" ", strip=True) if h1 else "")) & _SK_CHARS)
    if ratio < _SK_MIN_RATIO:
        return False, f"Slovak body is {ratio:.0%} of the English one"
    if not h1_sk:
        return False, "the Slovak headline is not in Slovak"
    return True, ""


def _drop_sk_alternate(soup: BeautifulSoup) -> None:
    for l in soup.find_all("link", rel="alternate"):
        if (l.get("hreflang") or "").lower() == "sk":
            l.decompose()
    for span in soup.find_all("span", class_="lng"):
        span.decompose()


def _clip(text: str, n: int = 155) -> str:
    """Trim to n chars on a word boundary. Meta descriptions on this site run to 424 characters, which is
    2.5x what any SERP shows; the derived Slovak ones start correct."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(" ,;:-—")
    return cut + "…"


def _localise_head(soup: BeautifulSoup, keep: str, self_url: str) -> None:
    """Give the Slovak document Slovak <title>, description and headline.

    Those three live in <head> as plain text, outside the language wrappers, so stripping `.en` left the
    Slovak page announcing itself in English to every search engine and every share card -- a Slovak URL
    that cannot rank in Slovak is the whole point of the split, undone.

    Everything here is DERIVED FROM THE PAGE'S OWN SLOVAK TEXT: the title from its Slovak <h1>, the
    description from its first Slovak paragraph. Nothing is translated, guessed or invented -- if the
    Slovak h1 is missing the English title is left alone rather than fabricated.
    """
    if keep != "sk":
        # the English document is now monolingual too: inLanguage ["en","sk"] described the page that no
        # longer exists, and a bilingual declaration on a single-language URL is the same defect as the
        # hreflang pair this split exists to fix
        for s in soup.find_all("script", type="application/ld+json"):
            s.string = re.sub(r'"inLanguage":\s*(?:"[^"]*"|\[[^\]]*\])',
                              '"inLanguage": "en"', s.string or "")
        return
    h1 = soup.find("h1")
    sk_title = h1.get_text(" ", strip=True) if h1 else ""
    if sk_title:
        suffix = " · Agora"
        if soup.title:
            soup.title.string = sk_title + suffix
        for m in soup.find_all("meta", property="og:title"):
            m["content"] = sk_title + suffix
        for s in soup.find_all("script", type="application/ld+json"):
            s.string = re.sub(r'("headline":\s*)"(?:[^"\\]|\\.)*"',
                              lambda mo: mo.group(1) + _json_str(sk_title), s.string or "")

    body = soup.find("article") or soup.body
    para = ""
    for p in (body.find_all("p") if body else []):
        t = p.get_text(" ", strip=True)
        if len(t) > 60:
            para = t
            break
    if para:
        desc = _clip(para)
        for m in soup.find_all("meta", attrs={"name": "description"}):
            m["content"] = desc
        for m in soup.find_all("meta", property="og:description"):
            m["content"] = desc
        for m in soup.find_all("meta", attrs={"name": "twitter:description"}):
            m["content"] = desc

    for s in soup.find_all("script", type="application/ld+json"):
        txt = s.string or ""
        txt = re.sub(r'("url":\s*)"(?:[^"\\]|\\.)*"', lambda mo: mo.group(1) + _json_str(self_url), txt)
        txt = re.sub(r'"inLanguage":\s*(?:"[^"]*"|\[[^\]]*\])', '"inLanguage": "sk"', txt)
        s.string = txt


def _json_str(v: str) -> str:
    import json as _json
    return _json.dumps(v, ensure_ascii=False)


def _toggle_to_links(soup: BeautifulSoup, keep: str, en_url: str, sk_url: str) -> None:
    """The EN/SK control was a pair of buttons flipping a CSS class. With one language per document there
    is nothing left to flip, so it becomes the navigation between the two URLs -- which is also how a
    crawler discovers the alternate."""
    for span in soup.find_all("span", class_="lng"):
        span.clear()
        for code, href in (("EN", en_url), ("SK", sk_url)):
            a = soup.new_tag("a", href=href)
            a.string = code
            a["hreflang"] = code.lower()
            if code.lower() == keep:
                a["class"] = ["on"]
                a["aria-current"] = "true"
            span.append(a)


def _rewrite_links_for_sk(soup: BeautifulSoup, page: pathlib.Path, mirrored: set[str]) -> None:
    """Keep a Slovak reader in Slovak, without pointing at files the mirror does not contain.

    The SK document sits one directory deeper, so every relative href would resolve wrong. Each internal
    link is made site-absolute: to the SK twin when that page is part of the mirror, and to the ORIGINAL
    otherwise -- crucible.json, the leaderboard data and every non-HTML asset live only in the real tree,
    and a link into a mirror that has no copy of them is a 404 dressed as a translation.
    """
    base = page.parent
    for tag, attr in (("a", "href"), ("link", "href"), ("script", "src"), ("img", "src")):
        for el in soup.find_all(tag):
            v = el.get(attr)
            if not v or re.match(r"^(?:[a-z]+:|//|#|data:)", v, re.I):
                continue
            frag = ""
            if "#" in v:
                v, frag = v.split("#", 1)
                frag = "#" + frag
            if not v:
                el[attr] = frag
                continue
            try:
                target = (base / v).resolve()
                rel = target.relative_to(ROOT).as_posix()
            except (ValueError, OSError):
                continue
            el[attr] = ("/agora/sk/" + rel if rel in mirrored else "/agora/" + rel) + frag


def _text(html: str, keep: str | None = None) -> str:
    """The document's VISIBLE BODY text, with the other language removed first when asked.

    Body only, deliberately. <head> is compared nowhere because the Slovak document's title and
    description are rewritten on purpose -- an earlier version compared whole-document text and failed
    the split over its own intended +2-character title change, which is a check crying wolf about itself.
    What must not change is the CONTENT, and that is what this measures.
    """
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    # The EN/SK control is chrome, and the split rewrites it (to links) or removes it (when there is no
    # alternate). Comparing it would make the check fail on its own intended edit -- which it did, twice.
    for t in soup.find_all("span", class_="lng"):
        t.decompose()
    if keep:
        _strip_other_language(soup, keep)
    body = soup.body or soup
    return re.sub(r"\s+", " ", body.get_text(" ")).strip()


def split_one(page: pathlib.Path, mirrored: set[str] | None = None) -> bool:
    """Split ONE freshly-rendered page in place. Called by render_post.py so a new post never lands as a
    bilingual document again. Returns False (and writes nothing) if the text check fails."""
    original = page.read_text(encoding="utf-8", errors="replace")
    if 'class="sk"' not in original or 'class="en"' not in original:
        return False
    if mirrored is None:
        # what the SK tree ALREADY holds (paths relative to the real tree), plus this page. A link is
        # rewritten into the mirror only if the mirror actually has that document -- see
        # _rewrite_links_for_sk; guessing here is how a translated page ends up linking to 404s.
        existing = {p.relative_to(SK_DIR).as_posix() for p in SK_DIR.rglob("*.html")} if SK_DIR.exists() else set()
        mirrored = existing | {page.relative_to(ROOT).as_posix()}
    en_url, sk_url = urls_for(page)
    want = {"en": _text(original, "en"), "sk": _text(original, "sk")}

    built = []
    for keep in ("en", "sk"):
        soup = BeautifulSoup(original, "html.parser")
        _strip_other_language(soup, keep)
        _set_head(soup, keep, en_url, sk_url)
        _localise_head(soup, keep, sk_url if keep == "sk" else en_url)
        _toggle_to_links(soup, keep, en_url, sk_url)
        if keep == "sk":
            _rewrite_links_for_sk(soup, page, mirrored)
        html = str(soup)
        if _text(html) != want[keep]:
            print(f"  [split] {page.name} [{keep}]: text differs -- NOT written")
            return False
        built.append((page if keep == "en" else SK_DIR / page.relative_to(ROOT), html))

    for dest, html in built:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    ap.add_argument("--only", help="limit to one path substring (for trying a single page first)")
    args = ap.parse_args()

    pages = bilingual_pages()
    if args.only:
        pages = [p for p in pages if args.only in p.as_posix()]
    if not pages:
        print("no bilingual pages found -- nothing to do")
        return 0
    # TWO PASSES. Decide which pages actually get a Slovak twin BEFORE rewriting any links, because the
    # link rewriter turns internal links into /agora/sk/... only for pages the mirror will contain. A
    # single pass used every bilingual page as the mirror set, so the posts index linked to the Slovak
    # version of the one post that was never translated -- a 404 created by the fix itself.
    translatable = {p: sk_is_real(p.read_text(encoding="utf-8", errors="replace")) for p in pages}
    mirrored = {p.relative_to(ROOT).as_posix() for p, (ok, _) in translatable.items() if ok}
    skipped = [(p, why) for p, (ok, why) in translatable.items() if not ok]
    print(f"{len(pages)} bilingual page(s); {len(mirrored)} get a Slovak twin")
    for p, why in skipped:
        print(f"  no Slovak twin: {p.relative_to(ROOT).as_posix()} ({why})")
    print()

    failures, written = [], 0
    for page in pages:
        original = page.read_text(encoding="utf-8", errors="replace")
        en_url, sk_url = urls_for(page)
        want_en, want_sk = _text(original, "en"), _text(original, "sk")

        real, why = translatable[page]
        if not real:
            soup = BeautifulSoup(original, "html.parser")
            _strip_other_language(soup, "en")
            _set_head(soup, "en", en_url, sk_url)
            _localise_head(soup, "en", en_url)
            _drop_sk_alternate(soup)
            html = str(soup)
            if _text(html) != want_en:
                failures.append(f"{page.relative_to(ROOT).as_posix()} [en-only]: text differs -- NOT written")
                continue
            rel = page.relative_to(ROOT).as_posix()
            if args.dry_run:
                print(f"  would write {rel} EN-ONLY (no Slovak mirror: {why})")
            else:
                page.write_text(html, encoding="utf-8")
                written += 1
                print(f"  {rel} -> EN only, no Slovak alternate claimed ({why})")
            continue

        outputs = []
        for keep in ("en", "sk"):
            soup = BeautifulSoup(original, "html.parser")
            _strip_other_language(soup, keep)
            _set_head(soup, keep, en_url, sk_url)
            _localise_head(soup, keep, sk_url if keep == "sk" else en_url)
            _toggle_to_links(soup, keep, en_url, sk_url)
            dest = page if keep == "en" else SK_DIR / page.relative_to(ROOT)
            if keep == "sk":
                _rewrite_links_for_sk(soup, page, mirrored)
            outputs.append((keep, dest, str(soup)))

        # VERIFY BEFORE WRITING. A split that silently dropped a language would pass every other check.
        for keep, dest, html in outputs:
            got, want = _text(html), (want_en if keep == "en" else want_sk)
            if got != want:
                lost = len(want) - len(got)
                failures.append(f"{page.relative_to(ROOT).as_posix()} [{keep}]: text differs by "
                                f"{lost:+d} chars -- NOT written")
        if any(page.relative_to(ROOT).as_posix() in f for f in failures):
            continue

        for keep, dest, html in outputs:
            rel = dest.relative_to(ROOT).as_posix()
            if args.dry_run:
                print(f"  would write {rel}  ({len(html):,} bytes)")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(html, encoding="utf-8")
                written += 1
        if not args.dry_run:
            print(f"  {page.relative_to(ROOT).as_posix()} -> EN in place + sk/ mirror")

    if failures:
        print(f"\nFAILED on {len(failures)} document(s) -- nothing was written for these:")
        for f in failures:
            print("  " + f)
        return 1
    print(f"\n{'dry run, nothing written' if args.dry_run else f'{written} documents written'}; "
          f"every document's text matches its language half of the original")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
