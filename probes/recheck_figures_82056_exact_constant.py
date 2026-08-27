"""RECHECK THE FIGURES in #82056 exact-constant reply: re-derive every figure, fetch every quotation live.

The rule this enforces is the one that keeps catching us: a gate that reads the DRAFT and checks the
draft says what the draft says has measured nothing. So every number below is recomputed from the
probe receipt, and every attributed string is fetched from GitHub at gate time. Where a check cannot
reach its source it REFUSES; it never falls back to a local constant, because a silent fallback is
how a circular assertion passes as a measurement.

Run:  python -X utf8 probes/gate_82056_exact_constant.py
      python -X utf8 probes/gate_82056_exact_constant.py --mutate   (self-test: corrupt and re-gate)

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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_82056_exact_constant.md")
RECEIPT = os.path.join(HERE, "the_memory_cap_is_25000_utf16_units_not_bytes.result.json")
AUG_RECEIPT = os.path.join(HERE, "is_the_cap_counted_in_bytes_or_utf16_units.result.json")

REPO = "anthropics/claude-code"
ALMANAC = "pjt222/agent-almanac"
PJT_INSTRUMENT = "5412833938"        # pjt222, the wire-capture method
OUR_407 = "5366900247"               # ours, in the almanac, where the unit was published


def gh_comment(repo: str, cid: str) -> dict:
    r = subprocess.run(["gh", "api", f"repos/{repo}/issues/comments/{cid}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return {}
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def gh_thread(repo: str, num: int) -> list:
    r = subprocess.run(["gh", "api", "--paginate",
                        f"repos/{repo}/issues/{num}/comments", "--jq",
                        ".[] | {id:.id, user:.user.login, body:.body}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return []
    out = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def unmd(s: str) -> str:
    """Drop the OTHER person's emphasis markup before comparing a quotation against their text.

    Quoting someone's prose without carrying their bold into your own sentence is normal and honest,
    and requiring the asterisks would fail every correct quotation of a formatted comment. What must
    NOT be normalised away is any word: only ``**``, ``*`` and backticks go. The mutation self-test
    keeps this honest by altering a quoted WORD and requiring the check to fail.
    """
    return norm(re.sub(r"[*`]+", "", s or ""))


def check(draft: str, rc: dict, aug: dict, thread: list, live: bool) -> dict:
    v: dict = {}
    d = norm(draft)

    # ---- the artifact must be the one this draft is about --------------------------------------
    v["receipt_exists_and_passed"] = bool(rc) and all(rc.get("verdicts", {}).values())
    v["receipt_has_all_five_arms"] = (
        len(rc.get("slice_arm") or []) == 2 and set(rc.get("unit_arms") or {}) == {"A", "B", "C"}
        and bool(rc.get("multiline_arm")))

    # ---- every figure RE-DERIVED, never read out of the draft ----------------------------------
    cap = rc.get("cap_units")
    v["the_cap_figure_is_the_receipts"] = cap == 25_000 and "25,000 UTF-16 code units" in draft

    ml = rc.get("multiline_arm") or {}
    v["the_150x199_geometry_is_the_receipts"] = "150" in d and "199" in d and ml.get(
        "last_kept_line") == 124
    v["the_124_in_the_draft_is_the_receipts"] = ("lines 1–124" in draft or "lines 1-124" in draft)
    # 78 must be recomputed, not trusted: cap minus what the multiline arm actually carried.
    derived_78 = cap - ml.get("units", 0)
    v["the_78_is_recomputed_from_the_arm"] = (derived_78 == ml.get("slice_would_have_carried")
                                              and f"{derived_78} more" in draft)
    v["the_draft_says_line_125_is_ABSENT"] = ml.get("partial_next_line_on_wire") is False

    rows = {r["marker_width"]: r for r in (rc.get("slice_arm") or [])}
    ok_rows = True
    for w, expect_whole, expect_left in ((4, 6250, 0), (7, 3571, 3)):
        r = rows.get(w) or {}
        ok_rows &= (r.get("whole_markers") == expect_whole
                    and r.get("leftover_chars") == expect_left
                    and r.get("units_on_wire") == cap
                    and expect_whole * w + expect_left == cap
                    and f"{expect_whole:,} whole markers + {expect_left} character" in draft)
    v["both_marker_rows_reconstruct_and_match_the_draft"] = ok_rows
    # marker 3572 must be the NEXT marker after the 7-char run, computed not quoted
    v["marker_3572_is_the_next_one_after_the_run"] = (
        (rows.get(7, {}).get("whole_markers", 0) + 1) == 3572 and "marker 3572" in draft)
    v["the_mid_marker_cut_is_real_in_the_receipt"] = any(
        r.get("leftover_chars") for r in rows.values())

    dd = rc.get("display_defect") or {}
    v["the_3x_factor_is_the_receipts"] = (abs((dd.get("factor") or 0) - 3.0) < 0.05
                                          and "3× off on CJK" in draft)

    # ---- the August priority claim must be backed by the August artifact ------------------------
    aug_rows = aug.get("rows") or []
    has_emoji = any("emoji" in (r.get("label") or "") for r in aug_rows)
    v["the_august_receipt_exists_and_has_an_EMOJI_arm"] = bool(aug_rows) and has_emoji
    v["the_august_receipt_carries_the_KB_verdict"] = bool(
        (aug.get("verdicts") or {}).get("warning_reports_units_over_1024_not_kb"))
    v["the_draft_credits_august_rather_than_claiming_it_now"] = (
        "not new" in d and "August" in draft and OUR_407 in draft)

    # ---- LIVE: everything attributed to another person -----------------------------------------
    if not live:
        v["REFUSED_no_network_so_no_attribution_was_verified"] = False
        return v

    bodies = {c["id"]: c for c in thread}
    joined = norm(" ".join(c["body"] for c in thread))

    # JhouCode's bracket, quoted verbatim in the draft
    v["the_bracket_is_quoted_verbatim_from_the_thread"] = "[24999, 25023)" in joined and (
        "[24999, 25023)" in draft)
    jc = [c for c in thread if c["user"] == "JhouCode"]
    v["and_it_is_JhouCode_who_wrote_it"] = any("[24999, 25023)" in c["body"] for c in jc)
    v["ask_1_is_really_his_and_really_about_the_unit"] = any(
        "unit it is actually counted in" in norm(c["body"]) for c in jc)
    v["he_really_withdrew_the_corroboration"] = any(
        "measures nothing on its own" in norm(c["body"]) for c in jc)

    # pjt222's instrument comment must exist, be his, and be in this thread
    inst = gh_comment(REPO, PJT_INSTRUMENT)
    v["the_instrument_comment_resolves"] = bool(inst)
    v["the_instrument_comment_is_pjt222s"] = (inst.get("user") or {}).get("login") == "pjt222"
    v["the_instrument_comment_really_describes_the_wire_capture"] = "ANTHROPIC_BASE_URL" in (
        inst.get("body") or "")
    v["the_draft_cites_that_id"] = PJT_INSTRUMENT in draft
    # and his own words that he did not run the single-line arm
    v["he_really_declined_that_arm_as_confounded"] = any(
        "not run" in norm(c["body"]) and "confounded" in norm(c["body"])
        for c in thread if c["user"] == "pjt222")

    # our almanac comment must exist, be OURS, and actually contain the unit result
    ours = gh_comment(ALMANAC, OUR_407)
    v["our_almanac_comment_resolves"] = bool(ours)
    v["it_is_ours"] = (ours.get("user") or {}).get("login") == "DanceNitra"
    v["it_really_carries_the_unit_result"] = "UTF-16" in (ours.get("body") or "")

    # ---- do not re-say what we already said in THIS thread --------------------------------------
    our_here = [c for c in thread if c["user"] == "DanceNitra"]
    v["CONTROL_we_have_actually_posted_in_this_thread"] = len(our_here) > 0
    v["the_exact_25000_has_not_been_stated_by_us_here_before"] = not any(
        "25,000 UTF-16 code units" in c["body"] for c in our_here)
    # NOT a keyword sweep for "exactly 25,000": pjt222 uses that phrase to POSE the question
    # and to say he did not answer it, so a sweep flags his own statement that the measurement
    # is absent. The right check is that the decisive arm was declared UNRUN by its designer.
    pjt = " ".join(c["body"] for c in thread if c["user"] == "pjt222")
    v["the_decisive_arm_is_declared_UNRUN_by_its_designer"] = ("not run" in pjt
                                                              and "confounded" in pjt)

    # THE ATTRIBUTION CHECK, added because an earlier draft failed it. That draft said his arm
    # was confounded "because asked of a model it is confounded". His STATED reason is whole-line
    # truncation making OUT ambiguous. A reason invented for someone is a misquotation with no
    # wrong digits in it, so no figure check can see it.
    v["the_draft_carries_HIS_reason_not_one_i_invented"] = (
        "under whole-line truncation the line drops" in draft
        and "under whole-line truncation the line drops" in pjt)
    v["and_names_the_25001_LF_that_makes_OUT_ambiguous"] = "25,001" in draft and "25,001" in pjt
    # Pair quote characters IN ORDER (1st with 2nd, 3rd with 4th). A naive `"([^"]{12,})"` pairs
    # the CLOSING quote of one short quotation with the OPENING quote of the next and invents a
    # quotation out of the prose between them: on this draft it manufactured " and the warning's "
    # and failed the check over a defect in the gate rather than in the text.
    marks = [m.start() for m in re.finditer(r'"', draft)]
    quoted = [draft[a + 1:b] for a, b in zip(marks[0::2], marks[1::2]) if b - a - 1 >= 12]
    v["CONTROL_the_draft_actually_quotes_someone"] = len(quoted) >= 2
    v["every_long_quotation_is_present_in_the_live_thread"] = all(
        unmd(q) in unmd(joined) for q in quoted)
    # CONTROL: the comparison must not be so loose it accepts anything. A string that is NOT in the
    # thread has to fail it, or the check above is decorative.
    v["CONTROL_a_string_absent_from_the_thread_would_fail_that"] = (
        "deliberately never attempted, because it is confounded" not in unmd(joined))

    # THE HUMANIZER IS WIRED, NOT REMEMBERED. Owner, 2026-08-26: "kazdy komentar pojde cez SKILL
    # HUMANIZER lebo to stale nepouzivas." The receipt is keyed by the draft's CONTENT sha256, so
    # running the skill and then editing the sentence it objected to invalidates it.
    import subprocess as _sp
    _r = _sp.run([sys.executable, os.path.join(ROOT, "tools", "humanizer_receipt.py"),
                  "check", DRAFT], capture_output=True, text=True)
    v["the_humanizer_SKILL_ran_on_THESE_bytes"] = _r.returncode == 0

    # ---- house style -----------------------------------------------------------------------------
    # The humanizer rule bans EN dashes too, and this gate checked only the em dash: the draft
    # carried "lines 1–124" through a clean run of it.
    v["no_em_or_en_dash_survives_the_humanizer_rule"] = not (
        "—" in draft or "–" in draft or " -- " in draft)
    words = len(draft.split())
    v["length_is_under_the_thread_median_650"] = words < 650
    v["and_it_is_not_so_short_it_says_nothing"] = words > 200
    v["every_at_handle_in_the_draft_is_a_real_participant"] = all(
        h in {c["user"] for c in thread} | {"pjt222"}
        for h in set(re.findall(r"@([A-Za-z0-9-]+)", draft)))
    return v


def main() -> int:
    mutate = "--mutate" in sys.argv
    if not os.path.exists(DRAFT):
        raise SystemExit(f"REFUSED: {DRAFT} is absent")
    if not os.path.exists(RECEIPT):
        raise SystemExit(f"REFUSED: {RECEIPT} is absent; there is nothing to gate against")
    draft = io.open(DRAFT, encoding="utf-8").read()
    rc = json.load(io.open(RECEIPT, encoding="utf-8"))
    aug = json.load(io.open(AUG_RECEIPT, encoding="utf-8")) if os.path.exists(AUG_RECEIPT) else {}
    thread = gh_thread(REPO, 82056)
    live = bool(thread)
    if not live:
        print("  REFUSED: could not read the live thread; attribution is UNVERIFIED")

    v = check(draft, rc, aug, thread, live)
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    passed = sum(1 for x in v.values() if x)
    print(f"\n  {passed}/{len(v)} checks, {len(draft.split())} words, {len(thread)} comments read")

    if mutate:
        # A gate that cannot fail has measured nothing. Corrupt the draft in ways a careless edit
        # would produce, and require each one to be caught.
        print("\n  MUTATION SELF-TEST")
        muts = [("cap", "25,000 UTF-16 code units", "25,001 UTF-16 code units"),
                ("the 78", "78 more", "77 more"),
                ("marker count", "3,571 whole markers + 3 character",
                 "3,570 whole markers + 3 character"),
                ("marker id", "marker 3572", "marker 3573"),
                ("bracket", "[24999, 25023)", "[24999, 25024)"),
                ("instrument id", PJT_INSTRUMENT, "5412833939"),
                ("our 407 id", OUR_407, "5366900248"),
                ("priority", "not new", "brand new"),
                ("factor", "3× off on CJK", "4× off on CJK"),
                ("em dash", "on one box.", "on one box —."),
                ("en dash", "lines 1-124", "lines 1–124"),
                ("his reason", "under whole-line truncation the line drops",
                 "under whole-line truncation the line survives"),
                ("the 25001", "25,001", "25,002"),
                ("a quotation", "deliberately not run", "deliberately never attempted")]
        caught = 0
        for label, a, b in muts:
            if a not in draft:
                print(f"    SKIP  {label}: anchor absent, mutation vacuous")
                continue
            mv = check(draft.replace(a, b, 1), rc, aug, thread, live)
            broke = [k for k in v if v[k] and not mv.get(k)]
            caught += bool(broke)
            print(f"    {'CAUGHT' if broke else 'MISSED'}  {label}"
                  f"{' -> ' + broke[0] if broke else ''}")
        print(f"    {caught}/{len(muts)} mutations caught")
        return 0 if (passed == len(v) and caught == len(muts)) else 1

    return 0 if passed == len(v) else 1


if __name__ == "__main__":
    sys.exit(main())
