"""Command line for the Unreal plugin (the editor's Python has no OpenCV, so painting runs here).

  python cli.py list                      -> JSON list of base looks and the variant count
  python cli.py paint --look ID --bc BASE_BC.png --srmf BASE_SRMF.png --out-bc OUT_BC.png --out-srmf OUT_SRMF.png
  python cli.py describe --look ID        -> the look's layers as JSON
IDs: a base look id (for example "luvpauli_doll") or a variant id from library.generate()
(for example "latte__glam__classic_red__espresso").
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2  # noqa: E402

from agora_makeup import library, paint, zones  # noqa: E402


ZONEMAP = [("blush", [255, 0, 255], {"placement": "high"}), ("contour_cheek", [0, 0, 255], {}), ("contour_nose", [0, 160, 255], {}),
           ("conceal_undereye", [255, 255, 0], {}), ("lid", [0, 255, 0], {}), ("outer_v", [255, 128, 0], {}),
           ("liner", [255, 0, 0], {"wing_len": 0.4}), ("inner_corner", [255, 255, 255], {}), ("aegyo_sal", [0, 255, 255], {}),
           ("highlight", [128, 255, 128], {"spots": ["cheek", "nose_bridge", "nose_tip", "cupid", "browbone"]}),
           ("contour_temple", [128, 0, 255], {}), ("contour_jaw", [0, 90, 120], {}), ("lip_liner", [255, 60, 0], {"overline": 0.03})]


def find(look_id):
    if look_id == "zonemap":  # calibration: every zone a flat, opaque, distinct colour
        return {"id": "zonemap", "name": "Zone map", "family": "debug", "source": "", "layers":
                [{"zone": z, "color": c, "opacity": 0.85, "blend": "normal", "params": {**p, "soft": 0.02}} for z, c, p in ZONEMAP]}
    for b in library.base_looks():
        if b["id"] == look_id:
            return b
    parts = look_id.split("__")
    base = next(b for b in library.base_looks() if b["id"] == parts[0])
    inten = parts[1] if len(parts) > 1 else "standard"
    rest = parts[2:]
    lip = next((p for p in rest if p in library.LIP), None)
    eye = next((p for p in rest if p in library.EYE and p != lip), None)
    if lip and eye is None and rest.count(lip) == 2:
        eye = lip
    blush = next((p for p in rest if p in library.BLUSH), None)
    return library.variant(base, inten, lip, eye, blush)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "paint", "describe"])
    ap.add_argument("--look")
    ap.add_argument("--bc")
    ap.add_argument("--srmf")
    ap.add_argument("--out-bc")
    ap.add_argument("--out-srmf")
    ap.add_argument("--no-gain", action="store_true", help="UV preview strength (no render calibration)")
    ap.add_argument("--body-bc")
    ap.add_argument("--out-body-bc")
    a = ap.parse_args()
    if a.cmd == "list":
        print(json.dumps({"base": [{"id": b["id"], "name": b["name"], "family": b["family"]} for b in library.base_looks()],
                          "palettes": {"lip": list(library.LIP), "eye": list(library.EYE), "blush": list(library.BLUSH)},
                          "intensity": list(library.INTENSITY), "variants": len(library.generate())}))
        return
    look = find(a.look)
    if a.cmd == "describe":
        print(json.dumps(look, indent=1))
        return
    bc = cv2.imread(a.bc, cv2.IMREAD_COLOR)
    srmf = cv2.imread(a.srmf, cv2.IMREAD_UNCHANGED) if a.srmf else None
    body = cv2.imread(a.body_bc, cv2.IMREAD_COLOR) if a.body_bc else None
    out_bc, out_srmf, extra = paint.paint(bc, srmf, look, None, gain={} if a.no_gain else None, body_bc=body)
    if body is not None and a.out_body_bc:
        cv2.imwrite(a.out_body_bc, dict(extra)["body"])
    cv2.imwrite(a.out_bc, out_bc)
    if out_srmf is not None and a.out_srmf:
        cv2.imwrite(a.out_srmf, out_srmf)
    print(json.dumps({"ok": True, "look": look["id"], "layers": len(look["layers"])}))


if __name__ == "__main__":
    main()
