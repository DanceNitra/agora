"""Runs inside Unreal. Sets up the strand simulation of Yuki's hair groom, so the hair hangs and swings under gravity
when she moves. The hair has no bones: a strand groom moves through guide strands that Niagara simulates and the
other strands follow.

What the settings are for (each was a seen failure on 2026-11-13, reports/yuki_dance):
- No simulation: every strand turns rigidly with the head; with the head tilted the hair stands out like a board.
- Simulation with a soft bend and no gravity preloading: the hair forgets its style and falls as a curtain over the
  face and the body.
- Gravity preloading 1 with a stiff bend (0.5): keeps the style but is a board again.
So: gravity preloading 1 (the styled shape is the resting shape under gravity, whatever the stiffness), a low bend
stiffness, and a bend profile along the strand (PROFILE: stiff at the root, where the hair leaves the scalp and holds
the parting, soft towards the tip). Simulated strands get SIZE points, not the default 8, which is too few for hair
over a metre long. Collision uses the body's physics asset through the face mesh the groom is bound to: the face
skeleton carries pelvis, spine, clavicles, upper arms, neck and head, so the hair meets the torso and shoulders but
not forearms, hands or legs.

A wrapper may set ARGS = dict(GUIDES, BEND, BEND_DAMP, DRAG, PRELOAD, PROFILE=[(t, v), ...], SIZE=16, SOLVER, TAG, SIM).
A change of GUIDES needs a new TAG: the binding holds the guides. Saves the groom, the binding and the level."""
import re

import unreal

_A = globals().pop("ARGS", {})
GUIDES, BEND, BEND_DAMP, DRAG = _A.get("GUIDES", 0.03), _A.get("BEND", 0.06), _A.get("BEND_DAMP", 0.02), _A.get("DRAG", 0.15)
PRELOAD, SIZE, SOLVER = _A.get("PRELOAD", 1.0), _A.get("SIZE", 16), _A.get("SOLVER", "AngularSprings")
PROFILE = _A.get("PROFILE", [(0.0, 1.0), (0.3, 0.6), (1.0, 0.15)])
TAG, SIM = _A.get("TAG", "s3"), _A.get("SIM", True)
COLLIDE, COLL_RADIUS = _A.get("COLLIDE", True), _A.get("COLL_RADIUS", 0.1)
FRICTION = _A.get("FRICTION", 0.5)   # static and kinetic; lower lets hair slide off a raised arm
# Inertia. The MetaHuman hair component simulates in the space of the head bone and passes only half of the head's
# linear and angular velocity into the simulation (bLocalSimulation, both scales 0.5): stable, but in a turn the hair
# goes round with the head and does not lag, fan out or trail like a veil (owner, 2026-11-14). VEL_SCALE 1.0 passes
# the whole motion in; LOCAL False simulates in world space. SMOOTHING is the velocity smoothing between neighbouring
# strands (0.1 from Epic): higher makes the hair move as one sheet.
LOCAL, VEL_SCALE, SMOOTHING = _A.get("LOCAL", True), _A.get("VEL_SCALE", 0.5), _A.get("SMOOTHING", 0.1)
# COPY_FROM: a groom whose first physics group is copied whole, before anything else. The default is the MetaHuman long
# straight hair on Depesa, which Epic tuned and which dances well in the 2026-11-12 renders: gravity preloading 0.5,
# 10 sub-steps and iterations, air drag 0.5, bend stiffness 0.1 with the first fifth of the strand stiff and the rest
# at 5 %, friction 0.5, collision radius 5 cm at the root falling to 1 % at the tip, 16 points per strand. My own values
# (radius 0.1 cm, 5 sub-steps, a gradual bend profile) gave a board, a curtain and a puff in turn. With COPY_FROM set,
# only the values a wrapper names explicitly are changed after the copy.
COPY_FROM = _A.get("COPY_FROM", "/Game/Companions/MetaHuman/Built/MH_Depesa/Grooms/Hair_L_Straight")
PKG = "/Game/AgoraChar/Tripo/Yuki"
lib = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
GROOM = _A.get("GROOM", "GR_Yuki_HairLong")   # the long strands only: see ue_yuki_hair_split
g = unreal.load_asset(PKG + "/" + GROOM)
it = list(g.get_editor_property("hair_groups_interpolation"))
for i, x in enumerate(it):
    s2 = x.get_editor_property("interpolation_settings")
    s2.set_editor_property("guide_type", unreal.GroomGuideType.GENERATED)
    s2.set_editor_property("hair_to_guide_density", GUIDES)
    x.set_editor_property("interpolation_settings", s2)
    it[i] = x
g.set_editor_property("hair_groups_interpolation", it)


def keys(profile):
    return "Keys=(" + ",".join("(InterpMode=RCIM_Cubic,%sValue=%.6f)" % ("Time=%.6f," % t if t else "", v) for t, v in profile) + ")"


