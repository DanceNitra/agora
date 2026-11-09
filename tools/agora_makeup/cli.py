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


def find(look_id):
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
    out_bc, out_srmf, _ = paint.paint(bc, srmf, look, zones.Face(bc.shape[1]), gain={} if a.no_gain else None)
    cv2.imwrite(a.out_bc, out_bc)
    if out_srmf is not None and a.out_srmf:
        cv2.imwrite(a.out_srmf, out_srmf)
    print(json.dumps({"ok": True, "look": look["id"], "layers": len(look["layers"])}))


if __name__ == "__main__":
    main()
