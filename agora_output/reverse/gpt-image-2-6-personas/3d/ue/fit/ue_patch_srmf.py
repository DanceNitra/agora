# Runs INSIDE Unreal, AFTER the build: step "export" writes the baked SRMF (specular, roughness, ...) to PNG; step
# "import" brings our patched PNG back as a virtual texture with the source's settings and sets "SRMF Baked VT".
import json
import unreal
CFG = json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\srmf_cfg.json"))
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
SRC = "/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Face/Baked/T_Head_LOD1_SRMF_VT"
assert lib.does_asset_exist(SRC), SRC
src = lib.load_asset(SRC)
assert src is not None
if CFG["step"] == "export":
    task = unreal.AssetExportTask()
    task.set_editor_property("object", src)
    task.set_editor_property("filename", CFG["export_png"])
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    print("PATCH srmf export", unreal.Exporter.run_asset_export_task(task), src.get_editor_property("srgb"), src.get_editor_property("compression_settings"))
else:
    it = unreal.AssetImportTask()
    it.set_editor_property("filename", CFG["patched_png"])
    it.set_editor_property("destination_path", "/Game/Companions/KeenFace/Looks")
    it.set_editor_property("destination_name", CFG["asset"])
    it.set_editor_property("automated", True)
    it.set_editor_property("replace_existing", True)
    it.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([it])
    tex = lib.load_asset("/Game/Companions/KeenFace/Looks/" + CFG["asset"])
    assert tex is not None
    tex.set_editor_property("srgb", src.get_editor_property("srgb"))
    tex.set_editor_property("compression_settings", src.get_editor_property("compression_settings"))
    tex.set_editor_property("virtual_texture_streaming", True)
    lib.save_loaded_asset(tex, only_if_is_dirty=False)
    n = 0
    for a in lib.list_assets("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Face", recursive=True):
        if "MI_Face_Skin" not in a:
            continue
        m = lib.load_asset(a)
        cur = mel.get_material_instance_texture_parameter_value(m, "SRMF Baked VT")
        if cur and "T_Head_LOD1_SRMF_VT" in cur.get_path_name():
            mel.set_material_instance_texture_parameter_value(m, "SRMF Baked VT", tex)
            mel.update_material_instance(m)
            lib.save_loaded_asset(m, only_if_is_dirty=False)
            n += 1
    print("PATCH srmf materials", n, tex.get_path_name())
