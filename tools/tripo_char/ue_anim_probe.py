"""Runs inside Unreal. Compares the hero's body skeleton with the earlier MetaHuman's and lists animations at hand."""
import unreal

lib = unreal.EditorAssetLibrary
reg = unreal.AssetRegistryHelpers.get_asset_registry()
hero = lib.load_asset("/Game/AgoraChar/Tripo/Hero01/Built_MHC_Hero01_v2/MHC_Hero01_v2/Body/SKM_MHC_Hero01_v2_BodyMesh")
old = lib.load_asset("/Game/AgoraChar/MetaHuman/Built/MH_AgoraSoldier/Body/SKM_MH_AgoraSoldier_BodyMesh")
manny = lib.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
for n, m in (("hero", hero), ("soldier", old), ("manny", manny)):
    print(n, "skeleton", m.skeleton.get_path_name() if m else None)
f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence")], package_paths=["/Game"], recursive_paths=True)
by = {}
for a in reg.get_assets(f):
    sk = str(a.get_tag_value("Skeleton"))
    top = "/".join(str(a.package_path).split("/")[:4])
    by.setdefault((sk.split(".")[-1].rstrip("'"), top), []).append(str(a.asset_name))
for (sk, top), names in sorted(by.items()):
    print(len(names), "clips | skeleton", sk, "|", top, "|", names[:3])
