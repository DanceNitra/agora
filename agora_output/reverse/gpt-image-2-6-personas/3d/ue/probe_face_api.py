import unreal
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
names = [n for n in dir(mhs) if not n.startswith("_")]
print("SUBSYSTEM:", [n for n in names if any(k in n.lower() for k in ("face","head","template","preset","conform","blend","sculpt","import","landmark","skin","eye","makeup","hair","groom","wardrobe"))])
for n in ("import_from_template","import_from_face_dna","import_from_identity","conform","blend_face_region","apply_face_preset","get_face_presets","set_face_state","get_face_state"):
    f = getattr(mhs, n, None)
    if f: print("DOC", n, ":", (f.__doc__ or "").strip().replace("\n"," ")[:600])
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for path in ("/MetaHumanCharacter", "/MetaHuman", "/MetaHumanCharacter/Presets", "/MetaHumanCharacter/Optional"):
    try:
        assets = reg.get_assets_by_path(path, recursive=True)
        cls = {}
        for a in assets:
            c = str(a.asset_class_path.asset_name); cls[c] = cls.get(c, 0) + 1
        print("PATH", path, len(assets), sorted(cls.items(), key=lambda x:-x[1])[:12])
    except Exception as e:
        print("PATH", path, "ERR", e)
