# Runs INSIDE Unreal. Pilots the level viewport through a transient 12-degree camera FIT_TELE (mode "on")
# or ejects it (mode "off").
import unreal, json
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\pilot_cfg.json"))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
cams = [a for a in unreal.ObjectIterator(unreal.CameraActor) if a.get_actor_label() == "FIT_TELE"]
if cfg["mode"] == "on":
    h = cfg["head"]
    loc = unreal.Vector(h[0], h[1] + cfg["dist"] + 50.0, h[2] + cfg.get("dz", 0.0))  # body behind the capture point
    if cams:
        les.eject_pilot_level_actor()
        for c in cams:
            eas.destroy_actor(c)
    cam = eas.spawn_actor_from_class(unreal.CameraActor, loc, unreal.Rotator(0, -90, 0), True)
    cam.set_actor_label("FIT_TELE")
    cam.set_actor_location(loc, False, False)
    cam.set_actor_rotation(unreal.Rotator(0, -90, 0), False)
    cc = cam.get_component_by_class(unreal.CameraComponent)
    cc.set_editor_property("field_of_view", cfg["fov"])
    cc.set_editor_property("constrain_aspect_ratio", False)
    les.pilot_level_actor(cam)
    print("PILOT", cfg["fov"])
else:
    les.eject_pilot_level_actor()
    print("EJECT")
