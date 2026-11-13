"""Runs inside Unreal. Renders Yuki's face in L_Yuki_Preview to a PNG through a SceneCapture2D, so the picture does not
depend on the editor window (a minimized or covered editor fails CaptureEditorImage).

A wrapper sets ARGS = dict(...) with OUT (png path) and may set STATE ("all", "nohair", "noshadow"), BROWS (False hides the brow groom), DIST,
FOV, DZ, DX, PX, YAW, PASSES and BRIGHTNESS (the fixed exposure in EV100; lower is brighter).
The camera looks at the face root from DIST cm; with FOV 2.6 at 700 cm the frame is about 32 cm wide: a long lens, so
the picture compares with a front portrait. The capture is repeated so temporal effects settle. Changes no asset; the
capture actor Yuki_ShotCam stays in the level. The hair groom's cast shadow is left as STATE set it."""
import math
import os

import unreal

# Wrapper values arrive in one dict, ARGS, which is taken out of the globals before anything else runs. The editor's
# Python keeps its globals between runs: single variables set by a wrapper became the defaults of later runs, also
# when a run failed half way (2026-11-13: a close-up's FOV, an old iris scale and PIE=True leaked that way).
_A = globals().pop("ARGS", {})


OUT = _A.get("OUT", r"C:\Users\Danculus\agora\tools\tripo_char\reports\yuki_shot.png")
STATE = _A.get("STATE", "noshadow")
DIST, FOV = _A.get("DIST", 700.0), _A.get("FOV", 2.6)
DZ, DX, PX, YAW = _A.get("DZ", -1.0), _A.get("DX", 0.0), _A.get("PX", 1400), _A.get("YAW", 0.0)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
PIE = _A.get("PIE", False)     # True: render the play copy (Play-in-Editor running), where the face pose is live
if PIE:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    allact = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))
    ch = next(a for a in allact if "MHC_Yuki" in a.get_class().get_name())
    hair = next((a for a in allact if isinstance(a, unreal.GroomActor)), None)
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)   # the project's play pawn stood in the frame
    if pawn:
        pawn.set_actor_hidden_in_game(True)
        print("PAWN hidden", pawn.get_class().get_name())
else:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    ch, hair = acts["Yuki_Character"], acts.get("Yuki_Hair")
face = next(c for c in ch.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Face")
head = face.get_socket_location("FACIAL_C_FacialRoot")
hg = list(hair.get_components_by_class(unreal.GroomComponent)) if hair else []
for g in hg:
    g.set_visibility(STATE != "nohair")
    g.set_cast_shadow(STATE != "noshadow")
for g in ch.get_components_by_class(unreal.GroomComponent):
    if g.get_name() == "Eyebrows":
        g.set_visibility(_A.get("BROWS", True))
# Full detail: a freshly placed MetaHuman rendered in a low LOD through the capture (faceted skull, eye shell showing
# as a white rim, 2026-11-13). The LODSync component drives every mesh, so it is forced too.
for c in ch.get_components_by_class(unreal.SkeletalMeshComponent):
    c.set_forced_lod(1)
for c in ch.get_components_by_class(unreal.ActorComponent):
    if c.get_class().get_name() == "LODSyncComponent":
        c.set_editor_property("forced_lod", 0)
a = math.radians(YAW)
loc = unreal.Vector(head.x + DX + DIST * math.sin(a), head.y + DIST * math.cos(a), head.z + DZ)
rot = unreal.Rotator(roll=0, pitch=0, yaw=-90 - YAW)
# The capture actor Yuki_ShotCam lives in the level: Python cannot spawn an actor into the play world, so the play copy
# of this one is used there. Run one shot outside play first if the level does not have it yet.
if PIE:
    cap = next((a for a in allact if isinstance(a, unreal.SceneCapture2D)), None)
    if cap is None:
        raise RuntimeError("no SceneCapture2D in the play world: take one shot outside play first, then start play")
else:
    cap = acts.get("Yuki_ShotCam")
    if cap is None:
        cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, loc, rot)
        cap.set_actor_label("Yuki_ShotCam")
cap.set_actor_location_and_rotation(loc, rot, False, True)
cc = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
rt = unreal.RenderingLibrary.create_render_target2d(world, PX, PX, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cc.set_editor_property("texture_target", rt)
cc.set_editor_property("fov_angle", FOV)
cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_TONE_CURVE_HDR)
cc.set_editor_property("capture_every_frame", False)
cc.set_editor_property("capture_on_movement", False)
cc.set_editor_property("always_persist_rendering_state", True)
# fixed exposure: a scene capture has no eye adaptation history, and auto exposure blew the skin out to white
pp = cc.get_editor_property("post_process_settings")
B = _A.get("BRIGHTNESS", -0.8)   # EV100: the project uses the extended luminance range
for k, v in (("auto_exposure_min_brightness", B), ("auto_exposure_max_brightness", B), ("auto_exposure_bias", 0.0)):
    pp.set_editor_property("override_" + k, True)
    pp.set_editor_property(k, v)
cc.set_editor_property("post_process_settings", pp)
cc.set_editor_property("post_process_blend_weight", 1.0)
for _ in range(_A.get("PASSES", 24)):
    cc.capture_scene()
d, f = os.path.split(OUT)
os.makedirs(d, exist_ok=True)
unreal.RenderingLibrary.export_render_target(world, rt, d, f)
print("SHOT", STATE, OUT, os.path.exists(OUT) or os.path.exists(OUT + ".png"))
