import unreal
for n in ("GA_Depesa_Brow_R", "GA_Depesa_Brow_L"):
    g = unreal.EditorAssetLibrary.load_asset("/Game/Companions/Brows/" + n)
    print("PRM", n, g.get_editor_property("hair_groups_info")[0].get_editor_property("num_curves") if g else None)
