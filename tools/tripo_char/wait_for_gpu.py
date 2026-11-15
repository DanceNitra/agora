r"""Blocks until the shared GPU is free for an Unreal job, following C:\Users\Danculus\.claude\compute\README.md:
no active foreign lock with scope=gpu or scope=all (a lock is active for ttl= minutes, default 90, since its last
change), an empty ComfyUI queue on 127.0.0.1:8188 (if it answers), and at least MIN_FREE_GB of free VRAM.
Prints one heartbeat line per check.

    python wait_for_gpu.py [own_lock_name] [min_free_gb] [poll_s]"""
import glob, json, os, re, subprocess, sys, time, urllib.request
OWN = sys.argv[1] if len(sys.argv) > 1 else "agora-tripo-char.lock"
MIN_FREE = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
POLL = float(sys.argv[3]) if len(sys.argv) > 3 else 120.0
LOCKS = r"C:\Users\Danculus\.claude\compute"


def blockers():
    why = []
    for p in glob.glob(os.path.join(LOCKS, "*.lock")):
        if os.path.basename(p) == OWN:
            continue
        txt = open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"ttl=(\d+)", txt)
        ttl = int(m.group(1)) if m else 90
        if time.time() - os.path.getmtime(p) > ttl * 60:
            continue
        if "scope=cpu" in txt:
            continue
        why.append("lock " + os.path.basename(p))
    try:
        q = json.load(urllib.request.urlopen("http://127.0.0.1:8188/queue", timeout=5))
        n = len(q.get("queue_running", [])) + len(q.get("queue_pending", []))
        if n:
            why.append(f"comfy queue {n}")
    except Exception:
        pass
    try:
        free = float(subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                                    capture_output=True, text=True).stdout.split()[0]) / 1024
        if free < MIN_FREE:
            why.append(f"vram free {free:.1f} GB")
    except Exception as e:
        why.append(f"nvidia-smi {e}")
    return why


t0 = time.time()
while True:
    w = blockers()
    print(time.strftime("%H:%M:%S"), f"waited {(time.time() - t0) / 60:.0f} min", "FREE" if not w else "; ".join(w), flush=True)
    if not w:
        break
    time.sleep(POLL)
