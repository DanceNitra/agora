"""Runs inside Unreal. Sets Yuki's skin, eyes and built-in make-up on the MetaHuman character, then requests the cloud
auto-rig and the high-resolution textures. The first cloud call of an editor session may open Epic's sign-in; the owner
signs in himself. A wrapper may set NAME, RIG (False skips the cloud calls) and the look values below."""
import unreal

NAME = globals().get("NAME", "MHC_Yuki_v2")
RIG = globals().get("RIG", True)
# Skin tone picker: fair skin is V near 0 (presets Aoi 0.315/0.018, Aera 0.203/0.0; 0.25/0.30 came out tan).
SKIN_UV = globals().get("SKIN_UV", (0.27, 0.01))
FACE_TEX = globals().get("FACE_TEX", 8)                    # face detail texture; 8 is preset Aoi's
IRIS_TINT = globals().get("IRIS_TINT", (1.0, 0.55, 0.12))  # amber, over the iris pattern
LINER, LIPS, BLUSH = globals().get("LINER", 1.0), globals().get("LIPS", 0.85), globals().get("BLUSH", 0.6)
TEXTURES = globals().get("TEXTURES", True)                 # request the high-resolution textures again
IRIS = globals().get("IRIS", None)                         # (primary_u, primary_v, secondary_u, secondary_v) or None
PATH = "/Game/AgoraChar/Tripo/Yuki/" + NAME
lib = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.load_asset(PATH)
if not sub.try_add_object_to_edit(ch):
    raise RuntimeError("cannot open the character for edit")
try:
    if SKIN_UV:  # None keeps the skin of the preset the character was made from
        skin = ch.get_editor_property("skin_settings")
        sp = skin.get_editor_property("skin")
        sp.set_editor_property("u", SKIN_UV[0])
        sp.set_editor_property("v", SKIN_UV[1])
        sp.set_editor_property("face_texture_index", FACE_TEX)
        sp.set_editor_property("show_top_underwear", True)
        skin.set_editor_property("skin", sp)
        sub.commit_skin_settings(ch, skin)
    print("skin uv", SKIN_UV)

    eyes = ch.get_editor_property("eyes_settings")
    for side in ("eye_left", "eye_right"):
        e = eyes.get_editor_property(side)
        ir = e.get_editor_property("iris")
        if IRIS:
            ir.set_editor_property("primary_color_u", IRIS[0])
            ir.set_editor_property("primary_color_v", IRIS[1])
            ir.set_editor_property("secondary_color_u", IRIS[2])
            ir.set_editor_property("secondary_color_v", IRIS[3])
        if IRIS_TINT:
            ir.set_editor_property("global_tint", unreal.LinearColor(IRIS_TINT[0], IRIS_TINT[1], IRIS_TINT[2], 1))
            ir.set_editor_property("global_saturation", 2.2)
        e.set_editor_property("iris", ir)
        eyes.set_editor_property(side, e)
    sub.commit_eyes_settings(ch, eyes)
    print("iris", IRIS, "tint", IRIS_TINT)

    mk = ch.get_editor_property("makeup_settings")
    ey = mk.get_editor_property("eyes")
    ey.set_editor_property("type", unreal.MetaHumanCharacterEyeMakeupType.CAT_EYE)   # winged liner, as in the concept
    ey.set_editor_property("primary_color", unreal.LinearColor(0.008, 0.006, 0.006, 1))
    ey.set_editor_property("secondary_color", unreal.LinearColor(0.008, 0.006, 0.006, 1))
    ey.set_editor_property("opacity", LINER)
    mk.set_editor_property("eyes", ey)
    lp = mk.get_editor_property("lips")
    lp.set_editor_property("type", unreal.MetaHumanCharacterLipsMakeupType.NATURAL)
    lp.set_editor_property("color", unreal.LinearColor(0.72, 0.20, 0.17, 1))           # coral
    lp.set_editor_property("opacity", LIPS)
    lp.set_editor_property("roughness", 0.3)
    lp.set_editor_property("metalness", 0.0)
    mk.set_editor_property("lips", lp)
    bl = mk.get_editor_property("blush")
    bl.set_editor_property("type", unreal.MetaHumanCharacterBlushMakeupType.APPLE)
    bl.set_editor_property("color", unreal.LinearColor(0.80, 0.25, 0.30, 1))
    bl.set_editor_property("intensity", BLUSH)
    mk.set_editor_property("blush", bl)
    sub.commit_makeup_settings(ch, mk)
    print("makeup set")
    print("saved", lib.save_asset(PATH, only_if_is_dirty=False))

    if RIG:
        rig = unreal.MetaHumanCharacterAutoRiggingRequestParams()
        rig.blocking = True
        rig.report_progress = False
        rig.rig_type = unreal.MetaHumanRigType.JOINTS_ONLY
        print("auto-rig requested")
        sub.request_auto_rigging(ch, rig)
        print("auto-rig returned")
    if TEXTURES:
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
