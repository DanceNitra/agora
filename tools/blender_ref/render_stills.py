"""Step 08 RENDER: Cycles stills of the robot, run in a background Blender.

blender -b robot_v06_lighting.blend -P render_stills.py -- <out_dir> [samples]

Renders the hero (16:9 and 9:16), three close-ups, and front and side views whose cameras match
the concept-sheet views. Adds a glare node so the emissive parts bloom.
"""
import math
import os
import sys
import time

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0]
SAMPLES = int(argv[1]) if len(argv) > 1 else 256
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene

try:
    sc.render.engine = "CYCLES"
except TypeError as e:
    print("engines:", e)
prefs = bpy.context.preferences.addons["cycles"].preferences
for backend in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = backend
        prefs.get_devices()
        if any(d.type == backend for d in prefs.devices):
            break
    except TypeError:
        continue
for d in prefs.devices:
    d.use = d.type != "CPU"
sc.cycles.device = "GPU"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.render.film_transparent = False
sc.render.image_settings.file_format = "PNG"
print("cycles device", prefs.compute_device_type, [d.name for d in prefs.devices if d.use], flush=True)

# glare on emissive parts; the compositor API moved to node groups in Blender 5
try:
    ng = bpy.data.node_groups.new("robot_glare", "CompositorNodeTree")
    rl = ng.nodes.new("CompositorNodeRLayers")
    gl = ng.nodes.new("CompositorNodeGlare")
    out = ng.nodes.new("NodeGroupOutput")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    for name, val in (("Type", "Bloom"), ("Quality", "High")):
        if name in gl.inputs:
            gl.inputs[name].default_value = val
    if hasattr(gl, "glare_type"):
        gl.glare_type = "BLOOM"
    for name, val in (("Threshold", 1.0), ("Strength", 0.35), ("Size", 0.4)):
        if name in gl.inputs:
            gl.inputs[name].default_value = val
    ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
    ng.links.new(gl.outputs["Image"], out.inputs[0])
    sc.compositing_node_group = ng
    sc.render.use_compositing = True
    print("glare node group set", flush=True)
except Exception as e:  # keep rendering without bloom rather than stop
    print("glare skipped:", repr(e), flush=True)


def cam(name, loc, target, lens=50, dof=None):
    c = bpy.data.cameras.new(name)
    c.lens = lens
    o = bpy.data.objects.new(name, c)
    bpy.data.collections["CAMERAS"].objects.link(o)
    o.location = loc
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    if dof:
        c.dof.use_dof = True
        c.dof.focus_distance = (Vector(dof) - Vector(loc)).length
        c.dof.aperture_fstop = 4.0
    return o


for cname, loc in (("cam_front", (0, -5.2, 1.45)), ("cam_side", (5.2, 0, 1.45))):
    c = bpy.data.objects[cname]
    c.location = loc
    c.rotation_mode = "QUATERNION"
    c.rotation_quaternion = (Vector((0, 0, 0.78)) - Vector(loc)).to_track_quat("-Z", "Y")
hero = bpy.data.objects["cam_hero"]
hero.location = (3.35, -4.6, 1.75)
hero.rotation_quaternion = (Vector((0, 0, 0.72)) - hero.location).to_track_quat("-Z", "Y")
hero.data.dof.focus_distance = (Vector((0.0, -0.6, 1.13)) - hero.location).length

a = math.radians(-39.5)
leg_dir = Vector((math.cos(a), math.sin(a), 0))
hub = leg_dir * 0.98 + Vector((0, 0, 0.84))
foot = leg_dir * 1.17 + Vector((0, 0, 0.07))
side = Vector((math.cos(a - math.pi / 2), math.sin(a - math.pi / 2), 0))
jobs = [
    ("hero_16x9", bpy.data.objects["cam_hero"], (1920, 1080)),
    ("hero_9x16", bpy.data.objects["cam_hero"], (1080, 1920)),
    ("front_view", bpy.data.objects["cam_front"], (1248, 832)),
    ("side_view", bpy.data.objects["cam_side"], (1248, 832)),
    ("closeup_sensor", cam("cam_close_sensor", (0.6, -1.95, 1.2), (0, -0.58, 1.13), 85, (0, -0.6, 1.13)), (1600, 1067)),
    ("closeup_joint", cam("cam_close_joint", tuple(hub + side * 0.9 + leg_dir * 0.25 + Vector((0, 0, 0.12))), tuple(hub), 85, tuple(hub)), (1600, 1067)),
    ("closeup_foot", cam("cam_close_foot", tuple(foot + leg_dir * 0.9 + side * 0.35 + Vector((0, 0, 0.15))), tuple(foot), 85, tuple(foot)), (1600, 1067)),
]
only = argv[2].split(",") if len(argv) > 2 else None
MASK_MODE = len(argv) > 3 and argv[3] == "mask"
if MASK_MODE:  # silhouette renders for the overlay check: no studio, transparent film
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = "RGBA"
    bpy.data.objects["studio_backdrop"].hide_render = True
    sc.render.use_compositing = False
for name, camera, (w, h) in jobs:
    if only and name not in only:
        continue
    sc.camera = camera
    # turn the seamless backdrop to face this camera, so no view sees past its edge
    cl = camera.matrix_world.translation
    bpy.data.objects["studio_backdrop"].rotation_euler.z = math.atan2(cl.x, -cl.y)
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.filepath = os.path.join(OUT, name + ".png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[render] {name} {w}x{h} done in {time.time() - t0:.1f} s", flush=True)
print("[render] all done", flush=True)
