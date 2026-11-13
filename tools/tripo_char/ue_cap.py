"""Capture the Unreal Editor window to a PNG through the editor's MCP tool. Works on UE 5.8 and 5.9.

    python -I ue_cap.py <out.png>

UE 5.8 returned the image as base64 inside the JSON text. UE 5.9 returns a URN in the text and the PNG as its own
content item of type "image". The editor window must not be minimized.
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "comfy_char"))
import ue  # noqa: E402


def capture(path):
    payload = json.dumps({"toolset_name": ue.APP, "tool_name": "CaptureEditorImage", "arguments": {}})
    out = subprocess.run([sys.executable, "-I", "-X", "utf8", str(ue.UEMCP), "call", "call_tool", payload],
                         capture_output=True, text=True, encoding="utf-8").stdout
    msg = json.loads(out)["result"]
    if msg.get("isError"):
        raise RuntimeError("".join(c.get("text", "") for c in msg["content"]))
    data = next((c["data"] for c in msg["content"] if c.get("type") == "image"), None)
    if data is None:  # UE 5.8
        v = json.loads("".join(c.get("text", "") for c in msg["content"]))
        v = v.get("returnValue", v)
        data = v["image"]["data"] if "image" in v else v["data"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(base64.b64decode(data))
    return path


if __name__ == "__main__":
    print(capture(sys.argv[1]))
