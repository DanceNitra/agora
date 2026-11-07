"""Runs inside Unreal (ue_py.py). Retargets Epic's ABP_Unarmed (idle, walk/jog blend space, jump, fall, land) from
SKM_Manny_Simple onto the MetaHuman body built for MH_AgoraSoldier, into /Game/AgoraChar/MetaHuman/Anims.

Both are Epic skeletons with the same core bone names standing in an A-pose, so the auto-generated IK rigs and an
auto-aligned retarget pose are expected to map close to one to one. Epic's foot IK Control Rig in the copied ABP
is turned off (Alpha 0): it needs ik_foot bones the MetaHuman body does not have (2026-11-07 lesson)."""
import unreal

FOLDER = "/Game/AgoraChar/MetaHuman/Anims"
RIGS = "/Game/AgoraChar/MetaHuman/Retarget"
SRC_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
TGT_MESH = "/Game/AgoraChar/MetaHuman/Built/MH_AgoraSoldier/Body/SKM_MH_AgoraSoldier_BodyMesh"
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def get_or_create(name, cls, factory):
    path = f"{RIGS}/{name}"
    return lib.load_asset(path) if lib.does_asset_exist(path) else tools.create_asset(name, RIGS, cls, factory)


def rig(name, mesh):
    r = get_or_create(name, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(r)
    c.set_skeletal_mesh(lib.load_asset(mesh))
    c.apply_auto_generated_retarget_definition()
    c.apply_auto_fbik()
    c.set_root_motion_bone("root")
    print(name, "chains", len(c.get_retarget_chains()))
    lib.save_loaded_asset(r)
    return r


src = rig("IK_Manny_MH", SRC_MESH)
tgt = rig("IK_MH_AgoraSoldier", TGT_MESH)
rtg = get_or_create("RTG_Manny_to_MH_AgoraSoldier", unreal.IKRetargeter, unreal.IKRetargetFactory())
rc = unreal.IKRetargeterController.get_controller(rtg)
rc.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, src)
rc.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, tgt)
if rc.get_num_retarget_ops() == 0:
    rc.add_default_ops()
rc.assign_ik_rig_to_all_ops(unreal.RetargetSourceOrTarget.SOURCE, src)
rc.assign_ik_rig_to_all_ops(unreal.RetargetSourceOrTarget.TARGET, tgt)
rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
rc.auto_align_all_bones(unreal.RetargetSourceOrTarget.TARGET)
lib.save_loaded_asset(rtg)

abp = unreal.AssetRegistryHelpers.get_asset_registry().get_asset_by_object_path("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed")
out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
    [abp], lib.load_asset(SRC_MESH), lib.load_asset(TGT_MESH), rtg, "", "", "", "_MH", FOLDER, False, True, True)
for p in lib.list_assets(FOLDER):
    lib.save_asset(p, only_if_is_dirty=False)
print("retargeted", len(out), "assets in", FOLDER, [p.rsplit(".", 1)[-1] for p in lib.list_assets(FOLDER)][:30])
