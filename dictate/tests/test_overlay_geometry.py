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
    m = re.search(r"\.pill\s*\{[^}]*?border-radius:\s*(\d+)px", _css(), re.S)
    assert m, "no border-radius found on .pill; the clip has nothing to agree with"
    assert int(m.group(1)) == WebViewWindow.CSS_RADIUS, (
        "the window is clipped at %d px and the pill is drawn at %s px"
        % (WebViewWindow.CSS_RADIUS, m.group(1))
    )


def test_the_accent_is_one_colour():
    css = _css()
    m = re.search(r"--accent:\s*(#[0-9a-fA-F]{6})", css)
    assert m, "no --accent token in the stylesheet"
    accent = m.group(1).lower()

    # The canvas cannot read a CSS custom property, so the meter repeats the literal. Every other
    # literal of a full-brightness colour in the file should be that same accent.
    literals = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}", css)}
    bright = {c for c in literals if int(c[1:3], 16) + int(c[3:5], 16) + int(c[5:7], 16) > 400}
    stray = bright - {accent, "#ffffff"}
    assert not stray, "colours that are neither the accent nor white: %s" % sorted(stray)


def test_the_window_is_wide_enough_for_its_contents():
    # mark 25 + gap 8 + padding 8 twice + border 2 twice leaves this much for the meter.
    width, height = WebViewWindow.LOGICAL_SIZE
    meter = width - 25 - 8 - 16 - 4
    assert meter > 40, "only %d px left for the meter at %d px wide" % (meter, width)
    assert height >= 25 + 16 + 4, "the mark and its margins do not fit in %d px" % height
