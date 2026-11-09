# Runs INSIDE Unreal: render LS_Depesa_line1_v3 with Movie Render Queue (PIE executor) to PNG frames.
import unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
qs = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
q = qs.get_queue()
for j in list(q.get_jobs()):
    q.delete_job(j)
job = q.allocate_new_job(unreal.MoviePipelineExecutorJob)
job.sequence = unreal.SoftObjectPath("/Game/Companions/Lipsync/LS_Depesa_line1_v2.LS_Depesa_line1_v2")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
job.map = unreal.SoftObjectPath(world.get_path_name())
job.job_name = "Depesa_lipsync_v4"
c = job.get_configuration()
out = c.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
out.output_directory = unreal.DirectoryPath(F + r"\render_v4")
out.output_resolution = unreal.IntPoint(1080, 1440)
out.file_name_format = "{frame_number}"
c.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
c.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
aa = c.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
aa.spatial_sample_count = 1
aa.temporal_sample_count = 4
aa.override_anti_aliasing = True
aa.render_warm_up_frames = True
aa.engine_warm_up_count = 8
cv = c.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
for k, v in (("r.Shadow.Virtual.Enable", 0.0), ("r.MotionBlurQuality", 0.0)):
    cv.add_or_update_console_variable(k, v)
qs.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
print("MRQ started", world.get_path_name())
