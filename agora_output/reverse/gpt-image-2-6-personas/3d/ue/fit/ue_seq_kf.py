# Runs INSIDE Unreal. Builds LS_<name>: the lip-sync performance exported onto BP_MH_Depesa (spawnable, far
# from the level), plus a spawnable portrait CineCamera with manual exposure and three spawnable point lights.
# Nothing is added to the open level; everything lives in the sequence under /Game/Companions/Lipsync.
import json
import unreal

F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\lipsync_cfg.json"))
DIR = "/Game/Companions/Lipsync"
lib = unreal.EditorAssetLibrary
name = cfg["name"]
ORIGIN = unreal.Vector(0.0, 300000.0, 100000.0)
HEAD_Z = 164.0

perf = lib.load_asset(DIR + "/MHP_" + name)
bp = lib.load_asset("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/BP_MH_DepesaKF")
n = 2
while lib.does_asset_exist(DIR + "/LS_KF_%s_v%d" % (name, n)):
    n += 1
SEQ_NAME = "LS_KF_%s_v%d" % (name, n)
s = unreal.MetaHumanPerformanceExportLevelSequenceSettings()
for k, v in {"show_export_dialog": False, "package_path": DIR, "asset_name": SEQ_NAME,
             "target_meta_human_class": bp, "export_audio_track": True, "export_camera": False,
             "export_video_track": False, "export_image_plane": False, "export_identity": False,
             "export_depth_track": False, "export_control_rig_track": True,
             "enable_meta_human_head_movement": True}.items():
    s.set_editor_property(k, v)
seq = unreal.MetaHumanPerformanceExportUtils.export_level_sequence(perf, s)
print("SEQ", seq.get_path_name() if seq else None)


def const_transform(binding, loc, rot):
    old = [t for t in binding.get_tracks() if isinstance(t, unreal.MovieScene3DTransformTrack)]
    for t in old:
        binding.remove_track(t)
    tr = binding.add_track(unreal.MovieScene3DTransformTrack)
    sec = tr.add_section()
    sec.set_range(-100000, 1000000)
    ch = sec.get_all_channels()
    for c, v in zip(ch[:6], [loc.x, loc.y, loc.z, rot.roll, rot.pitch, rot.yaw]):
        c.set_default(v)


# move the MetaHuman far from the level geometry
for b in seq.get_bindings():
    if "MH Depesa" in str(b.get_display_name()) or "DepesaKF" in str(b.get_display_name()) or "Depesa KF" in str(b.get_display_name()) or "MH_Depesa" in str(b.get_display_name()):
        const_transform(b, ORIGIN, unreal.Rotator(0, 0, 0))
        print("MH binding", b.get_display_name())

head = unreal.Vector(ORIGIN.x, ORIGIN.y, ORIGIN.z + HEAD_Z)
cam = seq.add_spawnable_from_class(unreal.CineCameraActor)
const_transform(cam, unreal.Vector(head.x, head.y + cfg.get("dist", 110.0), head.z + 2.0), unreal.Rotator(0, -1, -90))
cam_obj = seq.get_bound_objects(cam) if hasattr(seq, "get_bound_objects") else None
tmpl = cam.get_object_template()
cc = tmpl.get_editor_property("camera_component")
fb = cc.get_editor_property("filmback")
fb.set_editor_property("sensor_width", 24.0)
fb.set_editor_property("sensor_height", 32.0)
cc.set_editor_property("filmback", fb)
cc.set_editor_property("current_focal_length", 85.0)
fs = cc.get_editor_property("focus_settings")
fs.set_editor_property("focus_method", unreal.CameraFocusMethod.MANUAL)
fs.set_editor_property("manual_focus_distance", cfg.get("dist", 110.0) - 12.0)
cc.set_editor_property("current_aperture", 16.0)
cc.set_editor_property("focus_settings", fs)
pp = cc.get_editor_property("post_process_settings")
pp.set_editor_property("override_auto_exposure_method", True)
pp.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
pp.set_editor_property("override_auto_exposure_bias", True)
pp.set_editor_property("auto_exposure_bias", cfg.get("bias", 2.0))
pp.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
pp.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
pp.set_editor_property("override_depth_of_field_fstop", True)
pp.set_editor_property("depth_of_field_fstop", 16.0)
cc.set_editor_property("post_process_settings", pp)
cut = seq.add_track(unreal.MovieSceneCameraCutTrack)
csec = cut.add_section()
csec.set_range(seq.get_playback_start(), seq.get_playback_end())
csec.set_camera_binding_id(seq.get_binding_id(cam) if hasattr(seq, "get_binding_id") else cam.get_binding_id())

for i, (dx, dy, dz, inten) in enumerate([(0, 70, 10, 0.6), (-60, 50, 20, 0.25), (60, 50, 20, 0.25)]):
    lb = seq.add_spawnable_from_class(unreal.PointLight)
    const_transform(lb, unreal.Vector(head.x + dx, head.y + dy, head.z + dz), unreal.Rotator(0, 0, 0))
    lc = lb.get_object_template().get_editor_property("point_light_component")
    lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    lc.set_editor_property("intensity", inten)
    lc.set_editor_property("light_color", unreal.Color(255, 233, 214) if i == 0 else unreal.Color(255, 230, 230))
    lc.set_editor_property("attenuation_radius", 400.0)
print("RANGE", seq.get_playback_start(), seq.get_playback_end(), "fps", seq.get_display_rate())
lib.save_loaded_asset(seq, only_if_is_dirty=False)
print("SAVED seq")
