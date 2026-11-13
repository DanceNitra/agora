"""Runs inside Unreal. Portrait light for L_Yuki_Preview, close to the concept picture: a soft key from the front and a
little above, a shadowless fill from the other front side, and the sky as ambient. Before 2026-11-13 the fill pointed
at the back of the head and the far cheek rendered black. Saves the level by its path."""
import unreal

# Wrapper values arrive in one dict, ARGS, which is taken out of the globals before anything else runs. The editor's
# Python keeps its globals between runs: single variables set by a wrapper became the defaults of later runs, also
# when a run failed half way (2026-11-13: a close-up's FOV, an old iris scale and PIE=True leaked that way).
_A = globals().pop("ARGS", {})


eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
# the character faces +Y; a light with yaw -90 travels towards -Y, straight into the face
for name, pitch, yaw, inten, shadow in (("Yuki_Sun", -22.0, -78.0, _A.get("KEY", 2.2), True), ("Yuki_Fill", -5.0, -118.0, _A.get("FILL", 1.5), False)):
    a = acts[name]
    a.set_actor_rotation(unreal.Rotator(roll=0, pitch=pitch, yaw=yaw), False)
    c = a.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_editor_property("intensity", inten)
    c.set_editor_property("cast_shadows", shadow)
    c.set_editor_property("light_source_angle", 6.0)
    c.set_editor_property("light_source_soft_angle", 4.0)
    c.set_editor_property("light_color", unreal.Color(r=255, g=_A.get("WARM_G", 240), b=_A.get("WARM_B", 226), a=255))   # warm: the sky ambient is grey-green
sky = acts["Yuki_Sky"].get_component_by_class(unreal.SkyLightComponent)
sky.set_editor_property("intensity", _A.get("SKY", 0.5))
sky.set_editor_property("real_time_capture", True)
print("LIGHTS set; level saved", unreal.EditorAssetLibrary.save_asset("/Game/AgoraChar/Tripo/Yuki/L_Yuki_Preview", only_if_is_dirty=False))
