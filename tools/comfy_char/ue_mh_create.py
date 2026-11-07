"""Runs inside Unreal (ue_py.py). Creates the MetaHuman soldier MH_AgoraSoldier under /Game/AgoraChar/MetaHuman with
the body, skin and eyes the MetaHumanGenerator toolset exposes, assembles a preview and spawns it next to the test
character's start. Prints what the character asset offers for face, hair and wardrobe, which come next."""
import unreal

PATH = "/Game/AgoraChar/MetaHuman/MH_AgoraSoldier"
lib = unreal.EditorAssetLibrary
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)

if lib.does_asset_exist(PATH):
    ch = lib.load_asset(PATH)
else:
    ch = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "MH_AgoraSoldier", "/Game/AgoraChar/MetaHuman", unreal.MetaHumanCharacter, unreal.new_object(unreal.MetaHumanCharacterFactoryNew))
print("character", ch.get_path_name())
print("added for edit", mhs.try_add_object_to_edit(ch))

# body: adult woman, 172 cm, athletic, low fat
cons = list(mhs.get_body_constraints(ch))
names = [str(c.name) for c in cons]
print("body constraints", names)
want = {"Masculine/Feminine": 0.85, "Fat": 0.2, "Muscularity": 0.55}
for c in cons:
    n = str(c.name)
    lo, hi = c.min_measurement, c.max_measurement
    if n == "Height":
        c.is_active = True; c.target_measurement = 172.0
    for key, v in want.items():
        if n.lower() == key.lower():
            c.is_active = True; c.target_measurement = lo + (hi - lo) * v
mhs.set_body_constraints(ch, cons)
mhs.commit_body_state(ch)
unreal.MetaHumanGeneratorSubsystemWrapper.reset_neck_to_body(ch)

skin = ch.skin_settings; skin.skin.u = 0.35; skin.skin.v = 0.45
mhs.commit_skin_settings(ch, skin)

print("character properties:", [p for p in dir(ch) if not p.startswith("_") and p not in dir(unreal.Object)])
mhs.assemble_for_preview(ch)
lib.save_loaded_asset(ch, only_if_is_dirty=False)
