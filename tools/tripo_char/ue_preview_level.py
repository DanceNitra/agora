"""Runs inside Unreal. Opens (or creates) a preview level inside our own folder and stands the built hero in it
with plain light. No other level is touched or saved."""
import json

import unreal

CFG = json.load(open(r"C:\Users\Danculus\agora\tools\tripo_char\current.json"))
PKG = "/Game/AgoraChar/Tripo/Hero01"
LEVEL = PKG + "/L_Hero01_Preview"
BP = f"{PKG}/Built_{CFG['name']}/{CFG['name']}/BP_{CFG['name']}"
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
    print("load", les.load_level(LEVEL))
else:
    print("new", les.new_level(LEVEL))
for a in eas.get_all_level_actors():
    if a.get_actor_label().startswith("Hero01_"):
        eas.destroy_actor(a)


def spawn(cls, label, loc=(0, 0, 0), rot=(0, 0, 0)):
    a = eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))
    a.set_actor_label(label)
    return a


sun = spawn(unreal.DirectionalLight, "Hero01_Sun", (0, 0, 400), (0, -35, -70))
sun.light_component.set_intensity(3.0)
sky = spawn(unreal.SkyLight, "Hero01_Sky", (0, 0, 300))
sky.light_component.set_editor_property("real_time_capture", True)
sky.light_component.set_intensity(2.5)
fill = spawn(unreal.DirectionalLight, "Hero01_Fill", (0, 0, 400), (0, -25, 70))
fill.light_component.set_intensity(2.0)
fill.light_component.set_cast_shadows(False)
spawn(unreal.SkyAtmosphere, "Hero01_Atmos")
floor = spawn(unreal.StaticMeshActor, "Hero01_Floor", (0, 0, -5))
floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
floor.set_actor_scale3d(unreal.Vector(20, 20, 1))
hero = eas.spawn_actor_from_object(unreal.load_asset(BP), unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
hero.set_actor_label("Hero01_Character")
print("hero", hero.get_class().get_name(), [c.get_name() for c in hero.get_components_by_class(unreal.SceneComponent)])
print("saved level", unreal.EditorAssetLibrary.save_asset(LEVEL, only_if_is_dirty=False))
