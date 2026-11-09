# Runs INSIDE Unreal: save ONLY MH_Depesa, by explicit path.
import unreal
ok = unreal.EditorAssetLibrary.save_asset("/Game/Companions/MetaHuman/MH_Depesa", only_if_is_dirty=False)
print("SAVED", ok)
