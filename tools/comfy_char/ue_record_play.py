"""Record what the character actually does in play, rendered by Unreal itself (not a desktop grab, which picks up
whatever window sits on top). Starts Play-in-Editor, slows the game to SLOMO, and captures the play viewport frame by
frame through the MCP CaptureEditorImage while a script drives the character: stand, run forward, jump while
running, stop, jump in place. Frames are written as PNG and joined into an MP4 at the real-time frame rate.

    python -I tools/comfy_char/ue_record_play.py OUT_DIR [view]
view = player (the third-person camera) or side (a close camera beside the character)."""
import base64, json, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from ue import call, APP  # noqa: E402
from ue_py import run_file  # noqa: E402

SLOMO = 0.1
OUT = Path(sys.argv[1])
VIEW = sys.argv[2] if len(sys.argv) > 2 else "player"
OUT.mkdir(parents=True, exist_ok=True)

PRE = """import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
ch = unreal.GameplayStatics.get_player_character(w, 0)
def setv(names, v):
    for n in names:
        try:
            ch.set_editor_property(n, v); return n
        except Exception:
            pass
    raise SystemExit("no variable among " + str(names))
"""
STEPS = {
    "setup": PRE + f"""unreal.GameplayStatics.set_global_time_dilation(w, {SLOMO})
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pc.set_control_rotation(unreal.Rotator(0, -15, ch.get_actor_rotation().yaw))
if "{VIEW}" == "side":
    boom = ch.get_component_by_class(unreal.SpringArmComponent)
    boom.set_editor_property("target_arm_length", 420.0)
    boom.set_editor_property("enable_camera_lag", False)
    boom.set_editor_property("socket_offset", unreal.Vector(0, 0, -95))
    pc.set_control_rotation(unreal.Rotator(0, -4, ch.get_actor_rotation().yaw + 90))
print("setup", ch.get_name(), "dilation", unreal.GameplayStatics.get_global_time_dilation(w))
""",
    "walk_on": PRE + 'print(setv(["bAutoWalkTest", "AutoWalkTest"], True))',
    "walk_off": PRE + 'print(setv(["bAutoWalkTest", "AutoWalkTest"], False))',
    "jump_on": PRE + 'print(setv(["bJumpTest", "JumpTest"], True))',
    "jump_off": PRE + 'print(setv(["bJumpTest", "JumpTest"], False))',
    "state": PRE + 'm = ch.get_editor_property("mesh"); print("loc", ch.get_actor_location(), "vel", round(ch.get_velocity().length()), "air", ch.get_movement_component().is_falling(), "anim", m.get_anim_instance().get_class().get_name())',
}


def py(step):
    f = Path(tempfile.gettempdir()) / f"agora_rec_{step}.py"
    f.write_text(STEPS[step], encoding="utf-8")
    return run_file(str(f))


def grab(i):
    r = json.loads(call(APP, "CaptureEditorImage", {}, raw=True))
    v = r.get("returnValue", r)
    data = v["image"]["data"] if "image" in v else v["data"]
    (OUT / f"f{i:04d}.png").write_bytes(base64.b64decode(data))


# timeline in captured frames: what to switch on before capturing frame i
PLAN = {0: [], 12: ["walk_on"], 30: ["jump_on"], 33: ["jump_off"], 48: ["walk_off"], 62: ["jump_on"], 65: ["jump_off"]}
N = int(sys.argv[3]) if len(sys.argv) > 3 else 80
call(APP, "StartPIE", {"options": {}})
time.sleep(5)
py("setup")
py("state")
t0 = time.time()
stamps = []
for i in range(N):
    for s in PLAN.get(i, []):
        py(s)
    stamps.append(time.time() - t0)
    grab(i)
    if i % 10 == 0:
        print(f"frame {i}/{N}  {stamps[-1]:.0f}s", flush=True)
        py("state")
call(APP, "StopPIE", {})
wall = (stamps[-1] - stamps[0]) / (N - 1)
fps = 1.0 / (wall * SLOMO)
print(f"captured {N} frames, {wall:.2f} s wall each = {wall * SLOMO:.3f} s game time, real-time fps {fps:.1f}")
(OUT / "fps.txt").write_text(f"{fps:.2f}")
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", f"{fps:.2f}", "-i", str(OUT / "f%04d.png"),
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-pix_fmt", "yuv420p", str(OUT / f"play_{VIEW}.mp4")], check=True)
print("video", OUT / f"play_{VIEW}.mp4")
