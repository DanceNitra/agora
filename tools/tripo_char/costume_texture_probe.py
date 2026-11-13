"""Measures the costume's colour texture around the shoulders: is the cloth there darker than the rest of the tunic?
Tripo bakes shading into the colour, so a fold that sat in shadow on the source figure stays dark when the pose opens
it. Prints luminance percentiles by region and paints the dark texels red in a copy of the texture.

    blender_headless.sh costume_texture_probe.py -- <body.fbx> <costume.fbx> <out_dir>
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

body_fbx, cos_fbx, out = sys.argv[-3], sys.argv[-2], Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(Path(path).resolve()))
    return [o for o in bpy.data.objects if o not in before]


barm = next(o for o in load(body_fbx) if o.type == "ARMATURE")
cobjs = load(cos_fbx)
cos = max((o for o in cobjs if o.type == "MESH"), key=lambda o: len(o.data.vertices))
img = next(n.image for m in cos.data.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and "Color" in n.image.name)
W, H = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)
lum = 0.2126 * px[..., 0] + 0.7152 * px[..., 1] + 0.0722 * px[..., 2]

me = cos.data
uv = np.zeros((len(me.loops), 2))
me.uv_layers.active.data.foreach_get("uv", uv.ravel())
lv = np.zeros(len(me.loops), dtype=np.int64)
me.loops.foreach_get("vertex_index", lv)
P = np.array([cos.matrix_world @ v.co for v in me.vertices])
xs = np.clip((uv[:, 0] % 1) * W, 0, W - 1).astype(int)
ys = np.clip((uv[:, 1] % 1) * H, 0, H - 1).astype(int)
L = lum[ys, xs]
LP = P[lv]
rep = {}
for side in ("l", "r"):
    j = np.array(barm.matrix_world @ barm.pose.bones["upperarm_" + side].head)
    d = np.linalg.norm(LP - j, axis=1)
    for name, m in (("within_12cm", d < 0.12), ("within_12cm_back", (d < 0.12) & (LP[:, 1] > j[1] + 0.02)),
                    ("within_12cm_below_joint", (d < 0.12) & (LP[:, 2] < j[2] - 0.02))):
        rep[f"{side}_{name}"] = [int(m.sum())] + [round(float(x), 3) for x in np.percentile(L[m], [5, 25, 50])]
torso = (LP[:, 2] > 1.0) & (LP[:, 2] < 1.35) & (np.abs(LP[:, 0]) < 0.12)
rep["torso_mid"] = [int(torso.sum())] + [round(float(x), 3) for x in np.percentile(L[torso], [5, 25, 50])]
dark = np.percentile(L[torso], 5)
mark = px.copy()
for side in ("l", "r"):
    j = np.array(barm.matrix_world @ barm.pose.bones["upperarm_" + side].head)
    m = (np.linalg.norm(LP - j, axis=1) < 0.12) & (L < dark)
    mark[ys[m], xs[m]] = (1, 0, 0, 1)
    rep[f"{side}_dark_loops_below_torso_p5"] = int(m.sum())
o = bpy.data.images.new("marked", W, H)
o.pixels = mark.ravel()
o.filepath_raw = str(out / "color_dark_shoulder_texels.png")
o.file_format = "PNG"
o.save()
(out / "texture_probe.json").write_text(json.dumps(rep, indent=1))
print("TEX", json.dumps(rep), flush=True)
