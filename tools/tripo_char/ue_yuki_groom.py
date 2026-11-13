"""Runs inside Unreal. Imports Yuki's strand hair (Alembic written in Unreal axes and centimetres by
yuki_hair_strands.py) as a groom with identity conversion, and stands it with the conformed head mesh in a preview
level of its own. Touches only /Game/AgoraChar/Tripo/Yuki and saves only the assets it names."""
import unreal

ABC = globals().get("ABC", r"C:\Users\Danculus\agora\tools\tripo_char\models\yuki\hair_strands_mh\yuki_hair_ue.abc")
PKG = "/Game/AgoraChar/Tripo/Yuki"
NAME = globals().get("GROOM_NAME", "GR_Yuki_Hair")
HEAD = globals().get("HEAD", PKG + "/Geo_MHC_Yuki_v2/MHC_Yuki_v2_Head")
LEVEL = PKG + "/L_Yuki_Preview"
lib = unreal.EditorAssetLibrary

opts = unreal.GroomImportOptions()
conv = unreal.GroomConversionSettings()
conv.set_editor_property("rotation", unreal.Vector(0, 0, 0))
conv.set_editor_property("scale", unreal.Vector(1, 1, 1))
opts.set_editor_property("conversion_settings", conv)
task = unreal.AssetImportTask()
task.filename = ABC
task.destination_path = PKG
task.destination_name = NAME
task.automated = True
task.replace_existing = True
task.save = False
task.options = opts
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
print("imported", [str(p) for p in task.imported_object_paths])
groom = unreal.load_asset(f"{PKG}/{NAME}")
if groom is None:
    raise RuntimeError("groom did not import")
print("groom", groom.get_class().get_name(), "groups", len(groom.get_editor_property("hair_groups_info")))

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
print("level", les.load_level(LEVEL) if lib.does_asset_exist(LEVEL) else les.new_level(LEVEL))
for a in eas.get_all_level_actors():
    if a.get_actor_label().startswith("Yuki_"):
        eas.destroy_actor(a)


def spawn(cls, label, loc=(0, 0, 0), rot=(0, 0, 0)):
    a = eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))
    a.set_actor_label(label)
    return a


sun = spawn(unreal.DirectionalLight, "Yuki_Sun", (0, 0, 400), (0, -35, -70))
sun.light_component.set_intensity(3.0)
sky = spawn(unreal.SkyLight, "Yuki_Sky", (0, 0, 300))
sky.light_component.set_editor_property("real_time_capture", True)
sky.light_component.set_intensity(2.5)
fill = spawn(unreal.DirectionalLight, "Yuki_Fill", (0, 0, 400), (0, -25, 70))
fill.light_component.set_intensity(2.0)
fill.light_component.set_cast_shadows(False)
spawn(unreal.SkyAtmosphere, "Yuki_Atmos")
floor = spawn(unreal.StaticMeshActor, "Yuki_Floor", (0, 0, -5))
floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
floor.set_actor_scale3d(unreal.Vector(20, 20, 1))
head = unreal.load_asset(HEAD)
if head:
    ha = eas.spawn_actor_from_object(head, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    ha.set_actor_label("Yuki_Head")
    o, e = ha.get_actor_bounds(False)
    print("head bounds lo", o - e, "hi", o + e)
ga = eas.spawn_actor_from_object(groom, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
ga.set_actor_label("Yuki_Hair")
o, e = ga.get_actor_bounds(False)
print("hair bounds lo", o - e, "hi", o + e, "class", ga.get_class().get_name())
print("save", lib.save_asset(f"{PKG}/{NAME}", only_if_is_dirty=False), lib.save_asset(LEVEL, only_if_is_dirty=False))
