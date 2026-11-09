# Runs INSIDE Unreal: apply a Makeup Studio look to MH_DepesaKF: our painted face layers as the BASECOLOR override,
# the look's MetaHuman makeup layers (eyes, lip gloss), save, then build OPTIMIZED into BuiltKF and save the build.
import json
import unreal

LOOK = json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\makeup\apply_cfg.json"))
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
t = unreal.AssetImportTask()
t.set_editor_property("filename", LOOK["bc_png"])
t.set_editor_property("destination_path", "/Game/Companions/KeenFace/Looks")
t.set_editor_property("destination_name", LOOK["asset_name"])
t.set_editor_property("automated", True)
t.set_editor_property("replace_existing", True)
t.set_editor_property("save", True)
tools.import_asset_tasks([t])
tex = lib.load_asset("/Game/Companions/KeenFace/Looks/" + LOOK["asset_name"])
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = lib.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
s = ch.get_editor_property("skin_settings")
ov = s.get_editor_property("texture_overrides")
face = ov.get_editor_property("face")
face[unreal.FaceTextureType.BASECOLOR] = tex
ov.set_editor_property("face", face)
s.set_editor_property("texture_overrides", ov)
mhs.commit_skin_settings(ch, s)

m = ch.get_editor_property("makeup_settings")
for path, v in LOOK["metahuman_makeup"].items():
    sec, prop = path.split(".")
    st = m.get_editor_property(sec)
    cur = st.get_editor_property(prop)
    if isinstance(v, list):
        v = unreal.LinearColor(*v)
    elif isinstance(v, str):
        v = getattr(type(cur), v)
    st.set_editor_property(prop, v)
    m.set_editor_property(sec, st)
mhs.commit_makeup_settings(ch, m)
lib.save_loaded_asset(ch, only_if_is_dirty=False)
print("LOOK applied", LOOK["asset_name"], "can_build", mhs.can_build_meta_human(ch, True))
