# Runs INSIDE Unreal: switch the camera in arc_target.json to the device framing (1:2 portrait, head and shoulders)
# and save a render preset that writes 640x1280 frames to render_dev.
import json
import unreal
lib = unreal.EditorAssetLibrary
seq = lib.load_asset(json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\arc_target.json"))["seq"])
for b in seq.get_bindings():
    if "Cine Camera" in str(b.get_display_name()):
        cc = b.get_object_template().get_editor_property("camera_component")
        fb = cc.get_editor_property("filmback")
        fb.set_editor_property("sensor_width", 16.0)
        fb.set_editor_property("sensor_height", 32.0)
        cc.set_editor_property("filmback", fb)
        cc.set_editor_property("current_focal_length", 85.0)
        for t in b.get_tracks():
            if isinstance(t, unreal.MovieScene3DTransformTrack):
                ch = t.get_sections()[0].get_all_channels()
                ch[1].set_default(300000.0 + 105.0)
                ch[2].set_default(100000.0 + 158.0)
        fs = cc.get_editor_property("focus_settings")
        fs.set_editor_property("manual_focus_distance", 93.0)
        cc.set_editor_property("focus_settings", fs)
        print("DEVCAM set")
lib.save_loaded_asset(seq, only_if_is_dirty=False)
DIR, NAME = "/Game/Companions/Lipsync", "MRQ_Depesa_device"
c = lib.load_asset(DIR + "/" + NAME) if lib.does_asset_exist(DIR + "/" + NAME) else \
    unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, DIR, unreal.MoviePipelinePrimaryConfig, None)
out = c.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
out.output_directory = unreal.DirectoryPath(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\render_dev")
out.output_resolution = unreal.IntPoint(640, 1280)
out.file_name_format = "{frame_number}"
c.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
c.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
aa = c.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
aa.override_anti_aliasing = True
aa.spatial_sample_count = 1
aa.temporal_sample_count = 4
aa.engine_warm_up_count = 8
c.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting).add_or_update_console_variable("r.Shadow.Virtual.Enable", 0.0)
c.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
print("PRESET", lib.save_loaded_asset(c, only_if_is_dirty=False))
