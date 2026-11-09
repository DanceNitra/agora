"""Paint looks onto a MetaHuman albedo (UV space) and write a contact sheet of face crops.
Usage: python preview.py <albedo.png> <out_sheet.png> [look_id ...]   (no ids = all base looks)"""
import sys
import cv2
import numpy as np
from agora_makeup import library, paint, zones

alb = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR)
alb = cv2.resize(alb, (2048, 2048), interpolation=cv2.INTER_AREA)
face = zones.Face(2048)
looks = library.base_looks()
ids = sys.argv[3:]
if ids:
    allv = {l["id"]: l for l in looks}
    looks = [allv[i] if i in allv else next(v for v in library.generate() if v["id"] == i) for i in ids]
tiles = []
for lk in looks:
    bc, _, _ = paint.paint(alb, None, lk, face, gain={})
    c = paint.face_crop(bc, face)
    c = cv2.resize(c, (360, int(360 * c.shape[0] / c.shape[1])))
    cv2.putText(c, lk["name"][:26], (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    tiles.append(c)
    print("painted", lk["id"])
h = max(t.shape[0] for t in tiles)
tiles = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 0, cv2.BORDER_CONSTANT) for t in tiles]
cols = 6
while len(tiles) % cols:
    tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(sys.argv[2], np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]))
