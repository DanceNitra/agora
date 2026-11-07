"""Run a Python file inside the running Unreal Editor through Epic's Python Remote Execution.

MyProject has bRemoteExecution=True (Config/DefaultEngine.ini). Usage:
    python -I tools/comfy_char/ue_py.py path/to/script.py
The script runs in the editor's interpreter (import unreal works); its print output comes back here.
"""
import sys
import time

sys.path.insert(0, r"C:\Program Files\Epic Games\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python")
import remote_execution as rex  # noqa: E402


def run_file(path, timeout=20.0):
    session = rex.RemoteExecution()
    session.start()
    try:
        deadline = time.time() + timeout
        while not session.remote_nodes and time.time() < deadline:
            time.sleep(0.2)
        nodes = session.remote_nodes
        if not nodes:
            raise SystemExit("no Unreal editor answered on the remote execution multicast group")
        session.open_command_connection(nodes[0]["node_id"])
        code = open(path, encoding="utf-8").read()
        result = session.run_command(code, unattended=True, exec_mode=rex.MODE_EXEC_FILE)
        for entry in result.get("output", []):
            print(entry.get("output", "").rstrip())
        if not result.get("success"):
            print("FAILED:", result.get("result"))
            return 1
        return 0
    finally:
        session.stop()


if __name__ == "__main__":
    sys.exit(run_file(sys.argv[1]))
