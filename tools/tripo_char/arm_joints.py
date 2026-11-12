"""blender -b --factory-startup --python arm_joints.py -- <metahuman_body.fbx>
Prints the arm joint positions and the mesh cross-section centre at each joint, to see whether joints sit inside the arm."""
import sys
import bpy
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=sys.argv[-1])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
pts = [m.matrix_world @ v.co for m in meshes for v in m.data.vertices]
names = ["clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "middle_01_l", "thigh_l", "calf_l", "foot_l", "spine_05", "head"]
pos = {n: arm.matrix_world @ arm.data.bones[n].head_local for n in names if n in arm.data.bones}
for n, p in pos.items():
    near = [q for q in pts if (q - p).length < 0.08]
    c = sum(near, Vector()) / len(near) if near else None
    print(f"{n:12s} joint ({p.x*100:7.1f},{p.y*100:7.1f},{p.z*100:7.1f}) cm | verts within 8 cm: {len(near):5d} | offset to their centre: {((c-p).length*100 if c else float('nan')):5.1f} cm")
for a, b in (("upperarm_l", "lowerarm_l"), ("lowerarm_l", "hand_l"), ("thigh_l", "calf_l"), ("calf_l", "foot_l")):
    print(f"{a}->{b} length {(pos[a]-pos[b]).length*100:5.1f} cm")
