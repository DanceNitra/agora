"""Runs inside Unreal. Exports the conformed character's geometry as skeletal meshes and writes the full-body mesh
to an FBX on disk, so Blender can measure it against the Tripo source."""
import json

import unreal

CFG = json.load(open(r"C:\Users\Danculus\agora\tools\tripo_char\current.json"))
PKG = "/Game/AgoraChar/Tripo/Hero01"
OUT = PKG + "/Geo_" + CFG["name"]
DISK = CFG["disk_out"]
lib = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.load_asset(PKG + "/" + CFG["name"])
added = sub.try_add_object_to_edit(ch)
print("added for edit", added)
try:
    p = unreal.MetaHumanGeometryExportParams()
    p.project_path = OUT
    p.body_skeletal_mesh = True
    p.head_skeletal_mesh = True
    p.full_body_skeletal_mesh = True
    p.overwrite_existing_assets = True
    r = unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(ch, p)
    print("export_geometry returned", r)
    assets = lib.list_assets(OUT, recursive=True)
    print("assets", [str(a) for a in assets])
    for a in assets:
        obj = unreal.load_asset(str(a).split(".")[0])
        if isinstance(obj, unreal.SkeletalMesh):
            b = obj.get_bounds()
            print(obj.get_name(), "bones", len(obj.skeleton.get_reference_pose().get_bone_names()) if obj.skeleton else None,
                  "origin", b.origin, "extent", b.box_extent)
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
