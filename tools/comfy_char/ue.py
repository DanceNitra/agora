"""Small helper over uemcp.py: call one Unreal MCP toolset tool and return its decoded result.

    from ue import call
    call("editor_toolset.toolsets.asset.AssetTools", "exists", {"path": "/Game/AgoraChar"})
"""
import json
import subprocess
import sys
from pathlib import Path

UEMCP = Path(__file__).with_name("uemcp.py")


def call(toolset, tool, args=None, raw=False):
    """Run one tool through call_tool; return returnValue, or the raw text on error."""
    payload = json.dumps({"toolset_name": toolset, "tool_name": tool, "arguments": args or {}})
    out = subprocess.run([sys.executable, "-I", "-X", "utf8", str(UEMCP), "call", "call_tool", payload],
                         capture_output=True, text=True, encoding="utf-8").stdout
    msg = json.loads(out)["result"]
    text = "".join(c.get("text", "") for c in msg["content"])
    if raw or msg.get("isError"):
        return text if not msg.get("isError") else "ERROR: " + text
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return text
    return value.get("returnValue", value) if isinstance(value, dict) else value


BP = "editor_toolset.toolsets.blueprint.BlueprintTools"
ASSET = "editor_toolset.toolsets.asset.AssetTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
ACTOR = "editor_toolset.toolsets.actor.ActorTools"
SCENE = "editor_toolset.toolsets.scene.SceneTools"
APP = "EditorToolset.EditorAppToolset"
