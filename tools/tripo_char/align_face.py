"""Similarity transform from the model's face render to the concept, from the two irises.

Both pictures have amber irises, the most saturated orange in the face. Their centroids give two
point pairs, which fix scale, rotation and shift exactly. Writes align.json and an overlay to check.

  uvx --from opencv-python-headless --with numpy python align_face.py <work_dir> <concept.png>
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

work, concept_path = Path(sys.argv[1]), Path(sys.argv[2])
render = cv2.imread(str(work / "face_render.png"))
concept = cv2.imread(str(concept_path))


def irises(img: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = region
    hsv = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 5) & (hsv[..., 0] <= 28) & (hsv[..., 1] > 110) & (hsv[..., 2] > 80)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, labels, stats, cents = cv2.connectedComponentsWithStats(m)
    blobs = sorted(range(1, count), key=lambda i: -stats[i, cv2.CC_STAT_AREA])[:2]
    if len(blobs) < 2:
        raise SystemExit(f"found {len(blobs)} iris blobs in {region}")
    pts = np.array([cents[i] + (x0, y0) for i in blobs])
    print("iris areas", [int(stats[i, cv2.CC_STAT_AREA]) for i in blobs], "at", pts.round(1).tolist())
    return pts[np.argsort(pts[:, 0])]   # left, right


r = irises(render, (250, 550, 800, 800))
c = irises(concept, (400, 80, 620, 175))
M, _ = cv2.estimateAffinePartial2D(r.astype(np.float32), c.astype(np.float32))
scale = float(np.hypot(M[0, 0], M[1, 0]))
print("scale", round(scale, 4), "rotation deg", round(float(np.degrees(np.arctan2(M[1, 0], M[0, 0]))), 2))
(work / "align.json").write_text(json.dumps({"render_to_concept": M.tolist(), "render_irises": r.tolist(),
                                             "concept_irises": c.tolist()}, indent=2))
warped = cv2.warpAffine(concept, cv2.invertAffineTransform(M), (render.shape[1], render.shape[0]))
cv2.imwrite(str(work / "align_overlay.png"), cv2.addWeighted(render, 0.5, warped, 0.5, 0))
print("done")
