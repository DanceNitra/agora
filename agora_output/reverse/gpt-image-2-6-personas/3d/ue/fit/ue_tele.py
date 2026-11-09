# Runs INSIDE Unreal. MODE "shoot": aims FIT_CAP as a portrait telephoto at the head and renders.
# MODE "save": exports the render target written by the previous call (one tick later) as tele_<tag>.png.
import unreal, json
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\tele_cfg.json"))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
cap = [a for a in eas.get_all_level_actors() if a.get_actor_label() == "FIT_CAP"][0]
comp = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
if cfg["mode"] == "shoot":
    rt = unreal.RenderingLibrary.create_render_target2d(world, cfg["w"], cfg["h"], unreal.TextureRenderTargetFormat.RTF_RGBA8)
    comp.set_editor_property("texture_target", rt)
    comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    comp.set_editor_property("fov_angle", cfg["fov"])
    pp = comp.get_editor_property("post_process_settings")
    pp.set_editor_property("override_auto_exposure_method", True)
    pp.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    pp.set_editor_property("override_auto_exposure_bias", True)
    pp.set_editor_property("auto_exposure_bias", cfg.get("bias", 2.0))
    comp.set_editor_property("post_process_settings", pp)
    comp.set_editor_property("post_process_blend_weight", 1.0)
    comp.set_editor_property("capture_every_frame", True)
    h = cfg["head"]
    cap.set_actor_location(unreal.Vector(h[0], h[1] + cfg["dist"], h[2] + cfg.get("dz", 0.0)), False, False)
    cap.set_actor_rotation(unreal.Rotator(0, -90, 0), False)
    comp.capture_scene()
    print("SHOT")
else:
    rt = comp.get_editor_property("texture_target")
    comp.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, F, "tele_" + cfg["tag"])
    print("SAVED")
