"""Runs inside Unreal. Exports the body skeletal mesh of the MetaHuman Yuki to an FBX on disk (mesh, skeleton, skin
weights), the source for her costume (yuki_costume_shell). A wrapper may set ARGS = dict(NAME=..., DISK=...)."""
import os

import unreal

_A = globals().pop("ARGS", {})
NAME = _A.get("NAME", "MHC_Yuki_v5")
DISK = _A.get("DISK", r"C:\Users\Danculus\agora\tools\tripo_char\models\yuki\mh_v5_body")
PKG = "/Game/AgoraChar/Tripo/Yuki"
os.makedirs(DISK, exist_ok=True)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")
for c in ch.get_components_by_class(unreal.SkeletalMeshComponent):
    m = c.get_skeletal_mesh_asset()
    print("BODYEXP component", c.get_name(), m.get_path_name() if m else None)
    if c.get_name() == "Body" and m:
        t = unreal.AssetExportTask()
        for k, v in (("object", m), ("filename", os.path.join(DISK, "yuki_body.fbx")), ("automated", True), ("prompt", False), ("replace_identical", True)):
            t.set_editor_property(k, v)
        o = unreal.FbxExportOption()
        o.set_editor_property("level_of_detail", False)
        o.set_editor_property("collision", False)
        o.set_editor_property("vertex_color", False)
        t.set_editor_property("options", o)
        b = m.get_bounds()
        print("BODYEXP exported", unreal.Exporter.run_asset_export_task(t), "extent", b.box_extent, "origin", b.origin)
