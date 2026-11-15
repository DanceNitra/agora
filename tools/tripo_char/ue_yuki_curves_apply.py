"""Runs inside Unreal. Makes a face AnimSequence from a curve file written by yuki_emotion_compose.py.

A wrapper sets ARGS = dict(SRC=<AnimSequence to copy: skeleton, length, rate>, DST=<new asset path>, STEM=<file stem
of .f32 and .json>, and optionally EPS). Curves of the file replace the copy's curves, one key per frame; a curve that
stays under EPS (default 0.002) in the file is written as a single zero key. Saves DST.

All edits go through the animation data controller inside one bracket. AnimationLibrary.add_float_curve_keys outside a
bracket rebuilds the compressed animation after EVERY key: measured 2026-11-14, 25 keys per second, 13 hours for this
file. Inside the bracket the rebuild runs once, at the end."""
import array
import json
import time

import unreal

_A = globals().pop("ARGS", {})
EPS = _A.get("EPS", 0.002)
lib, al = unreal.EditorAssetLibrary, unreal.AnimationLibrary
# An existing DST is reused: every curve is overwritten anyway. Deleting it and duplicating to the same path in one
# run gave an asset that reported no curves (measured 2026-11-14).
anim = unreal.load_asset(_A["DST"]) if lib.does_asset_exist(_A["DST"]) else lib.duplicate_asset(_A["SRC"], _A["DST"])
meta = json.load(open(_A["STEM"] + ".json"))
buf = array.array("f")
with open(_A["STEM"] + ".f32", "rb") as f:
    buf.fromfile(f, len(meta["names"]) * meta["keys"])
n, fps = meta["keys"], (meta["keys"] - 1) / meta["length"]
# Names compare without case: a duplicated asset reports its curve names in lower case (measured 2026-11-14).
have = set(str(x).lower() for x in al.get_animation_curve_names(anim, unreal.RawCurveTrackTypes.RCT_FLOAT))
assert have == set(x.lower() for x in meta["names"]), ("curve sets differ", sorted(have ^ set(x.lower() for x in meta["names"]))[:6])
ctl = anim.get_editor_property("controller") if hasattr(anim, "controller") else anim.controller
t0, dense = time.time(), 0
skel = anim.get_skeleton()
ctl.open_bracket(unreal.Text("Yuki composed face curves"), False)
try:
    for k, name in enumerate(meta["names"]):
        vals = buf[k * n:(k + 1) * n]
        cid = unreal.AnimationCurveIdentifierExtensions.get_curve_identifier(skel, name, unreal.RawCurveTrackTypes.RCT_FLOAT)
        assert cid.is_valid(), name
        if max(abs(v) for v in vals) < EPS:
            keys = [unreal.RichCurveKey(time=0.0, value=0.0)]
        else:
            keys = [unreal.RichCurveKey(time=i / fps, value=v, interp_mode=unreal.RichCurveInterpMode.RCIM_LINEAR) for i, v in enumerate(vals)]
            dense += 1
        if not ctl.set_curve_keys(cid, keys, False):
            raise RuntimeError("set_curve_keys failed for " + name)
        if k % 40 == 0:
            unreal.log("APPLY progress %d/%d curves, %.0f s" % (k, len(meta["names"]), time.time() - t0))
finally:
    ctl.close_bracket(False)
t, v = al.get_float_keys(anim, "CTRL_expressions_jawOpen")
print("APPLY", anim.get_path_name(), "curves", len(meta["names"]), "dense", dense, "jaw keys", len(v), "length", round(anim.get_play_length(), 3),
      "seconds", round(time.time() - t0, 1), "saved", lib.save_asset(_A["DST"], only_if_is_dirty=False))
