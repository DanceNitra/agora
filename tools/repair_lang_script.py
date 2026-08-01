#!/usr/bin/env python3
"""One-off repair: strip the language-switching JS from documents that are already single-language.

WHY THIS EXISTS AND WHY IT IS NOT PART OF THE PIPELINE. split_languages.py now removes this script when
it writes a document, but `bilingual_pages()` only finds pages containing BOTH class="en" and
class="sk". Once a page has been split it no longer qualifies, so every document split before the fix
is a terminal artifact the pipeline will never touch again. 44 Slovak mirrors were in that state.

WHAT THE SCRIPT DID. It ends with `localStorage.getItem('agora-lang'); if(s) setLang(s)`, which
overwrites the document's own data-lang with whatever the visitor last clicked ANYWHERE on the site.
On a combined page that was the feature. On a split page the content exists in one language only,
wrapped in spans of that language, so forcing the other one hides ALL of it: header, a date, and
nothing else. Anyone who had ever clicked EN saw every Slovak page blank from then on -- and the
reverse held too, so one click on SK blanked every English page.

It is invisible to a fresh browser and to a headless screenshot, because both start with no stored
preference. It took the owner switching language on a real page to surface it.

SAFETY RULE. A page that still carries BOTH languages needs its toggle, so it is skipped. Only
documents that are already single-language are repaired, and the progress-bar code that sits before
the language block in the same script is preserved.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CUT = "var root=document.documentElement"
SCRIPT_RE = re.compile(r"(<script(?![^>]*\bsrc=)[^>]*>)(.*?)(</script>)", re.S)


def repair(path: pathlib.Path) -> bool:
    html = path.read_text(encoding="utf-8", errors="ignore")
    if 'class="en"' in html and 'class="sk"' in html:
        return False                      # still bilingual: the toggle is real, leave it alone
    if "agora-lang" not in html:
        return False

    def _fix(m):
        head, body, tail = m.groups()
        if "agora-lang" not in body:
            return m.group(0)
        # Two shapes exist. The post template mixes the scroll-progress bar and the language block into
        # one script, so that one is cut at the language marker and the progress bar survives. The
        # deep-dive renderer emits a minified IIFE that does nothing BUT switch language, and names its
        # variable `r` rather than `root`, so a cut inside it would leave broken syntax -- that one is
        # removed whole. A marker that only matched the first shape left two pages unrepaired and
        # reported success, which is the same defect this whole repair exists to undo.
        if "getElementById('prog')" in body or 'getElementById("prog")' in body:
            i = body.find(CUT)
            return head + body[:i].rstrip() + "\n" + tail if i != -1 else m.group(0)
        return ""

    out = SCRIPT_RE.sub(_fix, html)
    if out == html:
        return False
    path.write_text(out, encoding="utf-8")
    return True


def main() -> int:
    targets = sorted(set(ROOT.glob("public/**/*.html")) | set(ROOT.glob("sk/**/*.html")))
    fixed = [p for p in targets if repair(p)]
    still = [p for p in targets if "agora-lang" in p.read_text(encoding="utf-8", errors="ignore")
             and not ('class="en"' in p.read_text(encoding="utf-8", errors="ignore")
                      and 'class="sk"' in p.read_text(encoding="utf-8", errors="ignore"))]
    print("scanned %d documents" % len(targets))
    print("repaired %d" % len(fixed))
    print("single-language documents still carrying the script: %d" % len(still))
    for p in still[:5]:
        print("   !", p.relative_to(ROOT))
    return 1 if still else 0


if __name__ == "__main__":
    sys.exit(main())
