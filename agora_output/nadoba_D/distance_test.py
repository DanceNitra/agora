"""Legibility test: what a 297 mm sheet resolves to at distance, at one arcminute per pixel."""
import math

from PIL import Image

import designs as D

names = list(D.DESIGNS)
rows = []
for metres in (10, 25):
    px = max(8, round(math.degrees(math.atan(0.297 / metres)) * 60))
    print(metres, "m:", px, "px high")
    row = []
    for n in names:
        im = Image.open(D.OUT / f"{n}_preview.png").convert("L")
        # Crop the 25 mm preview padding, so px maps to exactly the 297 mm sheet.
        p = 100
        im = im.crop((p, p, im.width - p, im.height - p))
        small = im.resize((round(px * 210 / 297), px), Image.BOX)
        row.append(small.resize((small.width * 4, small.height * 4), Image.BICUBIC))
    rows.append(row)
W = sum(i.width + 12 for i in rows[0]) + 12
H = sum(r[0].height + 12 for r in rows) + 12
s = Image.new("L", (W, H), 30)
y = 12
for r in rows:
    x = 12
    for i in r:
        s.paste(i, (x, y))
        x += i.width + 12
    y += r[0].height + 12
s.save(D.OUT / "test_vzdialenost.png")
