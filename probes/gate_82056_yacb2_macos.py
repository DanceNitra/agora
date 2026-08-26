"""Gate the reply to @yacb2: recompute every figure, and fetch every attributed claim live.

The rule this enforces is the one that keeps catching us: a gate that reads the DRAFT and checks the
draft says what the draft says has measured nothing. Every number below is recomputed from a probe
receipt or from the committed capture, and every sentence attributed to another person is fetched
from GitHub at gate time. Where a check cannot reach its source it REFUSES rather than falling back
to a local constant.

Run:  python -X utf8 probes/gate_82056_yacb2_macos.py
      python -X utf8 probes/gate_82056_yacb2_macos.py --mutate
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
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_82056_yacb2_macos.md")
NEST = os.path.join(HERE, "does_a_nested_session_ignore_the_isolation_variables.result.json")
CRLF_CAP = os.path.join(HERE, "_wire_capture_windows_crlf.json")
REPO = "anthropics/claude-code"


def gh_thread(num: int) -> list:
    r = subprocess.run(["gh", "api", "--paginate", f"repos/{REPO}/issues/{num}/comments",
                        "--jq", ".[] | {id:.id, user:.user.login, body:.body}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = []
    for line in (r.stdout or "").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def unmd(s: str) -> str:
    return norm(re.sub(r"[*`]+", "", s or ""))


def check(draft: str, nest: dict, thread: list, live: bool) -> dict:
    v: dict = {}

    # ---- the artifact behind the nested claim --------------------------------------------------
    v["nested_receipt_exists_and_passed"] = bool(nest) and all(nest.get("verdicts", {}).values())
    ns, cs = nest.get("nested_summary") or {}, nest.get("clean_summary") or {}
    trials = ns.get("trials", 0)
    v["CONTROL_more_than_one_trial_per_arm"] = trials >= 5 and cs.get("trials", 0) >= 5
    # Same trap: the table carries "| 5/5 |" twice. Require every N/N cell in the draft to be the
    # receipt's ratio, so changing one of them fails.
    cells = sorted(set(re.findall(r"\d+/\d+", draft)))
    v["the_5_of_5_in_the_draft_is_the_receipts"] = (
        ns.get("base_url_hits") == trials and cs.get("base_url_hits") == cs.get("trials")
        and cells == [f"{trials}/{trials}"] and draft.count(f"| {trials}/{trials} |") == 2)
    v["the_zero_leak_claim_is_the_receipts"] = (
        not ns.get("LEAKED_into_the_real_store") and not cs.get("LEAKED_into_the_real_store"))
    v["we_really_were_nested_in_the_run"] = bool(ns.get("inherited_CLAUDECODE")
                                                 and ns.get("inherited_CHILD_SESSION"))
    v["the_ten_runs_figure_matches"] = (trials + cs.get("trials", 0)) == 10 and "ten runs" in draft

    # ---- the 24,922 / 24,924 reconciliation, recomputed from the capture ------------------------
    if not os.path.exists(CRLF_CAP):
        raise SystemExit(f"REFUSED: {CRLF_CAP} is absent; the reconciliation would be unbacked")
    body = json.loads(json.load(io.open(CRLF_CAP, encoding="utf-8"))[0]["body"])
    text = body["messages"][0]["content"][0]["text"]
    CR = chr(13)
    s = text.index("- [E0001]")
    w = text.index("WARNING") if "WARNING" in text else len(text)
    stop = text.rindex("x", s, w)
    ours = text[s:stop + 1]                      # content only, terminator excluded
    theirs = len(ours) + 2                       # plus the CRLF that ends line 124
    # EVERY occurrence, not "is it present". A figure appearing twice survives a single-occurrence
    # mutation and the presence check keeps passing: 24,922 is in this draft twice, 24,924 three
    # times, and "| 5/5 |" twice, so three mutations walked straight through the first version of
    # this gate. Assert the SET of figures of that shape and their counts.
    shapes = sorted(set(re.findall(r"24,9\d\d", draft)))
    v["ONLY_the_two_expected_figures_of_that_shape_appear"] = shapes == ["24,922", "24,924"]
    v["our_24922_is_recomputed_and_every_instance_matches"] = (
        len(ours) == 24_922 and draft.count("24,922") == 2)
    v["their_24924_is_that_plus_the_final_CRLF_everywhere"] = (
        theirs == 24_924 and draft.count("24,924") == 3)
    v["the_CR_counts_123_and_124_are_recomputed"] = (
        ours.count(CR) == 123 and ours.count(CR) + 1 == 124
        and "123" in draft and "124 carriage returns" in draft)
    v["the_room_left_78_and_76_are_recomputed"] = (
        25_000 - len(ours) == 78 and 25_000 - theirs == 76 and "78" in draft and "76" in draft)
    v["201_times_124_really_is_24924"] = 201 * 124 == 24_924

    if not live:
        v["REFUSED_no_network_so_no_attribution_was_verified"] = False
        return v

    joined = unmd(" ".join(c["body"] for c in thread))
    by = lambda u: " ".join(c["body"] for c in thread if c["user"] == u)

    # ---- everything attributed to another person -----------------------------------------------
    v["yacb2_really_said_the_threshold_equals_the_cut"] = (
        "trigger threshold equals the cut length" in unmd(by("yacb2")))
    v["yacb2_really_reported_24924_and_124_CRs"] = (
        "24,924 units, 124 carriage returns" in unmd(by("yacb2")))
    v["yacb2_really_described_the_nested_hazard"] = (
        "CLAUDE_CODE_CHILD_SESSION=1" in by("yacb2") and "CLAUDE_CONFIG_DIR" in by("yacb2"))
    # pjt222's arithmetic is cited by name in the draft, so it has to be his and it has to be there
    v["pjt222_really_wrote_201_x_124_equals_24924"] = bool(
        re.search(r"201\s*[x×*]\s*124\s*=\s*24924", unmd(by("pjt222"))))
    v["the_draft_credits_pjt222_for_it"] = "@pjt222" in draft
    # and OUR 24,922 has to be ours, in this thread, or the reconciliation has no second side
    v["our_24922_was_published_by_us_here"] = "24,922" in by("DanceNitra")
    # THE PRIOR-STATEMENT CHECK: we must not re-answer a question we already answered, nor claim as
    # open something we closed. Our own comment has to contain the open question we say he closed.
    v["we_really_left_that_question_open"] = (
        "trigger threshold equals the cut length" in unmd(by("DanceNitra")))
    # NOT ALREADY SAID: nobody may have reconciled the two figures or tried this on Windows.
    v["nobody_has_reconciled_the_two_figures"] = not re.search(
        r"24,?922.{0,200}24,?924|24,?924.{0,200}24,?922", joined)
    v["nobody_has_reported_the_nested_check_on_windows"] = not re.search(
        r"win32.{0,120}CLAUDE_CODE_CHILD_SESSION|CLAUDE_CODE_CHILD_SESSION.{0,120}win32", joined)

    # ---- house style ----------------------------------------------------------------------------
    v["no_em_or_en_dash_survives_the_humanizer_rule"] = not (
        "—" in draft or "–" in draft or " -- " in draft)
    words = len(draft.split())
    v["length_is_under_the_thread_median_650"] = words < 650
    v["and_it_is_not_so_short_it_says_nothing"] = words > 180
    v["every_at_handle_is_a_real_participant"] = all(
        h in {c["user"] for c in thread} for h in set(re.findall(r"@([A-Za-z0-9-]+)", draft)))
    v["the_ai_disclosure_is_present"] = "AI assistance" in draft
    return v


def main() -> int:
    mutate = "--mutate" in sys.argv
    for p in (DRAFT, NEST):
        if not os.path.exists(p):
            raise SystemExit(f"REFUSED: {p} is absent")
    draft = io.open(DRAFT, encoding="utf-8").read()
    nest = json.load(io.open(NEST, encoding="utf-8"))
    thread = gh_thread(82056)
    live = bool(thread)
    if not live:
        print("  REFUSED: could not read the live thread; attribution is UNVERIFIED")

    v = check(draft, nest, thread, live)
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    passed = sum(1 for x in v.values() if x)
    print(f"\n  {passed}/{len(v)} checks, {len(draft.split())} words, {len(thread)} comments read")

    if mutate:
        print("\n  MUTATION SELF-TEST")
        muts = [("our figure", "24,922", "24,923"),
                ("their figure", "24,924", "24,925"),
                ("CR count", "124 carriage returns", "125 carriage returns"),
                ("room left", "78 our way, 76 yours", "77 our way, 75 yours"),
                ("trials", "| 5/5 |", "| 4/5 |"),
                ("ten runs", "ten runs", "twelve runs"),
                ("pjt222 credit", "@pjt222", "@somebody-else"),
                ("em dash", "Same bytes on the wire.", "Same bytes on the wire —."),
                ("en dash", "78 our way", "78–our way"),
                ("disclosure", "AI assistance", "no assistance")]
        caught = 0
        for label, a, b in muts:
            if a not in draft:
                print(f"    SKIP   {label}: anchor absent, mutation vacuous")
                continue
            mv = check(draft.replace(a, b, 1), nest, thread, live)
            broke = [k for k in v if v[k] and not mv.get(k)]
            caught += bool(broke)
            print(f"    {'CAUGHT' if broke else 'MISSED'}  {label}"
                  f"{' -> ' + broke[0] if broke else ''}")
        print(f"    {caught}/{len(muts)} mutations caught")
        return 0 if (passed == len(v) and caught == len(muts)) else 1
    return 0 if passed == len(v) else 1


if __name__ == "__main__":
    sys.exit(main())
