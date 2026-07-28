"""Backfill the Mode-B SEO upgrade onto already-rendered posts that predate the template change:
inject hreflang (en/sk/x-default) after the canonical link, and merge an Organization object into
the page's JSON-LD (turning a lone Article object into an [Article, Organization] array). Idempotent
— skips a post that already has both. FAQ schema is NOT backfilled (old bodies aren't re-parsed here;
new/re-rendered posts get FAQPage from the template). Run once; re-runnable safely."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "public" / "posts"
ORG = {"@context": "https://schema.org", "@type": "Organization", "name": "Agora",
       "url": "https://dancenitra.github.io/agora/",
       "sameAs": ["https://github.com/DanceNitra/agora",
                  "https://huggingface.co/Danchi17",
                  "https://github.com/DanceNitra/ramr"]}


def backfill(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    orig = s
    changed = []

    # 1) hreflang — insert after the canonical link if not already present
    if "hreflang=" not in s:
        cm = re.search(r'<link rel="canonical" href="([^"]+)">', s)
        if cm:
            href = cm.group(1)
            tags = (f'\n<link rel="alternate" hreflang="en" href="{href}">'
                    f'\n<link rel="alternate" hreflang="sk" href="{href}">'
                    f'\n<link rel="alternate" hreflang="x-default" href="{href}">')
            s = s.replace(cm.group(0), cm.group(0) + tags, 1)
            changed.append("hreflang")

    # 2) Organization — merge into the JSON-LD block (check TOP-LEVEL @type, not substring: the
    # Article's nested author is also an Organization, which a substring test would false-match).
    jm = re.search(r'(<script type="application/ld\+json">)(.+?)(</script>)', s, re.S)
    if not jm and "</head>" in s:
        # hand-built page with no JSON-LD at all → inject an Article + Organization block derived
        # from <title>/<meta description>/canonical.
        tm = re.search(r"<title>(.*?)</title>", s, re.S)
        dm = re.search(r'<meta name="description" content="([^"]*)"', s)
        cm2 = re.search(r'<link rel="canonical" href="([^"]+)">', s)
        # Strip the site suffix from the headline. The separator is written as the HTML ENTITY
        # `&middot;` in these templates, so a class matching only the literal '·' stripped nothing and
        # the Article headline shipped as the raw <title> including " &middot; Agora" -- which is exactly
        # what Google says a headline must not be. Handle the entity forms too.
        raw = tm.group(1).strip() if tm else "Agora"
        title = re.sub(r"\s*(?:[·|]|&middot;|&#183;|&#xB7;)\s*Agora\s*$", "", raw, flags=re.I).strip()
        art = {"@context": "https://schema.org", "@type": "Article", "headline": title,
               "description": (dm.group(1) if dm else ""),
               "author": {"@type": "Organization", "name": "Agora"},
               "publisher": {"@type": "Organization", "name": "Agora"},
               "inLanguage": ["en", "sk"]}
        if cm2:
            art["url"] = cm2.group(1)
        block = '<script type="application/ld+json">' + json.dumps([art, ORG], ensure_ascii=False) + "</script>\n"
        s = s.replace("</head>", block + "</head>", 1)
        changed.append("jsonld-injected")
    elif jm:
        try:
            data = json.loads(jm.group(2))
            graph = data if isinstance(data, list) else [data]
            if not any(isinstance(o, dict) and o.get("@type") == "Organization" for o in graph):
                graph.append(ORG)
                s = s[:jm.start(2)] + json.dumps(graph, ensure_ascii=False) + s[jm.end(2):]
                changed.append("organization")
        except Exception as e:
            changed.append(f"jsonld-skip({type(e).__name__})")

    if s != orig:
        path.write_text(s, encoding="utf-8")
    return ",".join(changed) if changed else "ok (already has both)"


if __name__ == "__main__":
    files = sorted(p for p in POSTS.glob("*.html") if p.name != "index.html")
    n_changed = 0
    for p in files:
        r = backfill(p)
        if r != "ok (already has both)":
            n_changed += 1
        print(f"  {p.name[:55]:<57} {r}")
    print(f"\n{n_changed}/{len(files)} posts updated")
