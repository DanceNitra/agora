"""Unload ComfyUI's models from the GPU as soon as ComfyUI is idle (owner, 2026-10-21).

Every POLL seconds the script reads ComfyUI's queue. When nothing is running or pending for GRACE seconds and
ComfyUI still holds VRAM, it calls POST /free with unload_models and free_memory. The shared-machine rule allows
/free only on an empty queue, and that is the only time this script calls it. ComfyUI itself is never stopped.
GRACE is 30 s so that a script submitting one prompt after another does not reload its models between them.

Each /free is one JSON line in ~/.claude/compute/comfy_idle_free.jsonl. Run detached:
    python tools/comfy_idle_free.py
"""
import json
import os
import time
import urllib.request

BASE = "http://127.0.0.1:8188"
POLL = 5
GRACE = 30
LOG = os.path.expanduser("~/.claude/compute/comfy_idle_free.jsonl")


def _get(path):
    with urllib.request.urlopen(BASE + path, timeout=3) as r:
        return json.load(r)


def _vram_used_mb():
    devs = _get("/system_stats").get("devices") or []
    return sum((d.get("vram_total", 0) - d.get("vram_free", 0)) for d in devs) // (1024 * 1024)


def main():
    idle_since = None
    freed = False
    while True:
        try:
            q = _get("/queue")
            busy = bool(q.get("queue_running") or q.get("queue_pending"))
        except (OSError, ValueError):
            idle_since, freed = None, False     # ComfyUI is down: nothing to free
            time.sleep(POLL)
            continue
        now = time.time()
        if busy:
            idle_since, freed = None, False
        else:
            idle_since = idle_since or now
            if not freed and now - idle_since >= GRACE:
                try:
                    before = _vram_used_mb()
                    req = urllib.request.Request(BASE + "/free", method="POST",
                                                 data=b'{"unload_models": true, "free_memory": true}',
                                                 headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(req, timeout=10).read()
                    time.sleep(2)
                    after = _vram_used_mb()
                    with open(LOG, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"at": int(now), "idle_s": int(now - idle_since),
                                            "gpu_used_mb_before": before, "gpu_used_mb_after": after}) + "\n")
                except (OSError, ValueError):
                    pass
                freed = True
        time.sleep(POLL)


if __name__ == "__main__":
    main()
