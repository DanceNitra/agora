# Runs INSIDE Unreal: hide the grooms named in grooms_hide.json on the transient FIT_MH actor.
import json
import unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
hide = set(json.load(open(F + r"\grooms_hide.json")))
for c in unreal.ObjectIterator(unreal.GroomComponent):
    o = c.get_owner()
    if o and o.get_actor_label() == "FIT_MH":
        c.set_visibility(c.get_name() not in hide, True)
        print("GROOM", c.get_name(), c.is_visible())
