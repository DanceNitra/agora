"""Send one command to the MCP for Blender add-on socket (port 9876) and print the reply.

Lets a session drive Blender before the blender MCP tools are loaded.
Usage: python bmcp.py <type> [json-params | @file.py for execute_code]
"""
import json
import socket
import sys


def call(cmd_type, params=None, host="localhost", port=9876, timeout=180):
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(json.dumps({"type": cmd_type, "params": params or {}}).encode())
        buf = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode())
            except json.JSONDecodeError:
                continue
    return json.loads(buf.decode())


if __name__ == "__main__":
    t = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    if t == "execute_code" and arg.startswith("@"):
        params = {"code": open(arg[1:], encoding="utf-8").read()}
    else:
        params = json.loads(arg) if arg else {}
    out = call(t, params)
    text = json.dumps(out, ensure_ascii=True)
    print(text[:4000])
