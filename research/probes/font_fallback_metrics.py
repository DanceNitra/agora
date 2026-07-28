"""Compute a metric-matched fallback for Newsreader, so the web font swap stops shifting layout.

MEASURED (Lighthouse 13.4.1, devtools throttling, real Chrome execution): CLS 0.13 on the homepage and
0.19 on the Crucible, and on every page the `layout-shifts` audit names the cause as "Web font loaded" --
the Newsreader woff2 arriving after first paint and replacing Georgia, whose metrics differ. The counter
animation, which was the assumed culprit, appears in ZERO shift entries.

Why not the two easier options:
  * `font-display: optional` removes the shift by never swapping late -- but then most visitors never see
    the brand font at all. That is a design decision, not a performance fix.
  * making the stylesheet non-render-blocking helps LCP (390-800ms of the render delay) but makes CLS
    WORSE: the font then arrives even later, so it swaps even further after layout. The two goals
    conflict unless the fallback occupies the same space.

A size-adjusted fallback resolves the conflict: Georgia is rendered at a corrected size with corrected
ascent/descent so it takes the same box as Newsreader, and the swap becomes invisible.

The numbers below are COMPUTED FROM THE FONT FILES, not copied from a generator. Formula is the standard
one: scale the fallback so its average advance width matches the web font's, then restate the vertical
metrics in the scaled coordinate system.
"""
import io
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from fontTools.ttLib import TTFont  # noqa: E402

#: the representative sample; average advance width over it is what `size-adjust` matches
SAMPLE = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "
          "the quick brown fox jumps over the lazy dog 0123456789")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def metrics(font: TTFont, label: str) -> dict:
    upem = font["head"].unitsPerEm
    hhea = font["hhea"]
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    widths = []
    for ch in SAMPLE:
        gname = cmap.get(ord(ch))
        if gname and gname in hmtx.metrics:
            widths.append(hmtx.metrics[gname][0])
    avg = sum(widths) / len(widths)
    m = {"label": label, "upem": upem, "ascent": hhea.ascent, "descent": hhea.descent,
         "lineGap": hhea.lineGap, "avg": avg, "n": len(widths)}
    print(f"  {label:22s} upem={upem:<6} asc={hhea.ascent:<6} desc={hhea.descent:<6} "
          f"gap={hhea.lineGap:<4} avg_advance={avg / upem:.4f} em  (n={len(widths)} glyphs)")
    return m


print("=== measured font metrics ===")
css_url = ("https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,300..700"
           "&display=swap")
css = urllib.request.urlopen(
    urllib.request.Request(css_url, headers={"User-Agent": UA}), timeout=30).read().decode()
import re  # noqa: E402
woff = re.findall(r"url\((https://[^)]+\.woff2)\)", css)
if not woff:
    print("  could not resolve a woff2 URL for Newsreader -- aborting rather than guessing")
    raise SystemExit(2)

# Google Fonts serves the family cut into unicode-range SUBSETS. Taking the first URL got a 10-glyph
# subset (Cyrillic/Vietnamese), so the average advance was computed over ten characters and came out at
# size-adjust 42% -- a number absurd on its face, caught only because the glyph count was printed beside
# it. Pick the subset that actually covers basic Latin, which is what the sample string is written in.
best, best_n = None, 0
for u in woff:
    try:
        f = TTFont(io.BytesIO(urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": UA}), timeout=30).read()))
    except Exception:
        continue
    cov = sum(1 for ch in SAMPLE if ord(ch) in f.getBestCmap())
    if cov > best_n:
        best, best_n = f, cov
if best is None or best_n < len(SAMPLE) * 0.9:
    print(f"  no subset covers the sample (best {best_n}/{len(SAMPLE)}) -- refusing to compute a "
          f"size-adjust from an unrepresentative glyph set")
    raise SystemExit(2)
print(f"  chose the subset covering {best_n}/{len(SAMPLE)} sample characters")
web = metrics(best, "Newsreader (web)")
fb = metrics(TTFont(r"C:\Windows\Fonts\georgia.ttf"), "Georgia (fallback)")

size_adjust = (web["avg"] / web["upem"]) / (fb["avg"] / fb["upem"])
asc = web["ascent"] / web["upem"] / size_adjust
desc = abs(web["descent"]) / web["upem"] / size_adjust
gap = web["lineGap"] / web["upem"] / size_adjust

print("\n=== computed overrides (paste into the stylesheet) ===")
print(f"""
@font-face {{
  font-family: "Newsreader-fallback";
  src: local("Georgia"), local("Times New Roman");
  size-adjust: {size_adjust * 100:.2f}%;
  ascent-override: {asc * 100:.2f}%;
  descent-override: {desc * 100:.2f}%;
  line-gap-override: {gap * 100:.2f}%;
}}""")
print(f'  --serif: "Newsreader","Newsreader-fallback",Georgia,"Times New Roman",serif;')
print(f"\n  size-adjust {size_adjust * 100:.2f}% means Georgia is drawn "
      f"{'larger' if size_adjust > 1 else 'smaller'} so its average advance matches Newsreader's.")
print("  A perfect 100% would mean the two already matched and there would be nothing to fix.")
