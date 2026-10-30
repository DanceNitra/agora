"""Smooth viewport camera moves for the recorded Blender session (runs inside Blender).

Exec this file once through MCP. It registers vp_move() and vp_orbit() in
bpy.app.driver_namespace, so later MCP calls can queue moves:

    import bpy; ns = bpy.app.driver_namespace
    ns["vp_move"](target=(0, 0, 0.9), yaw=35, elevation=15, distance=4.0, seconds=3)
    ns["vp_orbit"](degrees=360, seconds=10)

yaw 0 looks at the robot's front (from -Y), positive yaw orbits counter-clockwise seen from above.
Moves run on a Blender timer, one after another, with smoothstep easing.
"""
import math

import bpy
from mathutils import Euler, Quaternion, Vector

FPS = 30.0


def _view():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                return area, area.spaces.active.region_3d
    return None, None


def _rot(yaw, elevation):
    return Euler((math.radians(90.0 - elevation), 0.0, math.radians(yaw))).to_quaternion()


def _state():
    ns = bpy.app.driver_namespace
    if "vp_queue" not in ns:
        ns["vp_queue"] = []
        ns["vp_current"] = None
    return ns


def _tick():
    ns = _state()
    area, r3d = _view()
    if r3d is None:
        return 1.0 / FPS
    cur = ns["vp_current"]
    if cur is None:
        if not ns["vp_queue"]:
            return 1.0 / FPS
        cur = ns["vp_queue"].pop(0)
        cur["from"] = (r3d.view_location.copy(), r3d.view_rotation.copy(), r3d.view_distance)
        cur["t"] = 0.0
        ns["vp_current"] = cur
    cur["t"] += 1.0 / (FPS * cur["seconds"])
    t = min(cur["t"], 1.0)
    s = t * t * (3 - 2 * t)
    loc0, rot0, dist0 = cur["from"]
    if cur["kind"] == "move":
        r3d.view_location = loc0.lerp(Vector(cur["target"]), s)
        r3d.view_rotation = rot0.slerp(cur["rot"], s)
        r3d.view_distance = dist0 + (cur["distance"] - dist0) * s
    else:
        spin = Quaternion((0, 0, 1), math.radians(cur["degrees"]) * s)
        r3d.view_rotation = spin @ rot0
    area.tag_redraw()
    if t >= 1.0:
        ns["vp_current"] = None
    return 1.0 / FPS


def vp_move(target=(0, 0, 0.9), yaw=35.0, elevation=15.0, distance=4.0, seconds=3.0):
    r3d = _view()[1]
    if r3d is not None:
        r3d.view_perspective = "PERSP"
    _state()["vp_queue"].append({"kind": "move", "target": target, "rot": _rot(yaw, elevation),
                                 "distance": distance, "seconds": max(seconds, 0.1)})


def vp_orbit(degrees=360.0, seconds=10.0):
    _state()["vp_queue"].append({"kind": "orbit", "degrees": degrees, "seconds": max(seconds, 0.1)})


def vp_busy():
    ns = _state()
    return bool(ns["vp_queue"]) or ns["vp_current"] is not None


ns = _state()
ns["vp_move"], ns["vp_orbit"], ns["vp_busy"] = vp_move, vp_orbit, vp_busy
if not bpy.app.timers.is_registered(_tick):
    bpy.app.timers.register(_tick, persistent=True)
ns["vp_tick"] = _tick
print("viewport motion ready")
