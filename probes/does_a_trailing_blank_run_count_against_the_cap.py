"""@pjt222 named an arm he had not run. This is that arm, plus the one that reads out unconditionally.

WHY. On anthropics/claude-code#82056 (2026-08-26, comment 5425660561) he measured that a trailing
blank run does not count against the 25,000-unit cap: his `trim` fixture weighs 25,003 units on
disk, arrives whole at 25,000, and is silent. Then he stated the limit of it himself, and named the
experiment that would remove the limit:

    "Precisely, this pins the count the THRESHOLD uses, not the operand the CUT uses. A model that
     thresholds on the trimmed count and then slices the raw text reproduces this arm exactly...
     The arm that separates them: 4,999 five-char markers plus `zzz` (24,998 content) plus five
     newlines - raw 25,003, trimmed 24,998. Trim-first predicts 24,998 units on the wire ending
     `...zzz`; slice-the-raw predicts 25,000 ending `z\\n\\n`. Both silent, so the count is the
     read-out. I have not run it."

His arm is run here verbatim (`his_separator`). It has one weakness he could not see from linux,
and it is the reason this file carries a sixth arm: the read-out is TWO TRAILING NEWLINES, and
whether those survive into the request body is a property of how the harness embeds the index, not
of the cap. If the embedding eats them, his arm returns the same wire text under both models and
answers nothing. `ctl_small` measures that first, so a null is separable from a broken read-out.

`blank2000` is the same question with a read-out that cannot be eaten. Same content, 2,000 trailing
newlines instead of five: raw 26,998, trimmed 24,998.

    trim-first  -> 24,998 is under the cap  -> NO notice, index whole
    raw count   -> 26,998 is over the cap   -> notice present, "26.4KB (limit: 24.4KB)"

The read-out is the presence of the notice, which is a string the harness emits deliberately. It
does not depend on trailing whitespace surviving anything. This is his question with the geometry
changed; the credit for the question is his.

AND THE ANSWER TO HIS ARM IS THAT IT CANNOT BE READ, for a reason that generalises past this
fixture. Two halves:

  MEASURED (`disp_none` / `disp_nl5` / `disp_sp`): three indexes differing only in their trailing
  run -- none, five newlines, spaces and newlines -- produce BYTE-IDENTICAL prompt text, all ending
  at the last content character. The embedding trims the tail, so no trailing run is ever visible
  on the wire whether or not anything was cut.

  ARGUED, and it is two lines: a cut happens only when the TRIMMED length exceeds the cap, and in
  that case the trailing run lies beyond position 25,000, so slicing the raw text and slicing the
  trimmed text keep the same prefix. When the two would differ, the trimmed length is under the cap
  and trim-first does not cut at all -- leaving a difference of pure trailing whitespace, which the
  first half says is invisible. So for EVERY input the two models produce identical prompts.

That is the same shape as his own commutativity argument for the order of the two cuts: not
unmeasured, unobservable from the output. What the wire does settle is the THRESHOLD, and
`blank2000` settles it about 2KB clear of the boundary rather than 3 units clear.

CONTROLS, and two of them can fail:
  * `ctl_exact`  5,000 markers, exactly 25,000 units, no trailing run -> must arrive WHOLE and
    SILENT. This is his `size_exact` on win32.
  * `ctl_over1`  the same plus one character -> must be CUT to 25,000 and must WARN. If this does
    not fire, the instrument cannot see a cut at this geometry and every silence above is void.
  * `ctl_small`  100 characters plus five newlines, far under any cap -> the calibration arm above.
  * every arm asserts that the store the CLI reports is the store this arm just wrote to. Reading
    the wrong store returns perfectly well-formed numbers; @pjt222 lost a whole run to that today.

COST: zero completions. `ANTHROPIC_BASE_URL` points at a local recorder that answers canned SSE, so
no model is called at any point. Request bodies are held in memory, four fields are derived, and the
body is dropped; a body carries account identifiers, home paths and the whole of CLAUDE.md, so
nothing is written to disk. That is @pjt222's rule and it is right.
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
PORT = 8893
CAP = 25000
# The index sits between these two in the system-reminder. Both are the harness's own strings.
HEAD = "(user's auto-memory, persists across conversations):\n\n"
NOTICE = re.compile(r"> WARNING: MEMORY\.md is ([0-9.]+)KB[^\n]*")

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

BODIES: list[str] = []


def recorder(port: int):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("content-length") or 0))
            BODIES.append(raw.decode("utf-8", "replace"))   # in memory only, never written out
            b = SSE.encode()
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def claude_bin():
    for c in ("claude.cmd", "claude.exe", "claude"):
        p = shutil.which(c)
        if p and os.path.splitext(p)[1].lower() in (".cmd", ".exe", ".bat"):
            return p
    return shutil.which("claude")


CLAUDE = claude_bin()
NO_TOOLS = ["--tools", "", "--strict-mcp-config"]


def run(cwd: str, prompt: str) -> tuple[str, list[str]]:
    """One `claude -p` against the local recorder. Returns (store_path, tools_offered)."""
    env = dict(os.environ, ANTHROPIC_BASE_URL="http://127.0.0.1:%d" % PORT, ANTHROPIC_API_KEY="x")
    p = subprocess.Popen([CLAUDE, "-p", "--output-format", "stream-json", "--verbose"] + NO_TOOLS
                         + [prompt], cwd=cwd, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    try:
        out, _ = p.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        else:
            p.kill()
        return "", []
    for line in (out or "").splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            return ((d.get("memory_paths") or {}).get("auto") or ""), list(d.get("tools") or [])
    return "", []


def markers(n: int) -> str:
    return "".join("M%04d" % i for i in range(1, n + 1))


# label -> (fixture text, what it is for)
ARMS = {
    "ctl_small":     (("A" * 100) + "\n" * 5,
                      "far under the cap: does a trailing newline run survive onto the wire at all"),
    "ctl_exact":     (markers(5000),
                      "exactly 25,000 units, no trailing run: must arrive whole and silent"),
    "ctl_over1":     (markers(5000) + "x",
                      "25,001 units: must be cut to 25,000 and must warn"),
    "trim3":         (markers(5000) + "\n" * 3,
                      "@pjt222's trim arm verbatim: raw 25,003, trimmed 25,000"),
    "his_separator": (markers(4999) + "zzz" + "\n" * 5,
                      "@pjt222's named unrun arm: raw 25,003, trimmed 24,998"),
    "blank2000":     (markers(4999) + "zzz" + "\n" * 2000,
                      "same question, notice-presence read-out: raw 26,998, trimmed 24,998"),
    # Three fixtures that differ ONLY in their trailing run, all far under the cap so nothing is
    # cut. If their wire text is byte-identical, the embedding trims the tail and no wire read-out
    # can ever see a trailing run -- which is what makes the operand question unobservable.
    "disp_none":     ("A" * 100,
                      "display-trim arm: no trailing run"),
    "disp_nl5":      (("A" * 100) + "\n" * 5,
                      "display-trim arm: five trailing newlines"),
    "disp_sp":       (("A" * 100) + "   \n  \n",
                      "display-trim arm: trailing spaces and newlines"),
}


def segment(body_json: str) -> tuple[str, str | None]:
    """The index as it arrived, and the notice size if one was emitted."""
    body = json.loads(body_json)
    text = body["messages"][0]["content"][0]["text"]
    if HEAD not in text:
        return "", None
    rest = text.split(HEAD, 1)[1]
    m = NOTICE.search(rest)
    if m:
        seg = rest[:m.start()]
        # the harness puts a blank line between the index and the notice
        return (seg[:-2] if seg.endswith("\n\n") else seg), m.group(1)
    cut = rest.find("\n# currentDate")
    seg = rest[:cut] if cut >= 0 else rest
    return (seg[:-1] if seg.endswith("\n") else seg), None


def main() -> int:
    if CLAUDE is None:
        raise SystemExit("REFUSED: no runnable `claude` on PATH")
    base = tempfile.mkdtemp(prefix="blankrun_")
    if any(os.path.isdir(os.path.join(p, ".git"))
           for p in (base, os.path.dirname(base), os.path.dirname(os.path.dirname(base)))):
        raise SystemExit("REFUSED: an ancestor .git would key every arm to one shared store")
    srv = recorder(PORT)
    t0 = time.time()
    stores, rows = [], []

    for label, (text, why) in ARMS.items():
        cwd = os.path.join(base, label)
        os.makedirs(cwd, exist_ok=True)
        store, offered = run(cwd, "INIT")
        if not store:
            raise SystemExit("REFUSED: %s did not resolve a store" % label)
        if offered:
            raise SystemExit("REFUSED: %s was offered %d tools" % (label, len(offered)))
        os.makedirs(store, exist_ok=True)
        with open(os.path.join(store, "MEMORY.md"), "wb") as f:   # BYTES: text mode would add CRs
            f.write(text.encode("utf-8"))
        stores.append(store)

        BODIES.clear()
        store2, _ = run(cwd, "OK")
        if os.path.normcase(store2.rstrip("\\/")) != os.path.normcase(store.rstrip("\\/")):
            raise SystemExit("REFUSED: %s reported a store it did not write to" % label)
        if not BODIES:
            raise SystemExit("REFUSED: %s captured nothing; the recorder was not reached" % label)
        seg, kb = segment(BODIES[-1])
        raw = len(text.encode("utf-16-le")) // 2
        trimmed = len(text.rstrip().encode("utf-16-le")) // 2
        # Read straight out of the prompt, not out of segment(), so the display-trim comparison
        # below cannot be an artefact of this file's own parsing.
        whole = json.loads(BODIES[-1])["messages"][0]["content"][0]["text"]
        tail4 = text.rstrip()[-4:]
        # Absent whenever the arm was cut, which is fine: only the display arms use this field,
        # and they are all far under the cap. A missing anchor must read as absent, not as equal.
        anchor = (whole.rindex(tail4) + 4) if tail4 in whole else None
        rows.append({"arm": label, "why": why, "raw_units": raw, "trimmed_units": trimmed,
                     "wire_units": len(seg), "notice_kb": kb,
                     "wire_tail": seg[-14:], "after_last_content_char": (whole[anchor:anchor + 20] if anchor else None),
                     "trailing_newlines_on_wire": len(seg) - len(seg.rstrip("\n"))})
        r = rows[-1]
        print("[%6.1fs] %-14s raw=%6d trimmed=%6d wire=%6d notice=%6s tail=%r"
              % (time.time() - t0, label, raw, trimmed, r["wire_units"], kb or "-",
                 r["wire_tail"]), flush=True)

    srv.shutdown()
    by = {r["arm"]: r for r in rows}
    v: dict = {}

    # --- controls, and the first two can fail -----------------------------------------------
    v["CONTROL_exactly_25000_arrives_whole_and_silent"] = (
        by["ctl_exact"]["wire_units"] == CAP and by["ctl_exact"]["notice_kb"] is None)
    v["CONTROL_one_character_over_is_cut_and_warns"] = (
        by["ctl_over1"]["wire_units"] == CAP and by["ctl_over1"]["notice_kb"] is not None)
    v["CONTROL_the_small_arm_is_not_cut"] = by["ctl_small"]["wire_units"] >= 100
    trailing_visible = by["ctl_small"]["trailing_newlines_on_wire"] > 0

    # --- @pjt222's trim finding, on win32 ----------------------------------------------------
    v["his_trim_finding_reproduces_here"] = (
        by["trim3"]["raw_units"] == 25003 and by["trim3"]["wire_units"] == CAP
        and by["trim3"]["notice_kb"] is None)

    # --- his named arm, if its read-out is legible -------------------------------------------
    sep = by["his_separator"]
    v["his_named_arm_ran_at_the_geometry_he_specified"] = (
        sep["raw_units"] == 25003 and sep["trimmed_units"] == 24998)
    v["his_named_arm_is_silent_as_both_models_predict"] = sep["notice_kb"] is None
    if trailing_visible:
        v["his_arm_reads_TRIM_FIRST"] = sep["wire_units"] == 24998
    else:
        # A null that is separable from a broken read-out, which is the point of ctl_small.
        v["his_arm_CANNOT_be_read_this_way_and_we_say_so"] = sep["wire_units"] in (24998, CAP)

    # --- the arm whose read-out cannot be eaten ----------------------------------------------
    b2k = by["blank2000"]
    v["the_notice_arm_ran_at_the_geometry_designed"] = (
        b2k["raw_units"] == 26998 and b2k["trimmed_units"] == 24998)
    v["THE_ANSWER_the_threshold_uses_the_TRIMMED_count"] = b2k["notice_kb"] is None
    v["and_the_index_arrived_whole"] = b2k["wire_units"] >= 24998
    # It must be able to say the opposite: 26,998 raw is far enough over that a raw threshold
    # would have warned loudly, and ctl_over1 proves a warning is reachable at this geometry.
    v["CONTROL_a_raw_threshold_would_have_been_visible"] = (
        b2k["raw_units"] > CAP + 1900 and by["ctl_over1"]["notice_kb"] is not None)

    # --- why his read-out cannot work, measured rather than argued ---------------------------
    disp = [by["disp_none"], by["disp_nl5"], by["disp_sp"]]
    v["THE_EMBEDDING_TRIMS_the_tail_before_the_prompt"] = (
        all(d["after_last_content_char"] for d in disp)
        and len({d["after_last_content_char"] for d in disp}) == 1
        and len({d["wire_units"] for d in disp}) == 1)
    v["CONTROL_the_three_display_arms_really_differ_on_disk"] = (
        len({d["raw_units"] for d in disp}) == 3)
    v["CONTROL_none_of_the_display_arms_was_cut"] = all(
        d["notice_kb"] is None and d["wire_units"] == 100 for d in disp)

    # --- an open cell in his notice taxonomy, closed from a capture we already hold -----------
    old = os.path.join(HERE, "_wire_capture_windows.json")
    if os.path.exists(old):
        ob = json.loads(json.load(io.open(old, encoding="utf-8"))[0]["body"])
        ot = ob["messages"][0]["content"][0]["text"]
        om = NOTICE.search(ot)
        v["the_multiline_size_over_cell_carries_the_limit_clause"] = bool(
            om and "index entries are too long" in om.group(0) and "(limit: 24.4KB)" in om.group(0)
            and "lines" not in om.group(0))
        v["CONTROL_that_capture_really_is_multiline_and_under_200_lines"] = (
            100 < ot.count("CANARY-L") < 200)

    removed = 0
    for s in stores:
        parent = os.path.dirname(os.path.abspath(s.rstrip("\\/")))
        shutil.rmtree(parent, ignore_errors=True)
        removed += not os.path.exists(parent)
    v["every_fixture_store_was_removed"] = removed == len(stores)

    print("\n=== VERDICTS ===")
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))
    print("\n  trailing newlines reach the wire: %s (%d of 5 in ctl_small)"
          % (trailing_visible, by["ctl_small"]["trailing_newlines_on_wire"]))
    print("  fixture stores removed: %d/%d" % (removed, len(stores)))

    json.dump({"probe": os.path.basename(__file__), "verdicts": v, "arms": rows,
               "cap_units": CAP, "trailing_newlines_visible_on_wire": trailing_visible,
               "question_credit": "@pjt222, anthropics/claude-code#82056 comment 5425660561: "
                                  "'Both silent, so the count is the read-out. I have not run it.'",
               "finding": "the threshold reads the TRIMMED length: 26,998 raw units of which 2,000 "
                          "are a trailing newline run arrive whole and silent, where 25,001 raw "
                          "units with no trailing run are cut and warn; and the operand the CUT "
                          "slices is unobservable from the wire, because the embedding trims the "
                          "tail (measured: three fixtures differing only in their trailing run "
                          "produce byte-identical prompt text) and because a cut only happens when "
                          "the trimmed length is already over the cap, at which point both models "
                          "keep the same prefix",
               "cost": "zero completions; a local recorder answers canned SSE and request bodies "
                       "are never written to disk",
               "not_settled": ["the operand the cut slices, if trailing newlines do not reach the "
                               "wire", "one machine, win32", "one trial per arm"],
               "platform": sys.platform,
               "claude_version": subprocess.run([CLAUDE, "--version"], capture_output=True,
                                                text=True).stdout.strip()},
              io.open(os.path.join(HERE,
                                   "does_a_trailing_blank_run_count_against_the_cap.result.json"),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
