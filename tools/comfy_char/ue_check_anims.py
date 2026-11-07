"""Runs inside Unreal (ue_py.py). Compares every retargeted animation in FOLDER with its Epic source, frame by frame:
body lean (pelvis to head), sole tilt per foot, ankle height change. Each is measured against the skeleton's own
reference pose, where both characters stand upright with flat feet. Prints the worst difference per clip and FAIL
when lean differs by more than 6 degrees, a sole by more than 3, or the neck-to-head line by more than 8.
Control: pass FOLDER = Anims2 (the broken set) and it must FAIL."""
import unreal, math

FOLDER = "/Game/AgoraChar/Retarget/Anims6"
SRC_DIRS = ["/Game/Characters/Mannequins/Anims/Unarmed", "/Game/Characters/Mannequins/Anims/Unarmed/Walk", "/Game/Characters/Mannequins/Anims/Unarmed/Jog", "/Game/Characters/Mannequins/Anims/Unarmed/Jump"]
E = unreal.AnimPoseExtensions
W = unreal.AnimPoseSpaces.WORLD
opts = unreal.AnimPoseEvaluationOptions()
lib = unreal.EditorAssetLibrary
src_by_name = {}
for d in SRC_DIRS:
    for p in lib.list_assets(d, recursive=True):
        src_by_name.setdefault(p.split(".")[-1], p)

def measure(anim, frame, ref):
    pose = E.get_anim_pose_at_frame(anim, frame, opts)
    p, h = E.get_bone_pose(pose, "pelvis", W).translation, E.get_bone_pose(pose, "Head", W).translation
    lean = math.degrees(math.atan2(math.hypot(h.x - p.x, h.y - p.y), h.z - p.z))
    n = E.get_bone_pose(pose, "neck_01", W).translation
    neck = math.degrees(math.atan2(math.hypot(h.x - n.x, h.y - n.y), h.z - n.z))
    soles = []
    for s in ("l", "r"):
        rf, pf = E.get_bone_pose(ref, f"foot_{s}", W), E.get_bone_pose(pose, f"foot_{s}", W)
        up = (pf.rotation * rf.rotation.inversed()).rotate_vector(unreal.Vector(0, 0, 1))
        soles.append((math.degrees(math.acos(max(-1, min(1, up.z)))), pf.translation.z - rf.translation.z))
    return lean, soles, neck

fails = 0
for path in sorted(lib.list_assets(FOLDER, recursive=False)):
    t = lib.load_asset(path)
    if not isinstance(t, unreal.AnimSequence):
        continue
    sname = t.get_name().replace("_Agora", "")
    if sname not in src_by_name:  # backups such as MM_Idle_Agora_EpicStance
        continue
    s = lib.load_asset(src_by_name[sname])
    sref, tref = E.get_reference_pose(s.get_skeleton()), E.get_reference_pose(t.get_skeleton())
    n = unreal.AnimationLibrary.get_num_frames(s)
    wl = ws = wn = 0.0
    dz = []
    for fr in range(0, n, max(1, n // 12)):
        sl, ss, sn = measure(s, fr, sref)
        tl, ts, tn = measure(t, fr, tref)
        wn = max(wn, abs(sn - tn))
        wl = max(wl, abs(sl - tl))
        ws = max(ws, max(abs(a[0] - b[0]) for a, b in zip(ss, ts)))
        dz += [b[1] - a[1] for a, b in zip(ss, ts)]
    bad = wl > 6 or ws > 3 or wn > 8
    fails += bad
    print(f"{'FAIL' if bad else 'ok  '} {t.get_name():32s} lean diff {wl:5.1f}  sole diff {ws:5.1f}  neck diff {wn:5.1f}  ankle dz vs source {min(dz):5.1f}..{max(dz):5.1f} cm")
print(FOLDER, "clips failing:", fails)
