"""Runs inside Unreal (ue_py.py). Builds BP_AgoraMH: a copy of BP_AgoraChar (third-person input, camera, movement)
whose Mesh is the MetaHuman body animated by ABP_Unarmed_MH, plus the MetaHuman face, outfit, grooms and
MetaHumanComponent copied from the built BP_MH_AgoraSoldier. Then puts it in L_AgoraChar_Test as the player."""
import unreal

SRC_CHAR = "/Game/AgoraChar/AF/BP_AgoraChar"
NEW = "/Game/AgoraChar/MetaHuman/BP_AgoraMH"
MH_BP = "/Game/AgoraChar/MetaHuman/Built/MH_AgoraSoldier/BP_MH_AgoraSoldier"
ABP = "/Game/AgoraChar/MetaHuman/Anims/ABP_Unarmed_MH"
lib = unreal.EditorAssetLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
SDL = unreal.SubobjectDataBlueprintFunctionLibrary

if lib.does_asset_exist(NEW):
    lib.delete_asset(NEW)
lib.duplicate_asset(SRC_CHAR, NEW)
bp = lib.load_asset(NEW)
mh = lib.load_asset(MH_BP)

# templates from the MetaHuman blueprint, by component name
tmpl = {}
for h in sds.k2_gather_subobject_data_for_blueprint(mh):
    o = SDL.get_associated_object(SDL.get_data(h))
    if o and o.get_name().endswith("_GEN_VARIABLE") and o.get_name() not in tmpl:
        tmpl[o.get_name().replace("_GEN_VARIABLE", "")] = o
print("MetaHuman components:", sorted(tmpl))

handles = sds.k2_gather_subobject_data_for_blueprint(bp)
by_name = {}
for h in handles:
    o = SDL.get_associated_object(SDL.get_data(h))
    if o:
        by_name[o.get_name()] = h
mesh_h = next(h for n, h in by_name.items() if n.startswith("CharacterMesh0"))
cdo = unreal.get_default_object(bp.generated_class())
body = cdo.get_editor_property("mesh")
body.set_skeletal_mesh_asset(tmpl["Body"].get_skeletal_mesh_asset())
body.set_editor_property("anim_class", lib.load_asset(ABP).generated_class())
body.set_editor_property("relative_location", unreal.Vector(0, 0, -89))
body.set_editor_property("visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
body.set_editor_property("override_materials", [])


def add(cls, name, parent_handle, copy_from=None, props=()):
    params = unreal.AddNewSubobjectParams(parent_handle=parent_handle, new_class=cls, blueprint_context=bp)
    h, fail = sds.add_new_subobject(params)
    if not fail.is_empty():
        raise RuntimeError(f"{name}: {fail}")
    sds.rename_subobject(h, unreal.Text(name))
    o = SDL.get_associated_object(SDL.get_data(h))
    if copy_from is not None:
        for p in props:
            try:
                o.set_editor_property(p, copy_from.get_editor_property(p))
            except Exception as e:
                print("  could not copy", name, p, e)
    return h, o


SKM_PROPS = ("skeletal_mesh_asset", "anim_class", "animation_mode", "override_materials", "relative_location", "relative_rotation")
GROOM_PROPS = ("groom_asset", "binding_asset", "attach_parent_bone" if False else "relative_location")
face_h, face = add(unreal.SkeletalMeshComponent, "Face", mesh_h, tmpl["Face"], SKM_PROPS)
out_name = next((n for n in tmpl if n.startswith("SkeletalMesh")), None)
outfit_h, outfit = add(unreal.SkeletalMeshComponent, "Outfit", mesh_h, tmpl[out_name], SKM_PROPS) if out_name else (None, None)
for g in ("Hair", "Eyebrows", "Eyelashes", "Fuzz"):
    if g in tmpl and tmpl[g].get_editor_property("groom_asset"):
        add(unreal.GroomComponent, g, face_h, tmpl[g], ("groom_asset", "binding_asset", "relative_location", "relative_rotation"))
        print("groom", g, tmpl[g].get_editor_property("groom_asset").get_name())
root_h = next(h for n, h in by_name.items() if n.startswith("CollisionCylinder"))
mhc_h, mhc = add(unreal.MetaHumanComponentUE, "MetaHuman", root_h, tmpl.get("MetaHuman"),
                 ("enable_body_correctives", "enable_neck_correctives", "enable_neck_proc_control_rig", "legs", "feet"))
mhc.set_editor_property("body_component_name", "CharacterMesh0")
mhc.set_editor_property("face_component_name", "Face")
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
lib.save_loaded_asset(bp, only_if_is_dirty=False)
print("BP_AgoraMH compiled, status", bp.get_editor_property("status"))
