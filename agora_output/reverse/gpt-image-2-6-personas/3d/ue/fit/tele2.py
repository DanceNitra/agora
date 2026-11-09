"""Telephoto viewport capture through the piloted FIT_TELE camera: python tele2.py <tag> [fov] [dist]."""
import json, os, subprocess, sys, base64, io
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
import fit_lib as f
from PIL import Image

def shoot(tag, fov=12.0, dist=150.0, dz=0.0):
    json.dump({"mode": "on", "head": list(f.HEAD), "dist": dist, "fov": fov, "dz": dz},
              open(os.path.join(f.F, "pilot_cfg.json"), "w"))
    f.ue(open(os.path.join(f.F, "ue_pilot.py")).read())
    T = {"location": {"x": f.HEAD[0], "y": f.HEAD[1] + dist, "z": f.HEAD[2] + dz},
         "rotation": {"pitch": 0, "yaw": -90, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}
    out = os.path.join(f.F, "_cap.json")
    args = {"toolset_name": "EditorToolset.EditorAppToolset", "tool_name": "CaptureViewport",
            "arguments": {"captureTransform": T, "bShowUI": False,
                          "annotations": {"gridSpacing": 0, "gridExtent": 0, "gridHeight": 0,
                                          "maxLabelDistance": 0, "classFilter": None, "maxLabels": 0}}}
    subprocess.run([sys.executable, "-I", f.UMCP, "call_tool", json.dumps(args), out], capture_output=True, timeout=120)
    rv = json.loads(json.load(open(out, encoding="utf-8"))["result"]["content"][0]["text"])["returnValue"]
    im = Image.open(io.BytesIO(base64.b64decode(rv["image"]["data"]))).convert("RGB")
    p = os.path.join(f.F, f"tele_{tag}.png")
    im.save(p)
    json.dump({"loc": rv["cameraLocation"], "rot": rv["cameraRotation"], "fov": rv["cameraFOV"]},
              open(os.path.join(f.F, f"tele_{tag}_cam.json"), "w"))
    return p

if __name__ == "__main__":
    a = sys.argv
    print(shoot(a[1], *(float(x) for x in a[2:])))
