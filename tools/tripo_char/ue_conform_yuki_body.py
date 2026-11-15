"""Runs inside Unreal. Gives Yuki's MetaHuman the body of her Tripo model: a BODY_ONLY conform of a copy of the
character (head, skin and look stay as they are) to the Tripo body prepared by yuki_body_prep.

Route M of docs/TRIPO_UE_WORKFLOW (5.5): the Tripo static mesh is the conform target, the MetaHuman supplies topology
and rig. Until 2026-11-14 only Yuki's head was conformed and her body was the preset Aera's.
A wrapper sets ARGS = dict(SRC=<character to copy>, NAME=<new character>, FBX=<body target>, and optionally PIPE,
JOINTS (estimate the body joints from the mesh)). Touches only /Game/AgoraChar/Tripo/Yuki; saves the new character and
the imported target mesh. Refuses to run if NAME exists, unless REUSE is set (conform that character again)."""
import unreal

_A = globals().pop("ARGS", {})
SRC, NAME, FBX = _A.get("SRC", "MHC_Yuki_v5"), _A.get("NAME", "MHC_Yuki_v6"), _A["FBX"]
PKG = "/Game/AgoraChar/Tripo/Yuki"
MESH = f"{PKG}/yuki_body_target"
lib = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
task = unreal.AssetImportTask()
for k, v in (("filename", FBX), ("destination_path", PKG), ("destination_name", "yuki_body_target"), ("automated", True), ("save", False), ("replace_existing", True)):
    task.set_editor_property(k, v)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh = unreal.load_asset(MESH)
b = mesh.get_bounds()
print("BODYCONF target", mesh.get_class().get_name(), "origin", b.origin, "extent", b.box_extent)
verts, idx, *_ = sub.get_mesh_data_for_conforming(mesh)
print("BODYCONF target", len(verts), "verts", len(idx) // 3, "tris")
path = f"{PKG}/{NAME}"
made = not lib.does_asset_exist(path)
if not made and not _A.get("REUSE"):
    raise RuntimeError(path + " exists; change NAME or pass REUSE=True")
ch = lib.duplicate_asset(f"{PKG}/{SRC}", path) if made else unreal.load_asset(path)
if not sub.try_add_object_to_edit(ch):
    if made:
        lib.delete_asset(path)
    raise RuntimeError("cannot open the character for edit")
ok = False
try:
    p = unreal.ConformTargetParams()
    p.conform_target_mesh.target_parts_type = unreal.TargetPartsType.BODY_ONLY
    p.conform_target_mesh.body_vertices = verts
    p.conform_target_mesh.body_vertex_indices = idx
    p.estimate_body_joints_from_mesh = bool(_A.get("JOINTS", False))
    p.auto_solve = True
    print("BODYCONF solve settings", [x for x in dir(p.body_conform_solve_settings) if not x.startswith("_") and x not in dir(unreal.StructBase)])
    p.body_conform_solve_settings.pipeline_name = _A.get("PIPE", "combined")
    key = unreal.MetaHumanCharacterTargetMeshKey()
    key.body_mesh = mesh
    print("BODYCONF conform started")
    if not sub.conform_to_target_meshes(ch, key, p):
        raise RuntimeError("conform_to_target_meshes returned False")
    print("BODYCONF conform returned True")
    # The solve only stores a posed state for this target. Without this commit the character's body stays as it was
    # (first run 2026-11-14: exported body identical to the source, 0.00 mm moved).
    sub.commit_posed_state_as_a_pose(ch, key)
    sub.commit_body_state(ch)
    lib.save_asset(path, only_if_is_dirty=False)
    lib.save_asset(MESH, only_if_is_dirty=False)
    ok = True
    print("BODYCONF saved", path)
finally:
    if sub.is_object_added_for_editing(ch):
        sub.remove_object_to_edit(ch)
    if not ok and made:
        print("BODYCONF failed; deleting", path, lib.delete_asset(path))
