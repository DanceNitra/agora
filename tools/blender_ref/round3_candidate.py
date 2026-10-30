"""Build one round-3 candidate in a background Blender and save it.

blender -b robot_v10_legs_round2b.blend -P round3_candidate.py -- <params-json> <out.blend>
Body, under-frame and hip rise by the same DZ as the hub, so the leg stays attached.
"""
import json
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
params, out = json.loads(argv[0]), argv[1]
bpy.app.driver_namespace["leg_params"] = params
exec(open(r"C:\Users\Danculus\agora\tools\blender_ref\build_leg_v3.py", encoding="utf-8").read())
dz = bpy.app.driver_namespace["leg_dz"]
O = bpy.data.objects
O["body_root"].location.z = 1.15 + dz
B = params.get("B", 1.196)
O["body_root"].scale = (B, B, B)
for n in [n for n in O.keys() if n.startswith("under_frame")]:
    O[n].location.z += dz
bpy.ops.wm.save_as_mainfile(filepath=out)
print("[candidate] saved", out, "dz", round(dz, 3))
