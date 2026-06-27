"""Add a missing Slovak body to a bilingual post that was published EN-body-only.

Some early posts have <div class="sk"> containing only the (later-added) FAQ, and their <h1> / TL;DR
"sk" spans still hold the English text. This tool, given a delimited SK file, (1) replaces the h1 sk
span, (2) replaces the TL;DR sk span, and (3) inserts the SK body paragraphs into the sk div before
the FAQ. The English source spans are located automatically. NFC-normalized; idempotent-ish (refuses
if the sk body already has prose). Run AFTER confirming the post is missing its SK body.

SK file format (one post):
  ===H1===
  <slovak h1 text>
  ===TLDR===
  <slovak tldr excerpt>
  ===BODY===
  <slovak body html: <p>...</p>, <ul>...</ul>, with <strong class="b">/<em>/<a> as needed>
"""
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "public" / "posts"


def _nfc(x):
    return unicodedata.normalize("NFC", x)


def run(slug, sk_path):
    f = POSTS / f"{slug}.html"
    s = _nfc(f.read_text(encoding="utf-8"))
    raw = _nfc(Path(sk_path).read_text(encoding="utf-8"))
    parts = {}
    for sec in ("H1", "TLDR", "BODY"):
        m = re.search(rf"==={sec}===\n(.*?)(?=\n===|\Z)", raw, re.S)
        parts[sec] = m.group(1).strip() if m else ""

    notes = []
    # 1) h1 sk span
    h1en = re.search(r'<h1><span class="en">(.*?)</span>', s, re.S)
    if h1en and parts["H1"]:
        target = f'<span class="sk">{h1en.group(1)}</span>'
        if s.count(target) == 1:
            s = s.replace(target, f'<span class="sk">{parts["H1"]}</span>', 1); notes.append("h1")
        else:
            notes.append(f"h1-SKIP(count={s.count(target)})")
    # 2) tldr sk span
    tl = re.search(r'<div class="tldr">.*?<p><span class="en">(.*?)</span>', s, re.S)
    if tl and parts["TLDR"]:
        target = f'<span class="sk">{tl.group(1)}</span>'
        if s.count(target) == 1:
            s = s.replace(target, f'<span class="sk">{parts["TLDR"]}</span>', 1); notes.append("tldr")
        else:
            notes.append(f"tldr-SKIP(count={s.count(target)})")
    # 3) sk body before FAQ
    i = s.find('<div class="sk">')
    faq = s.find("<h2>FAQ</h2>", i)
    between = re.sub(r"<[^>]+>", "", s[i + len('<div class="sk">'):faq]).strip()
    if len(between) > 120:
        notes.append("body-SKIP(already has prose)")
    elif parts["BODY"]:
        s = s[:faq] + parts["BODY"] + "\n" + s[faq:]
        notes.append("body")

    f.write_text(s, encoding="utf-8")
    # integrity
    en0 = s.find('<div class="en"'); ft = s.find('<div class="foot"')
    body = s[en0:ft] if 0 <= en0 < ft else s
    bal = "DIV-OK" if body.count("<div") == body.count("</div") else "DIV-IMBALANCE!"
    skdiv = s[s.find('<div class="sk">'):ft]
    skpre = skdiv[:skdiv.find("<h2>FAQ")]
    leftover = len(re.findall(r'<span class="en">(.*?)</span><span class="sk">\1</span>', s))
    return (f"{slug}: {' '.join(notes)} | {bal} | sk-body <p>={skpre.count('<p>')} "
            f"| EN==SK spans left={leftover}")


if __name__ == "__main__":
    print(run(sys.argv[1], sys.argv[2]))
