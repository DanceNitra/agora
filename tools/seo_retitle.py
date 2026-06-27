"""Safely retitle already-rendered posts for SEO (keyword-first) WITHOUT changing the slug/URL.
Updates every place the title appears in the HTML (<title>, og:title, twitter:title, the <h1> en/sk
spans, and the JSON-LD headline) plus the posts.json manifest. Handles both the HTML-escaped form
(title/og/h1) and the raw form (JSON-LD headline). Idempotent. Only the few genuinely-weak titles
are listed — strong/keyword/result titles are intentionally left (churning indexed good titles hurts)."""
import json
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "public" / "posts"

# slug -> (old_en, new_en, old_sk, new_sk)
RETITLES = {
    "memory-poison-resistance-measured": (
        "Memory that won't let an uncorroborated fact become permanent — measured",
        "When should AI memory trust a new fact? Corroboration, measured",
        "Pamäť, ktorá nedovolí, aby sa nepodložený fakt stal trvalým — odmerané",
        "Kedy má AI pamäť dôverovať novému faktu? Corroboration, odmerané"),
    "multihop-recall-model-in-the-loop": (
        "Putting the model in the retrieval loop: an honest multi-hop recall result on LoCoMo",
        "Multi-hop recall on LoCoMo: put the model in the retrieval loop",
        "Model v slučke vyhľadávania: čestný výsledok multi-hop recall na LoCoMo",
        "Multi-hop recall na LoCoMo: daj model do vyhľadávacej slučky"),
}


def run():
    manifest = json.loads((POSTS / "posts.json").read_text(encoding="utf-8"))
    changed = 0
    for slug, (oen, nen, osk, nsk) in RETITLES.items():
        f = POSTS / f"{slug}.html"
        if not f.exists():
            print(f"  {slug}: FILE MISSING"); continue
        s = f.read_text(encoding="utf-8")
        before = s
        # cover every encoding the title can appear in: HTML-escaped (title/og/h1), raw, and the
        # JSON-LD headline (json.dumps with ensure_ascii=True escapes — as —). Replaces of
        # absent strings are no-ops, so this is safely idempotent / re-runnable.
        for old, new in ((oen, nen), (osk, nsk)):
            s = s.replace(html.escape(old), html.escape(new))     # <title>, og, twitter, h1 span
            s = s.replace(old, new)                               # raw (any unescaped occurrence)
        # JSON-LD headline: parse + patch the Article object (robust to ascii-escaping of —/quotes)
        jm = re.search(r'(<script type="application/ld\+json">)(.+?)(</script>)', s, re.S)
        if jm:
            try:
                data = json.loads(jm.group(2))
                graph = data if isinstance(data, list) else [data]
                touched = False
                for o in graph:
                    if isinstance(o, dict) and o.get("@type") == "Article" and o.get("headline") != nen:
                        o["headline"] = nen; touched = True   # set to new title regardless of old encoding
                if touched:
                    s = s[:jm.start(2)] + json.dumps(graph, ensure_ascii=False) + s[jm.end(2):]
            except Exception as e:
                print(f"  {slug}: jsonld parse skip ({type(e).__name__})")
        if s != before:
            f.write_text(s, encoding="utf-8")
            for x in manifest:
                if x["slug"] == slug:
                    x["title"], x["title_sk"] = nen, nsk
            changed += 1
            print(f"  {slug}: retitled -> {nen!r}")
        else:
            print(f"  {slug}: no change (old title not found?)")
    (POSTS / "posts.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{changed} posts retitled")


if __name__ == "__main__":
    run()
