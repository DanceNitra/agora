"""Capture the preview level from fixed cameras through the Unreal MCP.  python -I ue_shots.py OUT_DIR"""
import base64, json, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "comfy_char"))
from ue import call, APP  # noqa: E402
from ue_py import run_file  # noqa: E402

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
# name: (x, y, z, pitch, yaw) in cm and degrees; the hero faces +Y
SHOTS = {"full_front": (0, 420, 95, 0, -90), "full_back": (0, -420, 95, 0, 90), "full_side": (420, 0, 95, 0, 180),
         "face": (0, 75, 168, 0, -90), "face_34": (50, 60, 168, 0, -130), "hand": (60, 60, 95, -10, -110),
         "feet": (0, 120, 30, -12, -90)}
for name, (x, y, z, p, yw) in SHOTS.items():
    code = ("import unreal\n"
            f"unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector({x},{y},{z}), unreal.Rotator(roll=0, pitch={p}, yaw={yw}))\n")
    f = Path(tempfile.gettempdir()) / "hero_cam.py"; f.write_text(code); run_file(str(f)); time.sleep(2.5)
    r = json.loads(call(APP, "CaptureEditorImage", {}, raw=True))
    data = r.get("returnValue", r)
    img = None
    if isinstance(data, dict):
        img = data["image"]["data"] if isinstance(data.get("image"), dict) else data.get("data")
    if not img:
        print(name, "no image; keys", list(data.keys()) if isinstance(data, dict) else str(data)[:200]); continue
    (out / f"{name}.png").write_bytes(base64.b64decode(img)); print(name, "saved")
