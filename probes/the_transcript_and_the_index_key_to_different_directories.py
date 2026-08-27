# -*- coding: utf-8 -*-
"""In a repository subdirectory the transcript and the memory index resolve to two different stores.

WHY THIS EXISTS. @simplysdm filed anthropics/claude-code#90046 with this on darwin-arm64, CLI
2.1.246, and named the consequence that matters to anyone building a probe: the store path is NOT
derivable from transcript_path, which is the obvious handle because SessionStart hands it to a hook
directly. He was explicit about the limits of his own instrument, and both are addressed here:

  "No wire capture -- these are canary read-backs from completions ... I did not disable tools, so a
   model reaching for disk instead of context is not excluded on my side."
  "Current build here is now 2.1.247; I have not re-run the fixtures against it."

This asks the model nothing. The resolved index path is a field on the `system/init` event,
`memory_paths.auto`, so it is read off the protocol rather than out of a completion. Tools are
disabled and MCP is stripped, so there is no disk path to reach for even in principle, and the API
base points at a local recorder that returns a fixed SSE body, so no request leaves the machine and
no token is spent. And it runs on 2.1.247, the build he flagged as untested.

WHAT IT MEASURES, from ONE session launched in <repo>/sub:

    cwd                       <repo>/sub
    memory_paths.auto         ~/.claude/projects/<slug of repo>/memory/...      <- the repo ROOT
    transcript .jsonl lands   ~/.claude/projects/<slug of repo/sub>/            <- the CWD

So one session creates two project directories, reads the index from one and writes its transcript
to the other, and the subdirectory's own store is never read.

CONTROLS, because a probe that resolves one path and calls it a mismatch has proved nothing:

  * the repo-root arm must resolve to the SAME store as the subdirectory arm. If it does not, the
    difference is not "subdirectory versus root" and the finding is void.
  * a NON-repo subdirectory must resolve to its OWN store. That is the documented cd behaviour, and
    it is what tells a real result apart from "every arm returns the first path we saw".
  * the init event must actually carry memory_paths.auto. An absent field read as an empty string
    would make every comparison equal and every arm agree, silently.
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "cdstore", os.path.join(HERE, "outside_a_repo_cd_moves_your_store.py"))
_cd = importlib.util.module_from_spec(_spec)
_cd.__name__ = "cdstore"
try:
    _spec.loader.exec_module(_cd)
except SystemExit:
    pass

PROJECTS = os.path.join(os.path.expanduser("~"), ".claude", "projects")
PORT = 8894
WIRE_PORT = 8895

#: Request bodies captured by the wire arm. The recorder in the sibling probe answers but discards
#: the body; this one keeps it, which is the whole difference between reading a path and reading
#: what was actually sent.
BODIES = []


def init_event(d, port):
    """Launch in `d`, return the system/init event. No completion is requested of the model."""
    env = dict(os.environ, ANTHROPIC_BASE_URL="http://127.0.0.1:%d" % port,
               ANTHROPIC_API_KEY="x")
    p = subprocess.Popen([_cd.CLAUDE, "-p", "--output-format", "stream-json", "--verbose",
                          "--tools", "", "--strict-mcp-config", "x"],
                         cwd=d, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    try:
        out, _ = p.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        else:
            p.kill()
        return {}
    for line in (out or "").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            return ev
    return {}


def wire_recorder(port):
    """Like the sibling probe's recorder, but it KEEPS the request body."""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("content-length") or 0)
            BODIES.append(self.rfile.read(n).decode("utf-8", "replace"))
            b = _cd.SSE.encode()
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def wire_arm():
    """THE ARM THAT READS THE INDEX OFF THE WIRE, not off a path or out of a completion.

    @simplysdm's stated limit on #90046 was "no wire capture -- these are canary read-backs from
    completions ... I did not disable tools, so a model reaching for disk instead of context is not
    excluded". This closes both: distinct canaries are planted in the repo-root store and in the
    cwd store, one session runs in <repo>/sub, and the REQUEST BODY is inspected.

    THREE WAYS I GOT THIS WRONG BEFORE IT WORKED, all the same shape:

      1. The canaries went into a directory computed by hand. A drive letter became one dash
         writes `C--`, so nothing was ever planted where anything would look. Both canaries came
         back absent and that null was meaningless.
      2. memory_paths.auto is a DIRECTORY, not the index file. Writing to it as a file raised.
      3. Only a positive control separated 1 from a real finding: running in this repository, whose
         index is known to be delivered, and confirming its content DOES appear in the body. Without
         it the first null would have been published as the result.

    So the canaries are planted at the path the CLI itself reports, and the positive control is an
    assertion rather than a memory of having checked.
    """
    if _cd.CLAUDE is None:
        return {}
    srv = wire_recorder(WIRE_PORT)
    base = tempfile.mkdtemp(prefix="wire_arm_")
    repo = os.path.join(base, "arepo")
    sub = os.path.join(repo, "sub")
    os.makedirs(sub, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, capture_output=True)

    auto = (init_event(sub, WIRE_PORT).get("memory_paths") or {}).get("auto", "")
    if not auto:
        srv.shutdown()
        return {}
    os.makedirs(auto, exist_ok=True)
    io.open(os.path.join(auto, "MEMORY.md"), "w", encoding="utf-8").write(
        "# Memory Index" + chr(10) * 2 + "- CANARYROOT77 marker" + chr(10))

    tag = os.path.basename(base).replace("_", "-")
    cwd_slugs = [d for d in os.listdir(PROJECTS) if d.endswith("arepo-sub") and tag in d]
    if cwd_slugs:
        m = os.path.join(PROJECTS, cwd_slugs[0], "memory")
        os.makedirs(m, exist_ok=True)
        io.open(os.path.join(m, "MEMORY.md"), "w", encoding="utf-8").write(
            "# Memory Index" + chr(10) * 2 + "- CANARYSUB42 marker" + chr(10))

    BODIES.clear()
    init_event(sub, WIRE_PORT)
    body = " ".join(BODIES)
    posts = len(BODIES)

    # POSITIVE CONTROL: this repository's own index is known to be delivered. If its content is
    # absent from the body too, the recorder is not seeing index injection and every null above is
    # an instrument failure rather than a result.
    BODIES.clear()
    init_event(os.path.dirname(HERE), WIRE_PORT)
    control_body = " ".join(BODIES)
    srv.shutdown()
    return {"posts": posts, "bytes": len(body),
            "root_canary_in_request": "CANARYROOT77" in body,
            "sub_canary_in_request": "CANARYSUB42" in body,
            "control_real_index_reaches_the_wire": "Memory Index" in control_body}


