"""Step 02 REFINE: clean up the chosen concept with Qwen-Image-Edit 2511 + Lightning 8-step.

The video's goal for this step is "Cleaner. Readable. Buildable.": same design, simpler and
sharper parts. Uses the GPU gate and lock from explore.py. Results go to build/02_refine/.

Usage: python refine.py <source.png> [--seeds 4] [--steps 8]
"""
import argparse
import json
import os
import shutil
import sys
import time
import uuid

import explore as ex

OUT = r"C:\Users\Danculus\agora\agora_output\reverse\blender_spider_xCkjVUtVDEw\build\02_refine"
COMFY_IN = r"C:\ComfyUI\input\blender_ref"
LOCK = os.path.join(ex.COMPUTE, "agora-blender-refine.lock")
ex.LOCK = LOCK  # the gate skips the caller's own lock file
WORKFLOW_COPY = r"C:\ComfyUI\user\default\workflows\BLENDER_REF_02_refine_api.json"

PROMPT = (
    "Keep exactly the same robot: same design, same proportions, same colours, same four legs, "
    "same sensor with one large lens and two small lenses, same camera angle, same beige studio "
    "background. Make it cleaner and easier to model in 3D: fewer tiny greebles, crisp and "
    "continuous panel lines, clearly separated armour plates, clean bevelled hard-surface edges, "
    "clearly readable shoulder joints, pistons and feet, tidy cable routing. "
    "Sharp industrial-design product photograph."
)


def graph(image_name, seed, steps, prefix):
    lightning = steps <= 8
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2511_fp8mixed.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "5": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["4", 0]}},
        "6": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["3", 0]}},
        "7": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["20", 0] if lightning else ["1", 0], "shift": 3.1}},
        "8": {"class_type": "CFGNorm", "inputs": {"model": ["7", 0], "strength": 1.0, "pre_cfg": False}},
        "9": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["5", 0], "prompt": PROMPT}},
        "10": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["5", 0], "prompt": ""}},
        "11": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["9", 0], "reference_latents_method": "index_timestep_zero"}},
        "12": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["10", 0], "reference_latents_method": "index_timestep_zero"}},
        "13": {"class_type": "KSampler", "inputs": {"model": ["8", 0], "positive": ["11", 0], "negative": ["12", 0],
                                                    "latent_image": ["6", 0], "seed": seed, "steps": steps,
                                                    "cfg": 1.0 if lightning else 4.0, "sampler_name": "euler",
                                                    "scheduler": "simple", "denoise": 1.0}},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["3", 0]}},
        "15": {"class_type": "SaveImage", "inputs": {"images": ["14", 0], "filename_prefix": prefix}},
    }
    if lightning:
        g["20"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "strength_model": 1.0,
                   "lora_name": "Qwen-Image-Edit-2511-Lightning-8steps-V1.0-bf16.safetensors"}}
    return g


def run(g, dst, limit=1800):
    pid = ex.post("/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < limit:
        h = ex.get(f"/history/{pid}")
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                sys.exit(f"[refine] ComfyUI error: {json.dumps(st)[:800]}")
            imgs = [i for o in h[pid]["outputs"].values() for i in o.get("images", [])]
            if imgs:
                shutil.copy2(os.path.join(ex.COMFY_OUT, imgs[0]["subfolder"], imgs[0]["filename"]), dst)
                return time.time() - t0
        time.sleep(3)
    sys.exit("[refine] job exceeded the time limit")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--deadline-h", type=float, default=3.0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(COMFY_IN, exist_ok=True)
    name = os.path.basename(a.source)
    shutil.copy2(a.source, os.path.join(COMFY_IN, name))
    shutil.copy2(a.source, os.path.join(OUT, "before_" + name))
    image_name = "blender_ref/" + name
    seeds = [202 + 6007 * i for i in range(a.seeds)]
    with open(WORKFLOW_COPY, "w", encoding="utf-8") as f:
        json.dump(graph(image_name, seeds[0], a.steps, "blender_ref/refine"), f, indent=1)
    with open(os.path.join(OUT, "prompt.json"), "w", encoding="utf-8") as f:
        json.dump({"source": a.source, "prompt": PROMPT, "seeds": seeds, "steps": a.steps}, f, indent=1)
    deadline = time.time() + a.deadline_h * 3600
    ex.wait_for_gpu(deadline)
    with open(LOCK, "w", encoding="utf-8") as f:
        f.write(f"scope=gpu ttl=3600 agora: Blender ref step 02 refine, Qwen-Image-Edit 2511, pid {os.getpid()}\n")
    try:
        for i, s in enumerate(seeds, 1):
            ex.wait_for_gpu(deadline)
            dst = os.path.join(OUT, f"refine_{i:02d}_s{s}.png")
            dt = run(graph(image_name, s, a.steps, f"blender_ref/refine_{i:02d}"), dst)
            print(f"[refine] {i}/{len(seeds)} seed {s} done in {dt:.1f} s -> {dst}", flush=True)
            os.utime(LOCK)
    finally:
        os.remove(LOCK)
    print("[refine] all done", flush=True)


if __name__ == "__main__":
    main()
