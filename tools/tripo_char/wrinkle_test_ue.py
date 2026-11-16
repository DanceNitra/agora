"""Do Yuki's animated wrinkle maps show? Plays five held face poses (neutral, forehead = brows raised, glabella = brows
down and together, nose = nose wrinkle, all sad controls together) through the production path: curves into an
AnimSequence (ue_yuki_curves_apply), the dance sequence with a close camera (ue_yuki_dance_seq), Movie Render Queue
(render_yuki_seq.ps1), so RigLogic drives the wrinkle maps exactly as in a song render. Then measures, per pose, the
fine detail that appears in the forehead, between the brows and on the nose bridge against the neutral pose.

    .venv_mp/Scripts/python.exe wrinkle_test_ue.py

Creates /Game/AgoraChar/Tripo/Yuki/MHA/A_WrinkleTest_face and the sequence LS_Yuki_Dance_WrinkleTest (test assets)."""
import json, subprocess, sys, time
from pathlib import Path

import cv2, numpy as np

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT.parent / "comfy_char" / "ue_py.py"
UE_EXE = r"C:\Program Files\Epic Games\UE_5.9\Engine\Binaries\Win64\UnrealEditor.exe"
UPROJECT = r"C:\Users\Danculus\Desktop\codex\1hra\SFX\MyProject\MyProject.uproject"
LOCK = Path(r"C:\Users\Danculus\.claude\compute\agora-tripo-char.lock")
MHA = "/Game/AgoraChar/Tripo/Yuki/MHA"
IDLE = "/MetaHumanCharacter/Optional/Animation/UEFNAnimPreset/Locomotion/AS_MH_Neutral_Stand_Idle_Loop"
PROP_ADD = "/Game/AgoraChar/Tripo/Yuki/Anim/A_Yuki_ProportionsAdd"
W = ROOT / "reports" / "yuki_lipsync" / "wrinkle_test"
STEM = W / "wrinkle_test"
RDIR = W / "render"
meta = json.load(open(str(STEM) + ".json"))
N, HOLD, POSES = meta["keys"], meta["hold"], meta["poses"]


def wrap(args, script):
    return f"ARGS = dict({args})\n" + (ROOT / script).read_text(encoding="utf-8")


def ue(code, tag):
    p = W / f"_ue_{tag}.py"
    p.write_text(code, encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(RUNNER), str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout + r.stderr
    print("\n".join(l for l in out.splitlines() if l.strip() and "Deprecation" not in l)[-1500:], flush=True)
    if "FAILED" in out:
        raise SystemExit(f"unreal step {tag} failed")


if "--skip-unreal" not in sys.argv:
    LOCK.write_text(f"agora tripo_char: wrinkle test, Unreal 5.9 editor, scope=gpu ttl=40 started {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    ed = subprocess.Popen([UE_EXE, UPROJECT, "-AutoDeclinePackageRecovery"])  # a killed editor leaves a restore prompt that blocks the next start
    print("EDITOR PID", ed.pid, flush=True)
    try:
        for _ in range(72):      # up to 6 min: a cold editor takes minutes to answer
            time.sleep(5)
            p = W / "_ready.py"
            p.write_text("import unreal\nprint('READY')\n")
            if "READY" in subprocess.run([sys.executable, "-I", str(RUNNER), str(p)], capture_output=True, text=True).stdout:
                break
        else:
            raise SystemExit("the editor did not answer")
        ue(wrap(f"SRC='{MHA}/A_P_brel_nmqp_face_nohead', DST='{MHA}/A_WrinkleTest_face', STEM=r'{STEM.as_posix()}'", "ue_yuki_curves_apply.py"), "apply")
        lvl = "import unreal\nunreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/AgoraChar/Tripo/Yuki/L_Yuki_Preview')\n"
        ue(lvl + wrap(f"ANIM='{IDLE}', FACE='{MHA}/A_WrinkleTest_face', ADD=['{PROP_ADD}'], Z_OFF=29.5, PRE=45, TAG='WrinkleTest', "
                      f"RANGE=(0, {N - 1}), FOCAL=420.0, CAM_Z=126.0, OUT=r'{RDIR.as_posix()}'", "ue_yuki_dance_seq.py"), "sequence")
    finally:
        ed.kill()
        print("EDITOR closed", flush=True)
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "render_yuki_seq.ps1"), "-tag", "WrinkleTest", "-out", str(RDIR)], check=True)
    finally:
        LOCK.unlink(missing_ok=True)
frames = sorted(RDIR.glob("*.png"))
print("RENDER frames", len(frames), flush=True)
pick = {p: 45 + i * HOLD + HOLD // 2 for i, p in enumerate(POSES)}
ims = {p: cv2.imread(str(RDIR / f"{f:04d}.png")) for p, f in pick.items()}
ims = {p: im for p, im in ims.items() if im is not None}
if "neutral" not in ims:
    raise SystemExit("no neutral frame rendered")
H, Wd = ims["neutral"].shape[:2]
print("frame size", Wd, H, flush=True)
json.dump({p: str(RDIR / f"{f:04d}.png") for p, f in pick.items()}, open(W / "frames.json", "w"), indent=1)
