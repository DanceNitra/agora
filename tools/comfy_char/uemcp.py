"""Minimal JSON-RPC client for the Unreal editor MCP at 127.0.0.1:8000/mcp.
usage: uemcp.py list | uemcp.py call <tool> '<json args>'"""
import json, sys, urllib.request
URL = "http://127.0.0.1:8000/mcp"
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
def rpc(method, params, sid=None, rid=1):
    h = dict(H)
    if sid: h["Mcp-Session-Id"] = sid
    body = {"jsonrpc": "2.0", "method": method, "params": params}
    if rid is not None: body["id"] = rid
    r = urllib.request.urlopen(urllib.request.Request(URL, json.dumps(body).encode(), h), timeout=600)
    sid = r.headers.get("Mcp-Session-Id") or sid
    txt = r.read().decode("utf-8", "replace")
    if txt.startswith("event:") or "\ndata:" in txt or txt.startswith("data:"):
        txt = "\n".join(l[5:].strip() for l in txt.splitlines() if l.startswith("data:"))
    return (json.loads(txt) if txt.strip() else None), sid
res, sid = rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "agora-probe", "version": "0"}})
rpc("notifications/initialized", {}, sid, None)
if sys.argv[1] == "list":
    out, _ = rpc("tools/list", {}, sid, 2)
    for t in out["result"]["tools"]:
        print(t["name"], "::", (t.get("description") or "")[:160].replace("\n", " "))
else:
    out, _ = rpc("tools/call", {"name": sys.argv[2], "arguments": json.loads(sys.argv[3] if len(sys.argv) > 3 else "{}")}, sid, 3)
    print(json.dumps(out, ensure_ascii=False))
