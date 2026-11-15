"""Per frame, both halves of a side-by-side clip (left the source performer, right Yuki): the MediaPipe blendshapes.
Prints per channel the correlation over time and the amplitude ratio (std right / std left), and group means for the
upper face (brows, eyes, cheeks, nose) and the mouth and jaw. A lag search (+-6 frames) reports the best shift."""
import sys, numpy as np, cv2, mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision
MODEL = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL), num_faces=1, output_face_blendshapes=True))
UP = ["browInnerUp", "browDownLeft", "browDownRight", "browOuterUpLeft", "browOuterUpRight", "eyeBlinkLeft", "eyeBlinkRight",
      "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft", "eyeWideRight", "cheekSquintLeft", "cheekSquintRight", "noseSneerLeft", "noseSneerRight"]
LO = ["jawOpen", "mouthFunnel", "mouthPucker", "mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight",
      "mouthFrownLeft", "mouthFrownRight", "mouthUpperUpLeft", "mouthUpperUpRight", "mouthLowerDownLeft", "mouthLowerDownRight",
      "mouthPressLeft", "mouthPressRight", "mouthRollLower", "mouthRollUpper"]
cap = cv2.VideoCapture(sys.argv[1])
L, R = [], []
while True:
    ok, fr = cap.read()
    if not ok:
        break
    rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
    w = rgb.shape[1] // 2
    for half, acc in ((rgb[:, :w].copy(), L), (rgb[:, w:].copy(), R)):
        r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=half))
        if r.face_blendshapes:
            bs = {c.category_name: c.score for c in r.face_blendshapes[0]}
            acc.append([bs[k] for k in UP + LO])
        else:
            acc.append([np.nan] * len(UP + LO))
L, R = np.array(L), np.array(R)
ok = ~np.isnan(L).any(1) & ~np.isnan(R).any(1)
print("frames", len(L), "with both faces", int(ok.sum()))
def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1]) if a.std() > 1e-4 and b.std() > 1e-4 else float("nan")
best = []
for lag in range(-6, 7):
    i0, i1 = max(0, lag), len(L) + min(0, lag)
    m = ok[i0:i1] & ok[i0 - lag:i1 - lag]
    cs = [corr(L[i0 - lag:i1 - lag][m][:, k], R[i0:i1][m][:, k]) for k in range(len(UP + LO))]
    best.append((np.nanmean(cs), lag))
lag = max(best)[1]
i0, i1 = max(0, lag), len(L) + min(0, lag)
m = ok[i0:i1] & ok[i0 - lag:i1 - lag]
A, B = L[i0 - lag:i1 - lag][m], R[i0:i1][m]
print("best lag (frames, Yuki after source)", lag)
rows = []
for k, nm in enumerate(UP + LO):
    c = corr(A[:, k], B[:, k]); amp = B[:, k].std() / max(A[:, k].std(), 1e-6)
    rows.append((nm, c, amp, A[:, k].std()))
    print(f"{nm:20s} corr {c:+.2f}  amp Yuki/source {amp:4.2f}  source std {A[:, k].std():.3f}")
for nm, sel in (("UPPER FACE", UP), ("MOUTH + JAW", LO)):
    rr = [r for r in rows if r[0] in sel and r[3] > 0.02]
    print(f"{nm}: channels that move in the source {len(rr)}, mean corr {np.nanmean([r[1] for r in rr]):+.2f}, mean amp {np.nanmean([r[2] for r in rr]):.2f}")
