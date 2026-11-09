"""Print a stencil at 1:1 from the manual feed tray, as raw PostScript, with no driver scaling.

Usage: python print_ps.py B_vruborez          writes and verifies the .ps file
       python print_ps.py B_vruborez --send   also sends one copy to the printer
"""
import re
import sys

import numpy as np
from shapely.geometry import Polygon

import designs as D
import stencil_kit as K

PRINTER = "KONICA MINOLTA C360SeriesPS"
k = 72 / 25.4


def to_ps(cuts, title):
    out = [
        "%!PS-Adobe-3.0",
        f"%%Title: {title}",
        "%%Pages: 1",
        f"%%BoundingBox: 0 0 {K.W * k:.0f} {K.H * k:.0f}",
        "%%EndComments",
        f"mark {{<< /PageSize [{K.W * k:.3f} {K.H * k:.3f}] /ManualFeed true /Duplex false >> setpagedevice}} stopped cleartomark",
        "%%Page: 1 1",
        "/m {moveto} bind def /l {lineto} bind def /c {closepath} bind def",
        "newpath",
    ]
    for ring in K.rings(cuts.simplify(0.05)):
        pts = [f"{x * k:.3f} {y * k:.3f}" for x, y in ring[:-1]]
        out.append(pts[0] + " m " + " ".join(p + " l" for p in pts[1:]) + " c")
    out += ["gsave 0.8 setgray eofill grestore", f"0 setgray {0.25 * k:.3f} setlinewidth stroke"]
    # Scale bar and caption, the same as in the PDF.
    y, a, b = 7 * k, 8 * k, 58 * k
    out += [
        f"newpath {a:.3f} {y:.3f} m {b:.3f} {y:.3f} l {a:.3f} {y - 1.5 * k:.3f} m {a:.3f} {y + 1.5 * k:.3f} l",
        f"{b:.3f} {y - 1.5 * k:.3f} m {b:.3f} {y + 1.5 * k:.3f} l stroke",
        f"/Helvetica findfont 6.5 scalefont setfont {60 * k:.3f} {6 * k:.3f} moveto",
        f"(50 mm = print at 100 %   |   {title}   |   grey = cut out) show",
        "showpage",
        "%%EOF",
        "",
    ]
    return "\n".join(out)


def verify(ps, cuts):
    """Read the rings back from the PostScript text and compare them with the design."""
    rings = []
    for row in ps.splitlines():
        if row.endswith(" c") and " m " in row:
            nums = [float(v) for v in re.findall(r"-?\d+\.\d+", row)]
            rings.append(np.array(nums).reshape(-1, 2) / k)
    a = np.zeros((int(K.H * 8), int(K.W * 8)), dtype=bool)
    from PIL import Image, ImageDraw

    for r in rings:
        im = Image.new("1", (a.shape[1], a.shape[0]), 0)
        ImageDraw.Draw(im).polygon([(x * 8, (K.H - y) * 8) for x, y in r], fill=1)
        a ^= np.array(im, dtype=bool)  # XOR is the even-odd rule, the same as eofill.
    t = K.raster(cuts, 8)
    h, w = min(a.shape[0], t.shape[0]), min(a.shape[1], t.shape[1])
    iou = (a[:h, :w] & t[:h, :w]).sum() / (a[:h, :w] | t[:h, :w]).sum()
    xs = np.vstack(rings)
    return len(rings), float(iou), (xs[:, 0].min(), xs[:, 1].min(), xs[:, 0].max(), xs[:, 1].max())


if __name__ == "__main__":
    name = sys.argv[1]
    cuts = D.build(name)
    report = K.check(cuts)
    ps = to_ps(cuts, name)
    path = D.OUT / f"{name}.ps"
    path.write_text(ps, encoding="ascii")
    n, iou, bbox = verify(ps, cuts)
    print(f"{name}: check ok={report['ok']}, rings {n}, IoU {iou:.4f}, bbox mm {[round(v, 1) for v in bbox]}, {len(ps)} bytes")
    if not report["ok"] or iou < 0.995:
        sys.exit("refused: the PostScript does not match the design")
    if "--send" in sys.argv:
        import win32print

        h = win32print.OpenPrinter(PRINTER)
        try:
            job = win32print.StartDocPrinter(h, 1, (f"Sablona {name}", None, "RAW"))
            win32print.StartPagePrinter(h)
            win32print.WritePrinter(h, ps.encode("ascii"))
            win32print.EndPagePrinter(h)
            win32print.EndDocPrinter(h)
            print(f"sent: job {job} to {PRINTER}, 1 copy, manual feed")
        finally:
            win32print.ClosePrinter(h)
