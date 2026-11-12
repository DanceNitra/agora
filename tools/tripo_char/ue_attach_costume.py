"""Runs inside Unreal. Makes the costume permanent on the hero: the Blueprint's outfit component `SkeletalMesh` (child of
`Body`, already driven by the body's pose) takes the costume mesh in place of the MetaHuman default outfit.
Removes the test actor `Hero01_Costume` from the level. Saves only the Blueprint and the preview level. Undo: run with MESH set to OUTFIT."""
import unreal

BP = "/Game/AgoraChar/Tripo/Hero01/Built_MHC_Hero01_v3/MHC_Hero01_v3/BP_MHC_Hero01_v3"
OUTFIT = "/Game/AgoraChar/Tripo/Hero01/Built_MHC_Hero01_v3/MHC_Hero01_v3/Clothing/MHC_Hero01_v3_Outfits"
MESH = "/Game/AgoraChar/Tripo/Hero01/Costume/hero01_costume"
SAVE_LEVEL = True  # the preview level holds the hero actor with its own copy of the outfit mesh

bp = unreal.load_asset(BP)
mesh = unreal.load_asset(MESH)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
L = unreal.SubobjectDataBlueprintFunctionLibrary
done = set()
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    o = L.get_associated_object(sds.k2_find_subobject_data_from_handle(h))
    if isinstance(o, unreal.SkeletalMeshComponent) and o.get_name() == "SkeletalMesh_GEN_VARIABLE" and o.get_path_name() not in done:
        done.add(o.get_path_name())
        before = o.get_skeletal_mesh_asset()
        print("template", o.get_path_name(), "before", before.get_name() if before else None,
              "override materials", [m.get_name() if m else None for m in o.get_editor_property("override_materials")])
        o.set_editor_property("override_materials", [])
        o.set_skeletal_mesh_asset(mesh)
        print("after", o.get_skeletal_mesh_asset().get_name())
if not done:
    raise RuntimeError("outfit component template not found")
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "Hero01_Costume":
        eas.destroy_actor(a)
        print("removed test actor")
    if a.get_actor_label() == "Hero01_Character":
        # The actor already in the level keeps its own copy of the outfit mesh and its two garment materials, so the
        # Blueprint change alone left the default outfit on it (seen in play). The instance is set as well.
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "SkeletalMesh":
                c.set_editor_property("override_materials", [])
                c.set_skeletal_mesh_asset(mesh)
            m = c.get_skeletal_mesh_asset()
            print("level", c.get_name(), m.get_name() if m else None, [x.get_name() for x in c.get_materials()])
        LEVEL = a.get_world().get_path_name().split(".")[0]
print("save", BP, unreal.EditorAssetLibrary.save_asset(BP, only_if_is_dirty=False))
if SAVE_LEVEL:
    print("save", LEVEL, unreal.EditorAssetLibrary.save_asset(LEVEL, only_if_is_dirty=False))
