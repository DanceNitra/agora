"""Driver helpers run OUTSIDE Unreal: set coefficients, capture the face through the MCP viewport, track
landmarks inside Unreal, and score against the reference landmarks."""
import base64, io, json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
sys.path.insert(0, r"C:\Users\Danculus\agora\tools\comfy_char")
import ue_py  # noqa: E402

F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
UMCP = r"C:\Users\Danculus\.claude\skills\66-unreal-engine-director\scripts\umcp.py"
ASSET = "/Game/Companions/MetaHuman/MH_Depesa"
HEAD = (0.0, 300001.1, 100162.2)
CAM = {"location": {"x": HEAD[0], "y": HEAD[1] + 42.0, "z": HEAD[2] + 2.0},
       "rotation": {"pitch": -2, "yaw": -90, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}


def ue(code):
    p = os.path.join(F, "_ue_tmp.py")
    open(p, "w", encoding="utf-8").write(code)
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ue_py.run_file(p, timeout=30)
    if rc:
        raise RuntimeError(buf.getvalue())
    return buf.getvalue()


def get_coeffs():
    out = ue(f'''import unreal, json
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("{ASSET}")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
print("COEF" + json.dumps(list(mhs.get_face_model_coefficients(ch))))''')
    return json.loads(out.split("COEF", 1)[1].strip().splitlines()[0])


def set_coeffs(c):
    json.dump([float(x) for x in c], open(os.path.join(F, "_coeffs.json"), "w"))
    ue(f'''import unreal, json
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("{ASSET}")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
mhs.set_face_model_coefficients(ch, json.load(open(r"{F}\_coeffs.json")))''')


def capture(tag):
    out = os.path.join(F, tag + "_cap.json")
    args = {"toolset_name": "EditorToolset.EditorAppToolset", "tool_name": "CaptureViewport",
            "arguments": {"captureTransform": CAM, "bShowUI": False,
                          "annotations": {"gridSpacing": 0, "gridExtent": 0, "gridHeight": 0,
                                          "maxLabelDistance": 0, "classFilter": None, "maxLabels": 0}}}
    subprocess.run([sys.executable, "-I", UMCP, "call_tool", json.dumps(args), out], capture_output=True, timeout=120)
    d = json.load(open(out, encoding="utf-8"))
    inner = json.loads(d["result"]["content"][0]["text"])
    im = Image.open(io.BytesIO(base64.b64decode(inner["returnValue"]["image"]["data"]))).convert("RGBA")
    os.remove(out)
    return im


def track(im, tag):
    W, H = 512, 768
    w, h = im.size
    # centre crop to the reference aspect, then resize
    cw = int(h * W / H)
    x0 = (w - cw) // 2
    im = im.crop((x0, 0, x0 + cw, h)).resize((W, H), Image.LANCZOS)
    im.convert("RGB").save(os.path.join(F, tag + ".png"))
    r, g, b, a = im.split()
    open(os.path.join(F, "_cur.bgra"), "wb").write(Image.merge("RGBA", (b, g, r, a)).tobytes())
    out = ue(f'''import unreal, json
raw = open(r"{F}\_cur.bgra", "rb").read()
cols = [unreal.Color(raw[i+2], raw[i+1], raw[i], raw[i+3]) for i in range(0, len(raw), 4)]
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
res = mhs.track_face_landmarks_from_image(cols, {W}, {H})
o = {{str(k): [[p.x, p.y] for p in v.get_editor_property("tracking_points")] for k, v in (res or {{}}).items()}}
print("LM" + json.dumps(o))''')
    return json.loads(out.split("LM", 1)[1].strip().splitlines()[0])


def flat(lm, keys):
    return np.array([p for k in keys for p in lm[k]], dtype=float)


def aligned_error(cur, ref):
    """Similarity-align cur to ref (Procrustes), return RMS in reference pixels."""
    keys = sorted(set(cur) & set(ref))
    if not keys or any(len(cur[k]) != len(ref[k]) for k in keys):
        return 1e9, None
    A, B = flat(cur, keys), flat(ref, keys)
    ma, mb = A.mean(0), B.mean(0)
    a, b = A - ma, B - mb
    s = np.sqrt((b ** 2).sum() / (a ** 2).sum())
    u, _, vt = np.linalg.svd(a.T @ b)
    R = u @ vt
    a2 = s * a @ R
    return float(np.sqrt(((a2 - b) ** 2).sum(1).mean())), (a2 + mb)
