"""Decimated copy of a costume FBX for Chaos cloth simulation: same armature, weights carried by the decimation, no
underlayer faces needed. Chaos cloth runs a few thousand vertices; the full costume has 82 k.

    blender_headless.sh costume_sim_proxy.py -- <costume.fbx> <out.fbx> [ratio]
"""
import sys
from pathlib import Path

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
src, dst = str(Path(args[0]).resolve()), str(Path(args[1]).resolve())
ratio = float(args[2]) if len(args) > 2 else 0.06
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
n0 = len(mesh.data.vertices)
bpy.context.view_layer.objects.active = mesh
mod = mesh.modifiers.new("dec", "DECIMATE")
mod.ratio = ratio
mod.use_collapse_triangulate = True
# the armature modifier must stay after the decimation so the export keeps the skin binding
bpy.ops.object.modifier_move_to_index(modifier="dec", index=0)
bpy.ops.object.modifier_apply(modifier="dec")
print("PROXY", n0, "->", len(mesh.data.vertices), "vertices,", len(mesh.data.polygons), "faces", flush=True)
for o in bpy.data.objects:
    o.select_set(o in (arm, mesh))
# the same export settings as costume_build.py, so Unreal binds it to the same skeleton
bpy.ops.export_scene.fbx(filepath=dst, use_selection=True, object_types={"ARMATURE", "MESH", "EMPTY"},
                         add_leaf_bones=False, bake_anim=False, mesh_smooth_type="FACE")
print("WROTE", dst, flush=True)
