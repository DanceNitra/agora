"""Runs inside Unreal (ue_py.py). Builds a neutral standing idle for our character from Epic's idle, replacing the
earlier ue_idle_feet.py + ue_idle_stand.py edits. Always starts from the untouched retargeted clip
(MM_Idle_Agora_EpicStance).

Why (measured in play, 2026-11-07): Epic's idle stands with hips and shoulders turned 20-23 degrees from the facing
direction and the right foot turned 47 degrees out. Straightening only the feet left the legs twisted under a turned
body; from the side the owner saw a hunched, sway-backed figure.

What it does, every frame, with constants taken from frame 0 so Epic's breathing motion stays:
  1. turns the pelvis (and so the whole body) about the vertical so the hip line is square to the facing direction;
  2. moves the pelvis so it sits PELVIS_AHEAD cm in front of the ankles and at the height that gives KNEE_BEND;
  3. plants both feet symmetric under the hips (STANCE_HALF cm from the centre line), toes TOE_OUT degrees out,
     soles flat, and solves both legs with a two-bone IK.
Forward is +Y and the character's left is +X in the clip's world space."""
import math
import unreal

CLIP = "/Game/AgoraChar/Retarget/Anims6/MM_Idle_Agora"
SOURCE = CLIP + "_EpicStance"
KNEE_BEND = 5.0
PELVIS_AHEAD = 1.5
STANCE_HALF = 12.0
TOE_OUT = 8.0
E = unreal.AnimPoseExtensions
W, L = unreal.AnimPoseSpaces.WORLD, unreal.AnimPoseSpaces.LOCAL
lib = unreal.EditorAssetLibrary
src = lib.load_asset(SOURCE)
dst = lib.load_asset(CLIP)
opts = unreal.AnimPoseEvaluationOptions()
n = unreal.AnimationLibrary.get_num_frames(src) + 1


def V(x, y, z): return unreal.Vector(x, y, z)
def sub(a, b): return V(a.x - b.x, a.y - b.y, a.z - b.z)
def add(a, b): return V(a.x + b.x, a.y + b.y, a.z + b.z)
def mul(a, k): return V(a.x * k, a.y * k, a.z * k)
def dot(a, b): return a.x * b.x + a.y * b.y + a.z * b.z
def length(a): return math.sqrt(dot(a, a))
def unit(a): return mul(a, 1.0 / length(a))
def cross(a, b): return V(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x)
def rz(deg): return unreal.Quat(0, 0, math.sin(math.radians(deg) / 2), math.cos(math.radians(deg) / 2))


def between(a, b):
    a, b = unit(a), unit(b)
    ang = math.acos(max(-1.0, min(1.0, dot(a, b))))
    if ang < 1e-6:
        return unreal.Quat(0, 0, 0, 1)
    c, s = unit(cross(a, b)), math.sin(ang / 2)
    return unreal.Quat(c.x * s, c.y * s, c.z * s, math.cos(ang / 2))


def yaw_xy(v): return math.degrees(math.atan2(v.y, v.x))


poses = [E.get_anim_pose_at_frame(src, min(fr, n - 2), opts) for fr in range(n)]
g = lambda p, b: E.get_bone_pose(p, b, W)
p0 = poses[0]
P0 = g(p0, "pelvis").translation

# 1. turn: hip line (right thigh -> left thigh) should point along +X
hip = sub(g(p0, "thigh_l").translation, g(p0, "thigh_r").translation)
turn = -yaw_xy(hip)
R = rz(turn)
def turned(p, b):  # world position of bone b after turning the body about the pelvis
    return add(P0, R.rotate_vector(sub(g(p, b).translation, P0)))

# 3. foot targets (constant): symmetric under the turned hips
Hl, Hr = turned(p0, "thigh_l"), turned(p0, "thigh_r")
cx = (Hl.x + Hr.x) / 2
az = (g(p0, "foot_l").translation.z + g(p0, "foot_r").translation.z) / 2
ankle_y = P0.y - PELVIS_AHEAD          # pelvis stays put in Y, ankles go PELVIS_AHEAD behind it
T = {"l": V(cx + STANCE_HALF, ankle_y, az), "r": V(cx - STANCE_HALF, ankle_y, az)}


def foot_target_rot(p, s):
    """keep the sole flat as in the clip; turn about the vertical so the toes point TOE_OUT degrees out"""
    f, b = g(p, f"foot_{s}"), g(p, f"ball_{s}")
    cur = yaw_xy(sub(b.translation, f.translation))
    want = 90.0 - TOE_OUT if s == "l" else 90.0 + TOE_OUT
    return rz(want - cur) * f.rotation


