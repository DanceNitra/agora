"""Sweep one beauty parameter set, shoot each, measure cheek and iris colour against p6 (Lab distance).
python beauty_sweep.py <sweep.json>  where sweep.json = {"name": ..., "variants": [cfg, ...]}"""
import json, sys, os
import numpy as np, cv2
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
sys.path.insert(0, F); os.chdir(F)
import fit_lib as f, tele2, mp_lm

CHEEK = [50, 101, 118, 117, 123, 187, 205, 280, 330, 347, 346, 352, 411, 425]
IRIS_L, IRIS_R = 468, 473

def colours(path):
    im = cv2.imread(path); p = mp_lm.detect(path)
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(float)
    def patch(x, y, r):
        x, y = int(x), int(y)
        return lab[y - r:y + r, x - r:x + r].reshape(-1, 3)
    eye_r = max(2, int(np.linalg.norm(p[469] - p[471]) / 4))
    cheek = np.vstack([patch(*p[i], max(3, eye_r)) for i in CHEEK]).mean(0)
    iris = np.vstack([patch(*p[i], eye_r) for i in (IRIS_L, IRIS_R)]).mean(0)
    return cheek, iris

ref_cheek, ref_iris = colours("ref_512x768.png")
sw = json.load(open(sys.argv[1]))
for i, cfg in enumerate(sw["variants"]):
    json.dump(cfg, open("beauty_cfg.json", "w"))
    out = f.ue(open("ue_beauty.py").read())
    p = tele2.shoot(f"{sw['name']}{i}", 18.0, 90.0, -0.6)
    c, ir = colours(p)
    print(i, json.dumps(cfg), "cheek dE", round(float(np.linalg.norm(c - ref_cheek)), 1),
          "iris dE", round(float(np.linalg.norm(ir - ref_iris)), 1), "cheek", c.round(0).tolist(), "ref", ref_cheek.round(0).tolist(), flush=True)
