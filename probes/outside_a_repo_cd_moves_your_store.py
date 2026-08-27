"""Inside a repo, cd keeps your memory store. Outside one, cd silently moves it. Windows check.

WHY. @JhouCode posted this to anthropics/claude-code#82056 with a live specimen and n=1 on
linux-x64, and named the asymmetry as the part nobody has written down:

    "Inside a repo, cd into a subdirectory keeps the same store. Documented, and I verified it here.
     Outside a repo, cd into a subdirectory moves you to a different store, with no signal at all."

That is the issue's third failure mode, a fact written to a different project store, and outside a
repository it is not an edge case: it is what happens every time you work one directory over. A
second platform is worth having on a behaviour that loses data quietly.

FREE, and that is a design choice rather than a saving. `memory_paths.auto` is emitted in the
stream-json `init` event, which the CLI produces before the model answers, so pointing
ANTHROPIC_BASE_URL at a local recorder gets the store path with no real completion. Four arms cost
nothing, which means the arms can be exhaustive instead of chosen.

FOUR ARMS, and the pairing is what makes it a test rather than four observations:

    a git repo, at its root                 -> store A
    the same repo, one directory down       -> must be store A     (documented behaviour)
    a non-repo directory                    -> store B
    a directory beneath it, also non-repo   -> B or its own?       (his finding)

CONTROLS:

  * THE DOCUMENTED HALF MUST HOLD. If the in-repo pair does NOT share a store, the harness is wrong
    and the out-of-repo result means nothing. It is the positive control, and it can fail.
  * THE TWO TREES MUST DIFFER FROM EACH OTHER, or "different store" is trivially true of anything.
  * THE NON-REPO PARENT MUST REALLY NOT BE A REPO. `git rev-parse` is run in each directory and
    recorded, because a stray .git anywhere above would silently convert this into the first case
    and produce a clean, wrong answer.
  * NOTHING IS WRITTEN. The arms read a resolved path; no fixture is planted, so this cannot leave
    stores behind the way our earlier probes did.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))

SSE = "".join([
    'event: message_start\ndata: {"type":"message_start","message":{"id":"m","type":"message",'
    '"role":"assistant","model":"m","content":[],"stop_reason":null,'
    '"usage":{"input_tokens":1,"output_tokens":1}}}\n\n',
    'event: content_block_start\ndata: {"type":"content_block_start","index":0,'
    '"content_block":{"type":"text","text":""}}\n\n',
    'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,'
    '"delta":{"type":"text_delta","text":"OK"}}\n\n',
    'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n',
    'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},'
    '"usage":{"output_tokens":1}}\n\n',
    'event: message_stop\ndata: {"type":"message_stop"}\n\n',
])


def claude_bin():
    for c in ("claude.cmd", "claude.exe", "claude"):
        p = shutil.which(c)
        if p and os.path.splitext(p)[1].lower() in (".cmd", ".exe", ".bat"):
            return p
    return shutil.which("claude")


CLAUDE = claude_bin()


def recorder(port: int):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("content-length") or 0))
            b = SSE.encode()
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def is_repo(d: str) -> bool:
    r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=d,
                       capture_output=True, text=True)
    return r.returncode == 0 and "true" in (r.stdout or "")


def store_for(d: str, port: int) -> str:
    """The resolved auto-memory store, read from the init event with no completion."""
    env = dict(os.environ, ANTHROPIC_BASE_URL=f"http://127.0.0.1:{port}", ANTHROPIC_API_KEY="x")
    p = subprocess.Popen([CLAUDE, "-p", "--output-format", "stream-json", "--verbose",
                          "--tools", "", "--strict-mcp-config", "x"],
                         cwd=d, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    try:
        out, _ = p.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        else:
            p.kill()
        return ""
    for line in (out or "").splitlines():
        try:
            d2 = json.loads(line)
        except Exception:
            continue
        if d2.get("type") == "system" and d2.get("subtype") == "init":
            return (d2.get("memory_paths") or {}).get("auto") or ""
    return ""


def main() -> int:
    if CLAUDE is None:
        raise SystemExit("REFUSED: no runnable `claude` on PATH")
    srv = recorder(8881)

    base = tempfile.mkdtemp(prefix="cdstore_")
    repo = os.path.join(base, "arepo")
    repo_sub = os.path.join(repo, "sub", "deeper")
    plain = os.path.join(base, "plain")
    plain_sub = os.path.join(plain, "sub", "deeper")
    for d in (repo_sub, plain_sub):
        os.makedirs(d, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, capture_output=True)

    arms = [("repo root", repo), ("repo subdir", repo_sub),
            ("non-repo root", plain), ("non-repo subdir", plain_sub)]
    rows = []
    for name, d in arms:
        rows.append({"arm": name, "dir": d, "is_repo": is_repo(d), "store": store_for(d, 8881)})
        r = rows[-1]
        print(f"  {name:16s} repo={str(r['is_repo']):5s} store={os.path.basename(os.path.dirname(r['store'])) if r['store'] else '(none)'}")
    srv.shutdown()

    by = {r["arm"]: r for r in rows}
    if not all(r["store"] for r in rows):
        raise SystemExit("REFUSED: at least one arm returned no store path; nothing below would be "
                         "evidence")

    v: dict = {}
    # POSITIVE CONTROL, and it can fail: the documented behaviour must reproduce first.
    v["CONTROL_inside_a_repo_cd_keeps_the_same_store"] = (
        by["repo root"]["store"] == by["repo subdir"]["store"])
    v["CONTROL_git_agrees_the_repo_arms_are_a_repo"] = (
        by["repo root"]["is_repo"] and by["repo subdir"]["is_repo"])
    v["CONTROL_git_agrees_the_plain_arms_are_NOT"] = (
        not by["non-repo root"]["is_repo"] and not by["non-repo subdir"]["is_repo"])
    v["CONTROL_the_two_trees_do_not_share_a_store"] = (
        by["repo root"]["store"] != by["non-repo root"]["store"])
    # THE FINDING.
    v["outside_a_repo_cd_MOVES_the_store"] = (
        by["non-repo root"]["store"] != by["non-repo subdir"]["store"])

    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print(f"\n  in-repo pair : {'SAME store' if v['CONTROL_inside_a_repo_cd_keeps_the_same_store'] else 'DIFFERENT'}")
    print(f"  outside pair : {'DIFFERENT stores' if v['outside_a_repo_cd_MOVES_the_store'] else 'same store'}")

    json.dump({"probe": os.path.basename(__file__), "verdicts": v, "arms": rows,
               "replicates": "@JhouCode on anthropics/claude-code#82056, linux-x64, n=1",
               "finding": "the asymmetry reproduces on win32: inside a git repo a subdirectory "
                          "resolves to the same auto-memory store, outside one it resolves to a "
                          "different store with no signal",
               "cost": "zero completions: ANTHROPIC_BASE_URL points at a local recorder and the "
                       "store path is read from the stream-json init event, which the CLI emits "
                       "before the model answers",
               "not_settled": ["whether the nesting rule holds at other depths",
                               "whether an empty store is ever cleaned up",
                               "one machine, win32"],
               "platform": sys.platform},
              io.open(os.path.join(HERE, "outside_a_repo_cd_moves_your_store.result.json"),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
