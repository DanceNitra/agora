"""Insert a metric-matched fallback for Newsreader so the web-font swap stops shifting layout.

MEASURED CAUSE (Lighthouse 13.4.1, devtools throttling, real Chrome): CLS 0.13 on the homepage and 0.19
on the Crucible, and on every page the `layout-shifts` audit attributes the shift to "Web font loaded" --
Newsreader arriving after first paint and replacing Georgia, which is 5% wider. The counter animation,
the assumed culprit, appears in zero shift entries.

THE OVERRIDES ARE COMPUTED, NOT COPIED (research/probes/font_fallback_metrics.py): the average advance
width of both fonts over the same 107-character sample, then the vertical metrics restated in the scaled
coordinate system. The first run of that probe took Google Fonts' FIRST woff2 URL, which is a 10-glyph
unicode-range subset, and produced size-adjust 42% -- absurd on its face and caught only because the
glyph count was printed next to it. The values below come from the subset that covers all 107.

Not `font-display: optional` (removes the shift by never showing the brand font to most visitors -- a
design decision, not a fix) and not a non-blocking stylesheet (helps LCP but makes CLS WORSE, since the
font then swaps even later). A size-matched fallback is the one change that serves both.
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent

FACE = (
    '@font-face{font-family:"Newsreader-fallback";src:local("Georgia"),local("Times New Roman");'
    'size-adjust:95.18%;ascent-override:77.22%;descent-override:27.84%;line-gap-override:0%}'
)
OLD_SERIF = '--serif:"Newsreader",Georgia,"Times New Roman",serif'
NEW_SERIF = '--serif:"Newsreader","Newsreader-fallback",Georgia,"Times New Roman",serif'


def main() -> int:
    pages = [ROOT / "index.html"]
    pages += sorted((ROOT / "public").rglob("*.html"))
    if (ROOT / "sk").exists():
        pages += sorted((ROOT / "sk").rglob("*.html"))

    done, skipped = 0, 0
    for p in pages:
        s = p.read_text(encoding="utf-8", errors="replace")
        if OLD_SERIF not in s:
            skipped += 1
            continue
        if "Newsreader-fallback" in s:
            skipped += 1
            continue
        # the @font-face must precede its use; put it at the top of the first <style> block
        i = s.find("<style>")
        if i < 0:
            skipped += 1
            continue
        s = s[:i + len("<style>")] + FACE + s[i + len("<style>"):]
        s = s.replace(OLD_SERIF, NEW_SERIF)
        p.write_text(s, encoding="utf-8")
        done += 1
    print(f"{done} document(s) updated, {skipped} skipped (no Newsreader stack, or already done)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
