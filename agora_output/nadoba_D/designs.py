"""Four stencil directions for the family letter D. Run: python designs.py [name ...]"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import stencil_kit as K

OUT = Path(__file__).parent
CAP = 2  # flat line caps


def line(pts, w):
    return LineString(pts).buffer(w / 2, cap_style=CAP, join_style=2)


def bez(p0, p1, p2, p3=None, n=28):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = map(np.array, (p0, p1, p2))
    if p3 is None:
        return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t**2 * p2
    p3 = np.array(p3)
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3


def half_ellipse(cx, cy, rx, ry, n=90):
    a = np.linspace(-math.pi / 2, math.pi / 2, n)
    return np.c_[cx + rx * np.cos(a), cy + ry * np.sin(a)]


class RomanD:
    """A high-contrast Roman D with bracketed slab serifs, thick at the bowl and thin at top and bottom."""

    def __init__(s, x_serif=15, x0=33, stem=50, xb=96, x_right=195, y0=27, y1=270, thin=25, thick=45, h=13, r=15):
        s.x_serif, s.x0, s.stem, s.xb, s.x_right, s.y0, s.y1 = x_serif, x0, stem, xb, x_right, y0, y1
        s.yc = (y0 + y1) / 2
        s.ry = (y1 - y0) / 2
        s.rx = x_right - xb
        s.sx = x0 + stem
        s.irx = x_right - thick - xb
        s.iry = s.ry - thin
        s.outer = Polygon(np.vstack([[[x0, y0]], half_ellipse(xb, s.yc, s.rx, s.ry), [[x0, y1]]]))
        s.counter = Polygon(
            np.vstack([[[s.sx, s.yc - s.iry]], half_ellipse(xb, s.yc, s.irx, s.iry), [[s.sx, s.yc + s.iry]]])
        )
        serif = []
        for yb, sign in ((y1, -1), (y0, 1)):
            serif.append(box(x_serif, min(yb, yb + sign * h), x0 + 1, max(yb, yb + sign * h)))
            br = box(x0 - r, min(yb + sign * h, yb + sign * (h + r)), x0 + 1, max(yb + sign * h, yb + sign * (h + r)))
            serif.append(br.difference(Point(x0 - r, yb + sign * (h + r)).buffer(r, quad_segs=24)))
        s.silhouette = unary_union([s.outer] + serif)
        s.letter = s.silhouette.difference(s.counter)

    def spine_bowl(s, n=140):
        """Midline of the band, around the bowl from the bottom arm to the top arm."""
        a = np.linspace(-math.pi / 2, math.pi / 2, n)
        return np.c_[s.xb + (s.rx + s.irx) / 2 * np.cos(a), s.yc + (s.ry + s.iry) / 2 * np.sin(a)]


def over(p, q, m=7.0):
    """Line through p and q, extended by m on both ends so the strip reaches the paper."""
    p, q = np.array(p, float), np.array(q, float)
    v = (q - p) / np.linalg.norm(q - p)
    return [tuple(p - v * m), tuple(q + v * m)]


# ---------------------------------------------------------------- A: Cicmany
def quad_cells(o0, o1, i0, i1, n):
    """Yield n cells (a, b, c, d) along a band quad: a, b on the outer edge and c, d on the inner edge."""
    o0, o1, i0, i1 = map(np.array, (o0, o1, i0, i1))
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        yield o0 + (o1 - o0) * t0, o0 + (o1 - o0) * t1, i0 + (i1 - i0) * t1, i0 + (i1 - i0) * t0


def cicmany():
    """Faceted D drawn with straight cuts only: diagonal crosses in the stem, a triangle band in the bowl."""
    w = 6.0
    top, bot = 269, 28
    th = 41
    yc = 148.5
    O = [(84, top), (128, top), (194, 204), (194, 2 * yc - 204), (128, bot), (84, bot)]
    I = [(84, top - th), (113, top - th), (153, 188), (153, 2 * yc - 188), (113, bot + th), (84, bot + th)]
    out = Polygon([(15, top)] + O[1:5] + [(15, bot), (15, bot + 15), (35, bot + 15), (35, top - 15), (15, top - 15)])
    letter = out.difference(Polygon(I))

    lat = []
    x0, x1 = 35, 84
    ys = np.linspace(bot + 15, top - 15, 5)
    for a, b in zip(ys[:-1], ys[1:]):
        lat += [line(over((x0, a), (x1, b), 0.5), w), line(over((x0, b), (x1, a), 0.5), w)]
    for y in ys:
        lat.append(line([(8, y), (x1 + 2, y)], w))
    lat.append(line([(x1, bot - 8), (x1, top + 8)], w))

    # Bowl: paired nodes on the outer and inner edge from the axis up. A rail and a diagonal per step give
    # a triangle band; the lower half is the mirror image, which is the axial symmetry of the wall ornament.
    # Only two strips meet at any node, so the strips never bite a wide notch out of the letter's edge.
    zig = [(194, yc), (153, 188), (161, 236.5), (113, top - th), (98, top)]
    for flip in (False, True):
        f = (lambda p: (p[0], 2 * yc - p[1])) if flip else (lambda p: p)
        for a, b in zip(zig[:-1], zig[1:]):
            strip = line(over(f(a), f(b)), w)
            # This strip runs almost along the inner edge, so it must stop at the inner corner.
            lat.append(strip.intersection(box(113, 0, 300, 297)) if b == (113, top - th) else strip)
    cuts = letter.difference(unary_union(lat))

    cx, cy = 117, yc
    motif = []
    for ang in (45, 135, 225, 315):
        r = Polygon([(8.5, 0), (20, 8), (33, 0), (20, -8)])
        motif.append(affinity.translate(affinity.rotate(r, ang, origin=(0, 0)), cx, cy))
    return unary_union([cuts] + motif)


# ---------------------------------------------------------------- B: Vruborez
def drop(c, ang, r0, r1, half):
    """A chip-carved drop on one radius: narrow at the hub, full at the outer end."""
    pts = [tuple(p) for p in bez((r0, 0), (r0 + (r1 - r0) * 0.55, half * 1.05), (r1 - 1.5, half * 0.95), (r1, 0), n=26)]
    pts += [tuple(p) for p in bez((r1, 0), (r1 - 1.5, -half * 0.95), (r0 + (r1 - r0) * 0.55, -half * 1.05), (r0, 0), n=26)[1:]]
    return affinity.translate(affinity.rotate(Polygon(pts), ang, origin=(0, 0)), *c)


def vruborez():
    """Chip-carved D: stem of six-drop rosettes with white corners, bowl of interlocked triangles."""
    d = RomanD(thin=30, thick=46)
    w = 5.6
    x0, x1 = d.x0, d.sx
    y0, y1 = d.y0, d.y1
    parts = []
    cells = np.linspace(y0 + 13, y1 - 13, 4)
    ground = d.silhouette.intersection(box(0, 0, x1, 297))
    rail = line([(x1, y0 - 8), (x1, y1 + 8)], w)
    lat = [rail]
    for y in cells:
        lat.append(line([(x0 - 22, y), (x1 + 3, y)], w))
    cx = (x0 + x1) / 2
    for a, b in zip(cells[:-1], cells[1:]):
        cy = (a + b) / 2
        lat.append(Point(cx, cy).buffer(27.5, quad_segs=48))
        lat.append(line([(cx, a - 2), (cx, b + 2)], w))
        lat.append(line([(x0 - 3, cy), (x1 + 3, cy)], w))
        for k in range(6):
            parts.append(drop((cx, cy), 90 + 60 * k, 7.0, 24.5, 6.0))
    stem_open = ground.difference(unary_union(lat))

    band = d.letter.difference(box(0, 0, x1, 297))
    a = np.linspace(-math.pi / 2, math.pi / 2, 300)
    outer = np.c_[d.xb + (d.rx + 6) * np.cos(a), d.yc + (d.ry + 6) * np.sin(a)]
    inner = np.c_[d.xb + (d.irx - 6) * np.cos(a), d.yc + (d.iry - 6) * np.sin(a)]
    outer = np.vstack([[[x1 - 1, y0 - 6]], outer, [[x1 - 1, y1 + 6]]])
    inner = np.vstack([[[x1 - 1, d.yc - d.iry + 6]], inner, [[x1 - 1, d.yc + d.iry - 6]]])
    lo, li = LineString(outer), LineString(inner)
    n = 16
    zig = [(lo if k % 2 == 0 else li).interpolate(k / n, normalized=True).coords[0] for k in range(n + 1)]
    bowl_open = band.difference(unary_union([line([p, q], w) for p, q in zip(zig[:-1], zig[1:])] + [rail]))
    # The two slivers beside the rail add nothing and are the hardest cuts on the sheet, so they stay paper.
    bowl_open = unary_union([p for p in K.polys(bowl_open) if p.area >= 120])
    return unary_union([stem_open, bowl_open] + parts)


# ---------------------------------------------------------------- C: Klas, srdce a tulipan
def heart(cx, cy, s):
    """Folk heart: full shoulders and a soft point. cy is the height of the cleft."""
    right = np.vstack([
        bez((cx, cy - s * 0.1), (cx + s * 0.18, cy + s * 0.42), (cx + s * 0.78, cy + s * 0.34), (cx + s * 0.74, cy - s * 0.18), n=30),
        bez((cx + s * 0.74, cy - s * 0.18), (cx + s * 0.70, cy - s * 0.58), (cx + s * 0.22, cy - s * 0.82), (cx, cy - s * 1.08), n=30)[1:],
    ])
    left = right[::-1].copy()
    left[:, 0] = 2 * cx - left[:, 0]
    return Polygon(np.vstack([right, left[1:]]))


def klas():
    """Crisp Roman silhouette cut into grain cells by a spine and curved veins. Heart and tulip in the counter."""
    d = RomanD()
    w = 5.6
    lat = []

    def veins(path, n, hw, start=0.62, end=0.0, clip=None):
        ls = LineString(path)
        lat.append(ls.buffer(w / 2, cap_style=CAP, join_style=1))
        spacing = ls.length / (n + start + end)
        for k in range(n):
            s = spacing * (start + k)
            p = np.array(ls.interpolate(s).coords[0])
            q = np.array(ls.interpolate(min(s + 1, ls.length)).coords[0])
            t = (q - p) / max(np.linalg.norm(q - p), 1e-6)
            nrm = np.array([-t[1], t[0]])
            for side in (-1, 1):
                reach = hw(p) + 9
                tip = p + side * nrm * reach + t * reach * 0.95
                ctrl = p + side * nrm * reach * 0.62 + t * reach * 0.2
                strip = line(bez(p, ctrl, tip, n=14), w)
                lat.append(strip.intersection(clip) if clip is not None else strip)

    cx0 = d.x0 + d.stem / 2
    # Stem veins stop at the rail, so they never bite into the arms of the bowl.
    veins([(cx0, d.y0 - 8), (cx0, d.y1 + 8)], 8, lambda p: d.stem / 2, start=0.72, clip=box(0, 0, d.sx, 297))
    # The spine runs only where the band is thick. Each thin arm is a single row of slanted cells.
    path = d.spine_bowl()
    keep = np.abs(path[:, 1] - d.yc) < 0.885 * (d.ry + d.iry) / 2
    thick = lambda p: 12 + 11 * max(0.0, (p[0] - d.xb) / d.rx) ** 0.8
    # The last vein stays clear of the cross cut at the top end of the spine.
    veins(path[keep], 8, thick, start=0.72, end=1.25)
    lat.append(line([(d.sx, d.y0 - 8), (d.sx, d.y1 + 8)], w))
    xend = path[keep][0, 0]
    for x in (d.sx + 22, xend):
        lat.append(line([(x - 7, d.y1 + 4), (x + 7, d.y1 - 32)], w))
        lat.append(line([(x - 7, d.y0 + 32), (x + 7, d.y0 - 4)], w))
    cuts = d.letter.difference(unary_union(lat))

    # Heart, leaves, and tulip, then scaled together about the centre of the counter.
    cx = 112
    t = [heart(cx, 104, 17)]
    cup = 168
    t.append(Polygon(np.vstack([bez((cx, cup), (cx + 14.5, cup + 15), (cx, cup + 45)), bez((cx, cup + 45), (cx - 14.5, cup + 15), (cx, cup))[1:]])))
    for s in (-1, 1):
        t.append(Polygon(np.vstack([
            bez((cx + s * 8, cup - 3), (cx + s * 22, cup + 1), (cx + s * 24, cup + 35)),
            bez((cx + s * 24, cup + 35), (cx + s * 15.5, cup + 25), (cx + s * 11.5, cup + 7))[1:],
        ])))
        t.append(Polygon(np.vstack([
            bez((cx + s * 5.5, 118), (cx + s * 24, 124), (cx + s * 22, 160)),
            bez((cx + s * 22, 160), (cx + s * 9.5, 146), (cx + s * 5.5, 118))[1:],
        ])))
    t.append(box(cx - 2, 121, cx + 2, cup - 11))
    flower = affinity.scale(unary_union(t), 1.14, 1.14, origin=(cx, 148.5))
    return unary_union([cuts, flower])


# ---------------------------------------------------------------- D: Slnko
def slnko():
    """Reversed: the D stays unpainted, in a white sun of petals. The gaps between petals hold the letter."""
    a, b = 93, 135
    c = (105, 148.5)
    # No serifs here: rays grazing a serif leave slivers that are hard to cut.
    d = RomanD(x_serif=47, x0=47, stem=42, xb=100, x_right=168, y0=148.5 - 92, y1=148.5 + 92, thin=20, thick=36, h=0.01, r=0.01)
    m = 30
    w = 6.0
    pts = []
    for k in range(m * 24):
        th = 2 * math.pi * k / (m * 24)
        scal = 5.5 * abs(math.sin(m / 2 * th))
        pts.append((c[0] + (a - 5.5 + scal) * math.cos(th), c[1] + (b - 5.5 + scal) * math.sin(th)))
    oval = Polygon(pts)
    field = oval.difference(d.silhouette)
    rays = []
    for k in range(m):
        th = 2 * math.pi * k / m
        p = (c[0] + 40 * math.cos(th), c[1] + 70 * math.sin(th))
        q = (c[0] + 115 * math.cos(th), c[1] + 165 * math.sin(th))
        rays.append(line([p, q], w))
    field = field.difference(unary_union(rays).difference(d.silhouette))
    return unary_union([field, d.counter])


DESIGNS = {"A_cicmany": cicmany, "B_vruborez": vruborez, "C_klas": klas, "D_slnko": slnko}


def build(name):
    cuts = DESIGNS[name]().buffer(0)
    # Remove burrs under 2 mm from the boolean operations, and keep the true corners sharp.
    cuts = cuts.buffer(-1.0, join_style=2).buffer(1.0, join_style=2)
    # Nobody cuts a shape under 12 mm2.
    return unary_union([p for p in K.polys(cuts) if p.area >= 12])


def contact_sheet(names, out, h=900):
    ims = [Image.open(OUT / f"{n}_preview.png").convert("RGB") for n in names]
    ims = [i.resize((int(i.width * h / i.height), h), Image.LANCZOS) for i in ims]
    sheet = Image.new("RGB", (sum(i.width for i in ims) + 20 * (len(ims) + 1), h + 40), (22, 22, 22))
    x = 20
    for im in ims:
        sheet.paste(im, (x, 20))
        x += im.width + 20
    sheet.save(out)


if __name__ == "__main__":
    only = sys.argv[1:] or list(DESIGNS)
    keys = ["ok", "openings", "cut_length_m", "paper_pieces_vector", "paper_pieces_raster", "core_parts_at_bridge",
            "core_detached_mm2", "thin_opening_spots", "sharp_paper_tips", "distance_to_sheet_edge_mm", "sprayed_cm2", "masses"]
    for name in only:
        cuts = build(name)
        r = K.check(cuts)
        K.preview(cuts, OUT / f"{name}_preview.png")
        K.to_svg(cuts, OUT / f"{name}.svg")
        K.to_pdf(cuts, OUT / f"{name}.pdf", name)
        print(name, json.dumps({k: r[k] for k in keys}, ensure_ascii=False))
    contact_sheet(list(DESIGNS), OUT / "porovnanie.png")
