"""Tripo API v3 client for the character workflow (docs/TRIPO_UE_WORKFLOW.md).

Every call that costs credits is refused unless --yes is passed. Without it the
call is printed with its price (dry run). The key is read from the .env file
beside this script and is never printed.

Usage:
  python tripo.py balance
  python tripo.py upload <image>
  python tripo.py create <endpoint> <body.json> --price N [--yes] [--out DIR]
  python tripo.py poll <task_id> [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BASE = "https://openapi.tripo3d.ai/v3"
HERE = Path(__file__).resolve().parent
POLL_SECONDS = 2
TIMEOUT_SECONDS = 900


def key() -> str:
    env = HERE / ".env"
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("TRIPO_API_KEY="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    sys.exit(f"TRIPO_API_KEY is missing in {env}")


def request(method: str, path: str, body: bytes | None = None, ctype: str | None = None) -> dict:
    req = urllib.request.Request(BASE + path, data=body, method=method)
    req.add_header("Authorization", "Bearer " + key())
    if ctype:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        text = err.read().decode("utf-8", errors="replace")
        sys.exit(f"HTTP {err.code} on {method} {path}: {text[:600]}")


def balance() -> dict:
    return request("GET", "/account/balance")


def upload(path: Path) -> dict:
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    head = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{path.name}\"\r\nContent-Type: {mime}\r\n\r\n"
    ).encode()
    body = head + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return request("POST", "/files", body, f"multipart/form-data; boundary={boundary}")


def poll(task_id: str, out: Path | None) -> dict:
    start = time.time()
    last = ""
    while True:
        data = request("GET", f"/tasks/{task_id}")
        task = data.get("data", data)
        status = str(task.get("status"))
        line = f"{status} {task.get('progress', '')}"
        if line != last:
            print(f"[{int(time.time() - start):4d} s] {line}", flush=True)
            last = line
        if status in ("success", "failed", "cancelled", "banned", "expired"):
            break
        if time.time() - start > TIMEOUT_SECONDS:
            sys.exit(f"timeout after {TIMEOUT_SECONDS} s; task {task_id} still {status}")
        time.sleep(POLL_SECONDS)
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "task.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        # Result URLs expire after 5 minutes: download at once.
        for name, url in sorted(_urls(task.get("output", {}))):
            suffix = Path(url.split("?", 1)[0]).suffix or ".bin"
            target = out / f"{name}{suffix}"
            urllib.request.urlretrieve(url, target)
            print(f"saved {target} ({target.stat().st_size} bytes)")
    return data


def _urls(node, prefix=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _urls(v, f"{prefix}{k}" if not prefix else f"{prefix}_{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _urls(v, f"{prefix}_{i}")
    elif isinstance(node, str) and node.startswith("http"):
        yield prefix, node


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("balance")
    p = sub.add_parser("upload")
    p.add_argument("image", type=Path)
    p = sub.add_parser("create")
    p.add_argument("endpoint", help="for example /generation/image-to-model")
    p.add_argument("body", type=Path)
    p.add_argument("--price", type=float, required=True, help="credits, from the price table")
    p.add_argument("--yes", action="store_true", help="really send; the owner approved this price")
    p.add_argument("--out", type=Path)
    p = sub.add_parser("poll")
    p.add_argument("task_id")
    p.add_argument("--out", type=Path)
    args = ap.parse_args()

    if args.cmd == "balance":
        print(json.dumps(balance(), indent=2))
    elif args.cmd == "upload":
        print(json.dumps(upload(args.image), indent=2))
    elif args.cmd == "create":
        body = json.loads(args.body.read_text(encoding="utf-8"))
        # Pass the endpoint without a leading slash: Git Bash rewrites "/x" into a Windows path.
        args.endpoint = "/" + args.endpoint.replace("\\", "/").split(":/")[-1].lstrip("/")
        if not args.endpoint.startswith(("/generation/", "/animations/", "/models/", "/mesh/")):
            sys.exit(f"unexpected endpoint {args.endpoint}")
        print(f"POST {BASE}{args.endpoint}")
        print(json.dumps(body, indent=2))
        print(f"price: {args.price:g} credits ({args.price / 100:.2f} USD)")
        if not args.yes:
            print("DRY RUN: nothing sent. Pass --yes after the owner approved the price.")
            return
        bal = balance()
        have = float(bal.get("data", bal).get("balance", 0))
        if have < args.price:
            sys.exit(f"balance {have:g} is under the price {args.price:g}; nothing sent")
        data = request("POST", args.endpoint, json.dumps(body).encode(), "application/json")
        print(json.dumps(data, indent=2))
        task_id = data.get("data", data).get("task_id")
        if task_id:
            poll(task_id, args.out)
            print(json.dumps(balance(), indent=2))
    elif args.cmd == "poll":
        poll(args.task_id, args.out)


if __name__ == "__main__":
    main()
