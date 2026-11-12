"""Runs inside Unreal. Lists the MetaHuman wardrobe items by folder."""
import unreal

reg = unreal.AssetRegistryHelpers.get_asset_registry()
f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/MetaHumanCharacterPalette", "MetaHumanWardrobeItem")], recursive_classes=True)
by = {}
for a in reg.get_assets(f):
    p = str(a.package_name)
    by.setdefault(p.rsplit("/", 1)[0], []).append(str(a.asset_name))
for k in sorted(by):
    print(k, sorted(by[k]))
