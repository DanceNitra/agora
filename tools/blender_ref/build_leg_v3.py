"""Round 3 leg (parameterised): rebuild the LEG_UNIT collection from the measured spec (runs inside Blender).

Spec: agora_output/reverse/blender_spider_xCkjVUtVDEw/build/07_iterate/round2/leg_spec.md.
Local frame of the unit: +X radial (away from the body axis), +Y tangent, +Z up, metres.
The three leg instances reference this collection, so they update with it.
"""
import math

import bmesh
import bpy
from mathutils import Vector

UNIT = bpy.data.collections["LEG_UNIT"]
ROOT = bpy.data.objects["leg_unit_root"]
M = bpy.data.materials


def hexc(h):
    h = h.lstrip("#")
    s = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [(c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in s] + [1.0]


def material(name, color, rough, metal):
    m = M.get(name) or M.new(name)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = hexc(color)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    return m


# Round 3 parameters. H stretches everything above the boot top (z 0.30) upward, S moves the leg
# below the hip outward, DZ lifts the hip by as much as the hub rises so the body can follow.
P = dict(H=1.0, S=0.0, ARM_R=0.042, KN_S=1.0, BOW=0.04, GAP=0.006, W=0.36)
P.update(bpy.app.driver_namespace.get("leg_params", {}))


def Zs(z):
    return z if z <= 0.30 else 0.30 + (z - 0.30) * P["H"]


def Rs(x):
    return x + P["S"]


DZ = Zs(0.84) - 0.84
bpy.app.driver_namespace["leg_dz"] = DZ

ORANGE, GRAPHITE, RUBBER = M["MAT_orange_armour"], M["MAT_graphite"], M["MAT_rubber"]
METAL, EMISSIVE = M["MAT_brushed_metal"], M["MAT_emissive_orange"]
GUNMETAL = material("MAT_gunmetal", "#45474B", 0.32, 1.0)

# clear the old unit, keep the root
for o in list(UNIT.objects):
    if o is not ROOT:
        bpy.data.objects.remove(o)


def link(o, name, mat=None, smooth=True):
    o.name = name
    for c in o.users_collection:
        c.objects.unlink(o)
    UNIT.objects.link(o)
    o.parent = ROOT
    if mat is not None and o.type in ("MESH", "CURVE"):
        o.data.materials.clear()
        o.data.materials.append(mat)
    if smooth and o.type == "MESH":
        for p in o.data.polygons:
            p.use_smooth = True
        # keep cylinder caps and box edges crisp; plain smooth shading bends a straight rod visually
        es = o.modifiers.new("edge_split", "EDGE_SPLIT")
        es.split_angle = math.radians(30)
    return o


def bevel(o, w, seg=3):
    b = o.modifiers.new("bevel", "BEVEL")
    b.width, b.segments, b.limit_method = w, seg, "ANGLE"
    return b


def cyl_y(name, loc, r, depth, mat, verts=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=(math.radians(90), 0, 0))
    return link(bpy.context.active_object, name, mat)


def rod(name, p0, p1, r, mat, verts=32):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = link(bpy.context.active_object, name, mat)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    return o


def ring_y(name, loc, r, minor, mat):
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=minor, major_segments=64, minor_segments=10,
                                     location=loc, rotation=(math.radians(90), 0, 0))
    return link(bpy.context.active_object, name, mat)


# ---- hip knuckle and arm -------------------------------------------------------------------
KN = Vector((0.53, 0, 0.56 + DZ))
HUB = Vector((Rs(0.84), 0, Zs(0.84)))
# Round metal hip housing, as in detail_joint.png: a grey cylinder with a bearing face of
# concentric rings on both sides and a rounded neck towards the arm. No box.
ks = P["KN_S"]
house = cyl_y("leg_hip_housing", KN, 0.075 * ks, 0.13 * ks, GUNMETAL, 64)
bevel(house, 0.012, 4)
for side in (1, -1):
    tag = "out" if side > 0 else "in"
    face = KN + Vector((0, side * 0.066 * ks, 0))
    cyl_y(f"leg_hip_bearing_{tag}", face, 0.058 * ks, 0.012, METAL, 64)
    ring_y(f"leg_hip_bearing_ring_{tag}", face + Vector((0, side * 0.006, 0)), 0.046 * ks, 0.005, GUNMETAL)
    cyl_y(f"leg_hip_bearing_cap_{tag}", face + Vector((0, side * 0.008, 0)), 0.026 * ks, 0.012, GUNMETAL, 48)
