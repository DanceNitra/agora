"""Measure the printable PDFs themselves: page size, the scale bar, and the grey area against the geometry."""
import numpy as np
import pymupdf

import designs as D
import stencil_kit as K

PX = 8
for n in D.DESIGNS:
    doc = pymupdf.open(D.OUT / f"{n}.pdf")
    p = doc[0]
    z = PX * 25.4 / 72
    pix = p.get_pixmap(matrix=pymupdf.Matrix(z, z), colorspace=pymupdf.csGRAY, alpha=False)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
    # The caption starts at x = 60 mm on the same row, so the bar is read only to its left.
    dark = np.where(a[int((297 - 7) * PX), :int(59.5 * PX)] < 128)[0]
    # The fill counts together with its knife line. The caption strip at the bottom is excluded.
    grey = a < 240
    grey[int((297 - 11) * PX):, :] = False
    t = K.raster(D.build(n), PX)
    h, w = min(grey.shape[0], t.shape[0]), min(grey.shape[1], t.shape[1])
    g, t = grey[:h, :w], t[:h, :w]
    print(
        n,
        f"page {p.rect.width * 25.4 / 72:.1f} x {p.rect.height * 25.4 / 72:.1f} mm,",
        f"bar {(dark.max() - dark.min()) / PX:.2f} mm,",
        f"grey vs geometry IoU {(g & t).sum() / (g | t).sum():.3f},",
        f"pages {len(doc)}",
    )
