"""Capture LS_Depesa_line1_v3 frames through the sequence camera: python seq_shoot.py <outdir> <f0> <f1> <step>."""
import json, os, sys, subprocess, base64, io
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
import fit_lib as f
from PIL import Image
outdir, f0, f1, step = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
os.makedirs(outdir, exist_ok=True)
T = {"location": {"x": 0.0, "y": 300110.0, "z": 100166.0}, "rotation": {"pitch": -1, "yaw": -90, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}
for fr in range(f0, f1, step):
    json.dump({"seq": "/Game/Companions/Lipsync/LS_Depesa_line1_v3", "frame": fr, "open": False}, open(os.path.join(f.F, "seqframe_cfg.json"), "w"))
    f.ue(open(os.path.join(f.F, "ue_seqframe.py")).read())
    out = os.path.join(f.F, "_cap.json")
    args = {"toolset_name": "EditorToolset.EditorAppToolset", "tool_name": "CaptureViewport",
            "arguments": {"captureTransform": T, "bShowUI": False, "annotations": {"gridSpacing": 0, "gridExtent": 0, "gridHeight": 0, "maxLabelDistance": 0, "classFilter": None, "maxLabels": 0}}}
    subprocess.run([sys.executable, "-I", f.UMCP, "call_tool", json.dumps(args), out], capture_output=True, timeout=120)
    rv = json.loads(json.load(open(out, encoding="utf-8"))["result"]["content"][0]["text"])["returnValue"]
    Image.open(io.BytesIO(base64.b64decode(rv["image"]["data"]))).convert("RGB").save(os.path.join(outdir, "%04d.png" % fr))
    print("F", fr, flush=True)
