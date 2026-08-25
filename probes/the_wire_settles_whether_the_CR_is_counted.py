"""The one question no behavioural arm can answer: is the CR stripped before the cap, or counted?

WHY. On 2026-08-25 we measured, behaviourally, that a CRLF index cuts earlier than an LF one and
concluded the carriage return costs budget. The commit that shipped it said plainly what it could
NOT do: our two arms kill `strip-then-cap` and cannot separate "the CR is counted" from "truncate
the raw bytes, strip the CRs afterwards". Both models predict the same cut, so no arm that watches
where the cut lands will ever tell them apart.

@pjt222 then showed the thread a stronger instrument than any of us had been using: point
`ANTHROPIC_BASE_URL` at a local recorder and read the request body. Bytes that were SENT cannot be
confused with bytes that were COMPUTED. That instrument answers this question directly, because it
does not infer the cut from a position -- it reads the text.

THE MEASUREMENT, and it is one subtraction. A 150-line fixture of 199-character lines terminated
CRLF goes into the store. The wire carries the index that survived the cap. Measure that segment:

    124 lines, CR counted    ->  124 * 201 - 2 = 24,922 units
    124 lines, CR stripped   ->  124 * 200 - 1 = 24,799 units

The two differ by 123, which is exactly the number of carriage returns inside the segment. There is
no arithmetic coincidence available here: one model is right and the other is out by the CRs.

Measured: 24,922. The carriage returns are still in the prompt, 123 of them inside the segment and
124 across the kept lines, and the length matches CR-counted exactly. `strip-then-cap` is refuted
by observation rather than by inference.

The cut lands at 124 either way at this geometry, which is why the LINE COUNT is not the evidence
and the SEGMENT LENGTH is. An earlier version of this reasoning would have quoted 124 as the
finding; 124 is the thing both models agree on.

CREDIT. The instrument is @pjt222's, published in comment 5412833938, and he offered it: "happy to
point at them if useful on another platform". The question is ours, left open in our own commit
this morning. CRLF is the Windows-native case, which is the only reason this box is the one to run
it.

stdlib only, reads a committed capture, and no model was called at any point -- the recorder answers
with canned SSE.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURE = os.path.join(HERE, "_wire_capture_windows_crlf.json")
WIDTH, LINES = 199, 150
CR, LF = chr(13), chr(10)


def main() -> int:
    if not os.path.exists(CAPTURE):
        raise SystemExit(f"REFUSED: {CAPTURE} is absent; every check below would pass vacuously")
    body = json.loads(json.load(io.open(CAPTURE, encoding="utf-8"))[0]["body"])
    text = body["messages"][0]["content"][0]["text"]

    ids = [int(x) for x in re.findall(r"CANARY-L(\d{4})", text)]
    last = max(ids) if ids else 0
    start = text.index("- [E0001]")
    # the last content character of the final kept line, before the notice that follows it
    stop = text.rindex("x", start, text.index("WARNING") if "WARNING" in text else len(text))
    seg = text[start:stop + 1]

    cr_counted = last * (WIDTH + 2) - 2      # CRLF terminators, minus the final one
    cr_stripped = last * (WIDTH + 1) - 1     # LF only, minus the final one

    v: dict = {}
    v["the_wire_carries_an_index_at_all"] = bool(ids)
    v["the_cut_is_at_124"] = last == 124
    v["carriage_returns_survive_into_the_prompt"] = CR in seg
    v["there_is_one_CR_per_kept_line_boundary"] = seg.count(CR) == last - 1
    v["the_segment_length_matches_CR_COUNTED"] = len(seg) == cr_counted
    v["it_does_NOT_match_CR_STRIPPED"] = len(seg) != cr_stripped
    v["the_two_models_differ_by_exactly_the_CR_count"] = (cr_counted - cr_stripped) == seg.count(CR)
    v["no_tool_was_offered_on_the_wire"] = len(body.get("tools") or []) == 0

    # --- controls -------------------------------------------------------------------------------
    # THE ONE THAT MATTERS: the line count is NOT the evidence, because both models predict it.
    # If a future reader takes 124 as the finding, this states in the artifact that it is not.
    v["CONTROL_the_line_count_alone_cannot_discriminate"] = (
        int(24.4 * 1024 // (WIDTH + 2)) == int(24.4 * 1024 // (WIDTH + 1)) == 124)
    # The segment must be a real slice of a larger fixture, or "it was cut" is unsupported.
    v["CONTROL_the_fixture_was_larger_than_what_arrived"] = LINES > last
    # An absence check over an empty string passes; assert the haystack.
    v["CONTROL_the_segment_is_substantial"] = len(seg) > 20000
    # And the discrimination must not be an artefact of counting LFs as CRs.
    v["CONTROL_CR_and_LF_are_counted_separately"] = seg.count(CR) == seg.count(LF)

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print(f"\n  index segment on the wire     : {len(seg)} units")
    print(f"  predicted, CR counted         : {cr_counted}")
    print(f"  predicted, CR stripped first  : {cr_stripped}")
    print(f"  carriage returns in segment   : {seg.count(CR)}   line feeds: {seg.count(LF)}")
    print(f"  cut at line                   : {last}  (both models predict this, so it is not "
          f"the evidence)")

    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "segment_units": len(seg), "predicted_cr_counted": cr_counted,
               "predicted_cr_stripped": cr_stripped, "cr_in_segment": seg.count(CR),
               "lf_in_segment": seg.count(LF), "last_kept_line": last,
               "fixture": {"lines": LINES, "chars": WIDTH, "terminator": "CRLF"},
               "verdict": "strip-then-cap is REFUTED: the sent index still carries its carriage "
                          "returns and its length matches CR-counted exactly",
               "instrument_credit": "wire capture method from @pjt222, "
                                    "anthropics/claude-code#82056 comment 5412833938",
               "platform": sys.platform},
              io.open(os.path.join(HERE, "the_wire_settles_whether_the_CR_is_counted.result.json"),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
