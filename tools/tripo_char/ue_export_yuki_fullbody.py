"""Runs inside Unreal. Exports the WHOLE body of the MetaHuman Yuki (no faces hidden under clothing) to an FBX on disk.

The built Body mesh has no torso, upper arms or upper thighs: the build removes what the default T-shirt and shorts
cover (measured 2026-11-14: no vertex follows a spine or pelvis bone). The character asset still holds the complete
body; export_geometry writes it as a skeletal mesh, and that is exported to DISK/yuki_fullbody.fbx.
A wrapper may set ARGS = dict(NAME=..., DISK=...)."""
import os

import unreal

_A = globals().pop("ARGS", {})
NAME = _A.get("NAME", "MHC_Yuki_v5")
DISK = _A.get("DISK", r"C:\Users\Danculus\agora\tools\tripo_char\models\yuki\mh_v5_body")
PKG = "/Game/AgoraChar/Tripo/Yuki"
OUT = PKG + "/Geo_" + NAME + "_Body"
os.makedirs(DISK, exist_ok=True)
lib = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.load_asset(PKG + "/" + NAME)
added = sub.try_add_object_to_edit(ch)
print("FULLBODY added for edit", added)
try:
    p = unreal.MetaHumanGeometryExportParams()
    p.project_path = OUT
    p.body_skeletal_mesh = True
    p.head_skeletal_mesh = False
    p.full_body_skeletal_mesh = False
    p.overwrite_existing_assets = True
    print("FULLBODY export_geometry", unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(ch, p))
    for a in lib.list_assets(OUT, recursive=True):
        obj = unreal.load_asset(str(a).split(".")[0])
        if isinstance(obj, unreal.SkeletalMesh):
            b = obj.get_bounds()
            t = unreal.AssetExportTask()
            for k, v in (("object", obj), ("filename", os.path.join(DISK, "yuki_fullbody.fbx")), ("automated", True), ("prompt", False), ("replace_identical", True)):
                t.set_editor_property(k, v)
            o = unreal.FbxExportOption()
            o.set_editor_property("level_of_detail", False)
            o.set_editor_property("collision", False)
            t.set_editor_property("options", o)
            print("FULLBODY", obj.get_name(), "skeleton", obj.get_editor_property("skeleton").get_name(), "extent", b.box_extent, "origin", b.origin, "fbx", unreal.Exporter.run_asset_export_task(t))
finally:
    if added:
        sub.remove_object_to_edit(ch)
