"""Starts the Unreal editor (own PID, compute lock), shows Yuki from behind with her current long hair and with each
given strand build, checks her face materials for wrinkle maps, closes the editor and writes one sheet. Saves nothing.

    .venv_mp/Scripts/python.exe back_preview_ue.py <out_dir> label=dir [label=dir ...]

The long groom builds while the editor ticks, so after each swap the driver waits (30 s steps, editor free) until a
back shot shows pink hair over the head, and only then takes the three views (behind, three-quarter back, side)."""
import subprocess, sys, time
from pathlib import Path

import cv2, numpy as np

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT.parent / "comfy_char" / "ue_py.py"
UE_EXE = r"C:\Program Files\Epic Games\UE_5.9\Engine\Binaries\Win64\UnrealEditor.exe"
UPROJECT = r"C:\Users\Danculus\Desktop\codex\1hra\SFX\MyProject\MyProject.uproject"
LOCK = Path(r"C:\Users\Danculus\.claude\compute\agora-tripo-char.lock")
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
longs = [("current", None)] + [(a.split("=", 1)[0], str((ROOT / a.split("=", 1)[1] / "yuki_hair_long_ue.abc").resolve())) for a in sys.argv[2:]]
VIEWS = (180, 140, 90)


def ue(code, tag):
    p = out / f"_{tag}.py"
    p.write_text(code, encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(RUNNER), str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout + r.stderr


def shot(path, yaw):
    ue(f"ARGS = dict(STATE='all', DIST=700.0, FOV=4.6, DZ=2.0, YAW={float(yaw)}, OUT=r'{path}')\n" + (ROOT / "ue_yuki_shot.py").read_text(encoding="utf-8"), "shot")
    return cv2.imread(str(path))


def pink_share(im, box):
    h, w = im.shape[:2]
    y0, y1, x0, x1 = box
    hsv = cv2.cvtColor(im[int(h * y0):int(h * y1), int(w * x0):int(w * x1)], cv2.COLOR_BGR2HSV)
    return float((((hsv[:, :, 0] > 135) | (hsv[:, :, 0] < 8)) & (hsv[:, :, 1] > 25) & (hsv[:, :, 2] > 90)).mean())


def wait_hair(tag):
    for k in range(20):
        time.sleep(30)
        im = shot(out / "_wait.png", 180)
        if im is None:
            continue
        s = pink_share(im, (0.35, 0.6, 0.4, 0.6))          # the back of the head, where a bald head is dark
        print(f"WAIT {tag} {k} pink over the head {s:.2f}", flush=True)
        if s > 0.4:
            time.sleep(20)
            return True
    return False


LOCK.write_text(f"agora tripo_char: back preview, Unreal 5.9 editor, scope=gpu ttl=40 started {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
ed = subprocess.Popen([UE_EXE, UPROJECT, "-AutoDeclinePackageRecovery"])  # a killed editor leaves a restore prompt that blocks the next start
print("EDITOR PID", ed.pid, flush=True)
state = out / "_hair_state.json"
state.unlink(missing_ok=True)
try:
    for _ in range(72):          # up to 6 min: a cold editor takes minutes to answer
        time.sleep(5)
        if "READY" in ue("import unreal\nprint('READY')\n", "ready"):
            break
    else:
        raise SystemExit("the editor did not answer")
    ue("import unreal\nunreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/AgoraChar/Tripo/Yuki/L_Yuki_Preview')\n", "level")
    print("\n".join(l for l in ue((ROOT / "ue_yuki_wrinkle_probe.py").read_text(encoding="utf-8"), "wrinkle").splitlines() if "WRINKLE" in l), flush=True)
    for i, (label, abc) in enumerate(longs):
        if abc:
            print("\n".join(l for l in ue(f"ARGS = dict(COMP='Hair', ABC=r'{abc}', NAME='GR_LongP{i}', STATE=r'{state}')\n"
                                           + (ROOT / "ue_yuki_groom_swap.py").read_text(encoding="utf-8"), "swap").splitlines() if "SWAP" in l or "Error" in l), flush=True)
        if not wait_hair(label):
            print("WAIT gave up", label, flush=True)
        for y in VIEWS:
            shot(out / f"{label}_back_{y}.png", y)
        print("BACK shots", label, flush=True)
    if state.exists():
        print("\n".join(l for l in ue(f"ARGS = dict(COMP='Hair', ABC=None, STATE=r'{state}')\n" + (ROOT / "ue_yuki_groom_swap.py").read_text(encoding="utf-8"),
                                       "restore").splitlines() if "SWAP" in l), flush=True)
finally:
    ed.kill()
    LOCK.unlink(missing_ok=True)
    print("EDITOR closed", flush=True)
rows = []
for label, _ in longs:
    ims = [cv2.imread(str(out / f"{label}_back_{y}.png")) for y in VIEWS]
    ims = [cv2.resize(x, (600, 600)) for x in ims if x is not None]
    if ims:
        cv2.putText(ims[0], label, (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        rows.append(np.hstack(ims))
if rows:
    cv2.imwrite(str(out / "back_sheet.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print("SHEET", out / "back_sheet.jpg", flush=True)
