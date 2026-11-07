"""Runs inside Unreal (ue_py.py). Replaces SK_AgoraChar's geometry and skin weights from a new FBX, keeping its
skeleton, materials and every reference to it (BP_AgoraChar, the retargeted animations). A copy of the previous
mesh is kept first as SK_AgoraChar_<BACKUP_SUFFIX>."""
import unreal

FBX = "C:/Users/Danculus/agora/agora_output/reverse/yt_bEiW6L7Y7NM/actionforge_export/AgoraChar_AF_cm_w5.fbx"
MESH = "/Game/AgoraChar/AF2/SK_AgoraChar"
BACKUP_SUFFIX = "AFweights"
lib = unreal.EditorAssetLibrary
backup = f"{MESH}_{BACKUP_SUFFIX}"
if not lib.does_asset_exist(backup):
    lib.duplicate_asset(MESH, backup)
mesh = lib.load_asset(MESH)
mats_before = [str(m.material_slot_name) + "=" + (m.material_interface.get_name() if m.material_interface else "None") for m in mesh.materials]

ui = unreal.FbxImportUI()
ui.import_mesh = True
ui.import_as_skeletal = True
ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
ui.skeleton = mesh.skeleton
ui.import_animations = False
ui.import_materials = False
ui.import_textures = False
ui.create_physics_asset = False
sk = ui.skeletal_mesh_import_data
sk.set_editor_property("import_morph_targets", False)
sk.set_editor_property("update_skeleton_reference_pose", False)
sk.set_editor_property("use_t0_as_ref_pose", False)

task = unreal.AssetImportTask()
task.filename = FBX
task.destination_path = MESH.rsplit("/", 1)[0]
task.destination_name = MESH.rsplit("/", 1)[1]
task.replace_existing = True
task.replace_existing_settings = True
task.automated = True
task.save = True
task.options = ui
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
print("imported", list(task.imported_object_paths))
mesh = lib.load_asset(MESH)
mats_after = [str(m.material_slot_name) + "=" + (m.material_interface.get_name() if m.material_interface else "None") for m in mesh.materials]
print("materials before", mats_before)
print("materials after ", mats_after)
print("skeleton", mesh.skeleton.get_path_name())
