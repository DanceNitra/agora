"""Portrait telephoto render of the head: python tele.py <tag>. Writes tele_<tag>.png (RGB)."""
import json, sys, os
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
import fit_lib as f
from PIL import Image

def shoot(tag, fov=12.0, dist=150.0, w=1024, h=1536):
    cfg = {"head": list(f.HEAD), "fov": fov, "dist": dist, "w": w, "h": h, "dz": 0.0, "tag": tag}
    for mode in ("shoot", "save"):
        cfg["mode"] = mode
        json.dump(cfg, open(os.path.join(f.F, "tele_cfg.json"), "w"))
        f.ue(open(os.path.join(f.F, "ue_tele.py")).read())
    p = os.path.join(f.F, "tele_" + tag)
    for ext in ("", ".hdr", ".png", ".exr"):
        if os.path.exists(p + ext):
            Image.open(p + ext).convert("RGB").save(p + ".png") if ext != ".png" else None
            if ext == "":
                os.replace(p + ".png", p + ".png")
            return p + ".png", ext
    return None, None

if __name__ == "__main__":
    print(shoot(sys.argv[1]))
