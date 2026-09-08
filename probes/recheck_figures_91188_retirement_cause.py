"""Bind every figure in the retirement-cause reply to what produced it.

THIS IS ONE CHECK INSIDE VALIDATE. IT IS NOT THE GATE. The gate is the skills. A script written
beside a draft is never a substitute for any of them, and the red team that ran on the previous
version of this draft found things nothing here could see.
"""
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, "tools")
import trim_memory_index as T  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from memory_index_files import is_index_file, looks_like_an_index, slug_is_index, _self_check  # noqa: E402,F401


D = "drafts/91188_retirement_cause_class.md"
R = "probes/was_the_row_judged_or_did_the_window_just_end.result.json"
MEM = os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+\.md)\)")


def main():
    raw = io.open(D, encoding="utf-8").read()
    draft = " ".join(raw.split())
    r = json.load(open(R, encoding="utf-8"))
    ok = True

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("  %-4s %-52s %s" % ("YES" if cond else "NO", name, got))

    # THE GROUND TRUTH. Both quotes must be verbatim in their own commit, or they are paraphrase
    # wearing quotation marks in front of people who can run git themselves.
    for sha, frag in (
            ("836d51a", "by the tool's own criterion: a one-off domain result leaves, "
                        "a cross-cutting working rule stays"),
            ("d22e378", "chosen by a stated criterion: one-off domain results (an EDRN degeneracy, "
                        "a LOCOMO ceiling, an inspeximus internal) rather than cross-cutting "
                        "working rules")):
        msg = " ".join(subprocess.run(["git", "log", "--format=%B", "-1", sha],
                                      capture_output=True, text=True).stdout.split())
        check("quote_%s_is_verbatim_in_its_commit" % sha, frag in msg and frag in draft)

    check("the_demote_list_really_holds_32", len(T.DEMOTE) == 32 and "32-entry list" in draft,
          len(T.DEMOTE))

    arc = io.open(os.path.join(MEM, "MEMORY_ARCHIVE.md"), encoding="utf-8",
                  errors="replace").read()
    sec = [s for s in re.split(r"^##\s+", arc, flags=re.M)
           if s.startswith("Demoted from the index 2026-09-04")][0]
    rows = {os.path.splitext(os.path.basename(m))[0] for m in LINK.findall(sec)
            if not is_index_file(m)}
    extra = rows - set(T.DEMOTE)
    check("the_section_holds_53_rows", len(rows) == 53 and "holds 53 rows" in draft, len(rows))
    check("32_of_them_are_named_by_the_tool", len(rows & set(T.DEMOTE)) == 32
          and "named only 32 of them" in draft, len(rows & set(T.DEMOTE)))
    check("21_are_not_named", len(extra) == 21 and "the other 21" in draft, len(extra))

    # The adjacency split, recomputed here rather than quoted from the earlier run.
    pre = os.path.join(MEM, "MEMORY.md.bak-20260904-pretrim")
    ordinals, line_of, k = {}, {}, 0
    for ln, line in enumerate(io.open(pre, encoding="utf-8", errors="replace").read().splitlines()):
        for m in LINK.finditer(line):
            s = os.path.splitext(os.path.basename(m.group(1)))[0]
            if slug_is_index(s) or s in ordinals:
                continue
            ordinals[s], line_of[s] = k, ln
            k += 1
    named_lines = {line_of[d] for d in T.DEMOTE if d in line_of}
    shared = [e for e in extra if e in line_of and line_of[e] in named_lines]
    check("15_shared_a_line_with_a_named_row",
          len(shared) == 15 and "15 shared a physical line" in draft, len(shared))
    check("6_are_from_an_untraced_edit",
          len(extra) - len(shared) == 6 and "remaining 6" in draft, len(extra) - len(shared))

    pos = sorted(ordinals[d] for d in T.DEMOTE if d in ordinals)
    runs, a, b = [], pos[0], pos[0]
    for x in pos[1:]:
        if x == b + 1:
            b = x
        else:
            runs.append((a, b)); a = b = x
    runs.append((a, b))
    last = max(ordinals.values())
    check("the_32_named_rows_form_24_runs", len(runs) == 24 and "24 separate runs" in draft,
          len(runs))
    check("the_largest_run_is_7", max(y - x + 1 for x, y in runs) == 7
          and "the largest is 7 rows" in draft, max(y - x + 1 for x, y in runs))
    check("none_reaches_the_end_of_the_file",
          not any(y >= last - 2 for x, y in runs) and "none reaches the end of the file" in draft)

    # The snapshot claims, from the probe's own receipt.
    chk = {c["check"]: c["got"] for c in r["checks"]}
    check("26_snapshots", r["snapshots"] == 26 and "26 dated copies" in draft, r["snapshots"])
    check("zero_cross_line_references",
          "0 cross-line references across 26" in chk["VOID_no_row_in_the_series_ever_cited_another_row"]
          and "Zero cross-line references exist in any of them" in draft)
    check("the_injected_control_is_cited",
          "found 1 with exactly 1 injected"
          in chk["CONTROL_the_reference_counter_finds_an_injected_reference"]
          and "An injected reference is found" in draft)

    # Attribution, which is the thing it would be worst to get wrong.
    check("credits_both_by_name_and_time",
          "@pm25coder raised typing the retirement cause at 07:11" in draft
          and "@stonianua, who stated it as point 1 at 11:26" in draft)
    # THE POINTER IS GONE, on the pregate's instruction: citing our own earlier comment is a
    # self-attribution it flags, and the paragraph reads complete without it. What must hold is
    # stricter than before: the note-level figure appears in NO form at all.
    check("the_note_level_figure_is_absent_in_every_form",
          not any(f in draft for f in ("122 of 196", "124 of 194", "63.9", "5580153257")),
          "the pregate flagged the pointer, so the figure is simply not here")
    check("the_retraction_of_my_own_excuse_is_in",
          "this morning I said I had no per-event snapshot. That was wrong" in draft)
    check("names_the_next_open_measurement", "Next open measurement" in draft)

    # WITHDRAWN by the red team. Each was in the previous version and must stay out.
    for phrase in ("122 of 196", "the reading all three of us had",
                   "testable without asking anyone what they meant",
                   "Every date in my first table was wrong",
                   "recorded rather than argued for"):
        check("WITHDRAWN_%s" % phrase[:24].replace(" ", "_"), phrase.lower() not in draft.lower())

    check("pure_ascii", all(ord(c) < 128 for c in raw))
    check("no_em_or_en_dash", "—" not in raw and "–" not in raw)
    check("length_fits_the_thread", len(raw) <= 4041, "%d chars against 4041" % len(raw))

    print("\n  %s" % ("all checks passed" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
