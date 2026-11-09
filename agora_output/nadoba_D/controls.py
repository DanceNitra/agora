"""Positive controls: each fixture carries one known defect, and check() must report it."""
from shapely.geometry import Point, box

import stencil_kit as K

ring = Point(105, 148).buffer(60).difference(Point(105, 148).buffer(30))
r = K.check(ring)
assert r["paper_pieces_vector"] == 2 and r["paper_pieces_raster"] == 2 and not r["ok"], r
r = K.check(ring.difference(box(100, 170, 103, 220)))  # A single 3 mm bridge holds the centre.
assert r["paper_pieces_vector"] == 1 and r["core_parts_at_bridge"] > 1 and not r["ok"], r
r = K.check(box(60, 60, 61.5, 240))  # A 1.5 mm slot.
assert r["thin_opening_spots"] >= 1 and not r["ok"], r
r = K.check(box(3, 60, 100, 240))  # Too close to the sheet edge.
assert r["distance_to_sheet_edge_mm"] < 10 and not r["ok"], r
r = K.check(box(60, 60, 150, 240))  # A clean shape has to pass.
assert r["ok"], r
print("controls: 5 of 5 behave as expected")
