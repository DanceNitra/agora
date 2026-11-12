"""Prepare a Tripo body GLB for MetaHuman Creator's From Custom Mesh tool.

    blender -b --factory-startup --python clean_body.py -- <in.glb> <out.fbx>

Welds UV-seam duplicates, removes loose parts, fills holes, stands the model on the floor facing -Y in
centimetres, and writes an FBX with the textures beside it. Prints before and after counts.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

src, dst = Path(sys.argv[-2]).resolve(), Path(sys.argv[-1]).resolve()
dst.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(src))
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
assert len(objs) == 1, f"expected one mesh, got {len(objs)}"
obj = objs[0]
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def counts(bm):
    return {
        "vertices": len(bm.verts), "faces": len(bm.faces),
        "boundary_edges": sum(1 for e in bm.edges if e.is_boundary),
        "non_manifold_edges": sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary),
    }


bm = bmesh.new()
bm.from_mesh(obj.data)
before = counts(bm)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
welded = counts(bm)
# Drop degenerate faces left by the weld, then close every hole.
bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context="VERTS")
# Fins: faces that hang on the surface by a non-manifold edge and end in boundary edges. Remove them
# before filling, repeat until none is left.
fins_removed = 0
for _ in range(10):
    fins = [f for f in bm.faces
            if any(e.is_boundary for e in f.edges) and any(len(e.link_faces) > 2 for e in f.edges)]
    if not fins:
        break
    fins_removed += len(fins)
    bmesh.ops.delete(bm, geom=fins, context="FACES")
holes = [e for e in bm.edges if e.is_boundary]
if holes:
    bmesh.ops.holes_fill(bm, edges=holes, sides=0)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
after = counts(bm)
bm.to_mesh(obj.data)
bm.free()

# Feet on the floor, centred, and facing -Y (Blender front). The widest horizontal axis is the arm span.
xs = [v.co.x for v in obj.data.vertices]
ys = [v.co.y for v in obj.data.vertices]
zs = [v.co.z for v in obj.data.vertices]
span_is_y = (max(ys) - min(ys)) > (max(xs) - min(xs))
if span_is_y:
    # Tripo exports the character facing +X; turn it to face -Y.
    obj.data.transform(Matrix.Rotation(-math.pi / 2, 4, "Z"))
xs = [v.co.x for v in obj.data.vertices]
ys = [v.co.y for v in obj.data.vertices]
obj.data.transform(Matrix.Translation((-(max(xs) + min(xs)) / 2, -(max(ys) + min(ys)) / 2, -min(zs))))
obj.data.update()
obj.name = obj.data.name = dst.stem

# The GLB carries packed textures; write them beside the FBX so the exporter can reference them.
for img in bpy.data.images:
    if img.size[0]:
        kind = img.name.split("_")[0]
        img.filepath_raw = str(dst.parent / f"{dst.stem}_{kind}.png")
        img.file_format = "PNG"
        img.save()

size = [max(c) - min(c) for c in zip(*[(v.co.x, v.co.y, v.co.z) for v in obj.data.vertices])]
bpy.ops.export_scene.fbx(
    filepath=str(dst), use_selection=True, object_types={"MESH"}, apply_scale_options="FBX_SCALE_UNITS",
    mesh_smooth_type="FACE", path_mode="COPY", embed_textures=False, add_leaf_bones=False,
)
# Front portrait for the face tracker of conform_to_target_meshes. The camera is written in Unreal units
# and axes (FBX import maps Blender (x, y, z) m to Unreal (x, -y, z) cm), so the solver gets the same camera.
FOV_DEG, DIST_M, PX = 20.0, 1.15, 1024
head_z = size[2] - 0.115
cam_data = bpy.data.cameras.new("portrait")
cam_data.sensor_fit = "HORIZONTAL"
cam_data.angle = math.radians(FOV_DEG)
cam = bpy.data.objects.new("portrait", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (0.0, -DIST_M, head_z)
cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
scene = bpy.context.scene
scene.camera = cam
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "TEXTURE"
scene.render.resolution_x = scene.render.resolution_y = PX
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.color = (0.5, 0.5, 0.5)
scene.world = world
scene.render.filepath = str(dst.parent / f"{dst.stem}_portrait.png")
bpy.ops.render.render(write_still=True)
camera = {"location_cm": [0.0, DIST_M * 100, head_z * 100], "rotation_pitch_yaw_roll": [0.0, -90.0, 0.0],
          "fov_deg": FOV_DEG, "image_px": [PX, PX], "portrait": f"{dst.stem}_portrait.png"}

report = {"source": src.name, "camera_unreal": camera, "before": before, "after_weld": welded, "after_clean": after,
          "fins_removed": fins_removed, "size_m_xyz": [round(s, 4) for s in size], "rotated_90": span_is_y,
          "out": dst.name}
dst.with_suffix(".clean.json").write_text(json.dumps(report, indent=2))
print("CLEAN", json.dumps(report))
