"""Finds the best continuous window of a singing video for a MetaHuman Animator mono solve. Per sampled frame
(10 fps): face found, head yaw and pitch (MediaPipe transformation matrix), face size (inner eye distance / frame
width), shot cut (grey frame difference), and the 52 blendshapes. A window qualifies when every frame has a face,
|yaw| < 25, |pitch| < 25, no cut, and the face is at least MIN_IOD of the width. Its score is the expression energy:
mean upper-face activity (brows, eye squint and wide, cheek squint, nose sneer) plus the mean per-channel spread of
all mouth, jaw and upper-face channels. Prints the best windows per video, with a progress line every 600 samples."""
import sys, json, time, numpy as np, cv2, mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision
MODEL = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"
WIN, STEP_S, MIN_IOD = float(sys.argv[2]), 0.1, float(sys.argv[3])
UPPER = ["browInnerUp", "browDownLeft", "browDownRight", "browOuterUpLeft", "browOuterUpRight", "eyeSquintLeft",
         "eyeSquintRight", "eyeWideLeft", "eyeWideRight", "cheekSquintLeft", "cheekSquintRight", "noseSneerLeft", "noseSneerRight"]
LOWER = ["jawOpen", "mouthFunnel", "mouthPucker", "mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight",
         "mouthFrownLeft", "mouthFrownRight", "mouthUpperUpLeft", "mouthUpperUpRight", "mouthLowerDownLeft", "mouthLowerDownRight"]
out = {}
for path in sys.argv[4:]:
    det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL), running_mode=vision.RunningMode.VIDEO, num_faces=1,
        output_face_blendshapes=True, output_facial_transformation_matrixes=True))
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    every = max(1, int(round(fps * STEP_S)))
    rows, prev, fi, t0 = [], None, 0, time.time()
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if fi % every == 0:
            H, W = fr.shape[:2]
            g = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (64, 36)).astype(float)
            cut = prev is not None and np.abs(g - prev).mean() > 28
            prev = g
            r = det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)), int(fi / fps * 1000))
            if r.face_landmarks:
                lm = r.face_landmarks[0]
                iod = np.hypot((lm[133].x - lm[362].x) * W, (lm[133].y - lm[362].y) * H) / W
                M = np.array(r.facial_transformation_matrixes[0])[:3, :3]
                yaw = np.degrees(np.arctan2(-M[2, 0], np.hypot(M[0, 0], M[1, 0])))
                pitch = np.degrees(np.arctan2(M[2, 1], M[2, 2]))
                bs = {c.category_name: c.score for c in r.face_blendshapes[0]}
                rows.append([fi / fps, 1, yaw, pitch, iod, cut] + [bs[k] for k in UPPER + LOWER])
            else:
                rows.append([fi / fps, 0, 0, 0, 0, cut] + [0] * (len(UPPER) + len(LOWER)))
            if len(rows) % 600 == 0:
                print(f"  {path.split('/')[-1]} t={fi / fps:.0f}s samples={len(rows)} {time.time() - t0:.0f}s", flush=True)
        fi += 1
    A = np.array(rows, float)
    n = int(WIN / STEP_S)
    nu = len(UPPER)
    good = (A[:, 1] == 1) & (np.abs(A[:, 2]) < 25) & (np.abs(A[:, 3]) < 25) & (A[:, 4] >= MIN_IOD) & (A[:, 5] == 0)
    best = []
    for s in range(0, len(A) - n, 5):
        if not good[s:s + n].all():
            continue
        B = A[s:s + n, 6:]
        score = B[:, :nu].sum(1).mean() + B.std(0).mean() * 5
        best.append((score, A[s, 0], A[s:s + n, 4].mean(), np.abs(A[s:s + n, 2]).mean(), B[:, :nu].sum(1).mean(), B[:, nu:].std(0).mean()))
    best.sort(reverse=True)
    picks = []
    for b in best:
        if all(abs(b[1] - p[1]) > WIN for p in picks):
            picks.append(b)
        if len(picks) == 3:
            break
    print(path.split("/")[-1], "dur", round(A[-1, 0]), "s | usable frames", f"{good.mean():.0%}", "| face found", f"{A[:, 1].mean():.0%}",
          "| cuts", int(A[:, 5].sum()), "| median iod", round(float(np.median(A[A[:, 1] == 1, 4])), 3) if A[:, 1].any() else 0, flush=True)
    for p in picks:
        print(f"   window {p[1]:6.1f}s  score {p[0]:.3f}  iod {p[2]:.3f}  |yaw| {p[3]:4.1f}  upper {p[4]:.3f}  mouth spread {p[5]:.3f}", flush=True)
    out[path] = [dict(start=float(p[1]), score=float(p[0])) for p in picks]
    np.save(path.rsplit(".", 1)[0] + "_track.npy", A)
json.dump(out, open(sys.argv[1], "w"), indent=1)
