"""Head pose at the render frame by PnP: 3D mesh landmarks (Blender metres) vs MediaPipe landmarks on the render,
with the real render camera (85 mm, 24 mm sensor across 1080 px). Writes makeup/head_pose57.json: rvec, tvec in the
camera frame (x right, y down, z forward) and the reprojection error in px."""
import json, cv2, numpy as np
C = json.load(open('makeup/ue_camera57.json'))
P3 = json.load(open('makeup/mesh_landmarks3d.json')); RL = np.array(json.load(open('makeup/render0057_landmarks.json')))
RIGID = {33, 133, 362, 263, 168, 6, 197, 195, 10, 151, 9, 8, 226, 446, 113, 342, 35, 265, 124, 353, 1, 4}
ids = [int(k) for k in P3 if int(k) in RIGID]
obj = np.array([P3[str(i)] for i in ids], np.float64); img = RL[ids].astype(np.float64)
f = C['focal'] / C['sensor'][0] * 1080.0
K = np.array([[f, 0, 540], [0, f, 720], [0, 0, 1]], np.float64)
ok, rv, tv = cv2.solvePnP(obj, img, K, None, flags=cv2.SOLVEPNP_ITERATIVE)
rv, tv = cv2.solvePnPRefineLM(obj, img, K, None, rv, tv)
proj, _ = cv2.projectPoints(obj, rv, tv, K, None)
err = np.linalg.norm(proj[:, 0] - img, axis=1)
json.dump({"rvec": rv.ravel().tolist(), "tvec": tv.ravel().tolist(), "f": f, "err_median_px": float(np.median(err)), "err_max_px": float(err.max())}, open('makeup/head_pose57.json', 'w'), indent=1)
print("reproj err px median", round(float(np.median(err)), 2), "max", round(float(err.max()), 2), "tvec", tv.ravel().round(3))
for i, e in zip(ids, err):
    if i in (33, 133, 362, 263, 168, 1, 10, 151): print(i, round(float(e), 2))
