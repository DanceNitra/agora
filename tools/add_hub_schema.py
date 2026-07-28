"""Give the three credibility hub pages the structured data and social tags they never had.

track-record, forecast and research-digest carried ZERO JSON-LD and only three og tags (type, title,
description) -- no og:url, no og:site_name, no og:image, no Twitter card. They are the pages a sceptical
reader lands on to answer "can I verify any of this?", and they were the least machine-legible pages on
the site.

Every value here is READ OFF THE PAGE or verified on disk:
  * titles and descriptions from the page's own <title>/<meta description>/<h1>
  * `distribution` for track-record points at public/crucible/crucible.json, which exists and is linked
    from the page. It was NOT safe to claim before today: the ledger and the page disagreed (53 vs 54
    verdicts), and pointing a Dataset at data that contradicts its own page is worse than no Dataset.
    They agree now, so the claim is true.
  * `license` is MIT, from the repo's own LICENSE file -- checked, not assumed.
  * research-digest is a CollectionPage, NOT a Dataset: it is three prose hypotheses with falsifiers, no
    tabular or numeric variables. Forcing Dataset on it would be inaccurate markup, which is the failure
    this whole audit is about.

The SK twins get the same treatment with their own url, their own Slovak name/description taken from
their own text, and inLanguage sk -- otherwise the Slovak hub pages would carry English structured data.

Idempotent: a page that already has JSON-LD is left alone.
"""
from __future__ import annotations

import io
import json
import pathlib
import sys

from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://dancenitra.github.io/agora"
REPO = "https://github.com/DanceNitra/agora"
ORG = {"@type": "Organization", "name": "Agora", "url": f"{SITE}/"}
MIT = "https://opensource.org/licenses/MIT"

PAGES = {
    "public/track-record.html": {
        "type": "Dataset",
        "variableMeasured": ["replications reproduced", "replications failed",
                             "replications not computable", "forecasts open"],
        "distribution": {"@type": "DataDownload", "encodingFormat": "application/json",
                         "contentUrl": f"{SITE}/public/crucible/crucible.json"},
    },
    "public/forecast.html": {
        "type": "Dataset",
        "variableMeasured": ["P(reproduced)", "resolution status", "Brier score"],
        "distribution": {"@type": "DataDownload", "encodingFormat": "text/plain",
                         "contentUrl": f"{REPO}/tree/main/agora_output/forecast"},
    },
    "public/research-digest.html": {"type": "CollectionPage"},
}


def _head_text(soup: BeautifulSoup) -> tuple[str, str]:
    title = (soup.title.string or "").strip() if soup.title else ""
    m = soup.find("meta", attrs={"name": "description"})
    return title.replace(" · Agora", "").strip(), (m.get("content", "").strip() if m else "")


def _add_meta(soup: BeautifulSoup, kind: str, key: str, value: str) -> bool:
    attr = "property" if kind == "og" else "name"
    if soup.find("meta", attrs={attr: key}):
        return False
    tag = soup.new_tag("meta")
    tag[attr] = key
    tag["content"] = value
    (soup.head or soup).append(tag)
    return True


def build(path: pathlib.Path, spec: dict, url: str, lang: str) -> bool:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    if soup.find("script", type="application/ld+json"):
        return False
    name, desc = _head_text(soup)

    obj = {"@context": "https://schema.org", "@type": spec["type"], "name": name,
           "description": desc, "url": url, "inLanguage": lang,
           "creator" if spec["type"] == "Dataset" else "author": ORG,
           "isPartOf": {"@type": "WebSite", "name": "Agora", "url": f"{SITE}/"}}
    if spec["type"] == "Dataset":
        obj["license"] = MIT
        obj["variableMeasured"] = spec["variableMeasured"]
        obj["distribution"] = spec["distribution"]
    else:
        parts = [h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3"])]
        parts = [p for p in parts if 12 < len(p) < 160][:8]
        if parts:
            obj["hasPart"] = [{"@type": "CreativeWork", "name": p} for p in parts]

    script = soup.new_tag("script", type="application/ld+json")
    script.string = json.dumps(obj, ensure_ascii=False)
    (soup.head or soup).append(script)

    added = [k for k, v in (("og:url", url), ("og:site_name", "Agora"),
                            ("og:image", f"{SITE}/public/og-card.png"),
                            ("og:image:alt", "Agora — research that ships receipts"),
                            ("og:locale", "sk_SK" if lang == "sk" else "en_US"))
             if _add_meta(soup, "og", k, v)]
    added += [k for k, v in (("twitter:card", "summary_large_image"),
                             ("twitter:title", name), ("twitter:description", desc))
              if _add_meta(soup, "name", k, v)]
    path.write_text(str(soup), encoding="utf-8")
    print(f"  {path.relative_to(ROOT).as_posix():40s} +{spec['type']}  +{len(added)} meta")
    return True


def main() -> int:
    n = 0
    for rel, spec in PAGES.items():
        en = ROOT / rel
        if en.exists():
            n += build(en, spec, f"{SITE}/{rel}", "en")
        sk = ROOT / "sk" / rel
        if sk.exists():
            n += build(sk, spec, f"{SITE}/sk/{rel}", "sk")
    print(f"\n{n} document(s) given structured data" if n else "\nnothing to do (already present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
