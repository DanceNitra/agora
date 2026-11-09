import unreal, json, os
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
bias = json.load(open(os.path.join(F, "_bias.json")))["bias"]
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
v = None
for a in unreal.ObjectIterator(unreal.PostProcessVolume):
    if a.get_actor_label() == "FIT_PPV":
        v = a
if v is None:
    v = eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0.0, 300001.1, 100162.2), unreal.Rotator(0, 0, 0), True)
    v.set_actor_label("FIT_PPV")
v.set_editor_property("unbound", True)
v.set_editor_property("priority", 1000.0)
s = v.get_editor_property("settings")
s.set_editor_property("override_auto_exposure_method", True)
s.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
s.set_editor_property("override_auto_exposure_bias", True)
s.set_editor_property("auto_exposure_bias", float(bias))
s.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
s.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
v.set_editor_property("settings", s)
print("ppv bias", bias)
