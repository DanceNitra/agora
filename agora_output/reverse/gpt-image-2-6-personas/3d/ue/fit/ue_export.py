# Runs INSIDE Unreal: writes the live FIT_MH face mesh vertices to face_v.bin.
import unreal, struct
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
for c in unreal.ObjectIterator(unreal.SkeletalMeshComponent):
    o = c.get_owner()
    if o and o.get_actor_label() == "FIT_MH" and c.get_name() == "Face":
        v, t = mhs.get_mesh_data_for_conforming(c.get_skeletal_mesh_asset())
open(F + r"\face_v.bin", "wb").write(struct.pack("<%df" % (3 * len(v)), *[x for p in v for x in (p.x, p.y, p.z)]))
print("EXPORT", len(v))
