"""Runs inside Unreal (tools/comfy_char/ue_py.py). Imports Yuki's face patch (yuki_head.py) as a static mesh and conforms
a new MetaHumanCharacter to it HEAD ONLY, with face landmarks from the full-head portrait. Hair, cat ears and clothing
are not in the patch, so they cannot swell the head. Touches only /Game/AgoraChar/Tripo/Yuki and saves only the assets
it names. A wrapper may set NAME and SRC above this file."""
import json

import unreal

SRC = globals().get("SRC", r"C:\Users\Danculus\agora\tools\tripo_char\models\yuki\head_v1")
NAME = globals().get("NAME", "MHC_Yuki_v1")
PIPE = globals().get("PIPE", "combined")
STEM = "yuki_head"  # file stem of the FBX, portrait and report in SRC
PKG = "/Game/AgoraChar/Tripo/Yuki"
MESH_NAME = globals().get("MESH_NAME", STEM)
MESH = f"{PKG}/{MESH_NAME}"
lib = unreal.EditorAssetLibrary
report = json.load(open(SRC + "\\" + STEM + ".clean.json"))
cam = report["camera_unreal"]

# 1. Import the face patch once.
if not lib.does_asset_exist(MESH):
    task = unreal.AssetImportTask()
    task.filename = SRC + "\\" + STEM + ".fbx"
    task.destination_path = PKG
    task.destination_name = MESH_NAME
    task.automated = True
    task.save = False
    task.replace_existing = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    print("imported", [str(p) for p in task.imported_object_paths])
mesh = unreal.load_asset(MESH)
if mesh is None:
    raise RuntimeError("face patch did not import as " + MESH)
b = mesh.get_bounds()
print("mesh class", mesh.get_class().get_name(), "origin", b.origin, "extent", b.box_extent)

sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)

# 2. Face landmarks from the full-head portrait (the patch alone has no brows or face outline for the tracker).
size, pixels = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(SRC + "\\" + cam["portrait"])
res = sub.track_face_landmarks_from_image(pixels, size.x, size.y)
if isinstance(res, tuple) and len(res) == 1:
    res = res[0]
curves = res if (res and hasattr(res, "items")) else None
print("face curves", len(curves) if curves else 0, sorted(curves.keys())[:40] if curves else None)
if not curves:
    raise RuntimeError("no face landmarks detected on the portrait")

verts, idx, *_ = sub.get_mesh_data_for_conforming(mesh)
print("target", len(verts), "verts", len(idx) // 3, "tris")

# 3. Character asset.
path = f"{PKG}/{NAME}"
if lib.does_asset_exist(path):
    raise RuntimeError(path + " exists; delete it by hand or change NAME before a second run")
# BASE: a MetaHuman preset to start from (for example /MetaHumanCharacter/Optional/Presets/Aoi). A new empty character
# keeps the default body and skin, which read as a man under Yuki's head (owner, 2026-11-13); a preset brings a female
# body, skin, eyes and lashes, and the head-only conform then replaces the face shape.
BASE = globals().get("BASE", "")
if BASE:
    ch = lib.duplicate_asset(BASE, path)
else:
    ch = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name=NAME, package_path=PKG, asset_class=unreal.MetaHumanCharacter,
        factory=unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew))
print("character from", BASE or "new", ch.get_path_name() if ch else None)
if not sub.try_add_object_to_edit(ch):
    lib.delete_asset(path)
    raise RuntimeError("cannot open the character for edit")

ok = False
try:
    p = unreal.ConformTargetParams()
    p.conform_target_mesh.target_parts_type = unreal.TargetPartsType.HEAD_ONLY
    p.conform_target_mesh.head_vertices = verts
    p.conform_target_mesh.head_vertex_indices = idx
    p.estimate_body_joints_from_mesh = False
    p.auto_solve = True
    p.body_conform_solve_settings.pipeline_name = PIPE  # empty: "Failed to find pipeline" in the autorigger
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
    key.head_mesh = mesh
    print("conform started")
    if not sub.conform_to_target_meshes(ch, key, p):
        raise RuntimeError("conform_to_target_meshes returned False")
    print("conform returned True")
    lib.save_asset(path, only_if_is_dirty=False)
    lib.save_asset(MESH, only_if_is_dirty=False)
    ok = True
    print("saved", path)
finally:
    if sub.is_object_added_for_editing(ch):
        sub.remove_object_to_edit(ch)
    if not ok:
        print("conform failed; deleting", path, lib.delete_asset(path))
