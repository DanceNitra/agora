"""Runs inside Unreal. Lists the materials on Yuki's Face component and any parameter whose name suggests MetaHuman
animated wrinkle maps (wm1/wm2/wm3, wrinkle, animated, mask), so we know whether her face can show forehead, frown and
nose wrinkles. Changes nothing."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")
for sk in ch.get_components_by_class(unreal.SkeletalMeshComponent):
    if sk.get_name() != "Face":
        continue
    n = sk.get_num_materials()
    print("WRINKLE face materials", n, flush=True)
    slots = list(sk.get_material_slot_names())
    for i in range(n):
        m = sk.get_material(i)
        if m is None:
            print("WRINKLE slot", i, "none", flush=True)
            continue
        names = []
        for getter in ("get_scalar_parameter_names", "get_texture_parameter_names", "get_vector_parameter_names"):
            try:
                names += [str(x) for x in getattr(unreal.MaterialEditingLibrary, getter)(m)]
            except Exception as e:
                names.append(f"<{getter} failed: {e}>")
        hits = [x for x in names if any(k in x.lower() for k in ("wm", "wrinkle", "animated", "mask"))]
        base = m
        while isinstance(base, unreal.MaterialInstance) and base.get_editor_property("parent"):
            base = base.get_editor_property("parent")
        print("WRINKLE slot", i, str(slots[i]) if i < len(slots) else "?", m.get_path_name(), "| base", base.get_path_name(),
              "| params", len(names), "| hits", hits[:16], flush=True)
