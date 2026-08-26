"""Does a nested `claude -p` ignore CLAUDE_CONFIG_DIR and ANTHROPIC_BASE_URL? On win32 it does not.

WHY. @yacb2 reported a hazard on anthropics/claude-code#82056 (darwin-arm64, 2.1.246): running a
capture probe from a Bash tool call INSIDE an interactive session, so that CLAUDECODE=1 and
CLAUDE_CODE_CHILD_SESSION=1 are inherited, made the child ignore both CLAUDE_CONFIG_DIR and
ANTHROPIC_BASE_URL. The child answered from the real API and wrote its transcript under the real
`~/.claude/projects/<slug>/`, so a fixture he believed was isolated would have landed in a live
store. He closed with the part that makes this worth measuring rather than repeating:

    "I have not bisected which inherited variable causes it, but it is the difference between the
     two runs and worth a check before trusting any nested capture."

We are the Windows box, and every wire capture we published today was taken from exactly that
nested condition. If the hazard is universal, our captures went to the real API and our figures came
from somewhere other than we said. That is a strong enough consequence to check rather than assume,
and checking it also hands him the third platform.

WHAT IS MEASURED, three things per arm, none of them asked of a model:

  1. Did the request reach OUR recorder? That is ANTHROPIC_BASE_URL being honoured, and it is
     visible as bytes on a socket rather than inferred.
  2. Did a `projects/` tree appear under the CLAUDE_CONFIG_DIR we passed? That is CLAUDE_CONFIG_DIR
     being honoured.
  3. THE ONE THAT MATTERS: did a NEW slug directory appear under the REAL `~/.claude/projects/`?
     That is the actual harm he describes, and it is measured by snapshotting the real directory
     before and after rather than by trusting either variable.

TWO ARMS. NESTED inherits this session's environment, including CLAUDECODE=1 and
CLAUDE_CODE_CHILD_SESSION=1. CLEAN keeps the environment but strips every CLAUDE_*/ANTHROPIC_* key
before setting the two under test, which isolates the inherited-variable hypothesis. A literal
`env -i` was tried first and could not start the launcher at all on Windows, where `claude` is a
.cmd needing COMSPEC and PATHEXT -- the control would have failed for a reason that has nothing to
do with the question. The clean arm is the positive control: if it also fails, the harness is broken
and the nested result means nothing.

Nothing is deleted. If the run leaks a slug into the real store, the probe REPORTS the directory
name and leaves it, because a probe that cleans up after itself removes the evidence that it leaked.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_PROJECTS = os.path.join(os.path.expanduser("~"), ".claude", "projects")


def _claude():
    """The launcher CreateProcess can actually start.

    `claude` on PATH here is an extensionless shell script, so shutil.which finds it and
    subprocess.run raises WinError 2 on it. The .cmd shim is the one Windows can execute, and
    checking which() alone reported a healthy tool that could not be run.
    """
    for c in ("claude.cmd", "claude.exe", "claude"):
        p = shutil.which(c)
        if p and os.path.splitext(p)[1].lower() in (".cmd", ".exe", ".bat"):
            return p
    return shutil.which("claude")


CLAUDE = _claude()

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


def recorder(port: int, hits: list):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("content-length") or 0)
            self.rfile.read(n)
            hits.append(self.path)
            body = SSE.encode()
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def slugs() -> set:
    try:
        return {d for d in os.listdir(REAL_PROJECTS)
                if os.path.isdir(os.path.join(REAL_PROJECTS, d))}
    except FileNotFoundError:
        return set()


def run_arm(name: str, port: int, nested: bool) -> dict:
    hits: list = []
    srv = recorder(port, hits)
    cfg = tempfile.mkdtemp(prefix=f"ccfg_{name}_")
    proj = tempfile.mkdtemp(prefix=f"cproj_{name}_")
    before = slugs()
    # CLEAN strips exactly the variable class under test and nothing else. A literal `env -i` was
    # the first attempt and it could not even start the launcher: `claude` on PATH here is a .cmd,
    # which needs COMSPEC and PATHEXT, so the control failed for a reason unrelated to the question
    # and would have been read as the remedy not working. Removing every CLAUDE_*/ANTHROPIC_* key
    # from an otherwise intact environment is the sharper experiment anyway: it isolates the
    # inherited-variable hypothesis instead of confounding it with a bare shell.
    env = dict(os.environ)
    if not nested:
        for k in [k for k in env
                  if k.upper().startswith("CLAUDE") or k.upper().startswith("ANTHROPIC")]:
            del env[k]
    env["CLAUDE_CONFIG_DIR"] = cfg
    env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{port}"
    env["ANTHROPIC_API_KEY"] = "x"
    t = time.time()
    try:
        subprocess.run([CLAUDE, "-p", "--output-format", "text", "--tools", "",
                        "--strict-mcp-config", "say OK"],
                       cwd=proj, env=env, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        pass
    time.sleep(1.0)
    srv.shutdown()
    after = slugs()
    cfg_projects = os.path.join(cfg, "projects")
    return {"arm": name, "nested": nested,
            "inherited_CLAUDECODE": bool(nested and os.environ.get("CLAUDECODE")),
            "inherited_CHILD_SESSION": bool(nested and os.environ.get("CLAUDE_CODE_CHILD_SESSION")),
            "requests_reached_our_recorder": len(hits),
            "base_url_honoured": len(hits) > 0,
            "config_dir_got_a_projects_tree": os.path.isdir(cfg_projects),
            "config_dir_entries": (len(os.listdir(cfg_projects))
                                   if os.path.isdir(cfg_projects) else 0),
            "LEAKED_into_the_real_store": sorted(after - before),
            "seconds": round(time.time() - t, 1),
            "_cfg": cfg, "_proj": proj}


def main() -> int:
    if CLAUDE is None:
        raise SystemExit("REFUSED: no runnable `claude` on PATH; every check below would be vacuous")
    print(f"  real store: {REAL_PROJECTS}  ({len(slugs())} slug dirs before)")
    print(f"  this process inherits CLAUDECODE={os.environ.get('CLAUDECODE')!r} "
          f"CLAUDE_CODE_CHILD_SESSION={os.environ.get('CLAUDE_CODE_CHILD_SESSION')!r}\n")

    rows = [run_arm("nested", 8841, True), run_arm("clean", 8842, False)]
    for r in rows:
        print(f"  {r['arm']:7s} recorder_hits={r['requests_reached_our_recorder']} "
              f"base_url_honoured={r['base_url_honoured']} "
              f"config_dir_used={r['config_dir_got_a_projects_tree']} "
              f"leaked={r['LEAKED_into_the_real_store'] or 'none'} [{r['seconds']}s]")

    nested = rows[0]
    clean = rows[1]
    v: dict = {}
    # THE POSITIVE CONTROL. If the clean arm fails, nothing about the nested arm can be concluded.
    v["CONTROL_the_clean_arm_reached_our_recorder"] = clean["base_url_honoured"]
    v["CONTROL_we_really_were_nested"] = (nested["inherited_CLAUDECODE"]
                                          and nested["inherited_CHILD_SESSION"])
    v["CONTROL_the_real_store_was_readable"] = os.path.isdir(REAL_PROJECTS)
    # THE MEASUREMENT.
    v["nested_ALSO_honoured_ANTHROPIC_BASE_URL"] = nested["base_url_honoured"]
    v["nested_ALSO_honoured_CLAUDE_CONFIG_DIR"] = nested["config_dir_got_a_projects_tree"]
    v["nested_did_NOT_leak_a_slug_into_the_real_store"] = not nested["LEAKED_into_the_real_store"]
    v["clean_did_NOT_leak_a_slug_into_the_real_store"] = not clean["LEAKED_into_the_real_store"]

    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    leaked = nested["LEAKED_into_the_real_store"] + clean["LEAKED_into_the_real_store"]
    if leaked:
        print("\n  LEFT IN THE REAL STORE, not cleaned up, so the evidence survives:")
        for d in leaked:
            print("   ", d)

    json.dump({"probe": os.path.basename(__file__), "verdicts": v, "arms": rows,
               "question": "@yacb2 on anthropics/claude-code#82056: a nested claude -p ignored "
                           "CLAUDE_CONFIG_DIR and ANTHROPIC_BASE_URL on darwin-arm64, and he had "
                           "not bisected which inherited variable causes it",
               "scope": "one machine, win32, one build. This says what happens HERE; it cannot "
                        "tell him why his box differs, only that the difference is real.",
               "platform": sys.platform},
              io.open(os.path.join(HERE, "does_a_nested_session_ignore_the_isolation_variables"
                                         ".result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
