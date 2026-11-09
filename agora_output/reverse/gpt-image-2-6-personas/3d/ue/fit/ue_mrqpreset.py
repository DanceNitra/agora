# Runs INSIDE Unreal: save a Movie Pipeline config preset for the out-of-editor render. No rendering here.
import unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
DIR, NAME = "/Game/Companions/Lipsync", "MRQ_Depesa_portrait"
lib = unreal.EditorAssetLibrary
c = lib.load_asset(DIR + "/" + NAME) if lib.does_asset_exist(DIR + "/" + NAME) else \
    unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, DIR, unreal.MoviePipelinePrimaryConfig, None)
out = c.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
out.output_directory = unreal.DirectoryPath(F + r"\render_v5")
out.output_resolution = unreal.IntPoint(1080, 1440)
out.file_name_format = "{frame_number}"
c.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
c.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
aa = c.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
aa.override_anti_aliasing = True
aa.spatial_sample_count = 1
aa.temporal_sample_count = 4
aa.engine_warm_up_count = 8
cv = c.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
cv.add_or_update_console_variable("r.Shadow.Virtual.Enable", 0.0)
c.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
print("PRESET", lib.save_loaded_asset(c, only_if_is_dirty=False), c.get_path_name())
