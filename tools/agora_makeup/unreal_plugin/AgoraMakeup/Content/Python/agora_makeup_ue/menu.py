"""Tools > Agora Makeup: one entry per base look (grouped by family), a few intensities, and Reset.
Each entry paints onto the MetaHuman selected in the level. Variants by id: in the Python console,
agora_makeup_ue.core.apply("latte__glam__classic_red")."""
import unreal

from . import core


def _cmd(look):
    return "import agora_makeup_ue.core as c; c.apply(%r)" % look


def register():
    menus = unreal.ToolMenus.get()
    tools = menus.find_menu("LevelEditor.MainMenu.Tools")
    if tools is None:
        return
    root = tools.add_sub_menu("AgoraMakeup", "Agora", "AgoraMakeup", "Agora Makeup", "Paint a makeup look on the selected MetaHuman")
    try:
        data = core.list_looks()
    except Exception as e:
        unreal.log_warning("Agora Makeup: cannot list looks: %s" % e)
        return
    fams = {}
    for b in data["base"]:
        fams.setdefault(b["family"], []).append(b)
    for fam, looks in sorted(fams.items()):
        sub = menus.register_menu("LevelEditor.MainMenu.Tools.AgoraMakeup." + fam, "", unreal.MultiBoxType.MENU, False)
        root_entry = menus.find_menu("LevelEditor.MainMenu.Tools.AgoraMakeup")
        root_entry.add_sub_menu("AgoraMakeup", "Looks", fam, fam.title(), "")
        for b in looks:
            for inten in ("soft", "standard", "glam"):
                e = unreal.ToolMenuEntry(name="%s_%s" % (b["id"], inten), type=unreal.MultiBlockType.MENU_ENTRY)
                e.set_label("%s (%s)" % (b["name"], inten))
                look = b["id"] if inten == "standard" else "%s__%s" % (b["id"], inten)
                e.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, "", _cmd(look))
                sub.add_menu_entry("Looks", e)
    r = unreal.ToolMenuEntry(name="AgoraMakeupReset", type=unreal.MultiBlockType.MENU_ENTRY)
    r.set_label("Reset makeup on selected")
    r.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, "", "import agora_makeup_ue.core as c; c.reset()")
    menus.find_menu("LevelEditor.MainMenu.Tools.AgoraMakeup").add_menu_entry("Reset", r)
    for name, label, cmd in (("AgoraMakeupCompare", "Compare 1000 looks (sheet of the best)", "c.compare(1000)"),
                             ("AgoraMakeupBest", "Apply #1 from the last comparison", "c.apply_rank(1)"),
                             ("AgoraMakeupBest2", "Apply #2 from the last comparison", "c.apply_rank(2)"),
                             ("AgoraMakeupBest3", "Apply #3 from the last comparison", "c.apply_rank(3)")):
        e = unreal.ToolMenuEntry(name=name, type=unreal.MultiBlockType.MENU_ENTRY)
        e.set_label(label)
        e.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, "", "import agora_makeup_ue.core as c; " + cmd)
        menus.find_menu("LevelEditor.MainMenu.Tools.AgoraMakeup").add_menu_entry("Compare", e)
    menus.refresh_all_widgets()
    unreal.log("Agora Makeup: %d base looks, %d variants" % (len(data["base"]), data["variants"]))
