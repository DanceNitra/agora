"""Runs inside Unreal (ue_py.py). Makes every retargeted animation in Anims2 play in place: the root bone track
is set to identity on every key, so forward travel cannot move the mesh away from the capsule."""
import unreal

lib = unreal.EditorAssetLibrary
done = 0
for path in lib.list_assets("/Game/AgoraChar/Retarget/Anims2", recursive=False):
    a = lib.load_asset(path)
    if not isinstance(a, unreal.AnimSequence):
        continue
    ctrl = a.get_editor_property("controller")
    n = unreal.AnimationLibrary.get_num_frames(a) + 1
    pos = [unreal.Vector(0, 0, 0)] * n
    rot = [unreal.Quat(0, 0, 0, 1)] * n
    scl = [unreal.Vector(1, 1, 1)] * n
    ctrl.open_bracket(unreal.Text("in place"), False)
    ok = ctrl.set_bone_track_keys("root", pos, rot, scl, False)
    ctrl.close_bracket(False)
    lib.save_loaded_asset(a, only_if_is_dirty=False)
    done += 1
    print(a.get_name(), "keys", n, "ok", ok)
print("in place", done)
