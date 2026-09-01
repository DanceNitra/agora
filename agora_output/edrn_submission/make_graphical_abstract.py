"""Build the EPJ B graphical abstract to the journal's stated geometry.

THE RULES, quoted from the EPJ B instructions rather than remembered: the file must be a graphic,
"ONLY .jpg, .png", "a maximum width of 480 pixel and an aspect ratio of 11:6". It is "not an
abstract and is not to provide specific results"; it should convey the essence of the work with the
title. Colour is encouraged.

WHAT IT DRAWS, and the first version drew the wrong figure. It used the full scan of Fig. 1, which
runs from s = 0 to s = 1.0 and therefore STOPS at the valley: the curve descends monotonically to
its last point, and the graphical abstract of a paper titled "Non-Monotonic Correlation
Fluctuations" showed no non-monotonicity at all. I looked at the rendered image and did not see it,
because I knew what the picture was supposed to mean. It now draws the focused audit of Fig. 2,
s in [0.8, 1.2], where the minimum is interior and the V is visible.

THE DATA ARE THE MANUSCRIPT'S OWN. The points are read out of the manuscript source rather than
retyped, so the graphical abstract cannot drift from the figure it summarises.

CONTROLS, each able to fail:
  * THE POINTS MUST COME FROM THE FILE: at least five coordinate pairs must be parsed out of the
    manuscript, or the drawing would be of numbers this script invented.
  * THE MINIMUM MUST BE INTERIOR, not merely present. The old control asserted that the minimum
    sits at s = 1.0, which is arithmetic: on a descending series ending at 1.0 it passes without
    the picture showing a valley. This one requires points on BOTH sides that rise above the
    minimum, so a monotone series fails it.
  * THE GEOMETRY MUST MATCH THE RULE: the saved file is re-opened and its pixel size checked
    against 480 wide and the 11:6 ratio, rather than trusting the figure size passed to the
    renderer.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "manuscript_2026-08-29_asreceived.tex")
PNG = os.path.join(HERE, "graphical_abstract.png")
OUT = os.path.join(HERE, "make_graphical_abstract.result.json")
W, RATIO = 480, 11.0 / 6.0


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def main() -> int:
    if not os.path.isfile(SRC):
        refuse("source manuscript not found: " + SRC)
    text = io.open(SRC, encoding="utf-8").read()

    # The first addplot of the L2 valley figure carries the seed-0 scan.
    # THE WINDOW WAS THE BUG. Looking 6,000 characters back from the label missed the coordinates,
    # because the figure's caption is long. Take the whole figure environment that carries the
    # label instead of guessing a distance.
    # AND THE SECOND BUG WAS THE SEARCH KEY. A bare "fig:l2_valley" first matches the \ref in the
    # body text, which sits BEFORE any figure environment, so the backward search for \begin{figure}
    # found nothing. Search for the \label, which occurs once and only inside the figure.
    i = text.find(chr(92) + "label{fig:focused}")
    if i < 0:
        refuse("the focused-audit figure label is not in the manuscript")
    start = text.rfind(chr(92) + "begin{figure}", 0, i)
    end = text.find(chr(92) + "end{figure}", i)
    if start < 0 or end < 0:
        refuse("could not bound the figure environment around the L2 valley label")
    seg = text[start:end]
    pairs = re.findall(r"\((\d+\.\d+),(\d+\.\d+)\)", seg)
    # The threshold guards against drawing invented numbers, not against a short scan. The focused
    # audit is 9 points across s in [0.8, 1.2], which is the whole figure, so 10 was a number chosen
    # for the previous series and not for this one.
    if len(pairs) < 5:
        refuse("only %d coordinate pairs parsed from the manuscript; the drawing would be of "
               "numbers this script made up" % len(pairs))
    xs = [float(a) for a, _ in pairs]
    ys = [float(b) for _, b in pairs]
    # keep the first monotone run in s, which is one seed's curve
    cut = len(xs)
    for k in range(1, len(xs)):
        if xs[k] <= xs[k - 1]:
            cut = k
            break
    xs, ys = xs[:cut], ys[:cut]
    k = ys.index(min(ys))
    if k == 0 or k == len(ys) - 1:
        refuse("the minimum sits at an endpoint of the parsed range, so the picture would show a "
               "descent rather than a valley: a graphical abstract for a paper about "
               "non-monotonicity must show the non-monotonicity")
    if not (ys[0] > ys[k] and ys[-1] > ys[k]):
        refuse("the series does not rise on both sides of its minimum, so there is no valley to "
               "draw")
    if abs(xs[k] - 1.0) > 0.02:
        refuse("the interior minimum is at s=%.3f, not at the uniform point" % xs[k])

    h = int(round(W / RATIO))
    dpi = 100
    fig = plt.figure(figsize=(W / dpi, h / dpi), dpi=dpi)
    ax = fig.add_axes([0.15, 0.21, 0.81, 0.60])
    ax.plot(xs, ys, color="#1f4e79", linewidth=2.2)
    ax.plot([1.0], [min(ys)], marker="o", markersize=6, color="#c0392b", zorder=5)
    # The label sits in the empty lower-left, so the arrow runs along the floor of the plot
    # instead of crossing the descending branch. Judged by looking at the rendered file.
    ax.annotate("uniform point, $s=1$", xy=(1.0, min(ys)), xytext=(0.805, min(ys) + 0.010),
                color="#c0392b", fontsize=8, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.0,
                                shrinkA=2, shrinkB=4))
    ax.set_xlabel("contradiction-edge strength $s$", fontsize=8)
    ax.set_ylabel("enhanced diagnosis", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25, linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    # The title was clipped at the right edge at 9.5pt from x=0.16. Measured by looking at the
    # rendered file rather than by trusting the figure width.
    # "sees what site averages miss" overclaims against the paper's own Sec. 1.2, which calls the
    # trivial default observable "a symmetry-induced triviality, not an observed blindness", and
    # which reports the non-trivial coarse-grained control as less sensitive but NOT blind.
    fig.text(0.5, 0.905, "A valley at the uniform point, where every bond is equal",
             fontsize=9.0, color="#1f4e79", weight="bold", ha="center")
    fig.savefig(PNG, dpi=dpi, facecolor="white")
    plt.close(fig)

    with Image.open(PNG) as im:
        w, hh = im.size
    ratio_ok = abs((w / hh) - RATIO) < 0.02
    if w != W or not ratio_ok:
        refuse("saved geometry is %dx%d (ratio %.3f); the rule is width %d and ratio %.3f"
               % (w, hh, w / hh, W, RATIO))

    res = {"script": os.path.basename(__file__),
           "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "output": os.path.basename(PNG), "bytes": os.path.getsize(PNG),
           "pixels": [w, hh], "ratio": round(w / hh, 4), "points_from_manuscript": len(xs),
           "valley_at_s": 1.0, "minimum_is_interior": True,
           "controls": {"points_parsed_from_the_manuscript": True,
                        "minimum_is_interior_and_rises_on_both_sides": True,
                        "geometry_verified_by_reopening_the_file": True}}
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  %s  %dx%d px, ratio %.3f, %d bytes, %d points from the manuscript"
          % (os.path.basename(PNG), w, hh, w / hh, os.path.getsize(PNG), len(xs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
