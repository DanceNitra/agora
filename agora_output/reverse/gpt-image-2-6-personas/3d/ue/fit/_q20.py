import unreal, json
lib = unreal.EditorAssetLibrary
seq = lib.load_asset("/Game/Companions/Lipsync/LS_KF_Depesa_lajk_confidence_v5")
LSE = unreal.LevelSequenceEditorBlueprintLibrary
LSE.open_level_sequence(seq); LSE.set_current_time(57); LSE.refresh_current_level_sequence()
out = {}
def T(t): 
    r = t.rotation.rotator()
    return {"loc": [t.translation.x, t.translation.y, t.translation.z], "rot_rpy": [r.roll, r.pitch, r.yaw], "q": [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w]}
for b in seq.get_bindings():
    n = str(b.get_display_name())
    for o in LSE.get_bound_objects(seq.get_binding_id(b)):
        if n == "Cine Camera Actor" and isinstance(o, unreal.Actor):
            cc = o.get_cine_camera_component()
            fb = cc.get_editor_property("filmback")
            out["cam"] = T(cc.get_world_transform())
            out["focal"] = cc.get_editor_property("current_focal_length")
            out["sensor"] = [fb.sensor_width, fb.sensor_height]
            out["aspect_ratio_axis"] = str(cc.get_editor_property("aspect_ratio_axis_constraint")) if hasattr(cc, "aspect_ratio_axis_constraint") else None
        if n == "BP MH Depesa KF" and isinstance(o, unreal.Actor):
            for c in o.get_components_by_class(unreal.SkeletalMeshComponent):
                if c.get_name() == "Face":
                    out["face_comp"] = T(c.get_world_transform())
                    out["head_world"] = T(c.get_socket_transform("head", unreal.RelativeTransformSpace.RTS_WORLD))
                    out["head_comp"] = T(c.get_socket_transform("head", unreal.RelativeTransformSpace.RTS_COMPONENT))
LSE.close_level_sequence()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tmp = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, -100000))
smc = tmp.get_editor_property("skeletal_mesh_component")
smc.set_skinned_asset_and_update(lib.load_asset("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Face/SKM_MH_DepesaKF_FaceMesh"))
out["head_ref_comp"] = T(smc.get_socket_transform("head", unreal.RelativeTransformSpace.RTS_COMPONENT))
eas.destroy_actor(tmp)
json.dump(out, open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\makeup\ue_camera57.json", "w"), indent=1)
print("PRM", json.dumps(out)[:900])
