import unreal
lib = unreal.EditorAssetLibrary
b = lib.load_asset("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Grooms/Eyebrows_L_Shaded_Binding")
print("PRM cls", type(b).__name__)
for p in ("groom", "target_skeletal_mesh", "source_skeletal_mesh", "binding_type", "num_interpolation_points", "group_infos"):
    try: v = b.get_editor_property(p); print("PRM", p, v.get_path_name() if hasattr(v, "get_path_name") else v)
    except Exception as e: print("PRM err", p, e)
print("PRM lib", [m for m in dir(unreal.GroomLibrary) if "binding" in m])
bp = lib.load_asset("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/BP_MH_DepesaKF")
