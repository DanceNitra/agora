"""Turntable: the robot turns 360 degrees in front of the fixed hero camera, Cycles, PNG frames.

blender -b robot_v08_iterate1.blend -P render_turntable.py -- <out_dir> [samples] [seconds]
"""
import math
import os
import sys
import time

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, SAMPLES = argv[0], int(argv[1]) if len(argv) > 1 else 128
SECONDS = float(argv[2]) if len(argv) > 2 else 6.0
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type != "CPU"
sc.cycles.device, sc.cycles.samples, sc.cycles.use_denoising = "GPU", SAMPLES, True

hero = bpy.data.objects["cam_hero"]
hero.location = (3.35, -4.6, 1.75)
hero.rotation_mode = "QUATERNION"
hero.rotation_quaternion = (Vector((0, 0, 0.72)) - hero.location).to_track_quat("-Z", "Y")
hero.data.dof.focus_distance = (Vector((0.0, -0.6, 1.13)) - hero.location).length
sc.camera = hero
bpy.data.objects["studio_backdrop"].rotation_euler.z = math.atan2(hero.location.x, -hero.location.y)

fps = 24
sc.render.fps = fps
sc.frame_start, sc.frame_end = 1, int(fps * SECONDS)
robot = bpy.data.objects["robot_root"]
robot.rotation_mode = "XYZ"
robot.animation_data_clear()
robot.rotation_euler.z = 0.0
robot.keyframe_insert("rotation_euler", index=2, frame=sc.frame_start)
robot.rotation_euler.z = math.radians(360) * (sc.frame_end) / (sc.frame_end - sc.frame_start + 1)
robot.keyframe_insert("rotation_euler", index=2, frame=sc.frame_end + 1)
for fc in robot.animation_data.action.fcurves if hasattr(robot.animation_data.action, "fcurves") else []:
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"
try:
    for layer in robot.animation_data.action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "LINEAR"
except AttributeError:
    pass

sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.image_settings.file_format = "PNG"
t0 = time.time()
for f in range(sc.frame_start, sc.frame_end + 1):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(OUT, f"tt_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    if f % 12 == 0 or f == sc.frame_start:
        el = time.time() - t0
        print(f"[turntable] {f}/{sc.frame_end} frames, {el:.0f} s, rot {math.degrees(robot.rotation_euler.z):.0f} deg", flush=True)
print(f"[turntable] all done in {time.time() - t0:.0f} s", flush=True)
