"""Measure a character GLB against the acceptance numbers in FIRST_CHARACTER_PLAN.md.

Run with the ComfyUI venv, which has trimesh:
    C:/ComfyUI/venv/Scripts/python.exe tools/comfy_char/check_glb.py <file.glb> [--target 12000]
    C:/ComfyUI/venv/Scripts/python.exe tools/comfy_char/check_glb.py --self-test
"""
import argparse
import json
import sys

import numpy as np
import trimesh


def measure(path):
    """Return the measured values of one GLB file."""
    scene = trimesh.load(path, force="scene")
    meshes = [g for g in scene.dump() if isinstance(g, trimesh.Trimesh)]
    if not meshes:
        return {"faces": 0, "meshes": 0}
    faces = sum(len(m.faces) for m in meshes)
    # UV seams duplicate vertices in a GLB, so closure is measured on positions only.
    merged = trimesh.util.concatenate([trimesh.Trimesh(m.vertices, m.faces, process=False) for m in meshes])
    merged.merge_vertices(merge_tex=True, merge_norm=True)
    material = getattr(meshes[0].visual, "material", None)
    extent = merged.bounds[1] - merged.bounds[0]
    return {
        "meshes": len(meshes),
        "faces": faces,
        "watertight": bool(merged.is_watertight),
        "components": len(merged.split(only_watertight=False)),
        "extent_xyz": [round(float(v), 4) for v in extent],
        "span_to_height": round(float(max(extent[0], extent[2]) / max(extent[1], 1e-9)), 3),
        "has_base_color": getattr(material, "baseColorTexture", None) is not None,
        "has_normal_map": getattr(material, "normalTexture", None) is not None,
        "has_metal_rough": getattr(material, "metallicRoughnessTexture", None) is not None,
    }


def verdict(values, target):
    """Return the list of failed acceptance checks."""
    failed = []
    if not target * 0.9 <= values.get("faces", 0) <= target * 1.01:
        failed.append(f"faces {values.get('faces')} outside {target * 0.9:.0f}..{target * 1.01:.0f}")
    for key in ("watertight", "has_base_color", "has_normal_map", "has_metal_rough"):
        if not values.get(key):
            failed.append(f"{key} is false")
    return failed


def self_test():
    """The checker must pass a complete mesh and fail each kind of defect."""
    import tempfile
    from pathlib import Path
    from PIL import Image

    tmp = Path(tempfile.mkdtemp(dir="."))
    image = Image.new("RGB", (8, 8), (128, 128, 255))

    def box(subdivisions, textured=True, open_mesh=False):
        mesh = trimesh.creation.box()
        for _ in range(subdivisions):
            mesh = mesh.subdivide()
        if open_mesh:
            mesh.update_faces(np.arange(len(mesh.faces)) != 0)
            mesh.remove_unreferenced_vertices()
        uv = np.zeros((len(mesh.vertices), 2))
        if textured:
            material = trimesh.visual.material.PBRMaterial(
                baseColorTexture=image, normalTexture=image, metallicRoughnessTexture=image)
            mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=material)
        return mesh

    full = box(3)
    target = len(full.faces)
    cases = [
        ("complete mesh", box(3), False),
        ("too many faces", box(4), True),
        ("open mesh", box(3, open_mesh=True), True),
        ("no textures", box(3, textured=False), True),
    ]
    bad = 0
    for label, mesh, must_fail in cases:
        file = tmp / "case.glb"
        mesh.export(file)
        failed = verdict(measure(file), target)
        ok = bool(failed) == must_fail
        bad += not ok
        print(f"  {label}: {'as expected' if ok else 'WRONG'} {failed}")
        file.unlink()
    tmp.rmdir()
    return 1 if bad else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("glb", nargs="?")
    parser.add_argument("--target", type=int, default=12000)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        sys.exit(self_test())
    values = measure(args.glb)
    print(json.dumps(values, indent=1))
    failed = verdict(values, args.target)
    print("PASS" if not failed else "FAIL: " + "; ".join(failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