def slug_of(store_path):
    """.../projects/<slug>/memory/... -> <slug>"""
    if not store_path:
        return ""
    parts = os.path.normpath(store_path).split(os.sep)
    return parts[parts.index("projects") + 1] if "projects" in parts else ""


def jsonl_count(slug):
    d = os.path.join(PROJECTS, slug)
    if not os.path.isdir(d):
        return None
    return len([f for f in os.listdir(d) if f.endswith(".jsonl")])


def main():
    if _cd.CLAUDE is None:
        raise SystemExit("REFUSED: no runnable `claude` on PATH; every check below would be vacuous")
    srv = _cd.recorder(PORT)
    base = tempfile.mkdtemp(prefix="tx_idx_")
    repo = os.path.join(base, "arepo")
    repo_sub = os.path.join(repo, "sub")
    plain_sub = os.path.join(base, "plain", "sub")
    for d in (repo_sub, plain_sub):
        os.makedirs(d, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, capture_output=True)

    arms = {}
    for name, d in (("repo_sub", repo_sub), ("repo_root", repo), ("nonrepo_sub", plain_sub)):
        ev = init_event(d, PORT)
        arms[name] = {
            "cwd": ev.get("cwd", ""),
            "version": ev.get("claude_code_version", ""),
            "store": (ev.get("memory_paths") or {}).get("auto", ""),
            "session_id": ev.get("session_id", ""),
        }
        arms[name]["store_slug"] = slug_of(arms[name]["store"])
        print("  %-12s cwd=%-46s store_slug=%s"
              % (name, os.path.basename(arms[name]["cwd"]) or "?",
                 arms[name]["store_slug"][-46:] or "(none)"))
    srv.shutdown()

    sub_slug = arms["repo_sub"]["store_slug"]
    cwd_slug = None
    for d in sorted(os.listdir(PROJECTS)):
        if d.endswith("arepo-sub") and os.path.basename(base).replace("_", "-") in d:
            cwd_slug = d
    v = {}
    v["CONTROL_init_carries_the_store_path"] = bool(arms["repo_sub"]["store"])
    v["CONTROL_repo_root_and_subdir_agree"] = (
        arms["repo_sub"]["store_slug"] == arms["repo_root"]["store_slug"] != "")
    v["CONTROL_a_non_repo_subdir_gets_its_own_store"] = (
        arms["nonrepo_sub"]["store_slug"] not in ("", arms["repo_sub"]["store_slug"]))
    v["the_index_keys_to_the_repo_root"] = sub_slug.endswith("arepo")
    v["a_separate_cwd_directory_exists"] = cwd_slug is not None
    v["the_transcript_lands_in_the_cwd_directory"] = bool(cwd_slug) and (jsonl_count(cwd_slug) or 0) >= 1
    # BY SESSION ID, not by count. The first version asserted the repo-root store held NO
    # transcript at all, and its own repo_root control arm falsified it: that arm launches from the
    # repo root and its transcript belongs there. The claim is narrower and this is what it says:
    # the SUBDIRECTORY session's transcript is not in the store that session read its index from.
    sid = arms["repo_sub"]["session_id"]
    root_dir = os.path.join(PROJECTS, sub_slug)
    root_files = os.listdir(root_dir) if os.path.isdir(root_dir) else []
    v["the_subdir_sessions_transcript_is_not_where_it_read"] = bool(sid) and not any(
        sid in f for f in root_files)
    cwd_dir = os.path.join(PROJECTS, cwd_slug) if cwd_slug else None
    v["that_transcript_is_in_the_cwd_directory"] = bool(sid) and bool(cwd_dir) and any(
        sid in f for f in (os.listdir(cwd_dir) if os.path.isdir(cwd_dir) else []))

    wire = wire_arm()
    if wire:
        v["CONTROL_a_known_delivered_index_reaches_the_wire"] = wire["control_real_index_reaches_the_wire"]
        v["the_repo_root_canary_is_in_the_request_body"] = wire["root_canary_in_request"]
        v["the_cwd_store_canary_is_NOT_in_the_request_body"] = not wire["sub_canary_in_request"]

    res = {"platform": sys.platform, "cli_version": arms["repo_sub"]["version"], "wire": wire,
           "arms": arms, "cwd_slug": cwd_slug,
           "jsonl_in_cwd_slug": jsonl_count(cwd_slug) if cwd_slug else None,
           "jsonl_in_repo_root_slug": jsonl_count(sub_slug),
           "verdicts": {k: bool(x) for k, x in v.items()}}
    io.open(os.path.join(HERE, "the_transcript_and_the_index_key_to_different_directories.result.json"),
            "w", encoding="utf-8").write(json.dumps(res, indent=2))
    print()
    for k, ok in res["verdicts"].items():
        print("%-52s %s" % (k, "PASS" if ok else "FAIL"))
    print("\n%d/%d" % (sum(res["verdicts"].values()), len(res["verdicts"])))
    return 0 if all(res["verdicts"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
