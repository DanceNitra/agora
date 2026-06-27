"""Add a Mode-A FAQ + topic-cluster links + FAQPage JSON-LD to an already-rendered bilingual post.

The hand-built posts share one structure: a `<div class="en">…</div>` then `<div class="sk">…</div>`
then `<div class="foot">`. This injects, idempotently, an `## FAQ` + a "Related research" link list
into BOTH language divs (right before each div's closing `</div>`), appends a FAQPage object to the
page's JSON-LD `@graph`, and bumps the Article `dateModified`. FAQ Q&A must use numbers VERIFIED from
the post itself — pass them in; this tool never invents content.

Usage: feed one spec dict via add_faq(spec). Spec keys:
  slug, faq_en=[(q,a),...], faq_sk=[(q,a),...], links=[(slug,en_text,sk_text),...], date="YYYY-MM-DD"
Returns a short status string. Re-running on a post that already has FAQPage is a no-op.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "public" / "posts"
SITE = "https://dancenitra.github.io/agora/public/posts"

EN_ANCHOR = '</div>\n  <div class="sk">'
SK_ANCHOR = '</div>\n  <div class="foot">'


def _block(pairs, heading, rel_heading, links, lang):
    qa = "\n".join(f'<p><strong class="b">{q}</strong> {a}</p>' for q, a in pairs)
    li = "\n".join(f'<li><a href="{SITE}/{sl}.html">{(en if lang=="en" else sk)}</a></li>'
                   for sl, en, sk in links)
    return f'\n<h2>{heading}</h2>\n{qa}\n<h2>{rel_heading}</h2>\n<ul>\n{li}\n</ul>\n'


def add_faq(spec) -> str:
    slug = spec["slug"]
    f = POSTS / f"{slug}.html"
    if not f.exists():
        return f"{slug}: FILE MISSING"
    s = f.read_text(encoding="utf-8")
    if "FAQPage" in s:
        return f"{slug}: already has FAQ (skip)"
    if s.count(EN_ANCHOR) != 1 or s.count(SK_ANCHOR) != 1:
        return f"{slug}: NON-STANDARD structure (en={s.count(EN_ANCHOR)} sk={s.count(SK_ANCHOR)}) — handle manually"

    en = _block(spec["faq_en"], "FAQ", "Related research", spec["links"], "en")
    sk = _block(spec["faq_sk"], "FAQ", "Súvisiaci výskum", spec["links"], "sk")
    s = s.replace(EN_ANCHOR, en + EN_ANCHOR, 1)
    s = s.replace(SK_ANCHOR, sk + SK_ANCHOR, 1)

    jm = re.search(r'(<script type="application/ld\+json">)(.+?)(</script>)', s, re.S)
    if not jm:
        return f"{slug}: NO JSON-LD block — handle manually"
    g = json.loads(jm.group(2))
    g = g if isinstance(g, list) else [g]
    for o in g:
        if isinstance(o, dict) and o.get("@type") == "Article":
            o["dateModified"] = spec.get("date", "2026-06-27")
    g.append({"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": a}}
                             for q, a in spec["faq_en"]]})
    s = s[:jm.start(2)] + json.dumps(g, ensure_ascii=False) + s[jm.end(2):]
    f.write_text(s, encoding="utf-8")

    # verify
    s2 = f.read_text(encoding="utf-8")
    g2 = json.loads(re.search(r'<script type="application/ld\+json">(.+?)</script>', s2, re.S).group(1))
    faq = next((o for o in g2 if o.get("@type") == "FAQPage"), None)
    cl = len(set(re.findall(r'posts/([a-z0-9-]+)\.html', s2)) - {slug})
    return f"{slug}: OK — FAQPage {len(faq['mainEntity'])} Qs, cluster {cl}, @types {[o.get('@type') for o in g2]}"


if __name__ == "__main__":
    import sys
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    specs = spec if isinstance(spec, list) else [spec]
    # tuples arrive from JSON as lists — coerce
    for sp in specs:
        sp["faq_en"] = [tuple(x) for x in sp["faq_en"]]
        sp["faq_sk"] = [tuple(x) for x in sp["faq_sk"]]
        sp["links"] = [tuple(x) for x in sp["links"]]
        print(add_faq(sp))
