"""Build a target face mesh: the current MetaHuman face warped smoothly in the frontal orthographic plane so
its MediaPipe landmarks land on the p6 landmarks. Usage: python warp_build.py <capture.png> <cam.json>
<alpha> <smooth>. Writes face_target_v.bin and warp_report.json."""
import json, sys
import numpy as np
import cv2
import mp_lm
from mp_regions import USED, REG
from warp_lib import ACTOR, N_HEAD, load_mesh, project, front_vertex, similarity, tps_fit, tps_eval

cap, camf, alpha, smooth = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
cam = json.load(open(camf))
V = load_mesh()                       # local coordinates, cm; face looks toward +Y
img = cv2.imread(cap)
H, W = img.shape[:2]
uv, depth = project(V[:N_HEAD] + ACTOR, cam["loc"], cam["rot"], cam["fov"], W, H)
mh2d = mp_lm.detect(cap)
ref2d = np.array(json.load(open("mp_ref_512x768.json")))
use = np.array(USED)
if len(sys.argv) > 5 and sys.argv[5] == "reliable":  # contour points only; inner cheek points are guesses
    keep = sorted({i for k in ("jaw_oval", "brows", "eyes", "irises", "nose", "lips") for i in REG[k]})
    use = np.array([i for i in USED if i in set(keep)])
vid = front_vertex(uv, depth, mh2d[use])
src = V[vid][:, [0, 2]]               # orthographic frontal plane (X, Z)
refp = ref2d[use] * np.array([1.0, -1.0])  # image y down -> Z up
s, R, t = similarity(refp, src)
dst = s * refp @ R + t                 # reference landmarks in MetaHuman centimetres
err0 = np.sqrt(((dst - src) ** 2).sum(1))
model = tps_fit(src, src + alpha * (dst - src), smooth)
disp = tps_eval(model, V[:, [0, 2]]) - 0.0
# weight: full on the front of the head, fading to zero behind the ears (depth Y)
y = V[:, 1]
w = np.clip((y - (-1.0)) / 6.0, 0.0, 1.0)
w = w * w * (3 - 2 * w)
# and fading with distance from the measured landmarks, so the scalp, ears and neck stay put
from scipy.spatial import cKDTree
dmin = cKDTree(src).query(V[:, [0, 2]])[0]
g = np.clip(1 - (dmin - 1.0) / 3.0, 0.0, 1.0)
w = w * g * g * (3 - 2 * g)
T = V.copy()
T[:N_HEAD, 0] += w[:N_HEAD] * disp[:N_HEAD, 0]
T[:N_HEAD, 2] += w[:N_HEAD] * disp[:N_HEAD, 1]
# eyes and teeth move rigidly with the warp at their centre
for a, b in ((24049, 28295), (28955, 29725), (29725, 30495)):
    c = V[a:b][:, [0, 2]].mean(0, keepdims=True)
    d = tps_eval(model, c)[0]
    T[a:b, 0] += d[0]
    T[a:b, 2] += d[1]
T.astype("<f4").tofile("face_target_v.bin")
per = {k: float(np.sqrt((err0[np.isin(use, ii)] ** 2).mean())) for k, ii in REG.items()}
rep = {"scale_px_per_cm": float(1 / s), "rms_cm": float(np.sqrt((err0 ** 2).mean())),
       "per_region_cm": per, "max_vertex_move_cm": float(np.abs(T - V).max())}
json.dump(rep, open("warp_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1))
# overlay: current landmarks (red) and targets (green) in the capture
for i, j in zip(range(len(use)), use):
    p0 = uv[vid[i]]
    cv2.circle(img, (int(p0[0]), int(p0[1])), 2, (0, 0, 255), -1)
Vt = T[:N_HEAD] + ACTOR
uvt, _ = project(Vt, cam["loc"], cam["rot"], cam["fov"], W, H)
for i in range(len(use)):
    p1 = uvt[vid[i]]
    cv2.circle(img, (int(p1[0]), int(p1[1])), 2, (0, 255, 0), -1)
cv2.imwrite("warp_overlay.png", img[250:1000, 300:1000])
