"""Capture the standing character from 8 directions in play, close and low, through Unreal's own render.
    python -I tools/comfy_char/ue_turntable.py OUT.png"""
import base64, json, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from ue import call, APP  # noqa: E402
from ue_py import run_file  # noqa: E402

OUT = Path(sys.argv[1])
TMP = Path(tempfile.mkdtemp(prefix="agora_tt_"))
CAM = """import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
ch = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Character) if "AgoraChar" in a.get_class().get_name())
boom = ch.get_component_by_class(unreal.SpringArmComponent)
boom.set_editor_property("target_arm_length", 260.0)
boom.set_editor_property("enable_camera_lag", False)
boom.set_editor_property("enable_camera_rotation_lag", False)
boom.set_editor_property("socket_offset", unreal.Vector(0, 0, -60))
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pc.set_control_rotation(unreal.Rotator(0, -8, ch.get_actor_rotation().yaw + YAW))
"""
call(APP, "StartPIE", {"options": {}})
time.sleep(5)
for i, yaw in enumerate(range(0, 360, 45)):
    f = TMP / f"cam{i}.py"
    f.write_text(CAM.replace("YAW", str(yaw)), encoding="utf-8")
    run_file(str(f))
    time.sleep(1.0)
    r = json.loads(call(APP, "CaptureEditorImage", {}, raw=True))
    v = r.get("returnValue", r)
    (TMP / f"t{i}.png").write_bytes(base64.b64decode(v["image"]["data"] if "image" in v else v["data"]))
call(APP, "StopPIE", {})
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(TMP / "t%d.png"),
                "-vf", "crop=520:560:140:270,scale=300:323,tile=4x2", "-frames:v", "1", str(OUT)], check=True)
print("saved", OUT)
