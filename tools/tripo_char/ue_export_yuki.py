"""Runs inside Unreal. Exports the conformed Yuki head as a skeletal mesh and writes it to an FBX on disk, so Blender can
render it beside the concept and measure it against the Tripo face. A wrapper may set NAME and DISK above this file."""
import os

import unreal

NAME = globals().get("NAME", "MHC_Yuki_v1")
DISK = globals().get("DISK", r"C:\Users\Danculus\agora\tools\tripo_char\models\yuki\mh_v1")
PKG = "/Game/AgoraChar/Tripo/Yuki"
OUT = PKG + "/Geo_" + NAME
os.makedirs(DISK, exist_ok=True)
lib = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.load_asset(PKG + "/" + NAME)
added = sub.try_add_object_to_edit(ch)
print("added for edit", added)
try:
    p = unreal.MetaHumanGeometryExportParams()
    p.project_path = OUT
    p.body_skeletal_mesh = False
    p.head_skeletal_mesh = True
    p.full_body_skeletal_mesh = False
    p.overwrite_existing_assets = True
    print("export_geometry returned", unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(ch, p))
    for a in lib.list_assets(OUT, recursive=True):
        obj = unreal.load_asset(str(a).split(".")[0])
        if isinstance(obj, unreal.SkeletalMesh):
            b = obj.get_bounds()
            print(obj.get_name(), "origin", b.origin, "extent", b.box_extent)
            t = unreal.AssetExportTask()
            t.object = obj
            t.filename = DISK + "\\" + obj.get_name() + ".fbx"
            t.automated = True
            t.replace_identical = True
            t.prompt = False
            o = unreal.FbxExportOption()
            o.level_of_detail = False
            o.collision = False
            t.options = o
            print("fbx", obj.get_name(), unreal.Exporter.run_asset_export_task(t))
finally:
    if added:
        sub.remove_object_to_edit(ch)
