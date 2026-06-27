"""Weave hand-chosen in-content contextual links into an already-rendered bilingual post.

This does NOT choose anchors — a human picks each (en_anchor, sk_anchor, target_slug) by reading the
prose, so links are genuine and semantically matched. The tool only APPLIES them safely: it refuses
unless the anchor phrase occurs exactly once and is not already inside a link, then wraps it in an
<a href=…> to the target post. Idempotent per anchor (skips if already linked). Keeps the existing
"Related research" list intact — contextual links are additive.

Spec JSON: [{"slug": "...", "links": [["en anchor phrase", "sk anchor phrase", "target-slug"], ...]}]
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "public" / "posts"
SITE = "https://dancenitra.github.io/agora/public/posts"


def apply(spec) -> str:
    slug = spec["slug"]
    f = POSTS / f"{slug}.html"
    if not f.exists():
        return f"{slug}: FILE MISSING"
    s = f.read_text(encoding="utf-8")
    notes = []
    for en_a, sk_a, target in spec["links"]:
        url = f"{SITE}/{target}.html"
        for lang, anchor in (("en", en_a), ("sk", sk_a)):
            if f">{anchor}</a>" in s:
                notes.append(f"{lang}:already-linked"); continue
            n = s.count(anchor)
            if n != 1:
                notes.append(f"{lang}:ANCHOR_NOT_UNIQUE({n}) {anchor[:30]!r}"); continue
            # guard: anchor must not span an existing tag
            if "<" in anchor or ">" in anchor:
                notes.append(f"{lang}:ANCHOR_HAS_TAG"); continue
            s = s.replace(anchor, f'<a href="{url}">{anchor}</a>', 1)
            notes.append(f"{lang}->{target[:24]}")
    f.write_text(s, encoding="utf-8")
    # integrity: div balance in the article body
    en0 = s.find('<div class="en"'); ft = s.find('<div class="foot"')
    body = s[en0:ft] if 0 <= en0 < ft else s
    bal = "DIV-OK" if body.count("<div") == body.count("</div") else "DIV-IMBALANCE!"
    # all anchors resolve
    dead = [sl for sl in set(re.findall(r'posts/([a-z0-9-]+)\.html', s))
            if sl != slug and not (POSTS / f"{sl}.html").exists()]
    return f"{slug}: {bal}{' DEAD:'+','.join(dead) if dead else ''} | " + " ; ".join(notes)


if __name__ == "__main__":
    import sys
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for sp in (spec if isinstance(spec, list) else [spec]):
        print(apply(sp))
