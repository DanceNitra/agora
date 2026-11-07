"""Runs inside Unreal (ue_py.py). Builds IK Rigs for Epic's Manny and for our character, and an IK Retargeter
between them, in /Game/AgoraChar/Retarget. Prints each rig's chains and the chain mapping so it can be checked.
"""
import unreal

FOLDER = "/Game/AgoraChar/Retarget"
SOURCE_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
TARGET_MESH = "/Game/AgoraChar/AF2/SK_AgoraChar"

lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def get_or_create(name, cls, factory):
    path = f"{FOLDER}/{name}"
    if lib.does_asset_exist(path):
        return lib.load_asset(path)
    return tools.create_asset(name, FOLDER, cls, factory)


def build_rig(name, mesh_path):
    rig = get_or_create(name, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    ctrl = unreal.IKRigController.get_controller(rig)
    ctrl.set_skeletal_mesh(lib.load_asset(mesh_path))
    ctrl.apply_auto_generated_retarget_definition()
    ctrl.apply_auto_fbik()
    ctrl.set_root_motion_bone("root")
    print(name, "root motion bone", ctrl.get_root_motion_bone())
    chains = [(str(c.chain_name), str(ctrl.get_retarget_chain_start_bone(c.chain_name)), str(ctrl.get_retarget_chain_end_bone(c.chain_name))) for c in ctrl.get_retarget_chains()]
    print(name, "root", ctrl.get_retarget_root(), "chains", len(chains))
    for c in chains:
        print("   ", c)
    lib.save_loaded_asset(rig)
    return rig


src = build_rig("IK_Manny_Agora", SOURCE_MESH)
tgt = build_rig("IK_AgoraChar", TARGET_MESH)

rtg = get_or_create("RTG_Manny_to_AgoraChar", unreal.IKRetargeter, unreal.IKRetargetFactory())
rc = unreal.IKRetargeterController.get_controller(rtg)
rc.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, src)
rc.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, tgt)
if rc.get_num_retarget_ops() == 0:
    rc.add_default_ops()
print("ops", [str(rc.get_op_name(i)) for i in range(rc.get_num_retarget_ops())])
rc.assign_ik_rig_to_all_ops(unreal.RetargetSourceOrTarget.SOURCE, src)
rc.assign_ik_rig_to_all_ops(unreal.RetargetSourceOrTarget.TARGET, tgt)
rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
rc.auto_align_all_bones(unreal.RetargetSourceOrTarget.TARGET)
for m in (n for n in dir(rc) if n.startswith("get_") and "chain" in n.lower()):
    print("controller has", m)
try:
    print("mapping:", [(str(a), str(rc.get_source_chain(a))) for a in [str(c.chain_name) for c in unreal.IKRigController.get_controller(tgt).get_retarget_chains()]])
except Exception as e:  # the getter name changed across versions; the printout above shows what exists
    print("mapping read failed:", e)
lib.save_loaded_asset(rtg)
print("saved", rtg.get_path_name())
