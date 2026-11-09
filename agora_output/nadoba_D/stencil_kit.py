"""Stencil kit: validate, preview, and export A4 paper stencils. Units are millimetres.

A design is a shapely geometry of OPENINGS (what gets sprayed). Paper is the sheet minus openings.
Geometry y grows upward from the bottom-left corner of the sheet.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union

W, H = 210.0, 297.0
SHEET = box(0, 0, W, H)
BROWN = (84, 56, 38)
SPRAY = (240, 236, 224)


def polys(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in g.geoms if p.geom_type == "Polygon"]


def rings(g):
    for p in polys(g):
        yield np.array(p.exterior.coords)
        for r in p.interiors:
            yield np.array(r.coords)


def acute_paper_tips(cuts, limit_deg=35.0):
    """Count corners where the paper wedge between two cut edges is narrower than limit_deg.

    Very short edges from flattened curves are merged first, so a curve never reads as a corner.
    """
    tips = []
    for p in polys(cuts.simplify(0.05)):
        for ring, paper_is_outside in [(p.exterior, True)] + [(r, False) for r in p.interiors]:
            pts = np.array(ring.coords)[:-1]
            n = len(pts)
            if n < 3:
                continue
            ccw = ring.is_ccw
            for i in range(n):
                a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
                u, v = a - b, c - b
                if np.linalg.norm(u) < 1.0 or np.linalg.norm(v) < 1.0:
                    continue
                ang = math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u @ v)) % 360
                # ang is measured from the previous edge to the next edge around b.
                inside_cut = (360 - ang) if ccw else ang
                paper = 360 - inside_cut
                if paper < limit_deg:
                    tips.append((round(float(b[0]), 1), round(float(b[1]), 1), round(paper, 1)))
    return tips


def check(cuts, bridge=5.0, slot=3.0, margin=10.0, px_per_mm=4):
    """Return a report dict. Every criterion reads the real geometry, and a raster check confirms it."""
    paper = SHEET.difference(cuts)
    r = {}
    r["openings"] = len(polys(cuts))
    r["paper_pieces_vector"] = len(polys(paper))
    r["cut_length_m"] = round(sum(p.length for p in polys(cuts)) / 1000, 2)
    r["sprayed_cm2"] = round(cuts.area / 100, 0)
    r["vertices_after_0.05mm"] = sum(len(x) for x in rings(cuts.simplify(0.05)))

    # Independent check: rasterise and label the paper, without shapely topology.
    a = raster(cuts, px_per_mm)
    lab, n = ndi.label(~a)
    r["paper_pieces_raster"] = int(n)

    # A neck narrower than the bridge width splits the eroded paper into pieces.
    core = paper.buffer(-bridge / 2, join_style=2)
    parts = sorted(polys(core), key=lambda p: -p.area)
    r["core_parts_at_bridge"] = len(parts)
    r["core_detached_mm2"] = [round(p.area, 1) for p in parts[1:12]]

    # Openings narrower than slot are hard to cut and clog under spray.
    opened = cuts.buffer(-slot / 2).buffer(slot / 2 + 0.02)
    thin = cuts.difference(opened)
    # A triangle tip always narrows below the limit; only a real slot leaves a large residue.
    thin_big = [p for p in polys(thin) if p.area > 12.0]
    r["thin_opening_spots"] = len(thin_big)
    r["thin_opening_mm2"] = round(sum(p.area for p in thin_big), 1)

    r["distance_to_sheet_edge_mm"] = round(
        min(cuts.bounds[0], cuts.bounds[1], W - cuts.bounds[2], H - cuts.bounds[3]), 1
    )
    tips = acute_paper_tips(cuts)
    r["sharp_paper_tips"] = len(tips)
    r["sharp_paper_tips_list"] = tips[:12]

    # Heavy paper masses joined to the rest only through narrow necks, and how many necks hold each.
    rad = 6.0
    heavy = polys(paper.buffer(-rad))
    grown = [h.buffer(rad + 0.05) for h in heavy]
    rest = paper.difference(unary_union(grown)) if grown else paper
    necks = {i: 0 for i in range(len(heavy))}
    for piece in polys(rest):
        touched = [i for i, g in enumerate(grown) if g.intersects(piece.buffer(0.1))]
        if len(touched) >= 2:
            for i in touched:
                necks[i] += 1
    frame = max(range(len(heavy)), key=lambda i: heavy[i].area) if heavy else None
    r["masses"] = [
        {"cm2": round(g.intersection(paper).area / 100, 1), "necks": necks[i]}
        for i, g in enumerate(grown)
        if i != frame
    ]
    r["ok"] = (
        r["paper_pieces_vector"] == 1
        and r["paper_pieces_raster"] == 1
        and r["core_parts_at_bridge"] == 1
        and r["thin_opening_spots"] == 0
        and r["distance_to_sheet_edge_mm"] >= margin
        and r["sharp_paper_tips"] == 0
    )
    return r


def raster(cuts, px_per_mm=8):
    """Boolean array, True where the sheet is open. Row 0 is the top of the sheet."""
    w, h = int(W * px_per_mm), int(H * px_per_mm)
    img = Image.new("1", (w, h), 0)
    d = ImageDraw.Draw(img)
    for p in polys(cuts):
        d.polygon([(x * px_per_mm, (H - y) * px_per_mm) for x, y in p.exterior.coords], fill=1)
        for hole in p.interiors:
            d.polygon([(x * px_per_mm, (H - y) * px_per_mm) for x, y in hole.coords], fill=0)
    return np.array(img, dtype=bool)


def preview(cuts, out, px_per_mm=4, seed=7):
    """Simulated spray on textured brown plastic, without the paper."""
    rng = np.random.default_rng(seed)
    pad = int(25 * px_per_mm)
    m = raster(cuts, px_per_mm).astype(np.float32)
    m = np.pad(m, pad)
    h, w = m.shape
    # Light bleed under the paper edge, plus the fine paint speckle a can leaves.
    soft = ndi.gaussian_filter(m, 0.35 * px_per_mm / 4 + 0.3)
    grain = ndi.gaussian_filter(rng.standard_normal((h, w)), 0.6)
    grain /= grain.std()
    cover = np.clip(soft * (0.965 + 0.02 * grain), 0, 1)
    tex = ndi.gaussian_filter(rng.standard_normal((h, w)), 1.2)
    tex /= tex.std()
    y, x = np.mgrid[0:h, 0:w]
    light = 1.06 - 0.20 * (y / h) - 0.22 * ((x / w - 0.5) * 2) ** 2
    base = np.array(BROWN, dtype=np.float32)[None, None] * (light + 0.022 * tex)[..., None]
    paint = np.array(SPRAY, dtype=np.float32)[None, None] * (0.97 * light + 0.04 + 0.012 * tex)[..., None]
    out_a = base * (1 - cover[..., None]) + paint * cover[..., None]
    Image.fromarray(np.clip(out_a, 0, 255).astype(np.uint8)).save(out)


def to_svg(cuts, out):
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:g}mm" height="{H:g}mm" viewBox="0 0 {W:g} {H:g}">',
        f'<rect width="{W:g}" height="{H:g}" fill="#fff"/>',
    ]
    d = []
    for ring in rings(cuts.simplify(0.05)):
        d.append("M" + " L".join(f"{x:.2f} {H - y:.2f}" for x, y in ring[:-1]) + " Z")
    lines.append(f'<path d="{" ".join(d)}" fill="#c9c9c9" fill-rule="evenodd" stroke="#000" stroke-width="0.25"/>')
    lines.append("</svg>")
    Path(out).write_text("\n".join(lines), encoding="utf-8")


def to_pdf(cuts, out, title):
    """A4 at 1:1 with a 50 mm scale bar. Grey fill means cut out, the thin line is the knife path."""
    import pymupdf

    k = 72 / 25.4
    doc = pymupdf.open()
    page = doc.new_page(width=W * k, height=H * k)
    shape = page.new_shape()
    for ring in rings(cuts.simplify(0.05)):
        shape.draw_polyline([pymupdf.Point(x * k, (H - y) * k) for x, y in ring])
    shape.finish(color=(0, 0, 0), fill=(0.8, 0.8, 0.8), width=0.25 * k, even_odd=True, closePath=True)
    shape.draw_line(pymupdf.Point(8 * k, (H - 7) * k), pymupdf.Point(58 * k, (H - 7) * k))
    shape.draw_line(pymupdf.Point(8 * k, (H - 8.5) * k), pymupdf.Point(8 * k, (H - 5.5) * k))
    shape.draw_line(pymupdf.Point(58 * k, (H - 8.5) * k), pymupdf.Point(58 * k, (H - 5.5) * k))
    shape.finish(color=(0, 0, 0), width=0.25 * k)
    shape.commit()
    page.insert_text(pymupdf.Point(60 * k, (H - 6) * k), f"50 mm = print at 100 %   |   {title}   |   grey = cut out", fontsize=6.5)
    doc.save(out)
    doc.close()
