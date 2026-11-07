"""Runs inside Unreal (ue_py.py). Locks the root of every retargeted animation in Anims2, so movement comes
from the Character Movement component and the mesh never runs ahead of the capsule."""
import unreal

lib = unreal.EditorAssetLibrary
done = 0
for path in lib.list_assets("/Game/AgoraChar/Retarget/Anims2", recursive=False):
    a = lib.load_asset(path)
    if isinstance(a, unreal.AnimSequence):
        before = (a.get_editor_property("enable_root_motion"), a.get_editor_property("force_root_lock"))
        a.set_editor_property("enable_root_motion", False)
        a.set_editor_property("force_root_lock", True)
        lib.save_loaded_asset(a, only_if_is_dirty=False)
        done += 1
        print(a.get_name(), "before", before)
print("locked", done)
