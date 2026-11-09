# Runs INSIDE Unreal: dress MH_Depesa's INTERNAL collection (the one the build reads) with the chosen grooms and
# colours, save it, and build a Cinematic MetaHuman into /Game/Companions/MetaHuman/BuiltKF.
import json
import unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
lib = unreal.EditorAssetLibrary
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
reg = unreal.AssetRegistryHelpers.get_asset_registry()
ch = lib.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
PICK = {"Hair": "/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_L_Straight",
        "Eyebrows": "/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_L_Shaded",
        "Eyelashes": "/MetaHumanCharacter/Optional/Grooms/Bindings/Eyelashes/WI_Eyelashes_L_ThickCurl"}
NO_BROWS = True
colours = json.load(open(F + r"\groomcolor_cfg.json"))
for col in (ch.get_editor_property("internal_collection"), mhs.get_preview_collection(ch)):
    inst = col.get_editor_property("default_instance")
    for slot, path in PICK.items():
        item = lib.load_asset(path)
        key = col.try_add_item_from_wardrobe_item(slot, item)
        if key is None:
            keys = col.get_item_keys_for_wardrobe_item(item)
            key = keys[0] if keys else None
        inst.set_single_slot_selection(slot, key)
    if NO_BROWS:  # our own p6-shaped brow grooms replace the MetaHuman brows in the render sequence
        try:
            inst.set_single_slot_selection("Eyebrows", unreal.MetaHumanPaletteItemKey())
        except Exception as e:
            print("NOBROWS", e)
    for p in inst.get_instance_parameter_item_paths():
        txt = p.export_text()
        for frag, vals in colours.items():
            if frag in txt:
                for q in inst.get_instance_parameters(p):
                    if str(q.name) in vals:
                        v = vals[str(q.name)]
                        q.set_color(unreal.LinearColor(*v)) if isinstance(v, list) else q.set_float(v)
mhs.on_edit_preview_collection(ch)
lib.save_loaded_asset(ch, only_if_is_dirty=False)
print("PIPES", [m for m in dir(unreal.MetaHumanDefaultPipelineType) if m.isupper()])
params = unreal.MetaHumanCharacterEditorBuildParameters()
params.set_editor_property("pipeline_type", unreal.MetaHumanDefaultPipelineType.OPTIMIZED)
params.set_editor_property("pipeline_quality", unreal.MetaHumanQualityLevel.HIGH)
params.set_editor_property("absolute_build_path", "/Game/Companions/MetaHuman/BuiltKF")
print("CAN", mhs.can_build_meta_human(ch, True))
mhs.build_meta_human(ch, params)
built = sorted(str(a.package_name) for a in reg.get_assets_by_path("/Game/Companions/MetaHuman/BuiltKF", True))
print("BUILT", len(built), [b for b in built if "/BP_" in b or b.split("/")[-1].startswith("BP")])
saved = unreal.EditorAssetLibrary.save_directory("/Game/Companions/MetaHuman/BuiltKF", only_if_is_dirty=False, recursive=True)
xs = unreal.EditorAssetLibrary.list_assets("/Game/Companions/MetaHuman/BuiltKF", True, False)
print("SAVEDIR", saved, len(xs), [x.split("/")[-1] for x in xs if any(k in x for k in ("Hair", "Brow", "Lash", "Groom", "Binding"))][:12])
