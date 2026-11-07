"""Runs inside Unreal (ue_py.py). Points BP_AgoraChar at the corrected animation set in Anims6 and raises the mesh
3 cm: every retargeted clip puts the ankle 2-3 cm lower than Epic's in stance (thicker boots than Manny's feet),
so the soles would sink into the floor. Also updates the placed test actor in L_AgoraChar_Test."""
import unreal

ABP = "/Game/AgoraChar/Retarget/Anims6/ABP_Unarmed_Agora"
BP = "/Game/AgoraChar/AF/BP_AgoraChar"
MESH_Z = -87.0
lib = unreal.EditorAssetLibrary
print("Anims6 contents:", [p.split(".")[-1] for p in lib.list_assets("/Game/AgoraChar/Retarget/Anims6") if "ABP" in p])
abp = lib.load_asset(ABP)
abp_class = abp.generated_class()
# the ABP must reference Anims5 clips, not Anims2 or Epic's
deps = lib.find_package_referencers_for_asset(ABP) and None
refs = [str(d) for d in (unreal.AssetRegistryHelpers.get_asset_registry().get_dependencies(ABP, unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=True)) or [])]
print("ABP deps:", sorted(d for d in refs if "Retarget" in d or "Mannequins" in d))
bp = lib.load_asset(BP)
cdo = unreal.get_default_object(bp.generated_class())
m = cdo.get_editor_property("mesh")
m.set_editor_property("anim_class", abp_class)
m.set_editor_property("relative_location", unreal.Vector(0, 0, MESH_Z))
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
lib.save_loaded_asset(bp, only_if_is_dirty=False)
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class() == bp.generated_class():
        am = a.get_editor_property("mesh")
        am.set_editor_property("anim_class", abp_class)
        am.set_relative_location(unreal.Vector(0, 0, MESH_Z), False, False)
        print("actor", a.get_name(), "anim", am.get_editor_property("anim_class").get_name(), "z", am.get_editor_property("relative_location").z)
print("CDO anim", m.get_editor_property("anim_class").get_name(), "z", m.get_editor_property("relative_location").z)
