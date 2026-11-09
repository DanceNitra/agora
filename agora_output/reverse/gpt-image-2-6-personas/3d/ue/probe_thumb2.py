import unreal
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
print([n for n in dir(mhs) if any(k in n.lower() for k in ("thumb","render","capture","snapshot","image","spawn","actor","preview","assemble"))])
for n in [n for n in dir(mhs) if "thumb" in n.lower() or "capture" in n.lower()]:
    print("DOC", n, (getattr(mhs,n).__doc__ or "").strip().replace("\n"," ")[:500])
print("PIE running:", unreal.EditorLevelLibrary.get_game_world() is not None if hasattr(unreal.EditorLevelLibrary,"get_game_world") else "n/a")
