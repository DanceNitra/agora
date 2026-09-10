"""The window's clip radius and the stylesheet's corner radius are one shape, described twice.

`_round_corners` clips the window to a rounded rectangle so the pill's glowing border is the
window's own silhouette rather than a rounded box sitting inside a square one. That clip uses
`WebViewWindow.CSS_RADIUS`; the page uses `border-radius` on `.pill`. If the two drift, the clip
either cuts through the border or leaves a sliver of square corner behind it, and nothing fails.

So the agreement is a test rather than a comment. The same goes for the accent: the border, the
meter bars and the embedded mark all have to be the one colour, and the colour is written in the
stylesheet in more than one place.
"""

from __future__ import annotations

import re
from pathlib import Path

from dictate.overlay import WebViewWindow

UI = Path(__file__).parent.parent / "dictate" / "ui" / "index.html"


def _css() -> str:
    return UI.read_text(encoding="utf-8")


def test_clip_radius_matches_the_stylesheet():
    # `0` carries no unit, so the pattern must not demand one.
    m = re.search(r"\.pill\s*\{[^}]*?border-radius:\s*(\d+)(?:px)?\s*;", _css(), re.S)
    assert m, "no border-radius found on .pill; the clip has nothing to agree with"
    assert int(m.group(1)) == WebViewWindow.CSS_RADIUS, (
        "the window is clipped at %d px and the pill is drawn at %s px"
        % (WebViewWindow.CSS_RADIUS, m.group(1))
    )


def test_the_accent_is_one_hue():
    """Every colour in the window is the accent's hue, a neutral, or white.

    The first version of this asked that every bright literal BE the accent, which was too blunt:
    the ring at rest is a dimmer shade of the same cyan and the check called it a stray colour.
    What matters is that the window carries one hue, not one value of it.
    """
    import colorsys

    css = _css()
    m = re.search(r"--accent:\s*(#[0-9a-fA-F]{6})", css)
    assert m, "no --accent token in the stylesheet"

    def hsv(hexstr):
        r, g, b = (int(hexstr[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return colorsys.rgb_to_hsv(r, g, b)

    accent_h = hsv(m.group(1))[0]
    stray = []
    for c in {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}", css)}:
        h, sat, val = hsv(c)
        # A near-black counts as neutral however saturated it computes: #0a0a0d is (10,10,13),
        # which is 23% saturated by the formula and black to the eye.
        if sat < 0.15 or val < 0.12:
            continue
        # hue distance on the circle
        d = min(abs(h - accent_h), 1 - abs(h - accent_h))
        if d > 0.04:                         # about 14 degrees
            stray.append((c, round(d * 360)))
    assert not stray, "colours off the accent hue: %s" % sorted(stray)


def test_the_window_is_wide_enough_for_its_contents():
    # The ring is a fixed overlay and takes no layout space, so the box is the mark, the gap and
    # 8 px of padding on each side. Nothing else.
    width, height = WebViewWindow.LOGICAL_SIZE
    meter = width - 25 - 8 - 16
    assert meter > 40, "only %d px left for the meter at %d px wide" % (meter, width)
    assert height == 25 + 16, "the mark and its margins want %d px, the window is %d" % (41, height)
