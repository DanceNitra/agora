"""Runs inside Unreal (ue_py.py) right after ue_idle_feet.py. Makes the idle stand upright.

Measured in play 2026-11-07 after the feet were put side by side: the pelvis sat 7.4 cm BEHIND the feet (Manny:
3.3 cm in front), the right shin leaned 15 degrees backward and both knees were bent 15-21 degrees. With our
proportions that reads as a hunched, sitting stance (owner: "ohnuta jak quasimodo").

This moves the pelvis (and so the whole upper body) by one constant offset so it sits PELVIS_AHEAD cm in front of
the ankles' midpoint and high enough that the more bent leg has KNEE_BEND degrees, keeping the clip's own breathing
motion. Both legs are then solved with a two-bone IK onto the unchanged foot positions; feet keep their world
orientation."""
import math
import unreal

CLIP = "/Game/AgoraChar/Retarget/Anims6/MM_Idle_Agora"
KNEE_BEND = 6.0
PELVIS_AHEAD = 2.0
E = unreal.AnimPoseExtensions
W, L = unreal.AnimPoseSpaces.WORLD, unreal.AnimPoseSpaces.LOCAL
lib = unreal.EditorAssetLibrary
clip = lib.load_asset(CLIP)
opts = unreal.AnimPoseEvaluationOptions()
n = unreal.AnimationLibrary.get_num_frames(clip) + 1


def V(x, y, z): return unreal.Vector(x, y, z)
def sub(a, b): return V(a.x - b.x, a.y - b.y, a.z - b.z)
def add(a, b): return V(a.x + b.x, a.y + b.y, a.z + b.z)
def mul(a, k): return V(a.x * k, a.y * k, a.z * k)
def dot(a, b): return a.x * b.x + a.y * b.y + a.z * b.z
def length(a): return math.sqrt(dot(a, a))
def unit(a): return mul(a, 1.0 / length(a))
def cross(a, b): return V(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x)


def between(a, b):
    a, b = unit(a), unit(b)
    ang = math.acos(max(-1.0, min(1.0, dot(a, b))))
    if ang < 1e-6:
        return unreal.Quat(0, 0, 0, 1)
    c, s = unit(cross(a, b)), math.sin(ang / 2)
    return unreal.Quat(c.x * s, c.y * s, c.z * s, math.cos(ang / 2))


poses = [E.get_anim_pose_at_frame(clip, min(fr, n - 2), opts) for fr in range(n)]
g = lambda p, b: E.get_bone_pose(p, b, W)

# one constant pelvis offset, from frame 0
p0 = poses[0]
fl, fr_ = g(p0, "foot_l").translation, g(p0, "foot_r").translation
mid = mul(add(fl, fr_), 0.5)
# forward is +Y in the clip's world (toe yaw 90 is forward)
dy = (mid.y + PELVIS_AHEAD) - g(p0, "pelvis").translation.y
dz = None
for s in ("l", "r"):
    H, K, A = (g(p0, f"{b}_{s}").translation for b in ("thigh", "calf", "foot"))
    a, b = length(sub(K, H)), length(sub(A, K))
    want = math.sqrt(a * a + b * b + 2 * a * b * math.cos(math.radians(KNEE_BEND)))
    Hn = V(H.x, H.y + dy, H.z)
    horiz = math.hypot(Hn.x - A.x, Hn.y - A.y)
    z_need = A.z + math.sqrt(max(want * want - horiz * horiz, 0.0)) - H.z
    dz = z_need if dz is None else min(dz, z_need)
delta = V(0, dy, dz)
print("pelvis offset (cm): forward", round(dy, 1), "up", round(dz, 1))

root_ref = E.get_bone_pose(E.get_reference_pose(clip.get_skeleton()), "root", L)
tracks = {b: ([], [], []) for b in ("pelvis", "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r")}
worst = 0.0
for p in poses:
    # pelvis: same rotation, translated by delta in world -> convert to its parent (root) space
    pl = E.get_bone_pose(p, "pelvis", L)
    root_w = g(p, "root").rotation
    local_delta = root_w.inversed().rotate_vector(delta)
    tracks["pelvis"][0].append(add(pl.translation, local_delta))
    tracks["pelvis"][1].append(pl.rotation)
    tracks["pelvis"][2].append(pl.scale3d)
    pel_w = g(p, "pelvis").rotation
    for s in ("l", "r"):
        H = add(g(p, f"thigh_{s}").translation, delta)
        K = add(g(p, f"calf_{s}").translation, delta)
        A0 = add(g(p, f"foot_{s}").translation, delta)  # where the ankle would be if the leg moved with the pelvis
        T = g(p, f"foot_{s}").translation              # where the ankle must stay
        la, lb = length(sub(K, H)), length(sub(A0, K))
        d = min(length(sub(T, H)), la + lb - 0.3)
        worst = max(worst, d / (la + lb))
        u = unit(sub(T, H))
        pole = sub(K, H)
        pole = unit(sub(pole, mul(u, dot(pole, u))))
        al = math.acos(max(-1.0, min(1.0, (la * la + d * d - lb * lb) / (2 * la * d))))
        Kn = add(H, add(mul(u, la * math.cos(al)), mul(pole, la * math.sin(al))))
        An = add(H, mul(u, d))
        r1 = between(sub(K, H), sub(Kn, H))
        thigh_w = r1 * g(p, f"thigh_{s}").rotation
        r2 = between(r1.rotate_vector(sub(A0, K)), sub(An, Kn))
        calf_w = r2 * r1 * g(p, f"calf_{s}").rotation
        foot_w = g(p, f"foot_{s}").rotation
        loc = {f"thigh_{s}": pel_w.inversed() * thigh_w, f"calf_{s}": thigh_w.inversed() * calf_w, f"foot_{s}": calf_w.inversed() * foot_w}
        for bn, q in loc.items():
            lt = E.get_bone_pose(p, bn, L)
            tracks[bn][0].append(lt.translation); tracks[bn][1].append(q); tracks[bn][2].append(lt.scale3d)
ctrl = clip.get_editor_property("controller")
ctrl.open_bracket(unreal.Text("idle stand upright"), False)
for bn, (ps, rs, ss) in tracks.items():
    ctrl.set_bone_track_keys(bn, ps, rs, ss, False)
ctrl.close_bracket(False)
lib.save_loaded_asset(clip, only_if_is_dirty=False)
print("leg reach used, worst frame:", round(worst, 3))
q = E.get_anim_pose_at_frame(clip, 0, opts)
for s in ("l", "r"):
    H, K, A = (g(q, f"{b}_{s}").translation for b in ("thigh", "calf", "foot"))
    u, v = sub(H, K), sub(A, K)
    bend = 180 - math.degrees(math.acos(dot(u, v) / (length(u) * length(v))))
    print(s, "knee bend", round(bend, 1), "foot moved (cm)", round(length(sub(A, g(p0, f"foot_{s}").translation)), 2))
