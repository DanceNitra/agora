import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in unreal.ObjectIterator(unreal.PointLight):
    if a.get_actor_label().startswith("FIT_LIGHT"):
        eas.destroy_actor(a)
H = unreal.Vector(0.0, 300001.1, 100162.2)
for i, (dx, dy, dz, inten) in enumerate([(0, 70, 10, 0.6), (-60, 50, 20, 0.25), (60, 50, 20, 0.25)]):
    l = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(H.x + dx, H.y + dy, H.z + dz), unreal.Rotator(0, 0, 0), True)
    l.set_actor_label("FIT_LIGHT_%d" % i)
    c = l.get_component_by_class(unreal.PointLightComponent)
    c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    c.set_editor_property("intensity", inten)
    c.set_editor_property("attenuation_radius", 400.0)
    c.set_editor_property("cast_shadows", False)
print("lights ok")
