"""Runs inside Unreal. Builds Yuki's own hair material and puts it on her hair grooms.

The MetaHuman hair material gave one flat pink: its melanin variation turns strands black and its highlight and ombre
layers came out dark brown (reports/yuki_ue_v13, 2026-11-14). This material takes the variation from the groom itself
through the Hair Attributes node: every strand a shade between DEEP and LIGHT by its Seed, a share HL_SHARE of the
clumps (by Clump ID) in the highlight colour HL, and the first quarter of each strand darker towards the root (ROOT).
Hair shading model, used with hair strands.

A wrapper may set ARGS = dict(LIGHT=(r,g,b), DEEP=..., HL=..., HL_SHARE=0.22, ROOT=0.72, ROUGH=0.3, SPEC=0.5, SCATTER=1.0,
APPLY=True). Colours are linear. Saves the material and, with APPLY, the level."""
import unreal

_A = globals().pop("ARGS", {})
LIGHT, DEEP, HL = _A.get("LIGHT", (0.86, 0.56, 0.74)), _A.get("DEEP", (0.66, 0.36, 0.55)), _A.get("HL", (0.97, 0.80, 0.90))
HL_SHARE, ROOT, ROUGH, SPEC, SCATTER = _A.get("HL_SHARE", 0.22), _A.get("ROOT", 0.72), _A.get("ROUGH", 0.3), _A.get("SPEC", 0.5), _A.get("SCATTER", 1.0)
PKG, NAME = "/Game/AgoraChar/Tripo/Yuki", "M_Yuki_HairOwn"
mel, lib = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary
mat = unreal.load_asset(f"{PKG}/{NAME}") or unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, PKG, unreal.Material, unreal.MaterialFactoryNew())
mel.delete_all_material_expressions(mat)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_HAIR)
mat.set_editor_property("two_sided", True)
E = lambda cls, x, y: mel.create_material_expression(mat, cls, x, y)


def c3(v, y):
    e = E(unreal.MaterialExpressionConstant3Vector, -900, y)
    e.set_editor_property("constant", unreal.LinearColor(v[0], v[1], v[2], 1.0))
    return e


def c1(v, x, y):
    e = E(unreal.MaterialExpressionConstant, x, y)
    e.set_editor_property("r", float(v))
    return e


ok = []
link = lambda a, out, b, inp: ok.append((out or "-", inp or "-", mel.connect_material_expressions(a, out, b, inp)))
ha = E(unreal.MaterialExpressionHairAttributes, -1300, 0)
lerp1 = E(unreal.MaterialExpressionLinearInterpolate, -600, 0)
link(c3(DEEP, -100), "", lerp1, "A")
link(c3(LIGHT, 60), "", lerp1, "B")
link(ha, "Seed", lerp1, "Alpha")
mul = E(unreal.MaterialExpressionMultiply, -1000, 300)
link(ha, "Clump ID", mul, "A")
link(c1(0.6180339, -1150, 380), "", mul, "B")
fr = E(unreal.MaterialExpressionFrac, -850, 300)
link(mul, "", fr, "")
sub = E(unreal.MaterialExpressionSubtract, -700, 300)
link(fr, "", sub, "A")
link(c1(1.0 - HL_SHARE, -850, 400), "", sub, "B")
m20 = E(unreal.MaterialExpressionMultiply, -550, 300)
link(sub, "", m20, "A")
link(c1(20.0, -700, 420), "", m20, "B")
sat = E(unreal.MaterialExpressionSaturate, -400, 300)
link(m20, "", sat, "")
lerp2 = E(unreal.MaterialExpressionLinearInterpolate, -250, 100)
link(lerp1, "", lerp2, "A")
link(c3(HL, 220), "", lerp2, "B")
link(sat, "", lerp2, "Alpha")
u4 = E(unreal.MaterialExpressionMultiply, -1000, 560)
link(ha, "U", u4, "A")
link(c1(4.0, -1150, 640), "", u4, "B")
usat = E(unreal.MaterialExpressionSaturate, -850, 560)
link(u4, "", usat, "")
rootl = E(unreal.MaterialExpressionLinearInterpolate, -650, 560)
link(c1(ROOT, -850, 660), "", rootl, "A")
link(c1(1.0, -850, 740), "", rootl, "B")
link(usat, "", rootl, "Alpha")
base = E(unreal.MaterialExpressionMultiply, -50, 200)
link(lerp2, "", base, "A")
link(rootl, "", base, "B")
props = []
for expr, out, prop in ((base, "", "MP_BASE_COLOR"), (c1(ROUGH, -200, 500), "", "MP_ROUGHNESS"), (c1(SPEC, -200, 580), "", "MP_SPECULAR"),
                        (c1(SCATTER, -200, 660), "", "MP_METALLIC")):
    props.append((prop, mel.connect_material_property(expr, out, getattr(unreal.MaterialProperty, prop))))
# the strand tangent: the output's name differs between engine versions, so the known spellings are tried in turn
for nm in ("World Tangent", "Tangent", "WorldTangent"):
    if mel.connect_material_property(ha, nm, unreal.MaterialProperty.MP_TANGENT):
        props.append(("MP_TANGENT:" + nm, True))
        break
else:
    props.append(("MP_TANGENT", False))
mel.set_material_usage(mat, unreal.MaterialUsage.MATUSAGE_HAIR_STRANDS)
mel.recompile_material(mat)
print("OWNHAIR links failed", [k for k in ok if not k[2]], "props", props, "saved", lib.save_asset(f"{PKG}/{NAME}", only_if_is_dirty=False))
if _A.get("APPLY", True):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")
    done = []
    for g in ch.get_components_by_class(unreal.GroomComponent):
        if g.get_name() in ("Hair", "Fuzz"):
            for i in range(max(1, g.get_num_materials())):
                g.set_material(i, mat)
            done.append(g.get_name())
    print("OWNHAIR applied to", done)
