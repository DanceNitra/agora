"""blender -b --factory-startup --python costume_probe.py -- <metahuman_fullbody.fbx> <dressed.glb>
Prints what each file holds, to plan the costume transfer."""
import sys
import bpy
from mathutils import Vector
fbx, glb = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
for o in bpy.data.objects:
    print("FBX", o.type, o.name, "scale", tuple(round(s, 3) for s in o.scale), "rot", tuple(round(r, 2) for r in o.rotation_euler))
    if o.type == "MESH":
        ws = [o.matrix_world @ v.co for v in o.data.vertices]
        lo = [min(p[i] for p in ws) for i in range(3)]; hi = [max(p[i] for p in ws) for i in range(3)]
        print("   verts", len(ws), "groups", len(o.vertex_groups), "mods", [m.type for m in o.modifiers], "lo", [round(x, 3) for x in lo], "hi", [round(x, 3) for x in hi], "mats", [m.name for m in o.data.materials])
    if o.type == "ARMATURE":
        print("   bones", len(o.data.bones))
        for n in ("pelvis", "spine_05", "neck_01", "head", "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "thigh_l", "calf_l", "foot_l", "ball_l"):
            if n in o.data.bones:
                p = o.matrix_world @ o.data.bones[n].head_local
                print(f"   {n:12s} ({p.x*100:7.1f},{p.y*100:7.1f},{p.z*100:7.1f})")
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
for o in set(bpy.data.objects) - before:
    if o.type != "MESH":
        continue
    ws = [o.matrix_world @ v.co for v in o.data.vertices]
    lo = [min(p[i] for p in ws) for i in range(3)]; hi = [max(p[i] for p in ws) for i in range(3)]
    print("GLB", o.name, "verts", len(ws), "lo", [round(x, 3) for x in lo], "hi", [round(x, 3) for x in hi])
    # arm line: mean z and y of vertices in x slabs
    for x0 in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        s = [p for p in ws if x0 <= p.x < x0 + 0.02]
        if s:
            print(f"   x={x0:.1f}: n={len(s)} z {min(p.z for p in s):.3f}..{max(p.z for p in s):.3f} y {min(p.y for p in s):.3f}..{max(p.y for p in s):.3f}")
    for z0 in (-0.9, -0.7, -0.45, -0.2, 0.0, 0.2, 0.4, 0.55, 0.62, 0.7, 0.8, 0.9):
        s = [p for p in ws if z0 <= p.z < z0 + 0.02 and abs(p.x) < 0.35]
        if s:
            print(f"   z={z0:+.2f}: n={len(s)} x {min(p.x for p in s):.3f}..{max(p.x for p in s):.3f} y {min(p.y for p in s):.3f}..{max(p.y for p in s):.3f}")
