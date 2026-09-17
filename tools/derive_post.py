#!/usr/bin/env python3
"""derive_post: derivatives of one gated article, and the check that they carry nothing new.

One gated article is the source. A Reddit post, an X thread, a LinkedIn post, the podcast
episode notes and the podcast transcript are derivatives. A derivative can only repeat what the
article already passed through the gate: every number, every link and every name in a derivative
must exist in the frozen article or in `verified_context.md`, the file that holds material from
the NotebookLM deep research after `verify-claims` passed on it.

That rule is what lets the derivatives ship without a second full gate. This file enforces it.

Usage:
    python tools/derive_post.py init <slug> [--url URL]        create the folder and freeze the sha
    python tools/derive_post.py check <slug> [FILE ...]         check derivatives (default: all)
    python tools/derive_post.py check <slug> FILE --spoken      a transcript: number words count
    python tools/derive_post.py selftest                        the control: a planted number fails

Exit code 1 on any missing item, on a changed article, or on an unverified context file.

WHAT IT CANNOT SEE. A claim with no number, no link and no name ("this is the fastest store")
passes this check. The humanizer receipt and the red-team receipt on the derivative cover that
class; this covers the class that a listener would quote.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import humanizer_receipt as hr  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "public" / "posts" / "src"
OUT = ROOT / "agora_output" / "derivatives"
SITE = "https://dancenitra.github.io/agora/public/posts"

# Links to our own pages are always allowed: a derivative links back to the article it derives from.
OWN_HOSTS = ("dancenitra.github.io", "github.com/dancenitra", "raw.githubusercontent.com/dancenitra")

# Words that are capitalised for reasons other than being a name, plus the channels and brands
# every derivative names. Lowercase, compared case-insensitively.
STOP = set("""
i a an the this that these those it its we our you your they their he she his her
monday tuesday wednesday thursday friday saturday sunday
january february march april may june july august september october november december
agora reddit spotify notebooklm gemini echoes tomorrow danchi linkedin github claude python
episode season title description chapters focus notes link links probe article post thread
tl dr tldr edit update source sources
api sql sqlite ssd dpo faq url json csv cpu gpu ram ok
""".split())

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000, "billion": 1_000_000_000}
_NUMWORD = re.compile(
    r"\b(?:(?:" + "|".join(list(_UNITS) + list(_SCALES) + ["and", "point"]) + r")[\s-]*)+\b",
    re.I,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def words_to_digits(text: str) -> str:
    """Rewrite spoken numbers as digits: 'twenty-five point five percent' -> '25.5 percent'.

    Applied to BOTH sides of the comparison, so 'three places' in the article and '3 places' in a
    derivative agree. A run that is only 'and' or 'point' is left alone.
    """

    def convert(m: re.Match) -> str:
        toks = [t for t in re.split(r"[\s-]+", m.group(0).strip()) if t]
        low = [t.lower() for t in toks]
        if not any(t in _UNITS or t in _SCALES for t in low):
            return m.group(0)
        # Trailing 'and' or 'point' belongs to the sentence, not the number.
        while low and low[-1] in ("and", "point"):
            low.pop(); toks.pop()
        head = 0
        while head < len(low) and low[head] in ("and",):
            head += 1
        low, toks = low[head:], toks[head:]
        if not low:
            return m.group(0)
        if "point" in low:
            i = low.index("point")
            whole, frac = low[:i], low[i + 1:]
            if not whole or not frac or any(t not in _UNITS for t in frac):
                return m.group(0)
            return "%d.%s" % (_value(whole), "".join(str(_UNITS[t]) for t in frac))
        return str(_value(low))

    return _NUMWORD.sub(convert, text)


def _value(low: list[str]) -> int:
    total, current = 0, 0
    for t in low:
        if t == "and":
            continue
        if t in _UNITS:
            current += _UNITS[t]
        elif t == "hundred":
            current = (current or 1) * 100
        else:
            total += (current or 1) * _SCALES[t]
            current = 0
    return total + current


_URL = re.compile(r"https?://[^\s<>()\[\]\"']+")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}(?::\d{2})?\b")
_NUM = re.compile(r"(?<![\w./-])[-+]?\d[\d,]*(?:\.\d+)?\s?%?")
_LIST_MARK = re.compile(r"^\s*(?:\d+[.)]|#+|[-*]|\|)\s*", re.M)
_CAP = re.compile(r"(?<![\w'])([A-Z][A-Za-z0-9'-]{2,})")


def _strip_urls(text: str) -> tuple[str, list[str]]:
    urls = [u.rstrip(".,;:") for u in _URL.findall(text)]
    return _URL.sub(" ", text), urls


THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


def _plain_numbers(text: str) -> str:
    """'200,050' -> '200050', so plain digits in a derivative match a source written with separators."""
    return THOUSANDS.sub("", text)


def numbers_in(text: str) -> list[str]:
    text = _DATE.sub(" ", _LIST_MARK.sub(" ", text))
    out = []
    for m in _NUM.finditer(text):
        n = m.group(0).replace(",", "").replace(" ", "")
        if n.startswith(("+", "-")):
            n = n[1:]
        out.append(n)
    return out


def names_in(text: str) -> list[str]:
    """Capitalised words that do not start a sentence, a line, a cell or a list item."""
    out = []
    for m in _CAP.finditer(text):
        raw_before = text[: m.start()]
        before = raw_before.rstrip()
        if not before or before[-1] in ".!?:|*#>-\"“(" or raw_before.endswith("\n"):
            continue
        w = m.group(1)
        if w.endswith(("'s", "’s")):
            w = w[:-2]
        w = w.rstrip("'’")
        if len(w) < 3 or w.lower() in STOP or w.isupper() and len(w) < 3:
            continue
        out.append(w)
    return out


def corpus_for(slug: str, folder: Path) -> tuple[str, list[str]]:
    """The article plus the verified research context, as one normalised string and its URLs."""
    art = SRC / f"{slug}.en.md"
    parts = [art.read_text(encoding="utf-8")]
    sk = SRC / f"{slug}.sk.md"
    if sk.exists():
        parts.append(sk.read_text(encoding="utf-8"))
    ctx = folder / "verified_context.md"
    if ctx.exists() and ctx.stat().st_size:
        if "verify" in hr.missing(str(ctx)):
            raise SystemExit(
                f"{ctx} has no verify-claims receipt for its current bytes. Run the verify-claims "
                f"skill on it, record the receipt with\n  python tools/humanizer_receipt.py record "
                f"{ctx} --skill verify --in-session\nand check again."
            )
        parts.append(ctx.read_text(encoding="utf-8"))
    text, urls = _strip_urls("\n".join(parts))
    return _plain_numbers(words_to_digits(text)).lower(), urls


def check_text(text: str, corpus: str, corpus_urls: list[str], spoken: bool = False) -> dict:
    body, urls = _strip_urls(text)
    body = _plain_numbers(words_to_digits(body))
    low = corpus
    missing_numbers = sorted({n for n in numbers_in(body) if n.lower() not in low})
    missing_links = sorted({
        u for u in urls
        if u not in corpus_urls and not any(h in u.lower() for h in OWN_HOSTS)
    })
    names = sorted({w for w in names_in(body) if w.lower() not in low})
    result = {"numbers": missing_numbers, "links": missing_links}
    if spoken:
        # Speech recognition spells names loosely; a missing name is a warning in a transcript.
        result["names_warning"] = names
    else:
        result["names"] = names
    result["ok"] = not (missing_numbers or missing_links or (not spoken and names))
    return result


TEMPLATES = {
    "reddit/README.md": "One file per target subreddit, named <subreddit>.md. Under 250 words. "
                        "The link last or absent. Never the same text in two subreddits.\n",
    "x.md": "# X thread\n\n1. \n2. \n3. \n",
    "linkedin.md": "# LinkedIn\n\n",
    "episode.md": "# Episode\n\n## Title\n\n## Description\n\n## Chapters\n\n## Focus\n\n"
                  "(the --focus string for the audio overview: what the hosts must cover, and "
                  "which numbers, all of them from the article or verified_context.md)\n",
    "verified_context.md": "",
}


def cmd_init(slug: str, url: str | None, refreeze: bool) -> int:
    art = SRC / f"{slug}.en.md"
    if not art.exists():
        print(f"no article at {art}")
        return 2
    folder = OUT / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "reddit").mkdir(exist_ok=True)
    frozen = folder / "article.sha256"
    if frozen.exists() and not refreeze:
        print(f"{frozen} exists; pass --refreeze after the article changed on purpose")
        return 2
    frozen.write_text(sha(art) + "\n", encoding="utf-8")
    meta = {"slug": slug, "article": str(art.relative_to(ROOT)),
            "url": url or f"{SITE}/{slug}.html"}
    (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    for name, body in TEMPLATES.items():
        p = folder / name
        if not p.exists():
            p.write_text(body, encoding="utf-8")
    print(f"{folder}: frozen {sha(art)[:12]}, url {meta['url']}")
    return 0


def cmd_check(slug: str, files: list[str], spoken: bool, as_json: bool) -> int:
    folder = OUT / slug
    art = SRC / f"{slug}.en.md"
    frozen = folder / "article.sha256"
    if not frozen.exists():
        print(f"{folder} is not initialised; run init first")
        return 2
    if sha(art) != frozen.read_text().strip():
        print(f"{art.name} changed since the derivatives were frozen; re-gate the article, then "
              f"init --refreeze and rewrite the derivatives")
        return 1
    corpus, urls = corpus_for(slug, folder)
    targets = [Path(f) for f in files] if files else sorted(
        p for p in folder.rglob("*.md")
        if p.name not in ("README.md", "verified_context.md")
    )
    rc, report = 0, {}
    for p in targets:
        res = check_text(p.read_text(encoding="utf-8"), corpus, urls, spoken=spoken)
        report[str(p)] = res
        if not res["ok"]:
            rc = 1
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        for p, res in report.items():
            flag = "ok  " if res["ok"] else "FAIL"
            print(f"{flag} {p}")
            for k in ("numbers", "links", "names", "names_warning"):
                if res.get(k):
                    print(f"       {k}: {', '.join(res[k])}")
    return rc


def selftest() -> int:
    """The control: a planted number must fail, a faithful derivative must pass."""
    article = ("We recovered 25.5% of names and 46.4% of locations from three implementations. "
               "Ghost Vectors (Chakraborttii et al., 2026) at https://arxiv.org/abs/2606.18497.")
    corpus_text, corpus_urls = _strip_urls(article)
    corpus = words_to_digits(corpus_text).lower()
    faithful = "They got 25.5% of names back from 3 implementations, per Chakraborttii."
    planted = "They got 31% of names back, per Chakraborttii and Smith."
    spoken = "they recovered twenty-five point five percent of names from three implementations"
    spoken_bad = "they recovered thirty one percent of names"
    cases = [
        ("faithful passes", check_text(faithful, corpus, corpus_urls)["ok"], True),
        ("planted number fails", check_text(planted, corpus, corpus_urls)["ok"], False),
        ("planted name is named",
         "Smith" in check_text(planted, corpus, corpus_urls)["names"], True),
        ("spoken faithful passes", check_text(spoken, corpus, corpus_urls, spoken=True)["ok"], True),
        ("spoken planted fails", check_text(spoken_bad, corpus, corpus_urls, spoken=True)["ok"], False),
        ("foreign link fails",
         check_text("see https://example.com/x", corpus, corpus_urls)["ok"], False),
        ("own link passes",
         check_text("see https://dancenitra.github.io/agora/public/posts/a.html", corpus,
                    corpus_urls)["ok"], True),
        ("words_to_digits", words_to_digits("one hundred and five point two"), "105.2"),
        ("words_to_digits scale", words_to_digits("twenty five thousand"), "25000"),
    ]
    bad = [(n, got, want) for n, got, want in cases if got != want]
    for n, got, want in cases:
        print(("ok   " if (n, got, want) not in bad else "FAIL ") + n + ("" if (n, got, want) not in bad else f": got {got!r}, want {want!r}"))
    return 1 if bad else 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init"); a.add_argument("slug"); a.add_argument("--url"); a.add_argument("--refreeze", action="store_true")
    c = sub.add_parser("check"); c.add_argument("slug"); c.add_argument("files", nargs="*")
    c.add_argument("--spoken", action="store_true"); c.add_argument("--json", action="store_true")
    sub.add_parser("selftest")
    ns = ap.parse_args()
    if ns.cmd == "init":
        return cmd_init(ns.slug, ns.url, ns.refreeze)
    if ns.cmd == "check":
        return cmd_check(ns.slug, ns.files, ns.spoken, ns.json)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
