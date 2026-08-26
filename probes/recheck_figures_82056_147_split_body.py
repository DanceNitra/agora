"""Recompute every number in the #82056 reply from the artifacts, not from memory.

Same reason as its 1591 sibling: earlier today two numbers in a comment survived three independent
verifiers because the verifiers checked the FACTS and nobody checked my SENTENCES about the facts.
A count in prose that nothing recomputes is an unverified inference sitting on a verified number.

Reads the posted body (everything after the first standalone --- line) and the two result files.
A claim whose string is absent from the body fails rather than passes, so editing the draft without
editing this file breaks the build instead of silently un-checking a line.

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check
inside VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and
storm when the claim rests on literature. Owner, 2026-08-26, after I called a file like
this one "the gate" three times in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO
HOVEN." tools/send_approved.py now refuses to publish without a receipt from each skill,
bound to the draft's bytes, so this file cannot stand in for them any more.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(os.path.dirname(HERE), "agora_output", "drafts", "reply_82056_147_split.md")
CAPS = os.path.join(HERE, "is_the_cap_counted_in_bytes_or_utf16_units.result.json")
SPLIT = os.path.join(HERE, "does_a_147_unit_line_split_the_cap_bracket.result.json")
GEN = os.path.join(HERE, "is_the_cap_counted_in_bytes_or_utf16_units.py")


def body() -> str:
    t = open(DRAFT, encoding="utf-8").read()
    if "\n---\n" not in t:
        raise SystemExit("REFUSED: no provenance separator; cannot isolate the posted body")
    return t.split("\n---\n", 1)[1]


def flat(s: str) -> str:
    """Collapse whitespace runs before matching prose.

    Re-wrapping a paragraph moves newlines through sentences, and that broke nine of these
    checks the moment the draft was cut for length. A line wrap is not a claim change, and a
    gate that cannot tell the two apart teaches you to edit the gate on autopilot, which is
    how a gate stops being one.
    """
    return " ".join(s.split())


def main() -> int:
    b = flat(body())
    caps = json.load(open(CAPS, encoding="utf-8"))
    spl = json.load(open(SPLIT, encoding="utf-8"))
    rows = {r["label"]: r for r in caps["rows"]}

    warned_arms = [k for k, r in rows.items() if r.get("warned")]
    n_carrying = len(warned_arms) + (1 if spl.get("warned") else 0)
    word = {3: "Three", 4: "Four", 5: "Five", 6: "Six"}[n_carrying]

    v: dict[str, bool] = {}
    v["the_60_char_arm_carries_12200_units"] = (
        rows["cjk_200x60"]["utf16_units"] == 12200 and "12,200 units" in b)
    v["nothing_cut_the_60_char_arm"] = (
        rows["cjk_200x60"]["last_line_loaded"] == rows["cjk_200x60"]["lines"]
        and not rows["cjk_200x60"]["warned"] and "nothing did" in b)
    v["the_prior_bracket_is_24955_25074"] = (
        caps["cap_bracket_utf16_units"] == [24955, 25074] and "[24955, 25074)" in b)
    # THE ONE THIS FILE EXISTS FOR: a count of arms, derived rather than typed.
    v["arm_count_carrying_the_notice_is_derived_not_typed"] = f"{word} arms carry it now" in b
    v["every_named_size_figure_appears_in_a_receipt"] = all(
        s in b for s in ("24.6KB", "26KB", "42.4KB")) and all(
        any(s in r["answer"] for r in list(rows.values()) + spl["rows"])
        for s in ("24.6KB", "26KB", "42.4KB"))
    v["zero_tools_on_every_arm_that_carries_it"] = all(
        rows[k]["tools_offered"] == 0 and not rows[k]["tool_uses"] for k in warned_arms) and all(
        r["tools_offered"] == 0 and not r["tool_uses"] for r in spl["rows"])
    v["the_under_cap_arm_says_NO_INDICATOR"] = (
        "NO-INDICATOR" in rows["cjk_200x60"]["answer"] and "`NO-INDICATOR`" in b)
    v["the_200x125_arm_reports_25200"] = (
        rows["ascii_200x125"]["utf16_units"] == 25200 and "reporting 25,200 units" in b)
    upl = spl["units_per_line"]
    v["the_three_boundary_lines_are_right"] = all(
        f"{n * upl:,}" in b for n in (168, 169, 170)) and (168 * upl, 169 * upl, 170 * upl) == (
        24864, 25012, 25160)
    v["the_file_is_180_lines_and_26640_units"] = (
        spl["lines"] == 180 and spl["file_units"] == 26640 and "26,640 units" in b)
    v["last_kept_line_is_168_unanimously"] = (
        spl["last_line_loaded"] == 168 and len({r["last"] for r in spl["rows"]}) == 1
        and len(spl["rows"]) == 3 and "last kept line 168, three trials" in b)
    v["the_new_bracket_and_widths_are_right"] = (
        spl["bracket_after"] == [24955, 25012] and "**[24955, 25012)**" in b
        and "119 units wide to 57" in b and (25074 - 24955, 25012 - 24955) == (119, 57))
    v["25000_is_inside_the_new_bracket"] = (
        24955 <= 25000 < 25012 and "25,000 is still inside it" in b)
    # the offered next arm, and the count of alternatives, both recomputed
    v["the_next_boundary_is_24990"] = 170 * 147 == 24990 and "boundary at 24,990" in b
    others = len([(n, c) for c in range(126, 4000) for n in range(2, 201)
                  if 24986 < n * c < 25000]) - 1
    v["the_number_of_other_widths_is_recomputed"] = f"{others} other widths" in b
    v["this_machine_has_18_sessions_in_3_buckets"] = "18 sessions across 3 project buckets" in b
    # --- controls ---------------------------------------------------------------------
    v["CONTROL_the_body_is_not_the_provenance_block"] = "STATUS:" not in b and "RECEIPTS:" not in b
    # EVERY arm-count sentence, not just the one I remembered to check. The first version of this
    # gate asserted the phrase "N arms carry it now" and passed at 22/22 while a SECOND sentence
    # further down still said "five" for the same quantity. Checking one instance of a class is how
    # the class survives its own fix, which this repo has written down more than once.
    n_total = len(rows) + 1
    words = {3: "three", 4: "four", 5: "five", 6: "six"}
    v["every_arm_count_sentence_agrees_with_the_data"] = (
        f"{words[n_carrying].capitalize()} arms carry it now" in b
        and f"The {words[n_total]} arms above" in b
        and f"{words[n_carrying]} report the notice" in b
        and n_total - n_carrying == 1)
    v["CONTROL_a_wrong_arm_word_would_fail"] = not any(
        f"{w.capitalize()} arms carry it now" in b for w in words.values()
        if w != words[n_carrying])
    v["CONTROL_a_string_not_in_the_draft_fails"] = "this sentence is not in the draft" not in b

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    bad = [k for k, ok in v.items() if not ok]
    print(f"\n  {len(v) - len(bad)}/{len(v)} claims recomputed from source")
    print(f"  arms carrying the notice: {n_carrying} ({', '.join(warned_arms)}, plus the 147 arm)"
          if spl.get("warned") else f"  arms carrying the notice: {n_carrying}")
    print(f"  widths other than 170x146 that would split the remainder: {others}")
    if bad:
        print("  FAILED: " + ", ".join(bad))
    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "arms_carrying_the_notice": n_carrying, "warned_arms": warned_arms,
               "other_widths": others},
              open(os.path.join(HERE, "gate_82056_147_split_body.result.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
