"""Submit one API graph to a running ComfyUI, wait for it, and record time and peak VRAM.

    python tools/comfy_char/run_graph.py tools/comfy_char/workflows/AGORA_CHAR_01_concept_api.json [--set NODE.INPUT=VALUE ...]

Prints a heartbeat every 15 s, then the output file names and a JSON receipt line.
"""
import argparse
import json
import subprocess
import sys
import threading
import time
import urllib.request
import uuid

URL = "http://127.0.0.1:8188"


def vram_used_mib():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout
    return int(out.strip().splitlines()[0])


def post(path, payload):
    req = urllib.request.Request(URL + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def get(path):
    with urllib.request.urlopen(URL + path) as r:
        return json.load(r)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("graph")
    parser.add_argument("--set", action="append", default=[], help="NODE.INPUT=VALUE, value parsed as JSON when possible")
    args = parser.parse_args()
    graph = json.load(open(args.graph, encoding="utf-8"))
    for item in args.set:
        key, value = item.split("=", 1)
        node, field = key.split(".", 1)
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
        graph[node]["inputs"][field] = value

    baseline = vram_used_mib()
    peak = [baseline]
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            peak[0] = max(peak[0], vram_used_mib())
            time.sleep(1)

    threading.Thread(target=sample, daemon=True).start()
    start = time.time()
    try:
        reply = post("/prompt", {"prompt": graph, "client_id": str(uuid.uuid4())})
    except urllib.error.HTTPError as e:
        print(e.read().decode(errors="replace"))
        sys.exit(2)
    pid = reply["prompt_id"]
    print(f"queued {pid}", flush=True)
    last = 0
    while True:
        hist = get(f"/history/{pid}")
        if pid in hist and hist[pid].get("status", {}).get("completed") is not None:
            break
        if hist.get(pid, {}).get("status", {}).get("status_str") == "error":
            break
        if time.time() - last >= 15:
            q = get("/queue")
            print(f"  {time.time() - start:6.0f} s  running={len(q['queue_running'])} pending={len(q['queue_pending'])} vram_peak={peak[0]} MiB", flush=True)
            last = time.time()
        time.sleep(2)
    stop.set()
    entry = hist[pid]
    status = entry.get("status", {})
    files = []
    for node_id, out in entry.get("outputs", {}).items():
        for kind, items in out.items():
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict) and "filename" in it:
                        files.append(f"{it.get('type', '')}/{it.get('subfolder', '')}/{it['filename']}")
    for msg in status.get("messages", []):
        if msg[0] == "execution_error":
            print(json.dumps(msg[1], indent=1)[:4000])
    print("\n".join(files))
    print(json.dumps({"prompt_id": pid, "status": status.get("status_str"), "seconds": round(time.time() - start, 1),
                      "vram_baseline_mib": baseline, "vram_peak_mib": peak[0], "files": len(files)}))
    sys.exit(0 if status.get("status_str") == "success" else 1)


if __name__ == "__main__":
    main()
