# Runs INSIDE Unreal: three 10-frame copies of LS_Depesa_line1_v2 for bisecting the render hang.
import unreal
lib = unreal.EditorAssetLibrary
SRC = "/Game/Companions/Lipsync/LS_Depesa_line1_v2"
for tag in ("A_noMH", "B_noRig", "C_full"):
    dst = "/Game/Companions/Lipsync/Bisect/LS_" + tag
    if lib.does_asset_exist(dst):
        lib.delete_asset(dst)
    seq = lib.duplicate_asset(SRC, dst)
    seq.set_playback_end(10)
    for b in seq.get_bindings():
        n = str(b.get_display_name())
        if tag == "A_noMH" and ("MH Depesa" in n or n in ("Face", "Body")):
            b.remove()
        elif tag == "B_noRig" and n in ("Face", "Body"):
            for t in list(b.get_tracks()):
                b.remove_track(t)
    lib.save_loaded_asset(seq, only_if_is_dirty=False)
    print("BISECT", tag, [str(b.get_display_name()) for b in seq.get_bindings()])
