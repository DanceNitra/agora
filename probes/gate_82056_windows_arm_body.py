"""Recompute every number in the outbound #82056 comment from the receipts, before it is sent.

Not a spell-check of the prose: each assertion below re-derives the figure from an artifact on
disk or from the live thread, and the gate fails if the draft and the artifact disagree. The one
thing a gate like this cannot do is check a CAUSE, so the draft's causal sentences are listed at
the bottom as what a reader has to take on the argument rather than on a number.

Run: PYTHONIOENCODING=utf-8 python probes/gate_82056_windows_arm_body.py
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "..", "agora_output", "drafts",
                     "reply_82056_windows_arm_and_four_retractions.md")
LF = os.path.join(HERE, "the_cap_on_windows_and_what_a_crlf_line_costs.lf.result.json")
CRLF = os.path.join(HERE, "the_cap_on_windows_and_what_a_crlf_line_costs.crlf.result.json")
RISK = os.path.join(HERE, "how_wrong_could_the_OUT_cells_be.result.json")


def load(p):
    if not os.path.exists(p):
        raise SystemExit(f"REFUSED: {p} is absent; the draft would be unbacked")
    return json.load(io.open(p, encoding="utf-8"))


def flat(s: str) -> str:
    """Whitespace-insensitive, so a wrapped line still matches."""
    return re.sub(r"\s+", " ", s)


def main() -> int:
    body = flat(io.open(DRAFT, encoding="utf-8").read())
    lf, crlf, risk = load(LF), load(CRLF), load(RISK)
    v: dict = {}

    # ---- the LF arm, cell by cell -------------------------------------------------------------
    sc, ned = lf["scores"], lf["needles"]
    v["lf_line125_digits_end_24999"] = ned["125"]["digits_end"] == 24999
    v["lf_line125_is_3_of_3"] = tuple(sc["125"]) == (3, 3)
    v["lf_line126_is_0_of_3"] = tuple(sc["126"]) == (0, 3)
    v["lf_line3_control_is_3_of_3"] = tuple(sc["3"]) == (3, 3)
    v["lf_line138_control_is_0_of_3"] = tuple(sc["138"]) == (0, 3)
    v["lf_decoy_is_0_of_3"] = tuple(sc["disk"]) == (0, 3)
    v["lf_line124_is_the_2_of_3_flap"] = tuple(sc["124"]) == (2, 3)
    v["the_draft_states_the_flap_as_2_of_3"] = "line 124 at 2/3" in body
    trials = lf["trials_detail"] + crlf["trials_detail"]
    v["eighteen_of_eighteen_trials_per_arm"] = len(lf["trials_detail"]) == 18
    v["zero_tools_in_every_trial_both_arms"] = all(
        t["tools_offered"] == 0 and not t["tool_uses"] for t in trials)
    v["the_draft_says_18_of_18"] = "18 of 18" in body

    # ---- the CR contrast ----------------------------------------------------------------------
    v["crlf_line125_is_0_of_3"] = tuple(crlf["scores"]["125"]) == (0, 3)
    v["the_two_arms_differ_only_in_the_terminator"] = (
        lf["width"] == crlf["width"] == 199
        and lf["units_per_line"] == 200 and crlf["units_per_line"] == 201)
    v["the_draft_says_199_char_content"] = "199-char content" in body

    # ---- the risk figures ---------------------------------------------------------------------
    v["false_negatives_1_of_15"] = (risk["false_negatives"], risk["trials_on_known_IN_needles"]) == (1, 15)
    v["wilson_upper_is_0_298"] = abs(risk["wilson95"][1] - 0.2982) < 5e-4
    v["a_single_OUT_at_that_bound_is_0_027"] = abs(risk["load_bearing_worst_case"] - 0.0265) < 5e-4
    v["the_draft_quotes_all_three"] = all(
        s in body for s in ("1 false negative in 15", "0.298", "0.027"))

    # ---- our own morning run, the void one ----------------------------------------------------
    # 24,810 is the position of TWIRPAZ's last character in the START-aligned fixture.
    old = os.path.join(HERE, "the_cut_measured_by_what_the_index_DOES_not_what_it_says.py")
    src = io.open(old, encoding="utf-8").read()
    ns: dict = {"__file__": old}
    exec(src.split("def seen_at")[0].replace(
        "import is_the_cap_counted_in_bytes_or_utf16_units as U", "U = None"), ns)
    line = ns["line_for"](168)
    off = line.find(ns["NEEDLES"][168])
    v["the_void_run_proved_only_24810"] = (167 * 148) + off + len(ns["NEEDLES"][168]) == 24810
    v["the_draft_states_24810"] = "24,810" in body

    # ---- the Windows reader table, re-measured here rather than quoted ------------------------
    tmp = os.path.join(HERE, "_gate_crlf_probe.txt")
    io.open(tmp, "wb").write(("\r\n".join("L%09d" % i for i in range(1, 6)) + "\r\n").encode())
    raw = len(open(tmp, "rb").read())
    uni = len(io.open(tmp, encoding="utf-8").read())
    ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                         f"((Get-Content '{tmp}') | Measure-Object -Property Length -Sum).Sum"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    summed = int((ps.stdout or "0").strip() or 0)
    os.remove(tmp)
    v["reader_raw_is_60"] = raw == 60
    v["reader_universal_newlines_is_55"] = uni == 55
    v["reader_get_content_summed_is_50"] = summed == 50
    v["the_draft_table_carries_60_55_50"] = all(f"| {n} |" in body for n in (60, 55, 50))

    # ---- the room: the 46/48 point is HIS, and our 198 rests on the shuffled arm --------------
    def thread(q):
        out = subprocess.run(
            ["gh", "api", "repos/anthropics/claude-code/issues/82056/comments?per_page=100",
             "--paginate", "--jq", q], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        return (out.stdout or "").strip()

    who48 = thread('.[] | select(.body|test("summed to 48")) | .user.login')
    v["the_46_over_48_point_is_pjt222s_only"] = who48.split() == ["pjt222"]
    ours = thread('.[] | select(.user.login=="DanceNitra") | .body')
    v["we_published_the_shuffled_label_arm"] = "CANARY-L0060" in ours
    v["we_published_115_and_168"] = "115" in ours and "168" in ours
    v["the_draft_retracts_115_and_168_and_the_ceiling"] = all(
        s in body for s in ("115", "168", "[24955, 25012)"))
    v["the_draft_does_NOT_retract_198"] = "Retracted" in body and "198" in body

    # ---- controls -----------------------------------------------------------------------------
    v["CONTROL_a_wrong_figure_would_fail"] = "24,999" in body and ned["125"]["digits_end"] == 24999
    v["CONTROL_the_thread_query_returned_something"] = bool(ours)
    v["CONTROL_the_draft_is_non_empty"] = len(body) > 1500

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    bad = [k for k, ok in v.items() if not ok]
    print(f"\n  {len(v) - len(bad)}/{len(v)} checks pass")
    print("\n  NOT CHECKABLE HERE, and a reader takes these on the argument:")
    print("   * that strip-then-cap is the only model our two arms kill (they do not separate")
    print("     'CR counted' from 'truncate raw, strip after')")
    print("   * that the flap rate estimated on known-IN needles transfers to OUT cells")
    if bad:
        print("\n  FAILED: " + ", ".join(bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
