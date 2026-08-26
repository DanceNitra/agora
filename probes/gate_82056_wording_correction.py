"""Gate the #82056 comment: every figure re-read from its receipt, every quotation from its source.

This comment does four things and each has a different way of going wrong, so the checks are grouped
by that rather than by paragraph.

THE CORRECTION is of our own published numbers, so the risk is overstating what the re-measurement
found. The run was PARTIAL, twenty of twenty-seven trials, and a draft that rounds that up or hides
it must fail. The opposite risk is a correction that quietly keeps the original claim alive: the old
framing called the non-SEE arms wrong answers, the receipt says they went to disk, and a draft still
calling them wrong must fail too.

THE pjt222 SECTION rests on an argument as well as a measurement, and an argument cannot be gated by
recomputation. What can be gated: that his words are byte-present in his live comment, that he really
said he had not run the arm, and that every number came out of the receipt rather than the docstring.

THE ATTRIBUTIONS are checked against the live thread, never against my memory of it.

One deliberate exception to the no-dash rule: the harness's own notice string contains an em dash and
is quoted verbatim. The check strips exactly that quotation and then forbids dashes everywhere else,
so a stray dash cannot hide behind the exemption.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_82056_wording_correction.md")
WORDING = os.path.join(HERE, "does_the_answer_track_the_wording_of_the_ask.result.json")
CD = os.path.join(HERE, "outside_a_repo_cd_moves_your_store.result.json")
UNITS = os.path.join(HERE, "is_the_cap_counted_in_bytes_or_utf16_units.result.json")
BLANK = os.path.join(HERE, "does_a_trailing_blank_run_count_against_the_cap.result.json")
CAPTURE = os.path.join(HERE, "_wire_capture_windows.json")

# The one string allowed to carry an em dash: it is the harness's, quoted verbatim.
QUOTED_NOTICE = "29.4KB (limit: 24.4KB) — index entries are too long"


def thread() -> list:
    r = subprocess.run(["gh", "api", "--paginate",
                        "repos/anthropics/claude-code/issues/82056/comments",
                        "--jq", ".[] | {id:.id,user:.user.login,body:.body}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = []
    for line in (r.stdout or "").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def check(draft: str, w: dict, cd: dict, un: dict, bl: dict, cap_text: str,
          cs: list, readme: str) -> dict:
    v: dict = {}
    by = lambda u: " ".join(c["body"] for c in cs if c["user"] == u)

    # ---- the correction, against today's receipt -------------------------------------------------
    t = w["tally"]
    v["the_see_arm_figure_is_the_receipts"] = (
        t["see"].get("answered_correctly") == 7 and "7 of 7" in draft)
    v["the_in_file_figures_are_the_receipts"] = (
        t["in_file"].get("answered_correctly") == 1
        and t["in_file"].get("went_to_disk") == 6 and "1 of 7" in draft)
    v["the_neutral_figures_are_the_receipts"] = (
        t["neutral"].get("answered_correctly", 0) == 0
        and t["neutral"].get("went_to_disk") == 6 and "0 of 6" in draft)
    total = sum(sum(c.values()) for c in t.values())
    v["CONTROL_the_run_really_was_partial"] = total == 20 and "PARTIAL" in w["status"]
    v["the_draft_states_the_honest_n"] = "Twenty trials" in draft and "stalled" in draft
    v["THE_CORRECTION_no_refusals_were_seen"] = (
        not any(c.get("refused") for c in t.values()) and "no refusals at all" in draft)
    v["the_draft_keeps_the_original_wording_quoted"] = (
        "9/9" in draft and "4/9" in draft and "2/9" in draft and "five refusals" in draft)
    v["it_says_the_mechanism_was_wrong_not_just_the_numbers"] = (
        "the mechanism I gave for it does not" in draft and "went to the file" in draft)
    v["it_no_longer_calls_them_wrong_answers"] = "are not answering incorrectly" in draft
    v["the_ground_truth_is_the_wire_not_arithmetic"] = (
        w["ground_truth"]["last_on_wire"] == 125 and "L0125" in draft
        and "off the wire" in draft)

    # ---- @pjt222's arm, against the receipt (never the docstring) ---------------------------------
    arms = {a["arm"]: a for a in bl["arms"]}
    ex, ov, tr = arms["ctl_exact"], arms["ctl_over1"], arms["trim3"]
    sep, b2k = arms["his_separator"], arms["blank2000"]
    v["the_boundary_pair_is_the_receipts"] = (
        ex["wire_units"] == 25000 and ex["notice_kb"] is None
        and ov["raw_units"] == 25001 and ov["wire_units"] == 25000 and ov["notice_kb"] is not None
        and "25,000 units arrive whole and silent" in draft
        and "25,001 is cut back to 25,000 and warns" in draft)
    v["the_trim_replication_is_the_receipts"] = (
        tr["raw_units"] == 25003 and tr["wire_units"] == 25000 and tr["notice_kb"] is None
        and "25,003 units on disk arriving whole at 25,000" in draft)
    v["his_named_arm_is_the_receipts"] = (
        sep["raw_units"] == 25003 and sep["trimmed_units"] == 24998
        and sep["wire_units"] == 24998 and sep["notice_kb"] is None
        and "raw 25,003, trimmed 24,998" in draft and "24,998 units on the wire" in draft)
    disp = [arms["disp_none"], arms["disp_nl5"], arms["disp_sp"]]
    v["the_display_arms_are_the_receipts"] = (
        sorted(d["raw_units"] for d in disp) == [100, 105, 107]
        and len({d["after_last_content_char"] for d in disp}) == 1
        and "100, 105 and 107 units on disk" in draft)
    v["the_2000_newline_arm_is_the_receipts"] = (
        b2k["raw_units"] == 26998 and b2k["trimmed_units"] == 24998
        and b2k["notice_kb"] is None and "raw 26,998, trimmed 24,998" in draft)
    v["CONTROL_the_probe_itself_passed_every_verdict"] = all(bl["verdicts"].values())
    # The argument is not gateable by arithmetic, but its SCOPE is: it must say "from the wire".
    # The scope has to travel WITH the universal, in one phrase. An earlier version of this check
    # looked for "unobservable" and "on the wire" separately, and passed a draft that had dropped
    # the scope, because "on the wire" occurs five other times in this comment.
    v["the_universal_is_scoped_to_the_wire"] = (
        "unobservable from the wire for every input" in draft
        and not re.search(r"unobservable(?! from the wire) for every input", draft)
        and "on this build" in draft)
    v["the_zero_cost_claim_is_stated"] = "Zero completions" in draft

    # ---- the taxonomy cell, from the capture itself -----------------------------------------------
    v["the_quoted_notice_is_byte_present_in_our_capture"] = QUOTED_NOTICE in cap_text
    v["that_capture_is_multiline_and_under_200_lines"] = 100 < cap_text.count("CANARY-L") < 200
    v["and_the_draft_quotes_it_verbatim"] = QUOTED_NOTICE in draft

    # ---- the cd replication -----------------------------------------------------------------------
    v["cd_receipt_passed"] = all(cd["verdicts"].values())
    tails = {a["arm"]: os.path.basename(os.path.dirname(
        a["store"].rstrip("\\/"))).split("Temp-")[-1] for a in cd["arms"]}
    # Rule 12: assert the extractor found its target. "projects" here would mean one dirname too
    # many, and every comparison below would then be true of the wrong string.
    v["CONTROL_the_slug_extractor_found_slugs"] = all(
        s.startswith("cdstore-") for s in tails.values())
    v["the_in_repo_pair_really_shares_a_store"] = tails["repo root"] == tails["repo subdir"]
    v["the_out_of_repo_pair_really_does_not"] = tails["non-repo root"] != tails["non-repo subdir"]
    v["all_four_slug_tails_in_the_draft_are_the_receipts"] = all(
        s in draft for s in tails.values())

    # ---- the unit note ------------------------------------------------------------------------------
    rows = {r["label"]: r for r in un["rows"]}
    cjk, emo = rows["cjk_200x125"], rows["emoji_200x125"]
    v["the_cjk_bytes_and_units_are_the_receipts"] = (
        f"{cjk['bytes']:,}" in draft and f"{cjk['utf16_units']:,}" in draft)
    v["the_cjk_ratio_is_recomputed"] = (
        abs(cjk["bytes"] / cjk["utf16_units"] - 2.44) < 0.01 and "2.44x" in draft)
    v["the_cjk_cut_line_is_the_receipts"] = (
        cjk["last_line_loaded"] == 198 and "line 198" in draft)
    v["the_emoji_figures_are_the_receipts"] = (
        f"{emo['bytes']:,}" in draft and f"{emo['utf16_units']:,}" in draft
        and emo["last_line_loaded"] == 115 and "line 115" in draft)
    v["his_README_really_says_25KB"] = "200 lines / 25KB" in readme
    v["and_he_said_it_again_in_the_thread_today"] = "200 lines / 25KB" in by("tonydzi")
    v["we_do_not_present_the_unit_point_as_new"] = "not news" in draft

    # ---- attribution, from the live thread ----------------------------------------------------------
    p = by("pjt222")
    v["pjt222_really_named_that_arm"] = "4,999 five-char markers" in p and "`zzz`" in p
    v["pjt222_really_said_he_had_not_run_it"] = "I have not run it" in p
    v["pjt222_really_left_the_taxonomy_cell_open"] = (
        "size-over" in p and "lines-under" in p and "multi-line" in p)
    v["JhouCode_really_reported_the_cd_asymmetry"] = "into a subdirectory keeps the same store" in by(
        "JhouCode")
    v["pjt222_really_hit_it_as_an_instrument_bug"] = "keyed to the git repository" in p
    v["tonydzi_really_published_the_diet"] = "always-loaded-diet" in by("tonydzi")

    # ---- house style ---------------------------------------------------------------------------------
    stripped = draft.replace(QUOTED_NOTICE, "")
    v["no_em_or_en_dash_outside_the_quoted_notice"] = not (
        "—" in stripped or "–" in stripped or " -- " in stripped)
    v["CONTROL_the_exemption_is_not_a_hole"] = "—" in QUOTED_NOTICE
    v["no_personal_name"] = not re.search(r"[Rr]astislav|Draho[sš]", draft)
    v["every_at_handle_is_a_real_participant"] = all(
        h in {c["user"] for c in cs} for h in set(re.findall(r"@([A-Za-z0-9]+)", draft)))
    v["the_AI_disclosure_is_present"] = "Written with AI assistance" in draft
    v["length_is_reasonable"] = 600 < len(draft.split()) < 1100

    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "humanizer_receipt.py"),
                        "check", DRAFT], capture_output=True, text=True)
    v["the_humanizer_SKILL_ran_on_THESE_bytes"] = r.returncode == 0
    return v


def main() -> int:
    draft = io.open(DRAFT, encoding="utf-8").read()
    w = json.load(io.open(WORDING, encoding="utf-8"))
    cd = json.load(io.open(CD, encoding="utf-8"))
    un = json.load(io.open(UNITS, encoding="utf-8"))
    bl = json.load(io.open(BLANK, encoding="utf-8"))
    cap_text = json.loads(json.load(io.open(CAPTURE, encoding="utf-8"))[0]["body"])[
        "messages"][0]["content"][0]["text"]
    try:
        with urllib.request.urlopen(
                "https://raw.githubusercontent.com/tonydzi/always-loaded-diet/main/README.md",
                timeout=60) as r:
            readme = r.read().decode("utf-8", "replace")
    except Exception as e:
        raise SystemExit(f"REFUSED: could not fetch his README ({e}); quoting it would be unchecked")
    cs = thread()
    if not cs:
        raise SystemExit("REFUSED: could not read the live thread")

    v = check(draft, w, cd, un, bl, cap_text, cs, readme)
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    passed = sum(1 for x in v.values() if x)
    print(f"\n  {passed}/{len(v)} checks, {len(draft.split())} words, {len(cs)} comments read")

    if "--mutate" in sys.argv:
        print("\n  MUTATION SELF-TEST")
        muts = [("inflate n", "Twenty trials", "Twenty-seven trials"),
                ("hide the stall", "stalled", "completed"),
                ("see arm", "7 of 7", "8 of 8"),
                ("neutral arm", "0 of 6", "2 of 6"),
                ("revive the accuracy framing", "are not answering incorrectly",
                 "are answering incorrectly"),
                ("drop the mechanism retraction", "the mechanism I gave for it does not",
                 "the mechanism I gave for it holds"),
                ("drop the no-refusals correction", "no refusals at all", "a couple of refusals"),
                ("boundary pair", "25,001 is cut back to 25,000 and warns",
                 "25,002 is cut back to 25,000 and warns"),
                ("trim replication", "25,003 units on disk arriving whole at 25,000",
                 "25,009 units on disk arriving whole at 25,000"),
                ("his named arm", "raw 25,003, trimmed 24,998", "raw 25,003, trimmed 24,997"),
                ("display arms", "100, 105 and 107 units on disk",
                 "100, 105 and 108 units on disk"),
                ("the 2000-newline arm", "raw 26,998, trimmed 24,998",
                 "raw 26,999, trimmed 24,998"),
                ("unscope the universal", "unobservable from the wire for every input",
                 "unobservable for every input"),
                ("corrupt the quoted notice", QUOTED_NOTICE,
                 QUOTED_NOTICE.replace("29.4", "29.5")),
                ("cd slug", "cdstore-jntsww91-plain-sub-deeper", "cdstore-jntsww91-plain-sub"),
                ("cjk ratio", "2.44x", "3.44x"),
                ("cjk bytes", "61,600", "61,700"),
                ("emoji cut", "line 115", "line 125"),
                ("claim the unit point as new", "not news", "a new finding"),
                ("drop the disclosure", "Written with AI assistance", "Written by hand"),
                ("em dash", "before anything else.", "before anything else —.")]
        caught = 0
        for label, a, b in muts:
            if a not in draft:
                print(f"    SKIP   {label}: anchor absent, mutation vacuous")
                continue
            mv = check(draft.replace(a, b, 1), w, cd, un, bl, cap_text, cs, readme)
            broke = [k for k in v if v[k] and not mv.get(k)]
            caught += bool(broke)
            print(f"    {'CAUGHT' if broke else 'MISSED'}  {label}"
                  f"{' -> ' + broke[0] if broke else ''}")
        print(f"    {caught}/{len(muts)} mutations caught")
        return 0 if (passed == len(v) and caught == len(muts)) else 1
    return 0 if passed == len(v) else 1


if __name__ == "__main__":
    sys.exit(main())
