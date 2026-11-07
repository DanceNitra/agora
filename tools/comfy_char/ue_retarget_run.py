"""Runs inside Unreal (ue_py.py). Duplicates Epic's ABP_Unarmed and every asset it references onto our
character's skeleton through RTG_Manny_to_AgoraChar, into FOLDER.
Anims2: first set, body tipped 13 degrees and soles tilted. Anims3: body and soles fixed. Anims4: toes also aligned. Anims5: neck and head aligned. Anims6: spine line aligned too."""
import unreal

FOLDER = "/Game/AgoraChar/Retarget/Anims6"

lib = unreal.EditorAssetLibrary
reg = unreal.AssetRegistryHelpers.get_asset_registry()
abp = reg.get_asset_by_object_path("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed")
src = lib.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
tgt = lib.load_asset("/Game/AgoraChar/AF2/SK_AgoraChar")
rtg = lib.load_asset("/Game/AgoraChar/Retarget/RTG_Manny_to_AgoraChar")
out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
    [abp], src, tgt, rtg, "", "", "", "_Agora", FOLDER, False, True, True)
names = sorted(str(a.package_name) for a in out)
print("retargeted", len(names))
for n in names:
    print("  ", n)
for n in names:
    lib.save_asset(n, only_if_is_dirty=False)
