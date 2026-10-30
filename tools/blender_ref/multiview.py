"""Step 03 CONCEPT SHEET: the views and detail close-ups of the refined robot.

Views use Qwen-Image-Edit 2511 + the fal multiple-angles LoRA (strength 0.9) + Lightning 4-step,
the settings of fal's own workflow. Prompt format from the LoRA's model card:
"<sks> [azimuth] [elevation] [distance]". Detail close-ups use plain edit prompts with
Lightning 8-step. Results go to build/03_sheet/.

Usage: python multiview.py <refined.png> [--only name1,name2] [--seed 303]
"""
import argparse
import json
import os
import shutil
import time

import explore as ex
import refine as rf

OUT = r"C:\Users\Danculus\agora\agora_output\reverse\blender_spider_xCkjVUtVDEw\build\03_sheet"
LOCK = os.path.join(ex.COMPUTE, "agora-blender-sheet.lock")
ex.LOCK = LOCK
WORKFLOW_COPY = r"C:\ComfyUI\user\default\workflows\BLENDER_REF_03_multiview_api.json"
ANGLES = "qwen-image-edit-2511-multiple-angles-lora.safetensors"
L4 = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
L8 = "Qwen-Image-Edit-2511-Lightning-8steps-V1.0-bf16.safetensors"

KEEP = (" Keep exactly the same robot design, colours, four legs, sensor and beige studio background.")
JOBS = {
    # name: (prompt, use_angles_lora)
    "front": ("<sks> front view eye-level shot medium shot", True),
    "side": ("<sks> right side view eye-level shot medium shot", True),
    "rear_three_quarter": ("<sks> back-right quarter view elevated shot medium shot", True),
    "low_angle": ("<sks> front-left quarter view low-angle shot medium shot", True),
    "high_angle": ("<sks> front view high-angle shot medium shot", True),
    "detail_sensor": ("Extreme close-up product photo of the robot's front sensor: the glowing orange ring, "
                      "the large lens and the two small lenses, filling the frame." + KEEP, False),
    "detail_joint": ("Extreme close-up product photo of one shoulder joint of the robot: the black bolted "
                     "joint hub, the brushed metal piston and the orange leg armour, filling the frame." + KEEP, False),
    "detail_foot": ("Extreme close-up product photo of one foot of the robot: the black lower leg, the rubber "
                    "foot pad and the orange light strip, filling the frame." + KEEP, False),
    "detail_underside": ("Close-up product photo of the underside of the robot body from a low angle: the hoses, "
                         "the leg pivots and the black under-panel, filling the frame." + KEEP, False),
    "detail_rear": ("Close-up product photo of the back of the robot body: the black band over the top, the "
                    "orange armour panels and bolts, filling the frame." + KEEP, False),
}


def graph(image_name, prompt, angles, seed, prefix):
    g = rf.graph(image_name, seed, 4 if angles else 8, prefix)
    g["9"]["inputs"]["prompt"] = prompt
    g["20"]["inputs"]["lora_name"] = L4 if angles else L8
    if angles:
        g["21"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["20", 0], "lora_name": ANGLES, "strength_model": 0.9}}
        g["7"]["inputs"]["model"] = ["21", 0]
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--only", default="")
    ap.add_argument("--seed", type=int, default=303)
    ap.add_argument("--deadline-h", type=float, default=3.0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(rf.COMFY_IN, exist_ok=True)
    name = os.path.basename(a.source)
    shutil.copy2(a.source, os.path.join(rf.COMFY_IN, name))
    shutil.copy2(a.source, os.path.join(OUT, "hero_" + name))
    image_name = "blender_ref/" + name
    names = [n for n in a.only.split(",") if n] or list(JOBS)
    with open(WORKFLOW_COPY, "w", encoding="utf-8") as f:
        json.dump(graph(image_name, JOBS["front"][0], True, a.seed, "blender_ref/view"), f, indent=1)
    with open(os.path.join(OUT, "jobs.json"), "w", encoding="utf-8") as f:
        json.dump({"source": a.source, "seed": a.seed, "jobs": JOBS}, f, indent=1)
    deadline = time.time() + a.deadline_h * 3600
    ex.wait_for_gpu(deadline)
    with open(LOCK, "w", encoding="utf-8") as f:
        f.write(f"scope=gpu ttl=3600 agora: Blender ref step 03 multi-view, Qwen-Image-Edit 2511, pid {os.getpid()}\n")
    try:
        for i, n in enumerate(names, 1):
            ex.wait_for_gpu(deadline)
            prompt, angles = JOBS[n]
            dst = os.path.join(OUT, f"{n}.png")
            dt = rf.run(graph(image_name, prompt, angles, a.seed, f"blender_ref/sheet_{n}"), dst)
            print(f"[sheet] {i}/{len(names)} {n} done in {dt:.1f} s -> {dst}", flush=True)
            os.utime(LOCK)
    finally:
        os.remove(LOCK)
    print("[sheet] all done", flush=True)


if __name__ == "__main__":
    main()