d_arm = (HUB - KN).normalized()
neck0 = KN + d_arm * 0.05 * ks
rod("leg_hip_neck", neck0, KN + d_arm * 0.12 * ks, P["ARM_R"] * 1.25, GUNMETAL, 48)
arm0 = KN + d_arm * 0.11 * ks
rod("leg_hip_arm", arm0, HUB - d_arm * 0.07, P["ARM_R"], GUNMETAL)
# collar seated against the hub rim: 0.09 to 0.115 from the hub centre along the arm
rod("leg_hip_arm_collar", HUB - d_arm * 0.118, HUB - d_arm * 0.09, P["ARM_R"] * 1.18, METAL)

# ---- shoulder hub ----------------------------------------------------------------------------
hub = cyl_y("leg_hub", HUB, 0.09, 0.12, GRAPHITE, 64)
bevel(hub, 0.006)
for side in (1, -1):
    tag = "out" if side > 0 else "in"
    face = HUB + Vector((0, side * 0.06, 0))
    ring_y(f"leg_hub_rim_{tag}", face, 0.084, 0.007, GRAPHITE)
    ring_y(f"leg_hub_ring_outer_{tag}", face + Vector((0, side * 0.002, 0)), 0.048, 0.0065, ORANGE)
    ring_y(f"leg_hub_ring_inner_{tag}", face + Vector((0, side * 0.002, 0)), 0.036, 0.005, ORANGE)
    cyl_y(f"leg_hub_boss_{tag}", face + Vector((0, side * 0.006, 0)), 0.026, 0.016, GRAPHITE)
    for i in range(8):
        t = math.radians(i * 45 + 22.5)
        cyl_y(f"leg_hub_bolt_{tag}{i}", face + Vector((0.066 * math.cos(t), side * 0.003, 0.066 * math.sin(t))), 0.0065, 0.008, METAL, 12)

# ---- two-part shell --------------------------------------------------------------------------
TOP_IN, BOT_IN = Vector((Rs(0.93), 0, Zs(0.97))), Vector((Rs(1.00), 0, 0.30))
AXIS = (BOT_IN - TOP_IN)
NRM = Vector((-AXIS.z, 0, AXIS.x)).normalized()
if NRM.x < 0:
    NRM = -NRM
W, T, BOW, CROSS = P["W"], 0.13, P["BOW"], 0.018


def shell_point(s, v, outer):
    base = TOP_IN + AXIS * s
    w = W * (0.86 + 0.14 * math.sin(math.pi * min(max(s, 0), 1)))
    off = BOW * math.sin(math.pi * s) - CROSS * v * v
    if s < 0.12:  # the top end rounds off over the hub
        off -= 0.035 * (1 - s / 0.12) ** 2
        w *= 0.80 + 0.20 * (s / 0.12) ** 0.5
    thick = T * (0.85 + 0.15 * math.sin(math.pi * s))
    return base + NRM * (off + (thick if outer else 0.0)) + Vector((0, v * w / 2, 0))


