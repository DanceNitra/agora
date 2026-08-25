"""@pjt222 read the wire on linux and found the cap stated in the prompt. Same read, on Windows.

WHY. On anthropics/claude-code#82056 (2026-08-25) @pjt222 stopped asking the model anything and
captured the request body instead, by pointing `ANTHROPIC_BASE_URL` at a local recorder. He found
that an over-cap index puts the limit into the prompt itself:

    > WARNING: MEMORY.md is 29.4KB (limit: 24.4KB) -- index entries are too long. Only part of it
      was loaded. Keep index entries to one line under ~200 chars; move detail into topic files.

That is the strongest instrument anyone has brought to the thread, because bytes that were SENT
cannot be confused with bytes that were COMPUTED -- it is not subject to his own reconstruction
ruler at all. And he flagged the one thing it could not settle: "one build, one platform... the
notice text is exactly the kind of string that gets reworded."

We are the Windows box. This is that check.

IT ALSO SETTLES SOMETHING ABOUT US. He corrected the thread that `--tools ""` is not tool-zero:
one tool, `advisor` (type `advisor_20260301`), survives it when `advisorModel` is set in
settings.json. Every cap probe of ours asserts tool-zero -- and asserts it from the CLI's OWN init
event, not from the wire. That is the weaker of the two surfaces and we published the stronger
wording. The wire settles it here, and it settles it in his favour on the method even though our
box comes out clean: this machine has no `advisorModel`, and the captured request carries zero
tools. His caveat is real and machine-dependent, exactly as he said.

WHAT IS MEASURED, all of it off one captured request and no model call at all:

  1. the notice is present, and its text is byte-identical to the one he published
  2. it rides in `messages[0].content[0]`, inline, not in the system block and not as an attachment
  3. the tools array on the wire is empty
  4. THE CUT ITSELF: count the CANARY tokens that actually crossed. 150 lines went in at 201 units
     each; the wire carries a contiguous 1..124, which is `floor(24.4 * 1024 / 201)` and the same
     number he measured on linux-x64.

The fixture geometry matches his by coincidence rather than design (150 lines, 201 units), which
makes this a clean replication and is worth saying rather than dressing up as independence.

stdlib only. Reads a committed capture; the recorder that produced it is described in the docstring
of `capture()` below so anyone can reproduce it on a third platform.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURE = os.path.join(HERE, "_wire_capture_windows.json")

# Verbatim from @pjt222's comment 5412833938, so a reworded string fails LOUDLY rather than
# quietly passing a looser match.
HIS_NOTICE = ("WARNING: MEMORY.md is 29.4KB (limit: 24.4KB) — index entries are too long. "
              "Only part of it was loaded. Keep index entries to one line under ~200 chars; "
              "move detail into topic files.")
WIDTH, LINES = 200, 150          # the fixture: 200 chars + LF = 201 units per line
PER = WIDTH + 1


def capture() -> str:
    """How the committed capture was produced, so this is reproducible rather than trusted.

        1. run a local HTTP server that records POST bodies and answers canned SSE
        2. ANTHROPIC_BASE_URL=http://127.0.0.1:<port> ANTHROPIC_API_KEY=x
        3. write a 150 x 200-char MEMORY.md into the project's auto-memory store
        4. claude -p --output-format stream-json --verbose --tools "" --strict-mcp-config "..."

    Only the BODY is recorded; headers are never touched, so no credential can ride along.
    """
    return capture.__doc__


def main() -> int:
    if not os.path.exists(CAPTURE):
        raise SystemExit(f"REFUSED: {CAPTURE} is absent; every assertion below would pass "
                         f"vacuously over an empty file")
    reqs = json.load(io.open(CAPTURE, encoding="utf-8"))
    body = json.loads(reqs[0]["body"])
    text = body["messages"][0]["content"][0]["text"]
    blob = json.dumps(body, ensure_ascii=False)

    v: dict = {}
    v["exactly_one_request_was_captured"] = len(reqs) == 1
    v["the_notice_is_present_on_the_wire"] = HIS_NOTICE in text
    v["it_is_byte_identical_to_the_one_he_published"] = HIS_NOTICE in text
    v["it_rides_in_messages_0_content_0"] = "MEMORY.md is" in text
    v["it_is_NOT_in_the_system_block"] = "MEMORY.md is" not in json.dumps(
        body.get("system"), ensure_ascii=False)
    v["the_tools_array_on_the_wire_is_empty"] = len(body.get("tools") or []) == 0

    ids = [int(x) for x in re.findall(r"CANARY-L(\d{4})", text)]
    last = max(ids) if ids else 0
    v["the_wire_carries_canaries_at_all"] = bool(ids)
    v["they_are_contiguous_from_one"] = ids == list(range(1, last + 1))
    v["the_cut_is_at_124"] = last == 124
    v["124_is_floor_of_the_stated_cap_over_the_line_width"] = int(24.4 * 1024 // PER) == 124
    v["that_is_the_number_he_measured_on_linux"] = last == 124

    # --- controls ---------------------------------------------------------------------------
    # An absence check over an empty haystack passes. Assert the haystack.
    v["CONTROL_the_prompt_is_large_enough_to_hold_the_index"] = len(text) > 20000
    # And the cut must be a REAL cut: the fixture had more lines than crossed.
    v["CONTROL_the_fixture_was_larger_than_what_arrived"] = LINES > last
    # If the notice matcher were broken it would report absent; prove it can find a string we
    # know is there for an unrelated reason.
    v["CONTROL_the_matcher_finds_an_unrelated_known_string"] = "CANARY-L0001" in text

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print(f"\n  canaries on the wire : {len(ids)}  (1..{last}, contiguous={v['they_are_contiguous_from_one']})")
    print(f"  fixture              : {LINES} lines x {WIDTH} chars = {LINES * PER} units")
    print(f"  last kept line {last}   : content ends at {last * PER - 1}, LF at {last * PER}")
    print(f"  floor(24.4*1024/{PER}) : {int(24.4 * 1024 // PER)}")

    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "canaries_on_wire": len(ids), "last_kept_line": last,
               "notice_verbatim": HIS_NOTICE,
               "tools_on_wire": len(body.get("tools") or []),
               "fixture": {"lines": LINES, "chars": WIDTH, "units_per_line": PER,
                           "total_units": LINES * PER},
               "platform": sys.platform,
               "replication_of": "anthropics/claude-code#82056 comment 5412833938 (@pjt222), "
                                 "linux-x64, same fixture geometry by coincidence"},
              io.open(os.path.join(HERE, "the_cap_is_stated_in_the_prompt_on_windows_too.result.json"),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
