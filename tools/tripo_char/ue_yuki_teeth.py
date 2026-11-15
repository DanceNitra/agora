"""Runs inside Unreal. Whiter teeth for the built MetaHuman Yuki.

The built teeth material (MI_Teeth_Baked) has "Use Baked Material" on, so its colour parameters do nothing (measured
2026-11-14: value 0.75 to 1.15 changed no pixel); the colour is the texture "Basecolor Baked". STEP="export" writes that
texture to DIR/teeth_BC_baked.png, the script yuki_teeth_white recolours it, STEP="apply" imports DIR/yuki_teeth_BC.png as
T_Yuki_teeth_BC and points the material at it. A wrapper sets ARGS = dict(STEP=..., DIR=..., NAME=...)."""
import unreal

_A = globals().pop("ARGS", {})
STEP, DIR, NAME = _A["STEP"], _A["DIR"], _A.get("NAME", "MHC_Yuki_v5")
PKG = "/Game/AgoraChar/Tripo/Yuki"
mel, lib = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary
m = unreal.load_asset(f"{PKG}/Built_{NAME}/{NAME}/Face/Materials/MI_Teeth_Baked")
if STEP == "export":
    tex = mel.get_material_instance_texture_parameter_value(m, "Basecolor Baked")
    t = unreal.AssetExportTask()          # properties set one by one: assigning them as attributes exported nothing
    for k, v in (("object", tex), ("filename", DIR + "\teeth_BC_baked.png"), ("automated", True), ("replace_identical", True), ("prompt", False)):
        t.set_editor_property(k, v)
    print("TEETH export", tex.get_path_name(), tex.blueprint_get_size_x(), unreal.Exporter.run_asset_export_task(t))
else:
    it = unreal.AssetImportTask()
    it.filename, it.destination_path, it.destination_name = DIR + "\yuki_teeth_BC.png", PKG + "/Tex", "T_Yuki_teeth_BC"
    it.automated, it.replace_existing, it.save = True, True, True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([it])
    tex = unreal.load_asset(PKG + "/Tex/T_Yuki_teeth_BC")
    print("TEETH set", mel.set_material_instance_texture_parameter_value(m, "Basecolor Baked", tex))
    mel.update_material_instance(m)
    print("TEETH saved", lib.save_asset(m.get_path_name().split(".")[0], only_if_is_dirty=False))
