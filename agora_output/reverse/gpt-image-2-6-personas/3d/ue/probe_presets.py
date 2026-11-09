import unreal
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
for n in ("track_face_landmarks_from_image","get_face_model_coefficients","set_face_model_coefficients","commit_face_state","compare_face_state","commit_head_model_settings","commit_makeup_settings","commit_eyes_settings"):
    f = getattr(mhs, n, None)
    print("DOC", n, ":", (f.__doc__ or "").strip().replace("\n"," ")[:420])
reg = unreal.AssetRegistryHelpers.get_asset_registry()
f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/MetaHumanCharacter", "MetaHumanCharacter")], package_paths=["/MetaHumanCharacter"], recursive_paths=True)
for a in sorted(reg.get_assets(f), key=lambda a: str(a.package_name)):
    print("PRESET", str(a.package_name))
