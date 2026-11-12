"""Runs inside Unreal. Lists LODs and materials of the hero's meshes and grooms in the editor world."""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
hero = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Hero01_Character")
for c in hero.get_components_by_class(unreal.SkeletalMeshComponent):
    sk = c.get_skeletal_mesh_asset()
    if not sk:
        print("SKM", c.get_name(), "no mesh"); continue
    n = unreal.EditorSkeletalMeshLibrary.get_lod_count(sk)
    print("SKM", c.get_name(), sk.get_name(), "lods", n, "forced", c.get_forced_lod(), "mats", len(c.get_materials()))
    for i, m in enumerate(c.get_materials()):
        print("   mat", i, m.get_name() if m else None, "parent", m.parent.get_name() if m and hasattr(m, "parent") and m.parent else "")
    try:
        info = [round(unreal.EditorSkeletalMeshLibrary.get_lod_build_settings(sk, i).threshold_position, 3) for i in range(0)]
    except Exception as e:
        print("  ", e)
for c in hero.get_components_by_class(unreal.GroomComponent):
    g = c.get_editor_property("groom_asset")
    print("GROOM", c.get_name(), g.get_name() if g else None)
    if not g:
        continue
    for prop in ("hair_groups_lod", "hair_groups_cards", "hair_groups_meshes", "hair_groups_materials"):
        try:
            v = g.get_editor_property(prop)
        except Exception as e:
            print("   ", prop, "ERR", e); continue
        print("   ", prop, len(v))
        for x in v:
            if prop == "hair_groups_lod":
                for j, l in enumerate(x.get_editor_property("lo_ds")):
                    print("       lod", j, l.get_editor_property("geometry_type"), "screen", round(l.get_editor_property("screen_size"), 3), "visible", l.get_editor_property("visible"))
            elif prop == "hair_groups_materials":
                m = x.get_editor_property("material")
                print("       slot", x.get_editor_property("slot_name"), m.get_name() if m else None)
            else:
                m = x.get_editor_property("material") if hasattr(x, "material") else None
                d = {}
                for k in ("lod_index", "group_index", "material", "material_slot_name", "imported_mesh", "textures"):
                    try:
                        val = x.get_editor_property(k)
                        d[k] = val.get_name() if hasattr(val, "get_name") else str(val)[:160]
                    except Exception:
                        pass
                print("      ", d)
    print("    comp mats", [(m.get_name() if m else None) for m in c.get_materials()])
