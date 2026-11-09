import unreal
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
n = 0
for a in eas.get_all_level_actors():
    if "MetaHumanDefaultEditorPipelineActor" in a.get_class().get_name() and a.get_actor_location().y > 250000:
        eas.destroy_actor(a); n += 1
for name in ["Ada","Aera","Aoi","Asha","Bo","Celeste","Etta","Grace","Jelena","Lani","Sook-ja","Sunita","Tuya","Vivian","Zuri"]:
    ch = unreal.EditorAssetLibrary.load_asset("/MetaHumanCharacter/Optional/Presets/" + name)
    if ch and mhs.is_object_added_for_editing(ch):
        mhs.remove_object_to_edit(ch)
print("destroyed", n)
