import unreal
u = unreal.EditorLoadingAndSavingUtils
c = [p.get_name() for p in u.get_dirty_content_packages()]
m = [p.get_name() for p in u.get_dirty_map_packages()]
print("OK dirty content", len(c), c[:30])
print("OK dirty maps", m)
