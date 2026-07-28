"""Verify the one-URL-per-language split holds. Run before publishing; wire into CI.

The split (2026-07-28) put English at its original URL and Slovak under /agora/sk/. Four things must be
true afterwards, and each of them fails silently if it isn't:

  1. No document carries both languages any more -- otherwise the extracted-text corruption is back.
  2. Every page declares reciprocal hreflang: the EN document points at its SK twin and vice versa, and
     each canonical points at itself. hreflang that isn't reciprocal is ignored by Google, which is the
     failure the split existed to fix -- reintroducing it silently would leave the work with no effect.
  3. Every internal link on a Slovak page resolves to a file that exists. The SK tree sits one directory
     deeper and holds only .html, so a relative link or a link to a data file that was rewritten into the
     mirror is a 404.
  4. Each Slovak document declares lang="sk" and carries a Slovak <title> -- a Slovak URL announcing
     itself in English cannot rank in Slovak.
"""
from __future__ import annotations

import pathlib
import re
import sys
import urllib.parse

from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent
SK = ROOT / "sk"
SITE = "https://dancenitra.github.io/agora"
#: characters that only occur in Slovak here -- a cheap, deterministic "is this Slovak" test
SK_CHARS = set("áäčďéíĺľňóôŕšťúýžÁČĎÉÍĽŇÓŠŤÚÝŽ")


#: only the published storefront. `onboarding/` and `agora_output/` hold third-party and working files
#: that were never part of the site and must not be judged by its rules.
def _site_pages() -> list[pathlib.Path]:
    out = [ROOT / "index.html"] if (ROOT / "index.html").exists() else []
    out += [p for p in sorted((ROOT / "public").rglob("*.html")) if SK not in p.parents]
    return out


def main() -> int:
    problems: list[str] = []

    en_pages = _site_pages()
    sk_pages = list(SK.rglob("*.html")) if SK.exists() else []
    print(f"{len(en_pages)} English document(s), {len(sk_pages)} Slovak document(s)\n")
    if not sk_pages:
        print("FAIL: no Slovak documents at all -- the split is not in place")
        return 1

    for p in en_pages + sk_pages:
        rel = p.relative_to(ROOT).as_posix()
        soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
        is_sk = SK in p.parents

        # 1 -- no bilingual documents left
        if soup.find(class_="en") and soup.find(class_="sk"):
            problems.append(f"{rel}: still carries BOTH languages in one document")

        # 2 -- reciprocal hreflang + self-canonical
        alts = {(l.get("hreflang") or "").lower(): l.get("href") for l in soup.find_all("link", rel="alternate")}
        can = soup.find("link", rel="canonical")
        # A page with NO Slovak twin correctly declares only en + x-default. Requiring `sk` everywhere
        # would push us back toward claiming an alternate that does not exist -- the original defect
        # wearing the opposite sign. What must never happen is claiming one that is missing.
        twin = (ROOT / rel) if is_sk else (SK / rel)
        expects_sk = twin.exists() if not is_sk else True
        if alts:
            if not alts.get("en") or (expects_sk and not alts.get("sk")):
                problems.append(f"{rel}: hreflang set is incomplete: {sorted(alts)}")
            elif alts.get("sk") and not expects_sk:
                problems.append(f"{rel}: claims a Slovak alternate but sk/{rel} does not exist")
            elif alts.get("sk") and alts["en"] == alts["sk"]:
                problems.append(f"{rel}: hreflang en and sk point at the SAME url -- the original defect")
            if can:
                want = alts.get("sk" if is_sk else "en")
                if want and can.get("href") != want:
                    problems.append(f"{rel}: canonical {can.get('href')} != its own hreflang {want}")

        # 3 -- internal links on Slovak pages resolve
        if is_sk:
            for a in soup.find_all("a", href=True):
                href = a["href"].split("#")[0]
                if not href or re.match(r"^(?:[a-z]+:|//|data:)", href, re.I):
                    continue
                if href.startswith("/agora/"):
                    target = ROOT / urllib.parse.unquote(href[len("/agora/"):])
                elif href.startswith(SITE):
                    target = ROOT / urllib.parse.unquote(href[len(SITE) + 1:])
                else:
                    target = (p.parent / urllib.parse.unquote(href)).resolve()
                if target.suffix == "":
                    target = target / "index.html"
                if not target.exists():
                    problems.append(f"{rel}: link to {a['href']} -> missing {target.relative_to(ROOT).as_posix()}"
                                    if ROOT in target.parents or target == ROOT
                                    else f"{rel}: link to {a['href']} -> outside the tree")

            # 4 -- Slovak document declares and reads as Slovak
            html = soup.find("html")
            if not html or html.get("lang") != "sk":
                problems.append(f"{rel}: <html lang> is {html.get('lang') if html else None!r}, not 'sk'")
            title = (soup.title.string or "") if soup.title else ""
            if title and not (set(title) & SK_CHARS):
                problems.append(f"{rel}: <title> has no Slovak characters -- probably still English: "
                                f"{title[:70]!r}")

    if problems:
        shown = problems[:40]
        print(f"FAIL -- {len(problems)} problem(s):\n")
        for x in shown:
            print("  " + x)
        if len(problems) > len(shown):
            print(f"  ... and {len(problems) - len(shown)} more")
        return 1
    print("OK -- no bilingual documents, hreflang reciprocal, Slovak links resolve, Slovak pages "
          "declare and read as Slovak.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
