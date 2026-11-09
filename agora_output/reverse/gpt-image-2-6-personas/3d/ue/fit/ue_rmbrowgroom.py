# Runs INSIDE Unreal: remove our DepesaBrows groom actors from the render sequence (to judge the painted fill alone).
import unreal
seq = unreal.EditorAssetLibrary.load_asset("/Game/Companions/Lipsync/LS_KF_Depesa_lajk_confidence_v5")
n = 0
for b in list(seq.get_bindings()):
    if str(b.get_display_name()).startswith("DepesaBrows"):
        b.remove(); n += 1
unreal.EditorAssetLibrary.save_loaded_asset(seq, only_if_is_dirty=False)
print("RMBROW", n)
