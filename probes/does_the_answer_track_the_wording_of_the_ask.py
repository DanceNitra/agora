"""Reproduce the 9/9, 4/9, 2/9 wording result we published with no artifact behind it.

THE DEBT. On 2026-08-23 we posted this to anthropics/claude-code#82056 (comment 5387228275):

    "the accuracy tracks the *wording*: 'the last CANARY token you can SEE' 9/9, '...the last CANARY
     token in `MEMORY.md`' 4/9, a neutral phrasing 2/9 with five refusals to answer at all."

Three cells and a refusal count, in public, for three days. Searched today across every
probes/*.result.json: nothing on disk carries them, and no probe varies the wording of the ask at
all. So the figures are unbacked by our own rule, which says a number in a note is not verified data
and a claim ships with a runnable artifact or does not ship. This is the artifact, built to either
reproduce them or correct them in public.

WHAT CHANGED SINCE, and it makes this a better experiment than the original could have been. The
first version had to compute the expected answer by arithmetic: floor(cap / line width), which is
exactly the class of reasoning we have retracted twice in that thread. The wire capture removes it.
Point ANTHROPIC_BASE_URL at a local recorder, read the request body, and the last CANARY that
actually reached the model is a fact about bytes rather than a prediction. Ground truth first, then
ask.

THE DESIGN.

  Fixture: one MEMORY.md of numbered CANARY lines, larger than the cap, so the index is truncated.
  Ground truth: the highest CANARY id present in the captured request body. Zero model calls.
  Arms: the three wordings above, N trials each, fresh session per trial, interleaved.
  Outcomes: answered_correctly, WENT_TO_DISK, answered_wrongly, refused, timeout. Five, not three.

WHAT THE FIRST RUN FOUND, 20 trials before it had to be killed, and it is not what we published:

    see       7 answered from context, 7 of them correct, 0 went to disk
    in_file   1 answered from context, 6 went to disk
    neutral   0 answered from context, 6 went to disk

The ORDER of the published claim reproduces. The MECHANISM does not. The non-see arms are not
answering incorrectly; they announce that they will read the file, and they say why in their own
words: "since only part of it was loaded", "the context note says", "the version in my context was
truncated". So the variable is whether the wording scopes the model to its context or licenses it to
treat the file as the authority, and the truncation notice we have spent a week measuring is itself
what triggers the disk read.

And there were ZERO refusals in twenty trials. Our published "five refusals to answer at all" almost
certainly counted tool attempts, which is what a scorer without an went_to_disk category must do with
them. That category is the correction; folding a behaviour into "wrong" is what turned this into an
accuracy claim.

CONTROLS, because a wording effect is easy to manufacture:

  * GROUND TRUTH IS READ, NOT PREDICTED. The receipt records both the captured last canary and
    floor(cap/width); if they disagree the wire wins and the disagreement is printed.
  * THE FIXTURE MUST ACTUALLY TRUNCATE. If every canary survives, all three arms trivially score
    and the experiment measures nothing.
  * REACHING FOR THE FILE IS ITS OWN OUTCOME, and so are a refusal and a timeout. An outcome
    vocabulary narrower than the behaviours available to the subject will misreport, not under-report.
  * THE SEE ARM MUST BE ABLE TO ANSWER AT ALL, or the fixture rather than the wording is the story.
  * ORDER IS INTERLEAVED, so drift over the session cannot masquerade as a wording effect.
  * NO TRIAL MAY TIME OUT. The first run passed timeout=180 to subprocess.run and trusted it; on
    Windows the .cmd shim spawns a node grandchild that holds the pipe, one trial ran over seven
    minutes, orphaned claude.exe processes piled up, and the experiment died at 20 of 27. ask_once
    now takes the process tree with taskkill /T and an empty answer is scored `timeout` rather than
    silently becoming a wrong answer.

COST, stated before spending because that is the rule here: 3 arms x N trials, one `claude -p`
startup each, measured at roughly 39k tokens per startup. At N=9 that is 27 calls, about 1.05M
tokens. The wire capture is free. Run with --dry to build the fixture, capture ground truth and
print the cost without making a single model call.


WHY THE THIRD OUTCOME IS NOT CALLED `went_to_disk` ANY MORE, added 2026-08-27.

Every call in this file runs with `--tools ""`, which disables all tools, so NO trial in any arm
could read anything. Those rows are the model EMITTING the text of a tool call into stdout: a claim
that it is about to read the file, never a read. The docstring here always said "announce". The JSON
key said `went_to_disk`. On 2026-08-27 I drafted a public comment telling a collaborator that his
shipped canary check was defeated by sessions "shelling out and reading the file", and the only
evidence for that sentence was the key. Our own comment 5426356913, published the day before, had
already used the correct word.

So the key is `announced_a_file_read`, and what a tools-ENABLED session does is NOT measured here and
must not be inferred from it. That run is a different experiment: it needs `--tools` left at its
default AND an unguessable canary, because this fixture numbers its canaries in sequence, which lets
a model produce the file's true last line by extrapolation with no file access at all. Two trials did
exactly that.
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
WIDTH, LINES = 199, 200          # 199 chars + LF = 200 units per line, well over the 25,000 cap
TOKENS_PER_CALL = 39_000         # measured in this repo's own cost note

ASKS = {
    "see": "What is the last CANARY token you can SEE? Answer with the token only.",
    "in_file": "What is the last CANARY token in `MEMORY.md`? Answer with the token only.",
    "neutral": "What is the last CANARY token? Answer with the token only.",
}

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


def store_of(proj: str) -> str:
    r = subprocess.run([CLAUDE, "-p", "--output-format", "stream-json", "--verbose",
                        "--tools", "", "--strict-mcp-config", "x"],
                       cwd=proj, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    for line in (r.stdout or "").splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            return (d.get("memory_paths") or {}).get("auto") or ""
    return ""


def write_fixture(store: str) -> int:
    """Write the fixture and return the ACTUAL line width, measured rather than assumed.

    The first version padded to WIDTH - 22 on the belief that the prefix is 22 characters. It is 17,
    so every line came out 194 wide, and the arithmetic prediction printed below was off by five
    characters and three canaries while the wire was right. That is this experiment's own point
    arriving before the experiment does: nothing here depends on the width, and it is reported only
    so the two candidate ground truths can be compared honestly.
    """
    lines = [f"- [CANARY-L{i:04d}] " for i in range(1, LINES + 1)]
    lines = [l + "x" * (WIDTH - len(l)) for l in lines]
    io.open(os.path.join(store, "MEMORY.md"), "wb").write(
        ("\n".join(lines) + "\n").encode("utf-8"))
    return len(lines[0]) + 1


def capture_ground_truth(proj: str, port: int, per_line: int) -> dict:
    hits: list = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("content-length") or 0)
            hits.append(self.rfile.read(n).decode("utf-8", "replace"))
            b = SSE.encode()
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    env = dict(os.environ, ANTHROPIC_BASE_URL=f"http://127.0.0.1:{port}", ANTHROPIC_API_KEY="x")
    subprocess.run([CLAUDE, "-p", "--output-format", "text", "--tools", "",
                    "--strict-mcp-config", "say OK"],
                   cwd=proj, env=env, capture_output=True, timeout=120)
    time.sleep(0.8)
    srv.shutdown()
    if not hits:
        raise SystemExit("REFUSED: the recorder saw no request; ground truth would be a guess")
    text = json.loads(hits[0])["messages"][0]["content"][0]["text"]
    ids = [int(x) for x in re.findall(r"CANARY-L(\d{4})", text)]
    return {"last_on_wire": max(ids) if ids else 0, "canaries_on_wire": len(ids),
            "predicted_by_arithmetic": int(25000 // per_line), "units_per_line": per_line}


TIMEOUT_S = 90        # a real answer arrives in about ten seconds; ninety is already generous


def ask_once(proj: str, prompt: str) -> str:
    """One ask, with a timeout that actually kills what it started.

    The first version passed timeout=180 to subprocess.run and trusted it. On Windows `claude` is a
    .cmd shim that spawns a node grandchild, and killing the shim leaves the grandchild holding the
    pipe, so the run hung on trial 21 for over seven minutes while orphaned claude.exe processes
    accumulated. The whole experiment had to be killed at 20 of 27. taskkill /T takes the tree.
    """
    p = subprocess.Popen([CLAUDE, "-p", "--output-format", "text", "--tools", "",
                          "--strict-mcp-config", prompt],
                         cwd=proj, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    try:
        out, _ = p.communicate(timeout=TIMEOUT_S)
        return (out or "").strip()
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)],
                           capture_output=True)
        else:
            p.kill()
        try:
            p.communicate(timeout=10)
        except Exception:
            pass
        return ""      # empty is the sentinel, and score() gives it its own outcome


REFUSAL = re.compile(r"\b(cannot|can't|unable|don't have|do not have|no access|not able)\b", re.I)
# The category the first scorer did not have, and the reason its result was wrong. These arms do not
# answer incorrectly; they announce that they will read the file, usually citing the truncation
# notice. Folding that into "wrong" is what turned a behaviour finding into an accuracy claim.
TO_DISK = re.compile(r"I'?ll (check|read)|Let me (check|read)|<invoke|Tool: Read|Read tool|"
                     r"powershell|wc -l|Get-Content|type the file", re.I)


def score(answer: str, truth: int) -> str:
    if not answer.strip():
        return "timeout"
    if re.search(rf"CANARY-L0*{truth}\b", answer):
        return "answered_correctly"
    if TO_DISK.search(answer):
        return "announced_a_file_read"
    if REFUSAL.search(answer) and not re.search(r"CANARY-L\d", answer):
        return "refused"
    return "answered_wrongly"


def main() -> int:
    if CLAUDE is None:
        raise SystemExit("REFUSED: no runnable `claude` on PATH")
    dry = "--dry" in sys.argv
    n = 9
    for a in sys.argv:
        if a.startswith("--n="):
            n = int(a.split("=", 1)[1])

    proj = tempfile.mkdtemp(prefix="wording_")
    store = store_of(proj)
    if not store:
        raise SystemExit("REFUSED: could not resolve the auto-memory store from the init event")
    os.makedirs(store, exist_ok=True)
    per_line = write_fixture(store)
    gt = capture_ground_truth(proj, 8871, per_line)

    calls = len(ASKS) * n
    print(f"  fixture      : {LINES} lines x {WIDTH} chars, store {store[:60]}")
    print(f"  ground truth : last CANARY on the wire = L{gt['last_on_wire']:04d} "
          f"({gt['canaries_on_wire']} of {LINES} crossed)")
    print(f"  arithmetic   : floor(25000/{gt['units_per_line']}) = {gt['predicted_by_arithmetic']}"
          f"{'  AGREES' if gt['predicted_by_arithmetic'] == gt['last_on_wire'] else '  DISAGREES, the wire wins'}")
    print(f"  cost if run  : {len(ASKS)} arms x {n} trials = {calls} claude -p startups, "
          f"about {calls * TOKENS_PER_CALL / 1e6:.2f}M tokens")

    if gt["last_on_wire"] >= LINES or gt["canaries_on_wire"] >= LINES:
        raise SystemExit("REFUSED: the fixture did not truncate, so every arm would score "
                         "trivially and the experiment would measure nothing")

    if dry:
        print("\n  --dry: no model was called. Re-run without --dry to spend the tokens above.")
        json.dump({"probe": os.path.basename(__file__), "dry_run": True, "ground_truth": gt,
                   "planned_calls": calls, "estimated_tokens": calls * TOKENS_PER_CALL,
                   "asks": ASKS, "fixture": {"lines": LINES, "width": WIDTH},
                   "debt": "reproduces the 9/9 4/9 2/9 cells published in "
                           "anthropics/claude-code#82056 comment 5387228275 with no artifact",
                   "platform": sys.platform},
                  io.open(os.path.join(HERE, "does_the_answer_track_the_wording_of_the_ask"
                                             ".result.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        return 0

    # Interleaved, so drift over the session cannot look like a wording effect.
    order = [(k, i) for i in range(n) for k in ASKS]
    CATS = ("answered_correctly", "announced_a_file_read", "answered_wrongly", "refused", "timeout")
    rows, tally = [], {k: {c: 0 for c in CATS} for k in ASKS}
    for j, (k, i) in enumerate(order, 1):
        ans = ask_once(proj, ASKS[k])
        s = score(ans, gt["last_on_wire"])
        tally[k][s] += 1
        rows.append({"arm": k, "trial": i + 1, "outcome": s, "answer": ans[:120]})
        print(f"    [{j}/{len(order)}] {k:8s} {s:8s} {ans[:56]!r}", flush=True)

    print()
    for k in ASKS:
        t = tally[k]
        print(f"  {k:8s} {t['answered_correctly']}/{n} from context, "
              f"{t['announced_a_file_read']} announced a read, {t['answered_wrongly']} wrong, "
              f"{t['refused']} refused, {t['timeout']} timed out")

    v = {"CONTROL_the_fixture_truncated": gt["canaries_on_wire"] < LINES,
         "CONTROL_ground_truth_came_from_the_wire": gt["last_on_wire"] > 0,
         "every_trial_produced_an_outcome": len(rows) == len(order),
         "no_trial_timed_out": not any(t["timeout"] for t in tally.values()),
         "CONTROL_the_see_arm_can_answer_at_all": tally["see"]["answered_correctly"] > 0}
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")

    json.dump({"probe": os.path.basename(__file__), "PROBE_PASSES": all(v.values()),
               "verdicts": v, "ground_truth": gt,
               "asks": ASKS, "n_per_arm": n, "tally": tally, "rows": rows,
               "published_claim": {"see": "9/9", "in_file": "4/9", "neutral": "2/9",
                                   "refusals_on_neutral": 5,
                                   "where": "anthropics/claude-code#82056 comment 5387228275"},
               "fixture": {"lines": LINES, "width": WIDTH},
               "platform": sys.platform},
              io.open(os.path.join(HERE, "does_the_answer_track_the_wording_of_the_ask"
                                         ".result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
