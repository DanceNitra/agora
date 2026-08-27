"""RECHECK THE FIGURES in #82056 comment: every figure re-read from its receipt, every quotation from its source.

The comment does four things and each fails differently, so the checks are grouped that way.

THE CORRECTION retracts figures I published with no artifact behind them. The way to get this wrong
twice is to correct them with figures that also have nothing behind them, and that nearly happened:
the first version of this gate passed a table assembled BY HAND from the console output of a run
that had stalled at 20 of 27, because the receipt on disk carried keys the probe does not write
(`raw_outcome`, `answer_preview`, `why_partial`) and its mtime preceded the .py by 73 seconds. So
this gate now asserts the receipt was EMITTED BY ITS OWN PROBE: the key set must be exactly what
`json.dump` in that file writes, and every table cell is read from `tally`, never from prose.

The opposite risk is a retraction that keeps the old claim alive. The published mechanism was
accuracy; the receipt says the non-SEE arms mostly announce a file read. A draft still calling them
wrong answers must fail, and so must one that hides the two timeouts or the scorer gap.

THE pjt222 SECTION rests on measurements plus one argument. The argument cannot be gated by
recomputation, so what is gated is that the two leading-run arms have partners, that each pair is a
byte comparison rather than a description, and that his own words are byte-present in his live
comment. An earlier draft carried a universal ("unobservable from the wire for every input") that an
adversarial pass refuted with a leading whitespace run; there is a check below that the universal is
gone and a mutation that puts it back.

THE ATTRIBUTIONS are read from the live thread, never from memory of it.

THE ROOM MOVED WHILE THIS WAS BEING MEASURED. @yacb2 ran the same arm on darwin and published the
same conclusion 34 minutes before the draft existed, with a control this box did not have. The
checks below require the draft to credit him FIRST and to frame ours as a second route; two
mutations put the priority claim back.

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check
inside VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and
storm when the claim rests on literature. Owner, 2026-08-26, after I called a file like
this one "the gate" three times in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO
HOVEN." tools/send_approved.py now refuses to publish without a receipt from each skill,
bound to the draft's bytes, so this file cannot stand in for them any more.
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
WORDING_PY = os.path.join(HERE, "does_the_answer_track_the_wording_of_the_ask.py")
CD = os.path.join(HERE, "outside_a_repo_cd_moves_your_store.result.json")
UNITS = os.path.join(HERE, "is_the_cap_counted_in_bytes_or_utf16_units.result.json")
BLANK = os.path.join(HERE, "does_a_trailing_blank_run_count_against_the_cap.result.json")

QUOTED_NOTICE = "29.4KB (limit: 24.4KB) — index entries are too long"
# Exactly the keys `does_the_answer_track_the_wording_of_the_ask.py` writes on a real run.
EMITTED_KEYS = {"probe", "verdicts", "ground_truth", "asks", "n_per_arm", "tally", "rows",
                "published_claim", "fixture", "platform"}


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


def check(draft: str, w: dict, cd: dict, un: dict, bl: dict, cs: list, readme: str,
          his_capture: str) -> dict:
    v: dict = {}
    by = lambda u: " ".join(c["body"] for c in cs if c["user"] == u)

    # ---- the receipt must have been emitted by its own probe ------------------------------------
    v["THE_RECEIPT_WAS_EMITTED_BY_THE_PROBE"] = set(w) == EMITTED_KEYS
    v["CONTROL_the_receipt_is_newer_than_the_probe"] = (
        os.path.getmtime(WORDING) > os.path.getmtime(WORDING_PY))
    v["CONTROL_every_arm_has_all_five_categories"] = all(
        len(c) == 5 for c in w["tally"].values())

    # ---- the correction, every cell read from the tally ------------------------------------------
    t = w["tally"]
    # EVERY occurrence, not the first. "27 trials" appears twice, so a presence check passed a
    # mutation that changed one of them to "20 trials" -- the same occurrence-vs-presence defect
    # that has now survived two of my gates.
    trial_counts = re.findall(r"(\d+) trials", draft)
    v["the_run_was_complete"] = (
        w["n_per_arm"] == 9 and len(w["rows"]) == 27
        and trial_counts and set(trial_counts) == {"27"})
    v["the_see_row_is_the_receipts"] = (
        t["see"]["answered_correctly"] == 9 and "9 of 9" in draft)
    v["the_in_file_row_is_the_receipts"] = (
        t["in_file"]["answered_correctly"] == 0 and t["in_file"]["went_to_disk"] == 6
        and t["in_file"]["answered_wrongly"] == 3
        and "| 0 of 9 | 6 | 3 | 0 |" in draft)
    v["the_neutral_row_is_the_receipts"] = (
        t["neutral"]["answered_correctly"] == 0 and t["neutral"]["went_to_disk"] == 5
        and t["neutral"]["answered_wrongly"] == 2 and t["neutral"]["timeout"] == 2
        and "| 0 of 9 | 5 | 2 | 2 |" in draft)
    v["THE_CORRECTION_no_refusals_in_the_receipt"] = (
        not any(c["refused"] for c in t.values()) and "no refusals at all in 27 trials" in draft)
    v["it_says_which_published_cells_failed_to_reproduce"] = (
        w["published_claim"]["see"] == "9/9" and w["published_claim"]["in_file"] == "4/9"
        and w["published_claim"]["neutral"] == "2/9"
        and "Only the first cell reproduces" in draft
        and "4/9 and 2/9 do not" in draft)
    v["the_draft_quotes_the_published_claim_exactly"] = (
        "9/9" in draft and "4/9" in draft and "2/9" in draft and "five refusals" in draft
        and "5387228275" in w["published_claim"]["where"])
    v["it_no_longer_calls_them_wrong_answers"] = (
        "announce that they are going to read the file" in draft
        and "not moving reading accuracy" in draft)
    v["the_ground_truth_is_the_wire_not_arithmetic"] = (
        w["ground_truth"]["last_on_wire"] == 125 and "L0125" in draft
        and "off the wire" in draft)
    # THE LIMITS. The receipt records a failing verdict and a scorer gap; both must be in the draft.
    v["THE_TIMEOUTS_ARE_DISCLOSED"] = (
        w["verdicts"]["no_trial_timed_out"] is False
        and "timed out at 90 seconds" in draft and "really 7 usable" in draft)
    v["THE_SCORER_GAP_IS_DISCLOSED"] = (
        any(r["outcome"] == "answered_wrongly" and "Tool Use: Bash" in r["answer"]
            for r in w["rows"])
        and "Tool Use: Bash" in draft and "a floor rather than a count" in draft)
    v["the_L0200_answers_are_real"] = (
        sum(1 for r in w["rows"] if "CANARY-L0200" in r["answer"]) >= 2
        and "CANARY-L0200" in draft)
    v["the_notice_causation_is_not_asserted"] = "I cannot separate the notice" in draft

    # ---- @pjt222's arms, against the receipt (never the docstring) --------------------------------
    a = {x["arm"]: x for x in bl["arms"]}
    v["the_boundary_pair_is_the_receipts"] = (
        a["ctl_exact"]["wire_units"] == 25000 and a["ctl_exact"]["notice_kb"] is None
        and a["ctl_over1"]["raw_units"] == 25001 and a["ctl_over1"]["wire_units"] == 25000
        and a["ctl_over1"]["notice_kb"] is not None
        and "25,000 units arrive whole and silent" in draft
        and "25,001 is cut back to 25,000 and warns" in draft)
    v["the_trim_replication_is_the_receipts"] = (
        a["trim3"]["raw_units"] == 25003 and a["trim3"]["wire_units"] == 25000
        and a["trim3"]["notice_kb"] is None
        and "25,003 units on disk arriving whole at 25,000" in draft)
    v["his_named_arm_is_the_receipts"] = (
        a["his_separator"]["raw_units"] == 25003 and a["his_separator"]["trimmed_units"] == 24998
        and a["his_separator"]["wire_units"] == 24998 and a["his_separator"]["notice_kb"] is None
        and "raw 25,003, trimmed 24,998" in draft and "24,998 units ending zzz" in draft)
    # THE ROOM. @yacb2 ran the same arm and published the same conclusion 34 minutes before this
    # draft existed. A version of this comment that claims the result rather than replicating it
    # must fail, and so must one that does not name his control.
    y = by("yacb2")
    v["yacb2_really_ran_the_same_arm_today"] = (
        "markers + `zzz` + 5 LF" in y and "24,998" in y)
    v["yacb2_really_added_the_TAIL_control"] = "`TAIL` (control)" in y
    v["THE_DRAFT_CREDITS_HIM_FIRST"] = (
        "@yacb2 posted half an hour ago" in draft
        and "@yacb2 has the same on darwin" in draft
        and "his reading is the one I would send you to" in draft)
    v["and_ours_is_framed_as_a_second_route"] = (
        "Same conclusion as his, from the opposite end of the file" in draft)
    disp = [a["disp_none"], a["disp_nl5"], a["disp_sp"]]
    v["the_display_arms_are_the_receipts"] = (
        sorted(d["raw_units"] for d in disp) == [100, 105, 107]
        and len({d["after_last_content_char"] for d in disp}) == 1
        and len({d["wire_units"] for d in disp}) == 1
        and "100, 105 and 107 units on disk" in draft)

    ls, lsc = a["lead_size"], a["lead_size_ctl"]
    ll, llc = a["lead_lines"], a["lead_lines_ctl"]
    v["the_leading_size_arm_is_the_receipts"] = (
        ls["raw_units"] == 32100 and ls["trimmed_units"] == 30099
        and ls["wire_units"] == 24982
        and "raw 32,100   trimmed 30,099" in draft and "wire 24,982 units" in draft)
    v["THE_ANSWER_it_is_byte_identical_to_its_partner"] = (
        ls["wire_units"] == lsc["wire_units"] and ls["wire_tail"] == lsc["wire_tail"]
        and ls["notice_kb"] == lsc["notice_kb"]
        and "byte-identical to the partner" in draft)
    v["the_leading_line_arm_is_the_receipts"] = (
        ll["raw_units"] == 3500 and ll["trimmed_units"] == 1499
        and ll["notice_kb"] is not None and "300 lines (limit: 200)" in ll["notice_kb"]
        and ll["wire_units"] == llc["wire_units"]
        and "raw 3,500    trimmed 1,499" in draft
        and 'notice "300 lines (limit: 200)", identical to the partner' in draft)
    v["CONTROL_each_leading_arm_really_has_a_partner"] = (
        lsc["raw_units"] == 30100 and llc["raw_units"] == 1500)
    v["the_2000_newline_arm_is_the_receipts"] = (
        a["blank2000"]["raw_units"] == 26998 and a["blank2000"]["trimmed_units"] == 24998
        and a["blank2000"]["notice_kb"] is None and "raw 26,998, trimmed 24,998" in draft)
    v["CONTROL_the_probe_itself_passed_every_verdict"] = all(bl["verdicts"].values())
    v["THE_REFUTED_UNIVERSAL_IS_GONE"] = "unobservable" not in draft
    v["the_conclusion_is_the_measured_one"] = "the cut slices the trimmed string" in draft
    v["the_zero_cost_claim_is_scoped_to_those_arms"] = "Zero completions for these arms" in draft

    # ---- the taxonomy cell: theirs, twice over, and we claim none of it -----------------------------
    v["CONTROL_his_own_capture_really_sits_in_that_cell"] = QUOTED_NOTICE in his_capture
    v["yacb2_also_closed_that_cell_today"] = "size-over / lines-under / multi-line cell" in y
    v["the_draft_claims_the_cell_for_neither_of_us"] = (
        "filled twice over already" in draft and "a capture I posted" not in draft
        and "No fourth variant there" not in draft)

    # ---- the cd replication -------------------------------------------------------------------------
    v["cd_receipt_passed"] = all(cd["verdicts"].values())
    tails = {x["arm"]: os.path.basename(os.path.dirname(
        x["store"].rstrip("\\/"))).split("Temp-")[-1] for x in cd["arms"]}
    v["CONTROL_the_slug_extractor_found_slugs"] = all(
        s.startswith("cdstore-") for s in tails.values())
    v["the_in_repo_pair_really_shares_a_store"] = tails["repo root"] == tails["repo subdir"]
    v["the_out_of_repo_pair_really_does_not"] = tails["non-repo root"] != tails["non-repo subdir"]
    v["all_four_slug_tails_in_the_draft_are_the_receipts"] = all(s in draft for s in tails.values())

    # ---- the unit note --------------------------------------------------------------------------------
    rows = {r["label"]: r for r in un["rows"]}
    cjk, emo = rows["cjk_200x125"], rows["emoji_200x125"]
    v["the_cjk_figures_are_the_receipts"] = (
        f"{cjk['bytes']:,}" in draft and f"{cjk['utf16_units']:,}" in draft
        and cjk["last_line_loaded"] == 198 and "line 198" in draft)
    v["the_cjk_ratio_is_recomputed"] = (
        abs(cjk["bytes"] / cjk["utf16_units"] - 2.44) < 0.01 and "2.44x" in draft)
    v["the_emoji_figures_are_the_receipts"] = (
        f"{emo['bytes']:,}" in draft and f"{emo['utf16_units']:,}" in draft)
    # WE RETRACTED THAT CELL IN THIS THREAD. `emoji 200x125 -> 115` is floor(25000/u), which the
    # model can read back off the cap stated in its own prompt, so it never measured where the cut
    # fell. Comment 5411236356, 25 August. The draft carried it again anyway and the prior-statement
    # gate caught it on the send. Three checks, because the first two alone would pass a draft that
    # simply never mentioned emoji at all.
    ours = by("DanceNitra")
    v["OUR_OWN_RETRACTION_IS_REAL"] = (
        "`emoji 200x125 -> 115`" in ours and "**Retracted.**" in ours)
    v["THE_RETRACTED_CELL_IS_NOT_REPUBLISHED"] = (
        "line 115" not in draft and "cut at line 115" not in draft)
    v["and_the_draft_says_so_rather_than_going_quiet"] = (
        "I have no measured cut position for that arm" in draft
        and "I retracted it here on the 25th" in draft)
    # The emoji case does NOT run the other way on bytes; both overcount. An earlier draft said
    # "run the other way" and that was wrong.
    v["the_emoji_direction_claim_is_gone"] = (
        emo["bytes"] > emo["utf16_units"] and "run the other way" not in draft)
    v["his_README_really_says_25KB"] = "200 lines / 25KB" in readme
    v["and_he_said_it_again_in_the_thread_today"] = "200 lines / 25KB" in by("tonydzi")
    v["we_do_not_present_the_unit_point_as_new"] = "not news" in draft

    # ---- attribution, from the live thread ------------------------------------------------------------
    p = by("pjt222")
    v["pjt222_really_named_that_arm"] = "4,999 five-char markers" in p and "`zzz`" in p
    v["pjt222_really_said_he_had_not_run_it"] = "I have not run it" in p
    v["pjt222_really_left_the_taxonomy_cell_open"] = (
        "size-over" in p and "lines-under" in p and "multi-line" in p)
    v["pjt222_really_lost_a_run_to_repo_keying"] = "keyed to the git repository" in p
    j = by("JhouCode")
    v["JhouCode_really_reported_the_cd_asymmetry"] = "into a subdirectory keeps the same store" in j
    v["JhouCode_really_drew_the_astral_narrowing"] = (
        'it is "astral"' in j and "the risk is not non-ASCII, it is astral" in draft)
    v["tonydzi_really_published_the_diet"] = "always-loaded-diet" in by("tonydzi")

    # ---- house style -----------------------------------------------------------------------------------
    v["no_em_or_en_dash"] = not ("—" in draft or "–" in draft or " -- " in draft)
    v["no_personal_name"] = not re.search(r"[Rr]astislav|Draho[sš]", draft)
    v["every_at_handle_is_a_real_participant"] = all(
        h in {c["user"] for c in cs} for h in set(re.findall(r"@([A-Za-z0-9]+)", draft)))
    v["the_AI_disclosure_is_present"] = "Written with AI assistance" in draft
    v["length_is_reasonable"] = 700 < len(draft.split()) < 1200

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
    try:
        with urllib.request.urlopen(
                "https://raw.githubusercontent.com/tonydzi/always-loaded-diet/main/README.md",
                timeout=60) as r:
            readme = r.read().decode("utf-8", "replace")
    except Exception as e:
        raise SystemExit(f"REFUSED: could not fetch his README ({e}); quoting it would be unchecked")
    hc = subprocess.run(["gh", "api", "repos/anthropics/claude-code/issues/comments/5412833938",
                         "--jq", ".body"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    if hc.returncode != 0 or not hc.stdout:
        raise SystemExit("REFUSED: could not read @pjt222's own capture comment 5412833938")
    cs = thread()
    if not cs:
        raise SystemExit("REFUSED: could not read the live thread")

    v = check(draft, w, cd, un, bl, cs, readme, hc.stdout)
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    passed = sum(1 for x in v.values() if x)
    print(f"\n  {passed}/{len(v)} checks, {len(draft.split())} words, {len(cs)} comments read")

    if "--mutate" in sys.argv:
        print("\n  MUTATION SELF-TEST")
        muts = [("shrink n", "27 trials", "20 trials"),
                ("see row", "9 of 9", "8 of 9"),
                ("in_file row", "| 0 of 9 | 6 | 3 | 0 |", "| 1 of 9 | 6 | 3 | 0 |"),
                ("neutral row", "| 0 of 9 | 5 | 2 | 2 |", "| 0 of 9 | 6 | 2 | 2 |"),
                ("drop the no-refusals correction", "no refusals at all in 27 trials",
                 "a couple of refusals in 27 trials"),
                ("claim all cells reproduce", "Only the first cell reproduces",
                 "Every cell reproduces"),
                ("hide the timeouts", "timed out at 90 seconds", "answered at 90 seconds"),
                ("hide the scorer gap", "a floor rather than a count", "an exact count"),
                ("assert the notice causes it", "I cannot separate the notice",
                 "the notice is what triggers"),
                ("revive the accuracy framing", "not moving reading accuracy",
                 "moving reading accuracy"),
                ("boundary pair", "25,001 is cut back to 25,000 and warns",
                 "25,002 is cut back to 25,000 and warns"),
                ("his named arm", "raw 25,003, trimmed 24,998", "raw 25,003, trimmed 24,997"),
                ("display arms", "100, 105 and 107 units on disk",
                 "100, 105 and 108 units on disk"),
                ("leading size arm", "wire 24,982 units", "wire 24,983 units"),
                ("break the pairing", "byte-identical to the partner", "close to the partner"),
                ("leading line arm", "raw 3,500    trimmed 1,499", "raw 3,500    trimmed 1,500"),
                ("the 2000-newline arm", "raw 26,998, trimmed 24,998",
                 "raw 26,999, trimmed 24,998"),
                ("bring back the refuted universal", "the cut slices the trimmed string",
                 "the operand is unobservable from the wire for every input"),
                ("unscope the zero cost", "Zero completions for these arms",
                 "Zero completions for all of it"),
                ("self-credit the cell", "filled twice over already",
                 "closed by a capture I posted on the 25th"),
                ("drop the credit to yacb2", "@yacb2 has the same on darwin",
                 "nobody else has run it"),
                ("claim priority", "Same conclusion as his, from the opposite end of the file",
                 "A conclusion nobody else has reached"),
                ("cd slug", "cdstore-jntsww91-plain-sub-deeper", "cdstore-jntsww91-plain-sub"),
                ("cjk ratio", "2.44x", "3.44x"),
                ("republish the retracted cell", "on the same geometry",
                 "and cut at line 115"),
                ("go quiet about the retraction",
                 "I have no measured cut position for that arm",
                 "The cut position for that arm"),
                ("claim the unit point as new", "not news", "a new finding"),
                ("drop the disclosure", "Written with AI assistance", "Written by hand"),
                ("em dash", "Correcting my own numbers first.",
                 "Correcting my own numbers first —.")]
        caught = 0
        for label, x, y in muts:
            if x not in draft:
                print(f"    SKIP   {label}: anchor absent, mutation vacuous")
                continue
            mv = check(draft.replace(x, y, 1), w, cd, un, bl, cs, readme, hc.stdout)
            broke = [k for k in v if v[k] and not mv.get(k)]
            caught += bool(broke)
            print(f"    {'CAUGHT' if broke else 'MISSED'}  {label}"
                  f"{' -> ' + broke[0] if broke else ''}")
        print(f"    {caught}/{len(muts)} mutations caught")
        return 0 if (passed == len(v) and caught == len(muts)) else 1
    return 0 if passed == len(v) else 1


if __name__ == "__main__":
    sys.exit(main())
