"""The sitemap is a claim about what the site serves. Assert it against the site, both directions.

The deploy already checks that every sitemap URL EXISTS in the artifact. That is not the same as the
site being navigable, and the difference is what a crawler experiences. Measured 2026-08-23 by
crawling from the homepage instead of from the sitemap:

  * 8 live pages were reachable and NOT declared in the sitemap -- integrity, ai-claims, audit,
    self-audit, aiaudit, langgraph-gdpr-erasure and two Slovak mirrors. The sitemap is the one
    artifact whose whole job is to list them.
  * 1 declared page, /public/compare/, was reachable from no link on the site at all.
  * 31 internal links omitted a directory's trailing slash. GitHub Pages answers both forms with 200
    and NO redirect, so each was a second live URL for the same page -- and on that second form every
    relative href resolves one directory too high, which is where the site's four real 404s came from.

On a host Googlebot last fetched on 2026-07-30, a wasted crawl is the most expensive kind there is.

CONTROLS. `--self-test` plants each defect into a synthetic site and requires the matching row to
fail. A reachability check that cannot fail would certify a broken site, which is how the first
version of this measurement reported "2 orphans" -- it crawled only sitemap URLs, so every edge
through an undeclared page was invisible, and both "orphans" were reachable.
"""
import argparse
import collections
import concurrent.futures as cf
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://dancenitra.github.io/agora/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; agora-selfaudit/1.0)"}
SKIP = (".json", ".xml", ".py", ".csv", ".zip", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".txt", ".pdf")

rows = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))
    return bool(ok)


def norm(u):
    u = u.split("#")[0].split("?")[0]
    return u[:-len("index.html")] if u.endswith("index.html") else u


def fetch(u, get_html=True):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30)
        return r.getcode(), (r.read().decode("utf-8", "replace") if get_html else "")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return None, ""


def hrefs(html):
    return [h for h in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\']', html, re.I)
            if not h.startswith(("#", "mailto:", "data:", "javascript:"))]


def crawl(base, fetch_fn):
    """Follow links from the homepage. Deliberately NOT restricted to the sitemap."""
    seen, graph, depth = set(), {}, {base: 0}
    frontier = [base]
    while frontier:
        todo = [u for u in frontier if u not in seen]
        seen.update(todo)
        with cf.ThreadPoolExecutor(16) as ex:
            got = list(ex.map(lambda u: (u, fetch_fn(u)), todo))
        nxt = []
        for u, (code, html) in got:
            outs = set()
            if code == 200:
                for h in hrefs(html):
                    full = norm(urllib.parse.urljoin(u, h))
                    if full.startswith(base) and not full.lower().endswith(SKIP):
                        outs.add(full)
            graph[u] = (code, outs)
            for d in outs:
                if d not in depth:
                    depth[d] = depth[u] + 1
                    nxt.append(d)
        frontier = nxt
    return graph, depth


def run(base, sitemap_xml, fetch_fn, min_pages=10):
    rows.clear()
    declared = {norm(x) for x in re.findall(r"<loc>([^<]+)</loc>", sitemap_xml)}
    graph, depth = crawl(base, fetch_fn)
    reached = {u for u, (c, _) in graph.items() if c == 200}

    # min_pages is a parameter, not a constant: the synthetic fixtures in --self-test are three
    # pages, and a guard calibrated for the live site would fail them for the wrong reason.
    ck(len(declared) >= min_pages, "the sitemap parsed", f"{len(declared)} urls")
    ck(len(reached) >= min_pages, "the crawl reached more than a handful", f"{len(reached)} pages")

    unreachable = sorted(declared - set(depth))
    ck(not unreachable, "every DECLARED page is reachable by following links",
       ", ".join(u.replace(base, "/") for u in unreachable[:6]))

    # A page that points its canonical somewhere else has DISAVOWED itself, and a sitemap must not
    # submit a URL the page argues against -- /public/inspeximus/ canonicalises cross-site to the
    # product's own Pages site and is excluded from the generator for exactly that reason. So the rule
    # is the property, not a name: undeclared is a defect only where the page claims itself.
    def self_canonical(u):
        _, html = fetch_fn(u)
        m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*>', html, re.I)
        if not m:
            return True                     # no opinion -> it should be declared
        h = re.search(r'href=["\']([^"\']+)["\']', m.group(0))
        return not h or norm(h.group(1)).rstrip("/") == u.rstrip("/")

    cand = [u for u in reached if u not in declared and u.rstrip("/") + "/" not in declared]
    undeclared = sorted(u for u in cand if self_canonical(u))
    disavowed = sorted(set(cand) - set(undeclared))
    ck(not undeclared, "every REACHABLE page that claims itself is declared in the sitemap",
       ", ".join(u.replace(base, "/") for u in undeclared[:6]))
    if disavowed:
        rows.append((True, "reachable but self-disavowed, correctly undeclared",
                     ", ".join(u.replace(base, "/") for u in disavowed[:4])))

    dead = sorted(u for u, (c, _) in graph.items() if c not in (200, None))
    ck(not dead, "no internal link points at a non-200",
       ", ".join(u.replace(base, "/") for u in dead[:6]))

    # a directory URL served without a redirect at BOTH forms is a duplicate, and breaks relatives
    dirs = {u for u in reached if u.endswith("/") and u != base}
    noslash = sorted(u for u in dirs if u.rstrip("/") in reached)
    ck(not noslash, "no directory is live at both the slash and slash-less form",
       ", ".join(u.replace(base, "/") for u in noslash[:6]))
    return all(ok for ok, _, _ in rows)


