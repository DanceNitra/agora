"""MediaPipe index groups and a Procrustes error per facial region."""
import numpy as np
from mediapipe.tasks.python.vision import FaceLandmarksConnections as C

def idx(conns):
    return sorted({i for c in conns for i in (c.start, c.end)})

TOP = {10, 338, 297, 332, 284, 251, 21, 54, 103, 67, 109}  # forehead rim, hidden by hair
REG = {
    "jaw_oval": [i for i in idx(C.FACE_LANDMARKS_FACE_OVAL) if i not in TOP],
    "brows": idx(C.FACE_LANDMARKS_LEFT_EYEBROW) + idx(C.FACE_LANDMARKS_RIGHT_EYEBROW),
    "eyes": idx(C.FACE_LANDMARKS_LEFT_EYE) + idx(C.FACE_LANDMARKS_RIGHT_EYE),
    "irises": idx(C.FACE_LANDMARKS_LEFT_IRIS) + idx(C.FACE_LANDMARKS_RIGHT_IRIS),
    "nose": idx(C.FACE_LANDMARKS_NOSE),
    "lips": idx(C.FACE_LANDMARKS_LIPS),
}
USED = sorted(set(range(478)) - TOP)  # all points except the forehead rim hidden by hair
W = np.ones(478)
for k in ("jaw_oval", "brows"):
    W[REG[k]] = 3.0  # the parts the curve tracker never measured

def align(A, B, w=None):
    """Weighted similarity transform of A onto B; returns aligned A."""
    w = np.ones(len(A)) if w is None else w
    ww = w[:, None] / w.sum()
    ma, mb = (A * ww).sum(0), (B * ww).sum(0)
    a, b = A - ma, B - mb
    u, _, vt = np.linalg.svd((a * w[:, None]).T @ b)
    R = u @ vt
    s = np.trace((a @ R).T @ (b * w[:, None])) / ((a ** 2) * w[:, None]).sum()
    return s * a @ R + mb

def report(cur, ref):
    cur, ref = np.asarray(cur)[:478], np.asarray(ref)[:478]
    a = align(cur[USED], ref[USED], W[USED])
    full = np.full_like(cur, np.nan); full[USED] = a
    out = {"all": float(np.sqrt(np.nanmean(((full - ref) ** 2).sum(1))))}
    for k, ii in REG.items():
        ii = [i for i in ii if i in set(USED)]
        out[k] = float(np.sqrt(((full[ii] - ref[ii]) ** 2).sum(1).mean()))
    return out, full
