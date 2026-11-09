"""Generate many looks, paint them on the frontal view of the face, rank them, write a sheet of the best.

  python compare.py --n 1000 [--ref photo.jpg] [--top 24] [--out sheet.png] [--seed 1]

Ranking:
  --ref  : closest to a reference face (per-zone Lab of lips, blush, lid, contour, read with MediaPipe
           landmarks on the reference), relative to each face's own skin.
  default: makeup-artist rules from the Makeup Atlas research: undertone harmony between skin, lips and
           blush; one statement feature (eyes or lips) rather than both at full strength; enough contrast to
           read on camera. The score is a ranking aid, not a verdict; the owner picks.
Speed: masks are computed once per zone and cached at preview size; looks are painted in parallel.
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agora_makeup import library, paint, zones  # noqa: E402

PX = 256
_G = {}


def _init(base_path):
    vm, face = paint.view_face()
    base = cv2.imread(base_path)
    _G["base"] = cv2.resize(base, (PX, PX), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    _G["valid"] = cv2.resize(np.isfinite(vm.view_uv[..., 0]).astype(np.float32), (PX, PX))
    _G["face"] = zones.Face(PX, os.path.join(paint.VM.DATA, "view_landmarks.json"), vm.view_px)  # masks drawn at preview size
    _G["masks"] = {}


def _mask(L):
    key = (L["zone"], json.dumps(L.get("params", {}), sort_keys=True))
    m = _G["masks"].get(key)
    if m is None:
        m = zones.mask(_G["face"], L["zone"], L.get("params", {})) * _G["valid"]
        _G["masks"][key] = m
    return m


def _paint(look):
    img = _G["base"].copy()
    for L in look["layers"]:
        if "color" not in L or not L.get("on", True):
            continue
        op = min(1.0, float(L.get("opacity", 0.5)) * paint.RENDER_GAIN.get(L["zone"], 1.0))
        if op > 0:
            img = paint._blend(img, L["color"], _mask(L) * op, L.get("blend", "normal"), L.get("keep_l", 0.6))
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def _lab(c):
    return cv2.cvtColor(np.uint8([[c[::-1]]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0] - [0, 128, 128]


def rule_score(look, skin_lab):
    """Higher is better. Uses only the look's own colours and strengths."""
    by = {}
    for L in look["layers"]:
        if "color" in L:
            by.setdefault(L["zone"], []).append(L)
    warm_skin = skin_lab[2] > 14
    s = 0.0
    lip = by.get("lips", [None])[0]
    blush = by.get("blush", [None])[0]
    if lip and blush:
        hl, hb = (np.degrees(np.arctan2(_lab(x["color"])[2], _lab(x["color"])[1])) for x in (lip, blush))
        s += 1.0 - min(abs(hl - hb), 60) / 60            # lips and blush in the same family
    if lip:
        h = np.degrees(np.arctan2(_lab(lip["color"])[2], _lab(lip["color"])[1]))
        s += 0.6 if (h > 25) == warm_skin else 0.2        # undertone harmony
    eye_strength = sum(L["opacity"] for z in ("outer_v", "liner", "crease") for L in by.get(z, []))
    lip_strength = lip["opacity"] * (1 - _lab(lip["color"])[0] / 100) if lip else 0
    s += 0.8 if (eye_strength > 1.0) != (lip_strength > 0.45) else 0.1  # one statement feature
    contrast = abs(_lab(lip["color"])[0] - skin_lab[0]) if lip else 0
    s += min(contrast, 35) / 35 * 0.6                     # reads on camera
    return round(float(s), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--top", type=int, default=24)
    ap.add_argument("--base", default=os.path.join(os.path.dirname(paint.VM.__file__), "data", "frontal_base.png"))
    ap.add_argument("--out", default="compare_top.png")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    t0 = time.time()
    import itertools
    combos = list(itertools.product(library.base_looks(), library.INTENSITY, [None] + list(library.LIP), [None] + list(library.EYE)))
    rng = np.random.default_rng(a.seed)
    looks = [library.variant(*combos[i]) for i in rng.choice(len(combos), min(a.n, len(combos)), replace=False)]
    base = cv2.imread(a.base)
    vm, face = paint.view_face()
    skin = cv2.cvtColor(base, cv2.COLOR_BGR2LAB).astype(np.float32)
    cz = np.array([face.P(i) for i in zones.EYE["A"]["cheek"]]).mean(0).astype(int)
    skin_lab = skin[cz[1] - 8:cz[1] + 8, cz[0] - 8:cz[0] + 8].reshape(-1, 3).mean(0) * [100 / 255, 1, 1] - [0, 128, 128]
    scored = sorted(((rule_score(l, skin_lab), l) for l in looks), key=lambda x: -x[0])
    with Pool(a.workers, initializer=_init, initargs=(a.base,)) as pool:   # paint ALL looks, not only the top
        allimgs = pool.map(_paint, [l for _, l in scored], chunksize=max(1, len(scored) // (a.workers * 4)))
    t1 = time.time()
    top, imgs = scored[:a.top], allimgs[:a.top]
    np.save(os.path.splitext(a.out)[0] + "_all.npy", np.stack(allimgs))
    tiles = []
    for (s, l), im in zip(top, imgs):
        im = im.copy()
        cv2.putText(im, l["id"][:34], (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1)
        cv2.putText(im, "score %.2f" % s, (4, PX - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        tiles.append(im)
    cols = 6
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(a.out, np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]))
    json.dump([{"rank": i + 1, "score": s, "id": l["id"]} for i, (s, l) in enumerate(scored)],
              open(os.path.splitext(a.out)[0] + "_ranking.json", "w"), indent=1)
    print(json.dumps({"looks": len(looks), "painted_and_ranked_s": round(t1 - t0, 2), "top": [l["id"] for _, l in top[:5]],
                      "sheet": a.out}))


if __name__ == "__main__":
    main()
