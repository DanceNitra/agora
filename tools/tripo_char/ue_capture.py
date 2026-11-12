"""Runs inside Unreal. Renders the preview level from fixed cameras with a SceneCapture2D into PNG files.
The capture actor and the render target are transient; the level is not saved."""
import json

import unreal

CFG = json.load(open(r"C:\Users\Danculus\agora\tools\tripo_char\current.json"))
OUT = CFG["shots_out"]
# name: (x, y, z, pitch, yaw, fov); cm and degrees; the hero faces +Y
SHOTS = {"full_front": (0, 430, 95, 0, -90, 28), "full_back": (0, -430, 95, 0, 90, 28), "full_side": (430, 0, 95, 0, 180, 28),
         "face": (0, 90, 170, 0, -90, 22), "face_34": (60, 70, 170, 0, -130.6, 22), "face_side": (90, 2, 170, 0, 180, 22),
         "hand_l": (-135, 8, 84, 0, 0, 20), "hand_r": (135, 8, 84, 0, 180, 20), "feet": (0, 120, 40, -17, -90, 26)}
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
rt = unreal.RenderingLibrary.create_render_target2d(world, 1100, 1100, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
try:
    c = cap.capture_component2d
    c.texture_target = rt
    c.capture_source = unreal.SceneCaptureSource.SCS_FINAL_TONE_CURVE_HDR
    c.capture_every_frame = False
    c.capture_on_movement = False
    for name, (x, y, z, p, yaw, fov) in SHOTS.items():
        cap.set_actor_location_and_rotation(unreal.Vector(x, y, z), unreal.Rotator(roll=0, pitch=p, yaw=yaw), False, False)
        c.fov_angle = fov
        for _ in range(3):
            c.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, name + ".png")
        print("shot", name)
finally:
    eas.destroy_actor(cap)