ph = list(g.get_editor_property("hair_groups_physics"))
src = list(unreal.load_asset(COPY_FROM).get_editor_property("hair_groups_physics"))[0].export_text() if COPY_FROM else None
for i, x in enumerate(ph):
    t = src or x.export_text()

    def setv(pattern, value, key):
        global t
        if not COPY_FROM or key in _A:
            t = re.sub(pattern, value, t)

    setv(r"EnableSimulation=\w+", "EnableSimulation=%s" % ("True" if SIM else "False"), "SIM")
    setv(r"NiagaraSolver=\w+", "NiagaraSolver=" + SOLVER, "SOLVER")
    setv(r"GravityPreloading=[-\d.]+", "GravityPreloading=%.6f" % PRELOAD, "PRELOAD")
    setv(r"AirDrag=[-\d.]+", "AirDrag=%.6f" % DRAG, "DRAG")
    setv(r"BendDamping=[-\d.]+", "BendDamping=%.6f" % BEND_DAMP, "BEND_DAMP")
    setv(r"BendStiffness=[-\d.]+", "BendStiffness=%.6f" % BEND, "BEND")
    setv(r"StrandsSize=\w+", "StrandsSize=Size%d" % SIZE, "SIZE")
    setv(r"SolveCollision=\w+", "SolveCollision=%s" % COLLIDE, "COLLIDE")
    setv(r"ProjectCollision=\w+", "ProjectCollision=%s" % COLLIDE, "COLLIDE")
    setv(r"CollisionRadius=[-\d.]+", "CollisionRadius=%.6f" % COLL_RADIUS, "COLL_RADIUS")
    setv(r"StaticFriction=[-\d.]+", "StaticFriction=%.6f" % FRICTION, "FRICTION")
    setv(r"StrandsSmoothing=[-\d.]+", "StrandsSmoothing=%.6f" % SMOOTHING, "SMOOTHING")
    setv(r"KineticFriction=[-\d.]+", "KineticFriction=%.6f" % FRICTION, "FRICTION")
    if not COPY_FROM or "PROFILE" in _A:
        a_ = t.index("BendScale=(EditorCurveData=(") + len("BendScale=(EditorCurveData=(")     # the first curve in the text is the bend scale
        b_ = t.index(",DefaultValue=", a_)
        t = t[:a_] + keys(PROFILE) + t[b_:]
    x.import_text(t)
    ph[i] = x
g.set_editor_property("hair_groups_physics", ph)
chk = list(g.get_editor_property("hair_groups_physics"))[0].export_text()
print("SIM set:", "copied from " + COPY_FROM.split("/")[-1] if COPY_FROM else "own values", re.search(r"CollisionRadius=[-\d.]+", chk).group(0), re.search(r"SubSteps=\d+", chk).group(0), re.search(r"SolveCollision=\w+", chk).group(0), re.search(r"EnableSimulation=\w+", chk).group(0), re.search(r"GravityPreloading=[-\d.]+", chk).group(0), re.search(r"BendStiffness=[-\d.]+", chk).group(0),
      re.search(r"StrandsSize=\w+", chk).group(0), "bend keys", chk[chk.index("BendScale=(EditorCurveData=(") + 28:chk.index(",DefaultValue=")][:200])
print("SIM groom saved", lib.save_asset(PKG + "/" + GROOM, only_if_is_dirty=False))
ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")
comps = {c.get_name(): c for c in ch.get_components_by_class(unreal.SkeletalMeshComponent)}
BIND = f"{PKG}/GB_{GROOM[3:]}_{TAG}"
binding = unreal.load_asset(BIND) or unreal.GroomLibrary.create_new_groom_binding_asset_with_path(BIND, g, comps["Face"].get_skeletal_mesh_asset(), 100, None, 0)
h = next(c for c in ch.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair")
h.set_binding_asset(binding)
pa = comps["Body"].get_skeletal_mesh_asset().get_editor_property("physics_asset")
h.set_physics_asset(pa)
if "LOCAL" in _A or "VEL_SCALE" in _A:
    st = h.get_editor_property("simulation_settings")
    tx = st.export_text()
    tx = re.sub(r"bLocalSimulation=\w+", "bLocalSimulation=%s" % LOCAL, tx)
    tx = re.sub(r"LinearVelocityScale=[-\d.]+", "LinearVelocityScale=%.6f" % VEL_SCALE, tx)
    tx = re.sub(r"AngularVelocityScale=[-\d.]+", "AngularVelocityScale=%.6f" % VEL_SCALE, tx)
    st.import_text(tx)
    h.set_editor_property("simulation_settings", st)
    ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")
    h = next(c for c in ch.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair")
    print("SIM component setup:", re.search(r"SimulationSetup=\(.*?\)", h.get_editor_property("simulation_settings").export_text()).group(0))
print("SIM binding", binding.get_name() if binding else None, "physics asset", pa.get_name() if pa else None,
      "saved", lib.save_asset(BIND, only_if_is_dirty=False), lib.save_asset(PKG + "/L_Yuki_Preview", only_if_is_dirty=False))
