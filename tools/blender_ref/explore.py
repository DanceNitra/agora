"""Step 01 EXPLORE: render concept variants of the robot with Qwen-Image 2512 in ComfyUI.

Waits until the GPU is free under the shared-machine rules, holds its own lock while it runs,
renders one timed test image first and then the remaining seeds, and copies every result to
agora_output/reverse/blender_spider_xCkjVUtVDEw/build/01_explore/.

Usage: python explore.py [--seeds 8] [--steps 50] [--deadline-h 6] [--dry]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid

COMFY = "http://127.0.0.1:8188"
COMFY_OUT = r"C:\ComfyUI\output"
COMPUTE = r"C:\Users\Danculus\.claude\compute"
LOCK = os.path.join(COMPUTE, "agora-blender-explore.lock")
OUT = r"C:\Users\Danculus\agora\agora_output\reverse\blender_spider_xCkjVUtVDEw\build\01_explore"
WORKFLOW_COPY = r"C:\ComfyUI\user\default\workflows\BLENDER_REF_01_explore_api.json"
MIN_FREE_MB = 18000

PROMPT = (
    "Industrial design product render of a compact four-legged robotic exploration walker, "
    "three-quarter front view, full body in frame. Rounded spherical armored chassis in saturated "
    "satin industrial orange with one wide matte black band running over the top from front to back. "
    "A circular front sensor housing with one large glowing warm orange emissive lens ring and two "
    "small dark optics. Four large articulated walking legs, two on each side, each with a curved "
    "orange armor shell, a round black shoulder joint hub with bolts, a brushed metal piston, "
    "a black lower segment and a rubber foot with a small orange light strip near the tip. "
    "Dark gunmetal mechanics and a few black hoses under the body. Clean readable panel lines, "
    "precise hard-surface engineering, premium sci-fi industrial design, symmetrical. "
    "Seamless warm beige studio backdrop, semi-matte floor, soft large key light, rim light, "
    "soft contact shadows, no environment, no props, no text."
)
NEGATIVE = (
    "\u4f4e\u5206\u8fa8\u7387\uff0c\u4f4e\u753b\u8d28\uff0c\u80a2\u4f53\u7578\u5f62\uff0c\u624b\u6307"
    "\u7578\u5f62\uff0c\u753b\u9762\u8fc7\u9971\u548c\uff0c\u8721\u50cf\u611f\uff0c\u4eba\u8138\u65e0"
    "\u7ec6\u8282\uff0c\u8fc7\u5ea6\u5149\u6ed1\uff0c\u753b\u9762\u5177\u6709AI\u611f\u3002\u6784\u56fe"
    "\u6df7\u4e71\u3002\u6587\u5b57\u6a21\u7cca\uff0c\u626d\u66f2"
    ", extra legs, six legs, eight legs, organic spider, fur, text, watermark, logo, cluttered background"
)


def graph(seed, steps, prefix):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2512_fp8_e4m3fn.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": PROMPT}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEGATIVE}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1584, "height": 1056, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0],
                                                   "latent_image": ["7", 0], "seed": seed, "steps": steps, "cfg": 4.0,
                                                   "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


def get(path):
    with urllib.request.urlopen(COMFY + path, timeout=30) as r:
        return json.loads(r.read())


def post(path, body):
    req = urllib.request.Request(COMFY + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


COMFY_MB_PS = (
    "$ids = @(Get-CimInstance Win32_Process | ? { $_.CommandLine -like '*main.py*' -and $_.CommandLine -like '*--port 8188*' } | % ProcessId);"
    "$mb = 0; Get-Counter '\\GPU Process Memory(*)\\Dedicated Usage' | % CounterSamples |"
    " ? { $ids -contains [int](($_.InstanceName -split '_')[1]) } | % { $mb += $_.CookedValue / 1MB }; [int]$mb"
)


def free_mb():
    """VRAM a ComfyUI job can use: free memory plus what ComfyUI itself holds.

    ComfyUI evicts its own cached models when a new job needs the space, so only memory
    held by other processes (Unreal, Blender, the desktop) blocks us.
    """
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout
    free = int(out.strip().splitlines()[0])
    comfy = subprocess.run(["powershell", "-NoProfile", "-Command", COMFY_MB_PS], capture_output=True, text=True).stdout
    try:
        held = int(comfy.strip().splitlines()[-1])
    except (ValueError, IndexError):
        held = 0
    return free + held


def active_gpu_locks():
    found = []
    now = time.time()
    for name in os.listdir(COMPUTE):
        p = os.path.join(COMPUTE, name)
        if not name.endswith(".lock") or p == LOCK:
            continue
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if "scope=gpu" not in text:
            continue
        m = re.search(r"ttl=(\d+)", text)
        ttl = int(m.group(1)) if m else 3600
        if os.path.getmtime(p) + ttl > now:
            found.append(name)
    return found


def gpu_blockers():
    reasons = active_gpu_locks()
    q = get("/queue")
    if q["queue_running"] or q["queue_pending"]:
        reasons.append("comfy queue busy")
    mb = free_mb()
    if mb < MIN_FREE_MB:
        reasons.append(f"free VRAM {mb} MB < {MIN_FREE_MB}")
    return reasons


def wait_for_gpu(deadline):
    start = time.time()
    while True:
        reasons = gpu_blockers()
        if not reasons:
            return
        if time.time() > deadline:
            sys.exit(f"[explore] deadline reached, still blocked: {reasons}")
        print(f"[explore] waiting {int(time.time() - start)} s: {reasons}", flush=True)
        time.sleep(60)


def run_one(seed, steps, idx):
    prefix = f"blender_ref/explore_{idx:02d}_s{seed}"
    pid = post("/prompt", {"prompt": graph(seed, steps, prefix), "client_id": str(uuid.uuid4())})["prompt_id"]
    t0 = time.time()
    while True:
        h = get(f"/history/{pid}")
        if pid in h:
            entry = h[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                sys.exit(f"[explore] ComfyUI error on seed {seed}: {json.dumps(status)[:800]}")
            imgs = [i for o in entry["outputs"].values() for i in o.get("images", [])]
            if imgs:
                img = imgs[0]
                src = os.path.join(COMFY_OUT, img["subfolder"], img["filename"])
                dst = os.path.join(OUT, f"explore_{idx:02d}_s{seed}.png")
                shutil.copy2(src, dst)
                return dst, time.time() - t0
        if time.time() - t0 > 1800:
            sys.exit(f"[explore] seed {seed} exceeded 30 min")
        time.sleep(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--steps", type=int, default=50)
    ap.add_argument("--deadline-h", type=float, default=6.0)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    seeds = [101 + 7919 * i for i in range(a.seeds)]
    with open(WORKFLOW_COPY, "w", encoding="utf-8") as f:
        json.dump(graph(seeds[0], a.steps, "blender_ref/explore"), f, indent=1)
    with open(os.path.join(OUT, "prompt.json"), "w", encoding="utf-8") as f:
        json.dump({"prompt": PROMPT, "negative": NEGATIVE, "seeds": seeds, "steps": a.steps,
                   "size": [1584, 1056], "model": "qwen_image_2512_fp8_e4m3fn"}, f, indent=1)
    if a.dry:
        print("[explore] dry run; blockers now:", gpu_blockers())
        return
    wait_for_gpu(time.time() + a.deadline_h * 3600)
    with open(LOCK, "w", encoding="utf-8") as f:
        f.write(f"scope=gpu ttl=3600 agora: Blender ref step 01 explore, Qwen-Image 2512, {a.seeds} images, pid {os.getpid()}\n")
    times = []
    try:
        for i, s in enumerate(seeds, 1):
            # Yield to any job another agent queued while the previous image rendered.
            wait_for_gpu(time.time() + a.deadline_h * 3600)
            dst, dt = run_one(s, a.steps, i)
            times.append(round(dt, 1))
            print(f"[explore] {i}/{len(seeds)} seed {s} done in {dt:.1f} s -> {dst}", flush=True)
            os.utime(LOCK)
    finally:
        os.remove(LOCK)
    with open(os.path.join(OUT, "timings.json"), "w") as f:
        json.dump({"seconds_per_image": times}, f)
    print("[explore] all done", times, flush=True)


if __name__ == "__main__":
    main()
