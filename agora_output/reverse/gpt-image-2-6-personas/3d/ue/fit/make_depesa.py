import unreal
SRC = "/MetaHumanCharacter/Optional/Presets/Vivian"
DST = "/Game/Companions/MetaHuman/MH_Depesa"
lib = unreal.EditorAssetLibrary
if not lib.does_asset_exist(DST):
    print("dup", lib.duplicate_asset(SRC, DST))
print("exists", lib.does_asset_exist(DST))
