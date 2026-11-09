"""Owner 11-08: bend the v32 image-left brow DOWN like his red sketch: both ends stay exactly where they were (the head
at the nose and the start of the tail), only the arch between them drops. Input: v32 image-left brow points in render
pixels (makeup/v32_left_pixels.json: u, v, s with s=0 at the head). Output: bent sample points + clip masks.
Usage: bend_left_brow.py <drop_px_at_arch> [thin]"""
import json, sys
import cv2, numpy as np
A = float(sys.argv[1]); thin = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
P = np.array(json.load(open('makeup/v32_left_pixels.json')))
u, v, s = P[:, 0], P[:, 1], P[:, 2]
bins = np.linspace(0, 1, 41); top = np.array([v[(s >= a) & (s < b)].min() if ((s >= a) & (s < b)).any() else np.nan for a, b in zip(bins[:-1], bins[1:])])
sc = (bins[:-1] + bins[1:]) / 2; ok = ~np.isnan(top)
end_line = np.interp(sc, [sc[ok][0], sc[ok][-1]], [top[ok][0], top[ok][-1]])
rise = end_line - top                                  # how far the arch sits above the line joining the two ends
sp = sc[ok][np.argmax(rise[ok])]
bump = np.clip(np.interp(s, sc[ok], rise[ok]) / max(1e-6, rise[ok].max()), 0, 1)
v2 = v + A * bump                                      # drop the arch, ends unchanged
if thin != 1.0:                                        # optional: thin toward the top edge
    t_at = np.interp(s, sc[ok], top[ok]) + A * bump; v2 = t_at + (v2 - t_at) * thin
pts = np.c_[u, v2]
mk = np.zeros((1440, 1080), np.uint8)
for x, y in pts: cv2.circle(mk, (int(round(x)), int(round(y))), 2, 255, -1)
mk = cv2.morphologyEx(mk, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
json.dump({"pts": pts.round(2).tolist(), "s": s.round(4).tolist()}, open('makeup/left_bent_samples.json', 'w'))
cv2.imwrite('makeup/left_bent_mask.png', mk)
R = cv2.imread('makeup/review/v32_0057.png')
for c in cv2.findContours(mk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]: cv2.polylines(R, [c], True, (0, 0, 255), 1)
red = cv2.imread('makeup/review/owner_red.png', 0)
cv2.imwrite('makeup/review/left_bent_on_v32.png', cv2.resize(R[440:620, 300:880], None, fx=2, fy=2))
print("arch peak s", round(float(sp), 2), "max rise px", round(float(np.nanmax(rise)), 1), "points", len(pts))
