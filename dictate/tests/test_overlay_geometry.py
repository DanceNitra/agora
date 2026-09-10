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


def test_the_window_carries_two_named_hues_and_no_others():
    """Every colour is the accent, the working colour, a neutral, or white.

    This began as "one hue" and the window now has two on purpose: cyan says the microphone is
    open, orange says the model is running, and the owner asked for them to be told apart at a
    glance. Widening the rule is the honest move; deleting it would not be. A third hue still
    fails, which is what the check is for.

    The first version asked that every bright literal BE the accent, which called the ring's own
    dimmer shade a stray colour. Hue is the thing that matters, not value.
    """
    import colorsys

    css = _css()
    tokens = {}
    for name in ("accent", "work"):
        m = re.search(r"--%s:\s*(#[0-9a-fA-F]{6})" % name, css)
        assert m, "no --%s token in the stylesheet" % name
        tokens[name] = m.group(1)

    def hsv(hexstr):
        r, g, b = (int(hexstr[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return colorsys.rgb_to_hsv(r, g, b)

    allowed = [hsv(v)[0] for v in tokens.values()]
    stray = []
    for c in {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}", css)}:
        h, sat, val = hsv(c)
        # A near-black counts as neutral however saturated it computes: #0a0a0d is (10,10,13),
        # which is 23% saturated by the formula and black to the eye.
        if sat < 0.15 or val < 0.12:
            continue
        d = min(min(abs(h - a), 1 - abs(h - a)) for a in allowed)
        if d > 0.04:                         # about 14 degrees from either
            stray.append((c, round(d * 360)))
    assert not stray, "colours off both named hues: %s" % sorted(stray)


def test_the_window_is_wide_enough_for_its_contents():
    # The ring is a fixed overlay and takes no layout space, so the box is the mark, the gap and
    # 8 px of padding on each side. Nothing else.
    width, height = WebViewWindow.LOGICAL_SIZE
    meter = width - 25 - 8 - 16
    assert meter > 40, "only %d px left for the meter at %d px wide" % (meter, width)
    assert height == 25 + 16, "the mark and its margins want %d px, the window is %d" % (41, height)
