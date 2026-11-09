import unreal, json
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
L = [[p.x, p.y, p.z] for p in mhs.get_face_landmarks(ch)]
json.dump(L, open(F + r"\kf_landmarks3d.json", "w"))
print("LIPS landmarks", len(L))
print("LIPS rig", str(mhs.get_rigging_state(ch)) if hasattr(mhs, "get_rigging_state") else "n/a")
bp = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/BP_MH_DepesaKF")
reg = unreal.AssetRegistryHelpers.get_asset_registry()
mats = [a for a in reg.get_assets_by_path("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF", recursive=True) if "Material" in str(a.asset_class_path.asset_name)]
for a in mats:
    if "ead" not in str(a.asset_name) and "ace" not in str(a.asset_name):
        continue
    mi = unreal.EditorAssetLibrary.load_asset(str(a.package_name))
    out = {"scalar": {}, "vector": {}, "texture": {}}
    for p in unreal.MaterialEditingLibrary.get_scalar_parameter_names(mi):
        out["scalar"][str(p)] = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, p)
    for p in unreal.MaterialEditingLibrary.get_vector_parameter_names(mi):
        c = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mi, p); out["vector"][str(p)] = [c.r, c.g, c.b, c.a]
    for p in unreal.MaterialEditingLibrary.get_texture_parameter_names(mi):
        t = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mi, p); out["texture"][str(p)] = t.get_path_name() if t else None
    json.dump(out, open(F + r"\kf_mat_%s.json" % a.asset_name, "w"), indent=1)
    print("LIPS mat", a.asset_name, len(out["scalar"]), len(out["vector"]), len(out["texture"]))