def shell_piece(name, s_from, s_to, nu=22, nv=12):
    bm = bmesh.new()
    grid = {}
    for side in (0, 1):
        for i in range(nu + 1):
            for j in range(nv + 1):
                v = -1 + 2 * j / nv
                a, b = s_from(v), s_to(v)
                s = a + (b - a) * i / nu
                grid[side, i, j] = bm.verts.new(shell_point(s, v, side == 1))
    for i in range(nu):
        for j in range(nv):
            bm.faces.new([grid[1, i, j], grid[1, i + 1, j], grid[1, i + 1, j + 1], grid[1, i, j + 1]])
            bm.faces.new([grid[0, i, j + 1], grid[0, i + 1, j + 1], grid[0, i + 1, j], grid[0, i, j]])
    for i in range(nu):
        for j in (0, nv):
            bm.faces.new([grid[0, i, j], grid[0, i + 1, j], grid[1, i + 1, j], grid[1, i, j]])
    for j in range(nv):
        for i in (0, nu):
            bm.faces.new([grid[0, i, j], grid[0, i, j + 1], grid[1, i, j + 1], grid[1, i, j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    UNIT.objects.link(o)
    link(o, name, ORANGE)
    bevel(o, 0.02, 4)
    o.modifiers.new("wn", "WEIGHTED_NORMAL").keep_sharp = True
    return o


def seam(v):  # V-shaped seam between the two shell parts, pointing up at the middle
    return 0.64 + 0.06 * (1 - abs(v))


shell_piece("leg_shell_upper", lambda v: 0.0, lambda v: seam(v) - P["GAP"])
shell_piece("leg_shell_lower", lambda v: seam(v), lambda v: 1.0)
for s, v, tag in ((0.06, -0.55, "t1"), (0.06, 0.55, "t2"), (0.93, -0.62, "b1"), (0.93, 0.62, "b2")):
    p = shell_point(s, v, True)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.011, depth=0.01, location=p)
    sc = link(bpy.context.active_object, f"leg_shell_screw_{tag}", GUNMETAL)
    sc.rotation_mode = "QUATERNION"
    sc.rotation_quaternion = NRM.to_track_quat("Z", "Y")

# ---- piston, knee housing, boot, knee bearing ------------------------------------------------
P0, P1 = HUB + Vector((0.0, 0, -0.08)), Vector((Rs(0.895), 0, Zs(0.50)))
mid = P0.lerp(P1, 0.5)
rod("leg_piston_cylinder", P0, mid, 0.034, GUNMETAL)
rod("leg_piston_rod", mid, P1, 0.024, METAL)
for f in (0.25, 0.46):
    q0 = P0.lerp(P1, f)
    rod(f"leg_piston_collar_{int(f * 100)}", q0, P0.lerp(P1, f + 0.04), 0.039, METAL)
bpy.ops.mesh.primitive_cube_add(size=1, location=(Rs(0.89), 0, (0.11 + Zs(0.49)) / 2))
kh = link(bpy.context.active_object, "leg_knee_housing", GRAPHITE)
kh.scale = (0.12, 0.18, Zs(0.49) - 0.11)
bevel(kh, 0.025, 4)
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.125, depth=0.19, location=(Rs(1.0), 0, 0.205))
boot = link(bpy.context.active_object, "leg_boot", GRAPHITE)
boot.scale = (0.85, 1.05, 1.0)
bevel(boot, 0.02, 3)
cyl_y("leg_knee_bearing", (Rs(0.93), 0, 0.15), 0.042, 0.26, METAL)
cyl_y("leg_knee_bearing_cap", (Rs(0.93), 0, 0.15), 0.026, 0.275, GUNMETAL)

# ---- wedge foot with light strip -------------------------------------------------------------
bm = bmesh.new()
x0, x1, y0, z0, zb, zf = Rs(0.86), Rs(1.19), 0.15, 0.02, 0.13, 0.10
pts = [(x0, -y0, z0), (x1, -y0, z0), (x1, y0, z0), (x0, y0, z0), (x0, -y0, zb), (x1, -y0, zf), (x1, y0, zf), (x0, y0, zb)]
vs = [bm.verts.new(p) for p in pts]
for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
    bm.faces.new([vs[i] for i in f])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("leg_foot_pad")
bm.to_mesh(me)
bm.free()
foot = bpy.data.objects.new("leg_foot_pad", me)
UNIT.objects.link(foot)
link(foot, "leg_foot_pad", RUBBER, smooth=False)
bevel(foot, 0.07, 8)
for k_, zz in enumerate((0.030, 0.043)):  # chevron tread on the outer toe face, as in detail_foot.png
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x1 + 0.002, side * 0.05, zz + 0.005))
        tb = link(bpy.context.active_object, f"leg_foot_tread_{k_}{'r' if side > 0 else 'l'}", RUBBER, smooth=False)
        tb.scale = (0.012, 0.11, 0.006)
        tb.rotation_euler.x = math.radians(-25 * side)
bpy.ops.mesh.primitive_cube_add(size=1, location=(x1 + 0.004, 0, 0.085))
st = link(bpy.context.active_object, "leg_foot_light_strip", EMISSIVE, smooth=False)
st.scale = (0.008, 0.17, 0.012)
bevel(st, 0.003, 2)

# ---- hoses from the under-frame up to the arm ------------------------------------------------
for k_, side in enumerate((-0.05, 0.05)):
    cu = bpy.data.curves.new(f"leg_hose_{k_}", "CURVE")
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", 0.011, 4
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(1)
    a, b = sp.bezier_points
    a.co, a.handle_left, a.handle_right = (0.30, side, 0.56 + DZ), (0.24, side, 0.60 + DZ), (0.36, side, 0.22 + DZ)
    b.co, b.handle_left, b.handle_right = (Rs(0.72), side * 1.3, 0.74 + DZ), (Rs(0.64), side * 1.3, 0.30 + DZ), (Rs(0.78), side * 1.3, 0.84 + DZ)
    ob = bpy.data.objects.new(f"leg_hose_{k_}", cu)
    UNIT.objects.link(ob)
    link(ob, f"leg_hose_{k_}", RUBBER)

print("leg unit rebuilt:", len(UNIT.objects), "objects")
