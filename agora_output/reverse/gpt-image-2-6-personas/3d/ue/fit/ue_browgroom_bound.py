# Runs INSIDE Unreal: bind our brow grooms to the face skin the way the MetaHuman brows are bound (GroomBindingAsset
# on the Face skeletal mesh), so the brows follow the skin under every expression instead of riding the head bone.
# Assumes the grooms are already imported by the brow groom script. Binding assets go to /Game/Companions/Brows.
import json
import unreal
CFG = json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\browgroom_cfg.json"))
lib = unreal.EditorAssetLibrary
face = lib.load_asset(CFG["face_mesh"])
seq = lib.load_asset(CFG["seq"])
mh = [b for b in seq.get_bindings() if "MH Depesa" in str(b.get_display_name())][0]
for b in list(seq.get_bindings()):
    if str(b.get_display_name()).startswith("DepesaBrows"):
        b.remove()
mat = lib.load_asset(CFG["material"])
for part in CFG["parts"]:
    g = lib.load_asset("/Game/Companions/Brows/" + part["asset"])
    bpath = "/Game/Companions/Brows/" + part["asset"] + "_Binding"
    if lib.does_asset_exist(bpath):
        lib.delete_asset(bpath)
    bind = unreal.GroomLibrary.create_new_groom_binding_asset_with_path(bpath, g, face, 100, None, 0)
    print("BOUND create", bind.get_path_name() if bind else None)
    lib.save_asset(bpath, only_if_is_dirty=False)
    la = seq.add_spawnable_from_class(unreal.GroomActor)
    la.set_display_name("DepesaBrows_" + part["name"])
    gc = la.get_object_template().get_editor_property("groom_component")
    gc.set_editor_property("groom_asset", g)
    gc.set_editor_property("binding_asset", bind)
    gc.set_material(0, mat)
    gc.set_editor_property("cast_shadow", False)
    at = la.add_track(unreal.MovieScene3DAttachTrack)
    sec = at.add_section()
    sec.set_range(seq.get_playback_start(), seq.get_playback_end())
    sec.set_constraint_binding_id(seq.get_binding_id(mh))
    sec.set_editor_property("attach_component_name", "Face")
    sec.set_editor_property("attach_socket_name", "")
    tr = la.add_track(unreal.MovieScene3DTransformTrack)
    ts = tr.add_section(); ts.set_range(seq.get_playback_start(), seq.get_playback_end())
    for ch, v in zip(ts.get_all_channels()[:9], [0, 0, 0, 0, 0, 0, 1, 1, 1]):
        ch.set_default(v)
lib.save_loaded_asset(seq, only_if_is_dirty=False)
print("BOUND done")