# 2. pelvis height: the leg that needs less lift sets it, so neither leg overstretches
dz = None
for s in ("l", "r"):
    H, K, A = turned(p0, f"thigh_{s}"), turned(p0, f"calf_{s}"), turned(p0, f"foot_{s}")
    a, b = length(sub(K, H)), length(sub(A, K))
    want = math.sqrt(a * a + b * b + 2 * a * b * math.cos(math.radians(KNEE_BEND)))
    horiz = math.hypot(H.x - T[s].x, H.y - T[s].y)
    need = T[s].z + math.sqrt(max(want * want - horiz * horiz, 0.0)) - H.z
    dz = need if dz is None else min(dz, need)
delta = V(0, 0, dz)
print("turn body", round(turn, 1), "deg; pelvis up", round(dz, 1), "cm; feet at x", round(T['l'].x, 1), round(T['r'].x, 1), "y", round(ankle_y, 1))

bones = ("pelvis", "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r")
tracks = {b: ([], [], []) for b in bones}
worst = 0.0
for p in poses:
    Pp = g(p, "pelvis").translation
    pel_w = R * g(p, "pelvis").rotation
    pl = E.get_bone_pose(p, "pelvis", L)
    root_w = g(p, "root").rotation
    # pelvis keeps its own breathing translation; the body turns about frame-0 pelvis and rises by dz
    new_pel = add(add(P0, R.rotate_vector(sub(Pp, P0))), delta)
    root_t = g(p, "root").translation
    tracks["pelvis"][0].append(root_w.inversed().rotate_vector(sub(new_pel, root_t)))
    tracks["pelvis"][1].append(root_w.inversed() * pel_w)
    tracks["pelvis"][2].append(pl.scale3d)
    for s in ("l", "r"):
        H = add(turned(p, f"thigh_{s}"), delta)
        K = add(turned(p, f"calf_{s}"), delta)
        A0 = add(turned(p, f"foot_{s}"), delta)
        Tg = T[s]
        la, lb = length(sub(K, H)), length(sub(A0, K))
        d = min(length(sub(Tg, H)), la + lb - 0.3)
        worst = max(worst, d / (la + lb))
        u = unit(sub(Tg, H))
        pole = sub(K, H)
        pole = unit(sub(pole, mul(u, dot(pole, u))))
        al = math.acos(max(-1.0, min(1.0, (la * la + d * d - lb * lb) / (2 * la * d))))
        Kn = add(H, add(mul(u, la * math.cos(al)), mul(pole, la * math.sin(al))))
        An = add(H, mul(u, d))
        thigh0 = R * g(p, f"thigh_{s}").rotation
        calf0 = R * g(p, f"calf_{s}").rotation
        r1 = between(sub(K, H), sub(Kn, H))
        thigh_w = r1 * thigh0
        r2 = between(r1.rotate_vector(sub(A0, K)), sub(An, Kn))
        calf_w = r2 * r1 * calf0
        foot_w = foot_target_rot(p, s)
        loc = {f"thigh_{s}": pel_w.inversed() * thigh_w, f"calf_{s}": thigh_w.inversed() * calf_w, f"foot_{s}": calf_w.inversed() * foot_w}
        for bn, q in loc.items():
            lt = E.get_bone_pose(p, bn, L)
            tracks[bn][0].append(lt.translation); tracks[bn][1].append(q); tracks[bn][2].append(lt.scale3d)

# Write in place. Every track an earlier idle edit touched (pelvis, thighs, calves, feet) is rewritten here.
# Never delete and recreate CLIP: that clears the AnimBP and blend space references to it (2026-11-07, see
# ue_relink_idle.py) and blocks the editor with a compile-error dialog on the next Play.
ctrl = dst.get_editor_property("controller")
ctrl.open_bracket(unreal.Text("neutral idle"), False)
for bn, (ps, rs, ss) in tracks.items():
    ctrl.set_bone_track_keys(bn, ps, rs, ss, False)
ctrl.close_bracket(False)
lib.save_loaded_asset(dst, only_if_is_dirty=False)
print("leg reach used, worst frame:", round(worst, 3))
q = E.get_anim_pose_at_frame(dst, 0, opts)
hip = sub(g(q, "thigh_l").translation, g(q, "thigh_r").translation)
sh = sub(g(q, "upperarm_l").translation, g(q, "upperarm_r").translation)
print("after: hip line yaw", round(yaw_xy(hip), 1), "shoulder line yaw", round(yaw_xy(sh), 1))
for s in ("l", "r"):
    H, K, A = (g(q, f"{b}_{s}").translation for b in ("thigh", "calf", "foot"))
    u, v = sub(H, K), sub(A, K)
    print(s, "knee", round(180 - math.degrees(math.acos(dot(u, v) / (length(u) * length(v)))), 1), "toe yaw", round(yaw_xy(sub(g(q, f'ball_{s}').translation, A)), 1),
          "ankle off target", round(length(sub(A, T[s])), 2))
