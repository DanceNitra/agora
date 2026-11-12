"""Runs inside Unreal (tools/comfy_char/ue_py.py). Imports the cleaned Tripo body as a static mesh and conforms a new
MetaHumanCharacter to it, following Epic's example_conform_from_custom_mesh.py. Touches only /Game/AgoraChar/Tripo/Hero01
and saves only the assets it names."""
import json

import unreal

# current.json names the run: {"src_dir": ..., "stem": ..., "name": ..., "disk_out": ...}
CFG = json.load(open(r"C:\Users\Danculus\agora\tools\tripo_char\current.json"))
SRC = CFG["src_dir"]
PKG = "/Game/AgoraChar/Tripo/Hero01"
MESH = f"{PKG}/" + CFG["stem"]
NAME = CFG["name"]
lib = unreal.EditorAssetLibrary
report = json.load(open(SRC + "\\" + CFG["stem"] + ".clean.json"))
cam = report["camera_unreal"]

# 1. Import the FBX once.
if not lib.does_asset_exist(MESH):
    task = unreal.AssetImportTask()
    task.filename = SRC + "\\" + CFG["stem"] + ".fbx"
    task.destination_path = PKG
    task.automated = True
    task.save = False
    task.replace_existing = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    print("imported", [str(p) for p in task.imported_object_paths])
mesh = unreal.load_asset(MESH)
if mesh is None:
    raise RuntimeError("body mesh did not import as " + MESH)
b = mesh.get_bounds()
print("mesh class", mesh.get_class().get_name(), "origin", b.origin, "extent", b.box_extent)

sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)

# 2. Face landmarks from the portrait rendered by clean_body.py.
size, pixels = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(SRC + "\\" + cam["portrait"])
res = sub.track_face_landmarks_from_image(pixels, size.x, size.y)
if isinstance(res, tuple) and len(res) == 1:
    res = res[0]
curves = res if (res and hasattr(res, "items")) else None
print("face curves", len(curves) if curves else 0)
if not curves:
    raise RuntimeError("no face landmarks detected on the portrait")

verts, idx, *_ = sub.get_mesh_data_for_conforming(mesh)
print("target", len(verts), "verts", len(idx) // 3, "tris")

# 3. Character asset.
path = f"{PKG}/{NAME}"
if lib.does_asset_exist(path):
    raise RuntimeError(path + " exists; delete it by hand or change NAME before a second run")
ch = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    asset_name=NAME, package_path=PKG, asset_class=unreal.MetaHumanCharacter,
    factory=unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew))
if not sub.try_add_object_to_edit(ch):
    lib.delete_asset(path)
    raise RuntimeError("cannot open the character for edit")

ok = False
try:
    p = unreal.ConformTargetParams()
    p.conform_target_mesh.target_parts_type = unreal.TargetPartsType.COMBINED
    p.conform_target_mesh.body_vertices = verts
    p.conform_target_mesh.body_vertex_indices = idx
    p.estimate_body_joints_from_mesh = bool(CFG.get("estimate_joints", True))
    print("estimate joints from mesh", p.estimate_body_joints_from_mesh)
    p.auto_solve = True
    p.body_conform_solve_settings.pipeline_name = "combined"
    view = unreal.MinimalViewInfo()
    view.location = unreal.Vector(*cam["location_cm"])
    view.rotation = unreal.Rotator(pitch=cam["rotation_pitch_yaw_roll"][0], yaw=cam["rotation_pitch_yaw_roll"][1],
                                   roll=cam["rotation_pitch_yaw_roll"][2])
    view.fov = cam["fov_deg"]
    view.aspect_ratio = float(size.x) / float(size.y)
    view.projection_mode = unreal.CameraProjectionMode.PERSPECTIVE
    p.curve_tracking_points = curves
    p.camera_view_info = view
    p.image_size = size
    key = unreal.MetaHumanCharacterTargetMeshKey()
    key.combined_mesh = mesh
    print("conform started")
    if not sub.conform_to_target_meshes(ch, key, p):
        raise RuntimeError("conform_to_target_meshes returned False")
    print("conform returned True")
    sub.commit_posed_state_as_a_pose(ch, key)
    lib.save_asset(path, only_if_is_dirty=False)
    lib.save_asset(MESH, only_if_is_dirty=False)
    ok = True
    print("saved", path)
finally:
    if sub.is_object_added_for_editing(ch):
        sub.remove_object_to_edit(ch)
    if not ok:
        print("conform failed; deleting", path, lib.delete_asset(path))
