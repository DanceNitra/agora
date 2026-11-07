"""Runs inside Unreal (ue_py.py) after ue_retarget_setup.py. Auto-align turns the target thighs and calves to match
Manny, and the feet inherit that turn: measured 2026-11-07, soles tipped 10-12 degrees in idle against Manny 2-3.
This sets a rotation offset on each foot in the TARGET retarget pose so the foot keeps its reference world
orientation (sole flat), turned about the vertical so the toes point as Manny's do (our rest pose splays them 12
degrees further out). After it, sole tilt matches Manny to 0.0 degrees in idle and jog."""
import unreal, math
CONV = "local_post"   # retarget pose offsets apply after the reference local rotation (L * D), measured
E = unreal.AnimPoseExtensions
T = unreal.RetargetSourceOrTarget.TARGET
rtg = unreal.load_asset("/Game/AgoraChar/Retarget/RTG_Manny_to_AgoraChar")
rc = unreal.IKRetargeterController.get_controller(rtg)
sk = unreal.load_asset("/Game/AgoraChar/AF2/SK_AgoraChar").get_editor_property("skeleton")
ref = E.get_reference_pose(sk)
L = lambda b: E.get_bone_pose(ref, b, unreal.AnimPoseSpaces.LOCAL).rotation
Wr = lambda b: E.get_bone_pose(ref, b, unreal.AnimPoseSpaces.WORLD).rotation
def comp(chain):
    w = unreal.Quat(0, 0, 0, 1)
    for b in chain:
        d = rc.get_rotation_offset_for_retarget_pose_bone(b, T)
        w = w * (L(b) * d if CONV == "local_post" else d * L(b))
    return w
# consistency: chain of reference locals reproduces the reference world rotation of the calf
chk = unreal.Quat(0, 0, 0, 1)
for b in ("root", "pelvis", "thigh_l", "calf_l"):
    chk = chk * L(b)
print("chain check (deg off):", round(math.degrees(chk.angular_distance(Wr("calf_l"))), 3))
# Manny's reference pose, to match where the toes point (yaw about the vertical)
mref = E.get_reference_pose(unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple").get_editor_property("skeleton"))
def toe_yaw(pose, s):
    f = E.get_bone_pose(pose, f"foot_{s}", unreal.AnimPoseSpaces.WORLD).translation
    b = E.get_bone_pose(pose, f"ball_{s}", unreal.AnimPoseSpaces.WORLD).translation
    return math.degrees(math.atan2(b.y - f.y, b.x - f.x))
for s in ("l", "r"):
    rc.set_rotation_offset_for_retarget_pose_bone(f"foot_{s}", unreal.Quat(0, 0, 0, 1), T)
    wcalf = comp(["root", "pelvis", f"thigh_{s}", f"calf_{s}"])
    dyaw = toe_yaw(mref, s) - toe_yaw(ref, s)
    # sole stays flat (reference orientation), turned about the vertical so the toes point where Manny's do
    want = unreal.Quat.from_axis_angle(unreal.Vector(0, 0, 1), math.radians(dyaw)) if hasattr(unreal.Quat, "from_axis_angle") else unreal.Rotator(0, 0, dyaw).quaternion()
    want = want * Wr(f"foot_{s}")
    print(s, "toe yaw Manny", round(toe_yaw(mref, s), 1), "ours", round(toe_yaw(ref, s), 1), "turn", round(dyaw, 1))
    lf = L(f"foot_{s}")
    if CONV == "local_post":
        d = lf.inversed() * wcalf.inversed() * want
    else:
        d = wcalf.inversed() * want * lf.inversed()
    rc.set_rotation_offset_for_retarget_pose_bone(f"foot_{s}", d, T)
    got = comp(["root", "pelvis", f"thigh_{s}", f"calf_{s}", f"foot_{s}"])
    print(s, CONV, "offset", d.rotator(), "foot off ref (deg):", round(math.degrees(got.angular_distance(want)), 3))
unreal.EditorAssetLibrary.save_loaded_asset(rtg)
