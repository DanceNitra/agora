# Runs INSIDE Unreal: import our clumped-lash Alembic parts as GroomAssets under /Game/Companions/Lashes and add one
# spawnable GroomActor per part to the render sequence, attached to a lid joint of the MetaHuman Face component, so
# the lashes follow the blinks. The grooms are authored in face-component space, so each actor gets the inverse of
# its joint's reference pose as its relative transform. The reference pose is read from a temporary, unanimated
# SkeletalMeshActor that is destroyed straight away (the level is not saved).
import json
import unreal

CFG = json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\lashgroom_cfg.json"))
lib = unreal.EditorAssetLibrary
DIR = "/Game/Companions/Lashes"

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tmp = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, -100000))
smc = tmp.get_editor_property("skeletal_mesh_component")
smc.set_skinned_asset_and_update(lib.load_asset(CFG["face_mesh"]))
ref = {p["socket"]: smc.get_socket_transform(p["socket"], unreal.RelativeTransformSpace.RTS_COMPONENT) for p in CFG["parts"]}
eas.destroy_actor(tmp)

seq = lib.load_asset(CFG["seq"])
mh = [b for b in seq.get_bindings() if "MH Depesa" in str(b.get_display_name())][0]
for b in list(seq.get_bindings()):
    if str(b.get_display_name()).startswith("DepesaLashes"):
        b.remove()
mat = lib.load_asset(CFG["material"])
for part in CFG["parts"]:
    opts = unreal.GroomImportOptions()
    conv = opts.get_editor_property("conversion_settings")
    conv.set_editor_property("rotation", unreal.Vector(*CFG["rot"]))
    conv.set_editor_property("scale", unreal.Vector(*CFG["scale"]))
    opts.set_editor_property("conversion_settings", conv)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", part["abc"])
    t.set_editor_property("destination_path", DIR)
    t.set_editor_property("destination_name", part["asset"])
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    t.set_editor_property("options", opts)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    g = lib.load_asset(DIR + "/" + part["asset"])

    la = seq.add_spawnable_from_class(unreal.GroomActor)
    la.set_display_name("DepesaLashes_" + part["name"])
    gc = la.get_object_template().get_editor_property("groom_component")
    gc.set_editor_property("groom_asset", g)
    gc.set_material(0, mat)
    gc.set_editor_property("cast_shadow", CFG.get("cast_shadow", False))
    at = la.add_track(unreal.MovieScene3DAttachTrack)
    sec = at.add_section()
    sec.set_range(seq.get_playback_start(), seq.get_playback_end())
    sec.set_constraint_binding_id(seq.get_binding_id(mh))
    sec.set_editor_property("attach_component_name", CFG["component"])
    sec.set_editor_property("attach_socket_name", part["socket"])
    inv = ref[part["socket"]].inverse()
    r = inv.rotation.rotator()
    tr = la.add_track(unreal.MovieScene3DTransformTrack)
    ts = tr.add_section()
    ts.set_range(seq.get_playback_start(), seq.get_playback_end())
    vals = [inv.translation.x, inv.translation.y, inv.translation.z, r.roll, r.pitch, r.yaw, 1.0, 1.0, 1.0]
    for ch, v in zip(ts.get_all_channels()[:9], vals):
        ch.set_default(v)
    print("LASHGROOM", part["name"], g.get_path_name() if g else None, part["socket"], [round(v, 3) for v in vals[:6]])
lib.save_loaded_asset(seq, only_if_is_dirty=False)
print("LASHGROOM done")
