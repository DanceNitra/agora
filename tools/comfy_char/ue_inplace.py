"""Runs inside Unreal (ue_py.py). Makes every retargeted animation in FOLDER play in place: every root key is set
to the root bone's REFERENCE local transform, so forward travel cannot move the mesh away from the capsule.

The reference transform matters. SK_AgoraChar's root carries a -13.3 degree roll in its reference pose. The first
version of this script wrote identity instead, which tipped the whole body 13 degrees forward and produced the
crooked, leaning stance and twisted feet the owner saw in play on 2026-11-07."""
import unreal

FOLDER = "/Game/AgoraChar/Retarget/Anims6"
lib = unreal.EditorAssetLibrary
E = unreal.AnimPoseExtensions
done = 0
for path in lib.list_assets(FOLDER, recursive=False):
    a = lib.load_asset(path)
    if not isinstance(a, unreal.AnimSequence):
        continue
    ref = E.get_bone_pose(E.get_reference_pose(a.get_skeleton()), "root", unreal.AnimPoseSpaces.LOCAL)
    ctrl = a.get_editor_property("controller")
    n = unreal.AnimationLibrary.get_num_frames(a) + 1
    pos = [ref.translation] * n
    rot = [ref.rotation] * n
    scl = [ref.scale3d] * n
    ctrl.open_bracket(unreal.Text("in place"), False)
    ok = ctrl.set_bone_track_keys("root", pos, rot, scl, False)
    ctrl.close_bracket(False)
    lib.save_loaded_asset(a, only_if_is_dirty=False)
    done += 1
    print(a.get_name(), "keys", n, "ok", ok)
print("in place", done, "root ref rotation", ref.rotation.rotator())
