"""Swap eyebrow grooms and shoot each only after the groom renders (brow band darkens or 150 s)."""
import json, sys, time
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
import numpy as np, cv2
import fit_lib as f, tele2, mp_lm

def brow_dark(path):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE); p = mp_lm.detect(path)
    if p is None:
        return 0.0
    pts = p[[70, 63, 105, 66, 107, 336, 296, 334, 293, 300]].astype(int)
    vals = [im[y - 4:y + 5, x - 4:x + 5].mean() for x, y in pts]
    return float(np.mean(np.array(vals) < 60))

items = sys.argv[1:]
for i, b in enumerate(items):
    json.dump({"items": {"Eyebrows": "/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/" + b}}, open("wardrobe_cfg.json", "w"))
    f.ue(open("ue_wardrobe.py").read()); f.ue(open("ue_groomcolor.py").read()); f.ue(open("ue_grooms.py").read())
    t0 = time.time(); d = 0.0
    while time.time() - t0 < 150:
        time.sleep(15)
        p = tele2.shoot(f"br{i}", 18.0, 90.0, -0.6)
        d = brow_dark(p)
        if d >= 0.5:
            break
    print("BR", i, b, "dark share", round(d, 2), "after", int(time.time() - t0), "s", flush=True)
