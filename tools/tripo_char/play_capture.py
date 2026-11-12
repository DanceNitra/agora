"""Play one animation clip on the hero in Play-in-Editor and capture frames through the Unreal MCP.

    python -I play_capture.py <clip_asset_name> <out_dir> <view> [frames] [gap_s]
view = face or full. The hero stands in L_Hero01_Preview; the play camera starts at the editor camera.
"""
import base64
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "comfy_char"))
from ue import call, APP  # noqa: E402
from ue_py import run_file  # noqa: E402

clip, out, view = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
frames = int(sys.argv[4]) if len(sys.argv) > 4 else 8
gap = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
out.mkdir(parents=True, exist_ok=True)
CAM = {"face": (0, 150, 166, 0, -90), "full": (0, 520, 100, 0, -90), "side": (520, 0, 100, 0, 180), "far": (0, 520, 100, 0, -90)}[view]

SETUP = f"""import unreal
reg = unreal.AssetRegistryHelpers.get_asset_registry()
f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence")], package_paths=["/Game"], recursive_paths=True)
hit = [a for a in reg.get_assets(f) if str(a.asset_name) == "{clip}"]
if not hit:
    raise RuntimeError("clip not found: {clip}")
anim = unreal.load_asset(str(hit[0].package_name))
print("clip", anim.get_path_name(), "length", round(anim.get_play_length(), 2), "skeleton", anim.get_skeleton().get_name())
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ues.set_level_viewport_camera_info(unreal.Vector({CAM[0]}, {CAM[1]}, {CAM[2]}), unreal.Rotator(roll=0, pitch={CAM[3]}, yaw={CAM[4]}))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()
"""
import os  # noqa: E402
STATE = SETUP.split("ues = ")[0] + "COSTUME = %r\n" % os.environ.get("COSTUME", "") + """
# The clip is set on the play copy only. A clip set on the editor actor poses the body while the face mesh stays in
# the reference pose outside play, which shows as a grey flap around the neck.
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    if "MHC_Hero01" in a.get_class().get_name():
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "Body":
                c.play_animation(anim, True)
                if COSTUME:
                    # Test only, on the play copy: the costume follows the body's pose as a leader-pose follower and the
                    # MetaHuman default outfit is hidden. Nothing in the level or the Blueprint changes.
                    # The costume actor `Hero01_Costume` stands in the preview level (ue_place_costume.py); this is its play copy.
                    sa = next(x for x in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.SkeletalMeshActor)
                              if x.skeletal_mesh_component.get_skeletal_mesh_asset() and x.skeletal_mesh_component.get_skeletal_mesh_asset().get_path_name().split(".")[0] == COSTUME)
                    sc = sa.skeletal_mesh_component
                    sa.attach_to_component(c, "", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.KEEP_WORLD, False)
                    sc.set_leader_pose_component(c, True)
                    print("COSTUME", sc.get_skeletal_mesh_asset().get_name(), "materials", [m.get_name() for m in sc.get_materials()])
            if COSTUME and c.get_name() == "SkeletalMesh":
                c.set_visibility(False, True)
            print("PIE", c.get_name(), "anim mode", c.get_animation_mode(), "playing", c.is_playing(), "pos", round(c.get_position(), 2), "leader", bool(c.get_editor_property("leader_pose_component")) if hasattr(c, "leader_pose_component") else "?")
"""


def py(code):
    f = Path(tempfile.gettempdir()) / "hero_play.py"
    f.write_text(code, encoding="utf-8")
    return run_file(str(f))


py(SETUP)
call(APP, "StartPIE", {"options": {}})
time.sleep(6)  # let grooms and shaders settle before the first frame
py(STATE)
if view in ("face", "far"):  # the play camera starts at the PlayerStart, so move the pawn close to the head
    py("""import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
pawn.set_actor_location(unreal.Vector(0, %d, 110), False, True)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pc.set_control_rotation(unreal.Rotator(roll=0, pitch=-5, yaw=-90))
print("pawn", pawn.get_actor_location())
""" % (115 if view == "face" else int(sys.argv[6]) if len(sys.argv) > 6 else 1000))
    time.sleep(1.5)
if os.environ.get("PAWN"):  # "x,y,z,yaw": the play camera from any side, for example "260,0,110,180" for the hero's left
    py("""import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
x, y, z, yaw = [float(v) for v in "%s".split(",")]
unreal.GameplayStatics.get_player_pawn(w, 0).set_actor_location(unreal.Vector(x, y, z), False, True)
unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(roll=0, pitch=-5, yaw=yaw))
""" % os.environ["PAWN"])
    time.sleep(1.5)
try:
    for i in range(frames):
        r = json.loads(call(APP, "CaptureEditorImage", {}, raw=True))
        v = r.get("returnValue", r)
        data = v["image"]["data"] if "image" in v else v["data"]
        (out / f"{view}_{i:02d}.png").write_bytes(base64.b64decode(data))
        time.sleep(gap)
finally:
    call(APP, "StopPIE", {})
print("frames", frames, "in", out)