def self_test():
    """Plant each defect into a synthetic site; the matching row must go red."""
    print("== controls: each planted defect must redden its own row ==")

    def site(pages):
        def f(u, get_html=True):
            return pages.get(u, (404, ""))
        return f

    B = "https://x/"
    good_pages = {
        B: (200, '<a href="a/">A</a><a href="b/">B</a>'),
        B + "a/": (200, '<a href="../b/">B</a>'),
        B + "b/": (200, '<a href="../a/">A</a>'),
    }
    good_map = "".join(f"<loc>{B}{p}</loc>" for p in ("", "a/", "b/"))

    def check(label, pages, xml, expect):
        run(B, xml, site(pages), min_pages=2)
        hit = [(o, l) for o, l, _ in rows if expect in l]
        good = bool(hit) and not hit[0][0]
        print(f"  {'OK  ' if good else 'FAIL'}  {label}")
        return good

    ok = True
    ok &= check("a declared page nothing links to", good_pages,
                good_map + f"<loc>{B}orphan/</loc>", "every DECLARED page is reachable")
    ok &= check("a reachable page the sitemap omits", good_pages,
                f"<loc>{B}</loc><loc>{B}a/</loc>", "that claims itself is declared")
    ok &= check("an internal link to a 404",
                {**good_pages, B: (200, '<a href="a/">A</a><a href="b/">B</a><a href="gone/">X</a>')},
                good_map, "no internal link points at a non-200")
    # the slash-less form must be LINKED, or the crawl never reaches it and the row cannot fire --
    # which is the same blindness that made the first orphan count wrong.
    ok &= check("a directory live at both forms",
                {**good_pages,
                 B: (200, '<a href="a/">A</a><a href="b/">B</a><a href="a">A no slash</a>'),
                 B + "a": (200, "")},
                good_map, "no directory is live at both")

    # the new behaviour needs its own control in BOTH directions: a page that points its canonical
    # elsewhere must NOT be reported, and one that claims itself must.
    disavow = {**good_pages,
               B: (200, '<a href="a/">A</a><a href="b/">B</a><a href="elsewhere/">E</a>'),
               B + "elsewhere/": (200, '<link rel="canonical" href="https://other/">')}
    run(B, good_map, site(disavow), min_pages=2)
    row = [(o, l) for o, l, _ in rows if "that claims itself is declared" in l]
    quiet = bool(row) and row[0][0]
    print(f"  {'OK  ' if quiet else 'FAIL'}  a self-disavowed page is NOT reported as undeclared")
    ok &= quiet

    claims = {**good_pages,
              B: (200, '<a href="a/">A</a><a href="b/">B</a><a href="mine/">M</a>'),
              B + "mine/": (200, f'<link rel="canonical" href="{B}mine/">')}
    run(B, good_map, site(claims), min_pages=2)
    row = [(o, l) for o, l, _ in rows if "that claims itself is declared" in l]
    fires = bool(row) and not row[0][0]
    print(f"  {'OK  ' if fires else 'FAIL'}  a self-claiming undeclared page IS reported")
    ok &= fires

    run(B, good_map, site(good_pages), min_pages=2)
    clean = all(o for o, _, _ in rows)
    print(f"  {'OK  ' if clean else 'FAIL'}  the clean synthetic site passes every row")
    return ok and clean


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        good = self_test()
        print("\n  CONTROLS " + ("GREEN" if good else "RED"))
        return 0 if good else 1

    code, xml = fetch(BASE + "sitemap.xml")
    if code != 200:
        print(f"REFUSED: sitemap.xml returned {code} -- a check that cannot see its target reports SAFE")
        return 2
    run(BASE, xml, fetch)
    print("== the sitemap and the site must agree, both directions ==")
    for ok, label, detail in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}{('   [' + detail + ']') if detail else ''}")
    bad = sum(1 for o, _, _ in rows if not o)
    print(f"\n  {len(rows)} checks, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
