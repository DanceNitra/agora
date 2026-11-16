"""Starts the Unreal editor (own PID, compute lock), runs ue_yuki_fringe_preview.py for the given strand builds, closes
the editor and puts the concept, the current fringe and the proposals on one sheet.

    .venv_mp/Scripts/python.exe fringe_preview_ue.py <out_dir> label=dir [label=dir ...]"""
import subprocess, sys, time
from pathlib import Path

import cv2, numpy as np

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT.parent / "comfy_char" / "ue_py.py"
UE_EXE = r"C:\Program Files\Epic Games\UE_5.9\Engine\Binaries\Win64\UnrealEditor.exe"
UPROJECT = r"C:\Users\Danculus\Desktop\codex\1hra\SFX\MyProject\MyProject.uproject"
LOCK = Path(r"C:\Users\Danculus\.claude\compute\agora-tripo-char.lock")
CONCEPT = ROOT / "reports" / "yuki_ue_v5" / "concept_front.png"
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
args_ = [(a.split("=", 1)[0], str((ROOT / a.split("=", 1)[1]).resolve())) for a in sys.argv[2:]]
# "long:<label>=<dir>" swaps the long groom (the back of the head) instead of the fringe.
variants = [("current", None)] + [(l, d) for l, d in args_ if not l.startswith("long:")]
longs = [(l[5:], d) for l, d in args_ if l.startswith("long:")]
LOCK.write_text(f"agora tripo_char: fringe preview, Unreal 5.9 editor, scope=gpu ttl=40 started {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
ed = subprocess.Popen([UE_EXE, UPROJECT, "-AutoDeclinePackageRecovery"])  # a killed editor leaves a restore prompt that blocks the next start
print("EDITOR PID", ed.pid, flush=True)
try:
    p = out / "_ready.py"
    p.write_text("import unreal\nprint('READY')\n")
    for _ in range(72):          # up to 6 min: a cold editor takes minutes to answer
        time.sleep(5)
        if "READY" in subprocess.run([sys.executable, "-I", str(RUNNER), str(p)], capture_output=True, text=True).stdout:
            break
    else:
        raise SystemExit("the editor did not answer")
    shot = dict(STATE="all", DIST=700.0, FOV=3.4, DZ=-4.0)
    # A fresh editor first shows the grey checker material and no hair while shaders and grooms build, and a remote
    # script blocks the editor's ticks. So: load the level, then capture a test shot every 30 s with the editor free in
    # between, until the middle of the picture has colour (skin and pink hair; the checker has none).
    lv = out / "_level.py"
    lv.write_text("import unreal\nunreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/AgoraChar/Tripo/Yuki/L_Yuki_Preview')\n")
    subprocess.run([sys.executable, "-I", str(RUNNER), str(lv)], capture_output=True, text=True)
    warm_png = out / "_warm.png"
    for k in range(24):
        time.sleep(30)
        w = out / "_warm.py"
        w.write_text(f"ARGS = dict(STATE='all', DIST=700.0, FOV=3.4, OUT=r'{warm_png}')\n" + (ROOT / "ue_yuki_shot.py").read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run([sys.executable, "-I", str(RUNNER), str(w)], capture_output=True, text=True)
        im = cv2.imread(str(warm_png))
        if im is None:
            continue
        # Share of pink hair pixels in the upper middle: 0.00004 on the grey checker shot, 0.37 on a finished one.
        hh, ww = im.shape[:2]
        hsv = cv2.cvtColor(im[:hh // 2, ww // 4:3 * ww // 4], cv2.COLOR_BGR2HSV)
        pink = float((((hsv[:, :, 0] > 135) | (hsv[:, :, 0] < 8)) & (hsv[:, :, 1] > 25) & (hsv[:, :, 2] > 90)).mean())
        print(f"WARM {k} pink share {pink:.3f}", flush=True)
        if pink > 0.2:
            time.sleep(30)          # one more pause: the last materials settle after the hair appears
            break
    extra = [(f"back_{y}", dict(STATE="all", DIST=700.0, FOV=4.6, DZ=2.0, YAW=float(y))) for y in (180, 140, 90)]
    code = f"ARGS = dict(VARIANTS={variants!r}, OUT_DIR=r'{out}', SHOT={shot!r}, EXTRA={extra!r}, LONG_VARIANTS={longs!r})\n" + (ROOT / "ue_yuki_fringe_preview.py").read_text(encoding="utf-8")
    q = out / "_preview.py"
    q.write_text(code, encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(RUNNER), str(q)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (r.stdout + r.stderr).splitlines() if "FRINGE" in l or "SHOT" in l or "WARM" in l or "WRINKLE" in l or "Error" in l or "FAILED" in l)[-3000:], flush=True)
finally:
    ed.kill()
    LOCK.unlink(missing_ok=True)
    print("EDITOR closed", flush=True)
tiles = []
for label, path in [("concept", CONCEPT)] + [(v[0], out / f"{v[0]}.png") for v in variants]:
    im = cv2.imread(str(path))
    if im is None:
        continue
    h, w = im.shape[:2]
    s = min(h, w)
    im = cv2.resize(im[(h - s) // 2:(h - s) // 2 + s, (w - s) // 2:(w - s) // 2 + s], (520, 520))
    cv2.putText(im, label, (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    tiles.append(im)
cv2.imwrite(str(out / "fringe_sheet.jpg"), np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 90])
rows = []
for ll in ["current"] + [l for l, _ in longs]:
    back = [cv2.imread(str(out / f"{ll}_back_{y}.png")) for y in (180, 140, 90)]
    back = [cv2.resize(b, (600, 600)) for b in back if b is not None]
    if back:
        for b in back[:1]:
            cv2.putText(b, ll, (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        rows.append(np.hstack(back))
if rows:
    cv2.imwrite(str(out / "back_sheet.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
print("SHEET", out / "fringe_sheet.jpg", flush=True)
