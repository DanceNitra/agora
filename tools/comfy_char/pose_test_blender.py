"""Apply one fixed test pose to a character rig in the owner's Blender, so two rigs can be compared.

Run inside Blender through the MCP:
    exec(open(r"C:/Users/Danculus/agora/tools/comfy_char/pose_test_blender.py").read())
    apply_test_pose(bpy.data.objects["RIG"], BONES)   # BONES maps the names below to pose bones

Every rotation is defined in world space from the rest pose, so the same pose lands on any rig whose
bones follow the body, whatever their roll. The character faces -Y, with +X on its left side.

Test pose: arms 60 degrees down, elbows bent 90 degrees forward, left leg 45 degrees forward with the
knee bent 60 degrees, right leg straight, every finger joint curled 60 degrees toward the palm, thumbs
curled 40 degrees.
"""
import math

import bpy
import mathutils

V = mathutils.Vector
FORWARD = V((0, -1, 0))

SEMANTIC = ["upper_arm.L", "forearm.L", "upper_arm.R", "forearm.R", "thigh.L", "shin.L"]
FINGERS = ["index", "middle", "ring", "pinky"]


def _bend(rig, name, toward, degrees):
    """Rotate one pose bone about its head, turning its direction toward a world vector."""
    pb = rig.pose.bones[name]
    bpy.context.view_layer.update()
    head = rig.matrix_world @ pb.head
    direction = (rig.matrix_world.to_3x3() @ (pb.tail - pb.head)).normalized()
    axis = direction.cross(toward)
    if axis.length < 1e-6:
        return
    rot = mathutils.Matrix.Rotation(math.radians(degrees), 4, axis.normalized())
    world = rig.matrix_world @ pb.matrix
    world = mathutils.Matrix.Translation(head) @ rot @ mathutils.Matrix.Translation(-head) @ world
    pb.matrix = rig.matrix_world.inverted() @ world
    bpy.context.view_layer.update()


def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.matrix_basis = mathutils.Matrix.Identity(4)
    bpy.context.view_layer.update()


def apply_test_pose(rig, bones):
    """bones maps 'upper_arm.L', 'forearm.L', ..., 'thigh.L', 'shin.L', 'thumb.1.L'..'pinky.3.R' to pose bones."""
    reset_pose(rig)
    for side, sign in (("L", 1), ("R", -1)):
        _bend(rig, bones[f"upper_arm.{side}"], V((sign * 0.5, 0, -0.866)), 60)
        _bend(rig, bones[f"forearm.{side}"], FORWARD, 90)
        for finger in FINGERS:
            for j in (1, 2, 3):
                key = f"{finger}.{j}.{side}"
                if key in bones:
                    _bend(rig, bones[key], FORWARD, 60)
        for j in (1, 2, 3):
            key = f"thumb.{j}.{side}"
            if key in bones:
                _bend(rig, bones[key], FORWARD, 40)
    _bend(rig, bones["thigh.L"], FORWARD, 45)
    _bend(rig, bones["shin.L"], V((0, 1, 0)), 60)
