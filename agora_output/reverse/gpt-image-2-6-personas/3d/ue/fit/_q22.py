import unreal
print("PRM", unreal.GroomLibrary.create_new_groom_binding_asset_with_path.__doc__)
b = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Grooms/Eyebrows_L_Shaded_Binding")
print("PRM props", [p for p in dir(b) if not p.startswith("_")][:60])
