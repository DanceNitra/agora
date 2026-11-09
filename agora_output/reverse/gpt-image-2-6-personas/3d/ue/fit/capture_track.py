# Runs inside Unreal. Reads fit/cfg.json: {"asset", "coeffs" (optional list), "tag"}.
# Ensures a transient actor of the character far from the level, captures its face from the front with a
# SceneCapture2D into a 512x768 render target, tracks landmarks, writes fit/<tag>_lm.json and <tag>.png.
import unreal, json, os, time
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(os.path.join(F, "cfg.json")))
W, H = 512, 768
LOC = unreal.Vector(0.0, 300000.0, 100000.0)
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
ch = unreal.EditorAssetLibrary.load_asset(cfg["asset"])
if not mhs.is_object_added_for_editing(ch):
    mhs.try_add_object_to_edit(ch)
if cfg.get("coeffs"):
    mhs.set_face_model_coefficients(ch, cfg["coeffs"])
actor = None
for a in eas.get_all_level_actors():
    if a.get_actor_label().startswith("FIT_MH"):
        actor = a
if actor is None:
    mhs.assemble_for_preview(ch)
    actor = mhs.spawn_meta_human_actor(ch, True)
    actor.set_actor_label("FIT_MH")
    actor.set_actor_location(LOC, False, False)
    actor.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
head = None
for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
    if c.does_socket_exist("FACIAL_C_FacialRoot") or c.does_socket_exist("head"):
        head = c.get_socket_location("head") if c.does_socket_exist("head") else c.get_socket_location("FACIAL_C_FacialRoot")
        break
if head is None:
    head = unreal.Vector(LOC.x, LOC.y, LOC.z + 160)
cap = None
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "FIT_CAP":
        cap = a
if cap is None:
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0))
    cap.set_actor_label("FIT_CAP")
    cap.set_flags(unreal.ObjectFlags.TRANSIENT) if hasattr(cap, "set_flags") else None
comp = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8)
comp.set_editor_property("texture_target", rt)
comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
comp.set_editor_property("fov_angle", 14.0)
dist = 260.0
cam = unreal.Vector(head.x, head.y + dist, head.z + 3.0)
cap.set_actor_location(cam, False, False)
cap.set_actor_rotation(unreal.Rotator(0, -90, 0), False)
comp.capture_scene()
cols = unreal.RenderingLibrary.read_render_target(world, rt, False)
res = mhs.track_face_landmarks_from_image(cols, W, H)
out = {}
if res:
    for k, tp in res.items():
        out[str(k)] = [[p.x, p.y] for p in tp.get_editor_property("tracking_points")]
tag = cfg.get("tag", "cur")
json.dump(out, open(os.path.join(F, tag + "_lm.json"), "w"))
unreal.RenderingLibrary.export_render_target(world, rt, F, tag)
print("head", head, "curves", len(out), "pixels", len(cols))
