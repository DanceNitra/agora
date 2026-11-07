"""Build and validate the first-character ComfyUI graphs, using only native ComfyUI nodes.

Graphs (API format, written to tools/comfy_char/workflows/):
  AGORA_CHAR_01_concept_api.json     Qwen-Image 2512: a front T-pose concept image.
  AGORA_CHAR_02_character_api.json   TRELLIS.2: image to 12k-triangle textured GLB.
  AGORA_CHAR_03_prop_api.json        The same graph at 2k triangles, for a held object.

The wiring and sampler values of 02 and 03 follow ComfyUI's own MIT template
3d_pixal3d_trellis2_image_to_model (read from the installed package, 2026-11-06). The only
deliberate changes: the Pixal3D branch and the MoGe camera step are gone, the face target is
12,000 instead of 700,000, and every map is also saved as a PNG.

Run:
    python tools/comfy_char/build_workflows.py <object_info.json>

Exit code 0 means every graph passed and every control failed as it must.
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "workflows"

# A front T-pose that follows the input rules measured from the source workflow notes:
# straight front view, empty hands, plain background, fitted clothing.
TEST_PROMPT = (
    "Full body game character concept, a stocky field engineer in fitted canvas work clothes, "
    "short sleeves, leather gloves with five separated fingers, sturdy boots, short dark hair, "
    "calm face. Exact front view, symmetrical T-pose, arms straight out at shoulder height, palms "
    "down, fingers spread, legs straight and slightly apart, both feet flat on the floor, empty "
    "hands. Even soft studio light with no cast shadow, plain light grey seamless background, the "
    "whole body in frame with margin on all sides, realistic painted PBR game asset."
)
NEGATIVE_PROMPT = (
    "low resolution, deformed limbs, deformed fingers, merged fingers, oversaturated, waxy skin, "
    "blurry, three-quarter view, side view, turned head, bent arms, crossed legs, spikes, large "
    "shoulder armour, cape, loose robe, long coat, glass, transparent objects, held objects, "
    "weapon, cast shadow, floor reflection, text, watermark, logo, cluttered background"
)


def concept_graph():
    """Qwen-Image 2512 with the sampler values of our BLENDER_REF_01 workflow."""
    return {
        "1": n("UNETLoader", "Qwen-Image 2512", unet_name="qwen_image_2512_fp8_e4m3fn.safetensors", weight_dtype="default"),
        "2": n("CLIPLoader", "Qwen text encoder", clip_name="qwen_2.5_vl_7b_fp8_scaled.safetensors", type="qwen_image", device="default"),
        "3": n("VAELoader", "Qwen VAE", vae_name="qwen_image_vae.safetensors"),
        "4": n("ModelSamplingAuraFlow", "Shift", model=["1", 0], shift=3.1),
        "5": n("CLIPTextEncode", "Positive: edit the character here", clip=["2", 0], text=TEST_PROMPT),
        "6": n("CLIPTextEncode", "Negative: keeps the pose animation-ready", clip=["2", 0], text=NEGATIVE_PROMPT),
        "7": n("EmptySD3LatentImage", "Square frame leaves room for the arms", width=1328, height=1328, batch_size=4),
        "8": n("KSampler", "Sampler", model=["4", 0], positive=["5", 0], negative=["6", 0], latent_image=["7", 0],
               seed=2026110601, steps=50, cfg=4.0, sampler_name="euler", scheduler="simple", denoise=1.0),
        "9": n("VAEDecode", "Decode", samples=["8", 0], vae=["3", 0]),
        "10": n("SaveImage", "Save: pick the best one for 02", images=["9", 0], filename_prefix="agora_char/concept"),
    }


def n(class_type, title, **inputs):
    return {"class_type": class_type, "_meta": {"title": title}, "inputs": inputs}


def mesh_graph(target_faces, prefix, input_image):
    """Image to low-poly GLB. Node numbers are stable so that notes can refer to them."""
    return {
        # 1. Input
        "10": n("LoadImage", "INPUT: front T-pose, empty hands, plain background", image=input_image),
        "11": n("LoadBackgroundRemovalModel", "BiRefNet", bg_removal_name="birefnet.safetensors"),
        "12": n("RemoveBackground", "Remove background", bg_removal_model=["11", 0], image=["10", 0]),
        "13": n("ImageCropToMask", "Crop to subject (pad 1.0 for TRELLIS.2)", images=["10", 0], masks=["12", 0],
                width=1024, height=1024, pad_factor=1.0, grow_mask=0, background="#000000"),
        "14": n("SaveImage", "CHECK 1: the crop must show the whole body", images=["13", 0], filename_prefix=f"{prefix}/crop"),
        # 2. Models
        "20": n("UNETLoader", "TRELLIS.2", unet_name="trellis_2_int8_convrot.safetensors", weight_dtype="default"),
        "21": n("VAELoader", "Shape VAE", vae_name="trellis_2_shape_vae_bf16.safetensors"),
        "22": n("VAELoader", "Texture VAE", vae_name="trellis_2_texture_vae_bf16.safetensors"),
        "23": n("CLIPVisionLoader", "DINOv3 image encoder", clip_name="dino_v3_L_naf_fp32.safetensors"),
        "24": n("Trellis2Conditioning", "Image conditioning", clip_vision_model=["23", 0], image=["13", 0]),
        # 3. Sparse structure
        "30": n("CFGOverride", "Structure CFG schedule", model=["20", 0], cfg=1.0, start_percent=0.667, end_percent=1.0),
        "31": n("RescaleCFG", "Structure rescale", model=["30", 0], multiplier=0.7),
        "32": n("ModelSamplingSD3", "Structure shift", model=["31", 0], shift=5.0),
        "33": n("EmptyTrellis2LatentStructure", "Empty structure", batch_size=1),
        "34": n("KSampler", "SEED: change this one for a different body", model=["32", 0], positive=["24", 0], negative=["24", 1],
                latent_image=["33", 0], seed=56, steps=12, cfg=7.5, sampler_name="euler", scheduler="normal", denoise=1.0),
        "35": n("VaeDecodeStructureTrellis2", "Decode structure", samples=["34", 0], vae=["21", 0], resolution="32"),
        # 4. Shape
        "40": n("CFGOverride", "Shape CFG schedule", model=["20", 0], cfg=1.0, start_percent=0.769, end_percent=1.0),
        "41": n("RescaleCFG", "Shape rescale", model=["40", 0], multiplier=0.5),
        "42": n("Trellis2ShapeStage", "Shape stage", positive=["24", 0], negative=["24", 1], voxel=["35", 0]),
        "43": n("KSampler", "Shape sampler", model=["41", 0], positive=["42", 0], negative=["42", 1], latent_image=["42", 2],
                seed=42, steps=20, cfg=7.5, sampler_name="euler", scheduler="normal", denoise=1.0),
        "44": n("Trellis2UpsampleStage", "Upsample: 1536 default, 1024 if VRAM runs out", positive=["42", 0], negative=["42", 1],
                shape_latent=["43", 0], vae=["21", 0], target_resolution=1536),
        "45": n("KSampler", "Upsample sampler", model=["41", 0], positive=["44", 0], negative=["44", 1], latent_image=["44", 2],
                seed=42, steps=12, cfg=7.5, sampler_name="euler", scheduler="simple", denoise=1.0),
        "46": n("VaeDecodeShapeTrellis", "Decode shape", samples=["45", 0], vae=["21", 0]),
        # 5. Texture voxels (MIT TRELLIS.2 stage, no FLUX.2)
        "50": n("Trellis2TextureStage", "Texture stage", positive=["44", 0], negative=["44", 1], shape_latent=["45", 0]),
        "51": n("KSampler", "Texture sampler", model=["20", 0], positive=["50", 0], negative=["50", 1], latent_image=["50", 2],
                seed=43, steps=12, cfg=1.0, sampler_name="euler", scheduler="normal", denoise=1.0),
        "52": n("VaeDecodeTextureTrellis", "Decode texture", samples=["51", 0], vae=["22", 0], shape_subdivides=["46", 1]),
        # 6. Low poly: replaces Quad Reconstruct, WTiVo, and LODTailor
        "60": n("RemeshMesh", "Clean closed high poly", mesh=["46", 0], resolution=768, sign_mode="udf", **{
            "sign_mode.qef": False, "sign_mode.drop_inverted_components": False, "sign_mode.drop_enclosed_components": False,
        }, band=1.0, project_back=0.0, fix_poles=False, smooth_iters=20, drop_small_components=0.01, precluster_max_verts=20000000),
        "61": n("SaveGLB", "High poly without texture, for comparison", mesh=["60", 0], filename_prefix=f"{prefix}/highpoly"),
        "62": n("DecimateMesh", f"TARGET: {target_faces} triangles", mesh=["60", 0], target_face_count=target_faces, placement_mode="midpoint"),
        "63": n("MeshSmoothNormals", "Smooth normals", mesh=["62", 0], crease_angle=180.0),
        "64": n("UnwrapMesh", "UV unwrap", mesh=["63", 0], segmenter="pec", resolution=2048, padding=2, weld_distance=0.0002),
        # 7. Bake: replaces Bake Forger and UltraTex
        "70": n("BakeTextureFromVoxel", "Bake colour, metal, roughness", mesh=["64", 0], voxel_colors=["52", 0],
                texture_size=2048, reference_mesh=["46", 0]),
        "71": n("BakeNormalMapFromMesh", "Bake normal map", low_poly=["64", 0], high_poly=["60", 0], resolution=2048,
                cage_distance=0.05, ignore_backfaces=True),
        "72": n("ApplyTextureToMesh", "Attach all maps", mesh=["64", 0], base_color=["70", 0], metallic=["70", 1],
                roughness=["70", 2], normal_map=["71", 0]),
        "73": n("MeshSmoothNormals", "Smooth final normals", mesh=["72", 0], crease_angle=180.0),
        "74": n("SaveGLB", "FINAL: this file goes to rigging", mesh=["73", 0], filename_prefix=f"{prefix}/final"),
        "75": n("SaveImage", "Base colour map", images=["70", 0], filename_prefix=f"{prefix}/base_color"),
        "76": n("SaveImage", "Metallic map", images=["70", 1], filename_prefix=f"{prefix}/metallic"),
        "77": n("SaveImage", "Roughness map", images=["70", 2], filename_prefix=f"{prefix}/roughness"),
        "78": n("SaveImage", "Normal map", images=["71", 0], filename_prefix=f"{prefix}/normal"),
    }


FILE_COMBOS = {
    "unet_name", "clip_name", "vae_name", "bg_removal_name", "image", "lora_name",
}


def outputs_of(info):
    return info["output"]


def accepts(want, have):
    if want == "*" or have == "*":
        return True
    return have in str(want).split(",")


def validate(graph, object_info):
    """Return (errors, files). A file combo is listed in files, because its options depend on the disk."""
    errors = []
    files = []
    for node_id, node in graph.items():
        cls = node["class_type"]
        info = object_info.get(cls)
        if info is None:
            errors.append(f"{node_id}: node type {cls} does not exist")
            continue
        spec = {}
        spec.update(info["input"].get("required") or {})
        required = set(info["input"].get("required") or {})
        spec.update(info["input"].get("optional") or {})
        given = node["inputs"]
        # Dynamic combos add sub-inputs named "<combo>.<sub>", which depend on the chosen option.
        for name, sp in list(spec.items()):
            if sp[0] != "COMFY_DYNAMICCOMBO_V3" or name not in given:
                continue
            keys = {o["key"]: o for o in sp[1]["options"]}
            if given[name] not in keys:
                errors.append(f"{node_id}.{name}: {given[name]!r} is not one of {sorted(keys)}")
                continue
            sub = keys[given[name]]["inputs"]
            for section in ("required", "optional"):
                for k, v in (sub.get(section) or {}).items():
                    spec[f"{name}.{k}"] = v
                    if section == "required":
                        required.add(f"{name}.{k}")
        for name in required:
            sp = spec.get(name)
            is_widget_state = sp is not None and sp[0] == "LOAD_3D"
            if name not in given and not is_widget_state:
                errors.append(f"{node_id} {cls}: required input {name} is missing")
        for name, value in given.items():
            sp = spec.get(name)
            if sp is None:
                errors.append(f"{node_id} {cls}: unknown input {name}")
                continue
            want, opts = sp[0], (sp[1] if len(sp) > 1 else {})
            if isinstance(value, list):
                src = graph.get(value[0])
                if src is None:
                    errors.append(f"{node_id}.{name}: links to absent node {value[0]}")
                    continue
                src_out = outputs_of(object_info.get(src["class_type"], {"output": []}))
                if value[1] >= len(src_out):
                    errors.append(f"{node_id}.{name}: {src['class_type']} has no output {value[1]}")
                elif not accepts(want, src_out[value[1]]):
                    errors.append(f"{node_id}.{name}: wants {want}, gets {src_out[value[1]]}")
                continue
            if name in FILE_COMBOS:
                files.append((cls, value))
                continue
            options = want if isinstance(want, list) else opts.get("options") if want == "COMBO" else None
            if options and value not in options:
                errors.append(f"{node_id}.{name}: {value!r} is not one of {options[:6]}")
            if want in ("INT", "FLOAT"):
                low, high = opts.get("min"), opts.get("max")
                if (low is not None and value < low) or (high is not None and value > high):
                    errors.append(f"{node_id}.{name}: {value} is outside {low}..{high}")
    return errors, files


def controls(graph, object_info):
    """Each mutation must make the validator report an error, or the validator measured nothing."""
    cases = {}

    bad = copy.deepcopy(graph)
    bad["62"]["class_type"] = "DecimateMeshTypo"
    cases["unknown node type"] = bad

    bad = copy.deepcopy(graph)
    bad["70"]["inputs"]["voxel_colors"] = ["46", 0]  # MESH into a VOXEL input.
    cases["wrong link type"] = bad

    bad = copy.deepcopy(graph)
    del bad["71"]["inputs"]["high_poly"]
    cases["missing required input"] = bad

    bad = copy.deepcopy(graph)
    bad["44"]["inputs"]["target_resolution"] = 4096  # Schema maximum is 2048.
    cases["value out of range"] = bad

    bad = copy.deepcopy(graph)
    bad["60"]["inputs"]["sign_mode"] = "nonsense"
    cases["bad dynamic combo"] = bad

    bad = copy.deepcopy(graph)
    bad["64"]["inputs"]["segmenter"] = "nonsense"
    cases["bad combo value"] = bad

    failures = []
    for label, mutated in cases.items():
        errors, _ = validate(mutated, object_info)
        status = "caught" if errors else "NOT CAUGHT"
        print(f"  control {label}: {status}")
        if not errors:
            failures.append(label)
    return failures


def main():
    object_info = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["nodes"]
    graphs = {
        "AGORA_CHAR_01_concept_api.json": concept_graph(),
        "AGORA_CHAR_02_character_api.json": mesh_graph(12000, "agora_char/character", "agora_char_input.png"),
        "AGORA_CHAR_03_prop_api.json": mesh_graph(2000, "agora_char/prop", "agora_prop_input.png"),
    }
    OUT.mkdir(exist_ok=True)
    failed = False
    for name, graph in graphs.items():
        errors, files = validate(graph, object_info)
        print(f"{name}: {len(graph)} nodes, {len(errors)} errors")
        for line in errors:
            print("  ERROR", line)
        failed = failed or bool(errors)
        (OUT / name).write_text(json.dumps(graph, indent=1, ensure_ascii=False), encoding="utf-8")
        print("  files:", sorted({v for _, v in files}))
    failures = controls(graphs["AGORA_CHAR_02_character_api.json"], object_info)
    sys.exit(1 if failed or failures else 0)


if __name__ == "__main__":
    main()
