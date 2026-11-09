import unreal
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
for n in ("spawn_meta_human_actor","assemble_for_preview","try_add_object_to_edit","remove_object_to_edit"):
    f=getattr(mhs,n,None); print("DOC",n,":",(f.__doc__ or "").strip().replace("\n"," ")[:500] if f else None)
print([n for n in dir(mhs) if "edit" in n.lower()])
