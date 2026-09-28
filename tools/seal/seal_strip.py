"""Render the inspeximus seal as a slim strip for places that take an image but not HTML.

    python tools/seal/seal_strip.py --root <64 hex> --entry 10 --date "26 Sep 2026" \
        --label "sealed reply" --out strip.png

LinkedIn comments, Threads posts and similar channels cannot carry the GitHub footer, so the seal
travels as a picture. Owner-approved layout, 2026-09-26: seal on the left, two lines on the right,
the image cropped to its content, dark background (#0a0a0b), rendered at 2x.

WHAT THIS GUARANTEES, MEASURED ON THE OUTPUT, NOT ON THE LAYOUT. Three iterations went to the owner
with visible defects: empty space on the right, a white column from a fractional-pixel crop, and a
seal 7 px low because the seal art keeps empty space above the circle (viewBox "0 -363 ..."). Each
check below would have caught one of them, and the tool refuses to write a strip that fails any:

  * every edge pixel is the background colour (no stray line),
  * the seal and the text block are each centred on the image within 2 px (at 2x),
  * the left and right margins differ by at most 2 px, and so do the top and bottom.

The seal art is the newest dark seal in DanceNitra/inspeximus docs/seal/, band replaced with the
root tail by seal_draft.replace_band, and cropped to the circle so the art is centred on itself.
"""
from __future__ import annotations

import argparse
import base64
import math
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seal_draft import SEAL_BRANCH, grouped, replace_band  # noqa: E402

REPO = os.path.join(os.path.expanduser("~"), "inspeximus-repo")
BG = (10, 10, 11)
CIRCLE_VIEWBOX = 'viewBox="10 2 2462 2462" width="246" height="246"'
FONTS = ("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600"
         "&family=JetBrains+Mono:wght@400;500&display=swap")

PAGE = """<!doctype html><meta charset=utf-8><link rel=stylesheet href="{fonts}">
<style>*{{margin:0;box-sizing:border-box}}body{{background:#0a0a0b}}
#c{{display:inline-flex;align-items:center;gap:28px;padding:28px 34px;background:#0a0a0b;color:#e9edf2;font-family:'Space Grotesk',sans-serif}}
img{{height:104px;flex:none}}.t{{font-size:30px;font-weight:600;letter-spacing:-.01em;line-height:1.1}}.t span{{color:#38f2d6;font-weight:500}}
.r{{font-family:'JetBrains Mono',monospace;font-size:19px;color:#8a909c;margin-top:12px;line-height:1.55;white-space:nowrap}}.r b{{color:#e9edf2;font-weight:500}}</style>
<div id=c><img src="data:image/svg+xml;base64,{seal}"><div><div class=t>Inspeximus <span>&middot; {label}</span></div>
<div class=r>entry <b>{entry}</b> &middot; root <b>&hellip; {tail}</b> &middot; {date}<br>certifies time and integrity, not correctness</div></div></div>"""


def newest_dark_seal() -> str:
    """The newest dark seal on the seal branch (seal_draft.SEAL_BRANCH), which main no longer carries."""
    ref = "origin/" + SEAL_BRANCH
    subprocess.run(["git", "-C", REPO, "fetch", "-q", "origin", SEAL_BRANCH], capture_output=True, check=True)
    names = subprocess.run(["git", "-C", REPO, "log", "--format=", "--name-only", ref, "--",
                            "docs/seal/"], capture_output=True, text=True, check=True).stdout.split()
    name = next(n for n in names if n.endswith("-seal-dark.svg"))
    return subprocess.run(["git", "-C", REPO, "show", ref + ":" + name],
                          capture_output=True, text=True, encoding="utf-8", check=True).stdout


def seal_art(root: str) -> str:
    svg = replace_band(newest_dark_seal(), root)
    svg, n = re.subn(r'viewBox="[^"]+" width="\d+" height="\d+"', CIRCLE_VIEWBOX, svg, count=1)
    if n != 1:
        raise SystemExit("REFUSED: the seal art has no viewBox/width/height triple to crop to the circle")
    return svg


def problems(path: str, split_x: int) -> list:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    lit = lambda x, y: sum(im.getpixel((x, y))) > 120  # noqa: E731
    out = []
    edge = [im.getpixel((x, y)) for x in (0, w - 1) for y in range(h)] + \
           [im.getpixel((x, y)) for y in (0, h - 1) for x in range(w)]
    if any(p != BG for p in edge):
        out.append("an edge pixel is not the background colour")

    def rows(x0, x1):
        ys = [y for y in range(h) if any(lit(x, y) for x in range(x0, x1, 2))]
        return ys[0], ys[-1]
    xs = [x for x in range(w) if any(lit(x, y) for y in range(0, h, 2))]
    (st, sb), (tt, tb) = rows(0, split_x), rows(split_x, w)
    mid = (h - 1) / 2
    for name, a, b in (("seal", st, sb), ("text", tt, tb)):
        if abs((a + b) / 2 - mid) > 2:
            out.append("%s is %.1f px off vertical centre" % (name, (a + b) / 2 - mid))
    if abs(xs[0] - (w - 1 - xs[-1])) > 2:
        out.append("left margin %d vs right margin %d" % (xs[0], w - 1 - xs[-1]))
    top, bottom = min(st, tt), h - 1 - max(sb, tb)
    if abs(top - bottom) > 2:
        out.append("top margin %d vs bottom margin %d" % (top, bottom))
    return out


def render(root: str, entry: str, date: str, label: str, out: str) -> None:
    from playwright.sync_api import sync_playwright
    s64 = base64.b64encode(seal_art(root).encode()).decode()
    html = PAGE.format(fonts=FONTS, seal=s64, label=label, entry=entry, tail=grouped(root), date=date)
    page = os.path.join(tempfile.mkdtemp(), "strip.html")
    with open(page, "w", encoding="utf-8") as fh:
        fh.write(html)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 1400, "height": 400}, device_scale_factor=2)
        pg.goto("file:///" + page.replace("\\", "/"))
        pg.wait_for_timeout(1500)
        box = pg.locator("#c").bounding_box()
        img = pg.locator("#c img").bounding_box()
        pg.screenshot(path=out, clip={"x": 0, "y": 0, "width": math.floor(box["width"]),
                                      "height": math.floor(box["height"])})
        b.close()
    bad = problems(out, int((img["x"] + img["width"] + 14) * 2))
    if bad:
        os.remove(out)
        raise SystemExit("REFUSED, strip not written: " + "; ".join(bad))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", required=True, help="the log root the seal was recorded under (64 hex)")
    ap.add_argument("--entry", required=True)
    ap.add_argument("--date", required=True, help='as it should read, e.g. "26 Sep 2026"')
    ap.add_argument("--label", default="sealed reply")
    ap.add_argument("--out", required=True,
                    help="the recipient sees the file name: inspeximus-<entry>-<last 12 hex of root>.png, kept in the vault at 06 Business/02_Brand/Seals with a row in its Seals register, never on the Desktop")
    a = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{64}", a.root):
        raise SystemExit("REFUSED: --root must be 64 lowercase hex characters")
    render(a.root, a.entry, a.date, a.label, a.out)
    print("wrote %s (all edge, centring and margin checks pass)" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
