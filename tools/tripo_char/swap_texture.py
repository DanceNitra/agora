"""Replace a GLB's base colour image (and optionally add an emission map) and write a new GLB.

  ./blender_headless.sh swap_texture.py -- <in.glb> <base_color.png> <out.glb> [<emission.png> [strength]]
"""
import sys
from pathlib import Path

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
src, tex, out = (Path(a).resolve() for a in args[:3])
emit_path = Path(args[3]).resolve() if len(args) > 3 else None
emit_strength = float(args[4]) if len(args) > 4 else 3.0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(src))
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
mat = mesh.data.materials[0]
bsdf = next(nd for nd in mat.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
node = bsdf.inputs["Base Color"].links[0].from_node
node.image = bpy.data.images.load(str(tex))
if emit_path:
    enode = mat.node_tree.nodes.new("ShaderNodeTexImage")
    enode.image = bpy.data.images.load(str(emit_path))
    uvsrc = node.inputs["Vector"].links[0].from_socket if node.inputs["Vector"].links else None
    if uvsrc:
        mat.node_tree.links.new(uvsrc, enode.inputs["Vector"])
    mat.node_tree.links.new(enode.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = emit_strength
for o in bpy.data.objects:
    o.select_set(o == mesh)
bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", use_selection=True)
print("done", out)
