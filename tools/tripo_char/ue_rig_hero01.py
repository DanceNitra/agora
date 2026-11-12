"""Runs inside Unreal. Cloud auto-rig and high-resolution textures for the character named in current.json.
The first cloud call of an editor session opens Epic's sign-in; the owner signs in himself."""
import json

import unreal

CFG = json.load(open(r"C:\Users\Danculus\agora\tools\tripo_char\current.json"))
PATH = "/Game/AgoraChar/Tripo/Hero01/" + CFG["name"]
lib = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.load_asset(PATH)
if not sub.try_add_object_to_edit(ch):
    raise RuntimeError("cannot open the character for edit")
try:
    rig = unreal.MetaHumanCharacterAutoRiggingRequestParams()
    rig.blocking = True
    rig.report_progress = False
    rig.rig_type = unreal.MetaHumanRigType.JOINTS_ONLY
    print("auto-rig requested")
    sub.request_auto_rigging(ch, rig)
    print("auto-rig returned")
    tex = unreal.MetaHumanCharacterTextureRequestParams()
    tex.blocking = True
    tex.report_progress = False
    print("textures requested")
    sub.request_texture_sources(ch, tex)
    print("textures returned; high-res", ch.has_high_resolution_textures)
    print("can build", sub.can_build_meta_human(ch, True))
    print("saved", lib.save_asset(PATH, only_if_is_dirty=False))
finally:
    if sub.is_object_added_for_editing(ch):
        sub.remove_object_to_edit(ch)
