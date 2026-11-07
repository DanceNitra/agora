"""Dump the input and output schema of every built-in ComfyUI node to a JSON file.

Runs in CPU mode with custom nodes disabled, so it starts no server, loads no model, and
takes no VRAM. Run it with the ComfyUI venv:

    C:/ComfyUI/venv/Scripts/python.exe tools/comfy_char/dump_object_info.py <out.json>
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

COMFY = Path("C:/ComfyUI")
out_path = Path(sys.argv[1]).resolve()

os.chdir(COMFY)
sys.path.insert(0, str(COMFY))
sys.argv = ["main.py", "--cpu", "--disable-all-custom-nodes"]

import comfy.options  # noqa: E402

comfy.options.enable_args_parsing()

import server  # noqa: E402

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
# Never started: some node modules read PromptServer.instance at import.
server.PromptServer(loop, MagicMock())

import nodes  # noqa: E402

loop.run_until_complete(nodes.init_builtin_extra_nodes())


def jsonable(value):
    """Convert schema values to JSON, and record anything unserializable by its type name."""
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(k): jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [jsonable(v) for v in value]
        return f"<{type(value).__name__}>"


info = {}
failed = {}
for name, cls in nodes.NODE_CLASS_MAPPINGS.items():
    try:
        info[name] = {
            "input": jsonable(cls.INPUT_TYPES()),
            "output": jsonable(list(getattr(cls, "RETURN_TYPES", []))),
            "output_name": jsonable(list(getattr(cls, "RETURN_NAMES", None) or [])),
            "is_output": bool(getattr(cls, "OUTPUT_NODE", False)),
        }
    except Exception as exc:  # A failed node is reported, never dropped silently.
        failed[name] = f"{type(exc).__name__}: {exc}"

out_path.write_text(json.dumps({"nodes": info, "failed": failed}, indent=1), encoding="utf-8")
print(f"nodes={len(info)} failed={len(failed)} -> {out_path}")
