"""Gate the #1591 ledger-history reply: every claim recomputed against a fresh clone, live.

WHAT CAN GO WRONG HERE, in the order it has gone wrong before in this thread:

  1. THE DEFECT IS ALREADY FIXED. Twice this thread has handed us a finding its author had already
     corrected. So the gate re-clones the repository and re-runs the checker at gate time, and fails
     if the unlogged state is no longer unlogged. It is not enough that the probe found it earlier.

  2. WE CLAIM THE GAP WHERE THE SUITE ALREADY COVERS IT. Fetched live: his checker's own source must
     contain no reference to CHANGELOG or git, or "C01 to C10 never open it" is false.

  3. WE OVERSTATE WHAT FIRED. Three of the four rules do NOT fire, and the draft says so. A version
     that reports only the hit is a version that implies the ledger is fabricated. There is a check
     that the non-firing rules are named and a mutation that removes them.

  4. THE REMEDY IS ASSERTED RATHER THAN TESTED. The draft says two lines fix it; the gate applies
     exactly those two lines to the real ledger and requires the checker to come back clean.

  5. WE CLAIM NOVELTY. The prior art sentence must be present.

  6. WE MISQUOTE @qingkong66. His line is fetched from the live comment and must be byte-present.

House rules for this thread specifically, both set by the owner: sign as DanceNitra only, no
personal name, and NO "written with AI assistance" line, which belongs in other threads but not
this one.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_1591_ledger_history_check.md")
REPO = "https://github.com/UID9622/longhun-financial-deep-seek.git"
QK_COMMENT = "5426973801"

sys.path.insert(0, HERE)
import does_the_ledger_match_the_history as C  # noqa: E402


def gh_body(cid: str) -> str:
    r = subprocess.run(["gh", "api", "repos/deepseek-ai/DeepSeek-V3/issues/comments/" + cid,
                        "--jq", ".body"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def fetch_checker() -> str:
    r = subprocess.run(["gh", "api",
                        "repos/UID9622/longhun-financial-deep-seek/contents/"
                        "integrity/calibration_dataset_check.py", "--jq", ".content"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    import base64
    return base64.b64decode(r.stdout).decode("utf-8", "replace")


def check(draft: str, findings: list, fixed_findings: list, hist: dict, checker: str,
          qk: str, checked_n: int, fixed_n: int) -> dict:
    v: dict = {}
    rules = {f["rule"] for f in findings}

    # ---- the defect is still live, re-measured at gate time --------------------------------------
    v["THE_UNLOGGED_STATE_IS_STILL_UNLOGGED"] = any(
        f["rule"] == "L3" and "fb267b62" in f["detail"] for f in findings)
    # EVERY occurrence, not the first. `b78c9509` appears twice, so a presence check passed a
    # draft whose first copy had been corrupted -- the same occurrence-vs-presence defect that got
    # through this morning's gate on "27 trials".
    def all_agree(prefix: str, correct: str) -> bool:
        hits = re.findall(prefix + r"[0-9a-f]*", draft)
        return bool(hits) and all(h == correct for h in hits)

    v["and_the_draft_names_that_commit_and_hash"] = (
        all_agree("fb267b", "fb267b62") and all_agree("b78c95", "b78c9509"))
    neg = [p for p in hist if "negative" in p][0]
    v["CONTROL_that_state_really_is_in_git"] = any(
        r["short"] == "fb267b62" and r["sha256"].startswith("b78c9509") for r in hist[neg])
    v["the_label_finding_is_labelled_heuristic"] = (
        "L4" in rules and "commit messages are prose" in draft
        and "should not rest on that" in draft)
    v["the_draft_puts_the_mechanical_rule_first"] = (
        draft.index("must be named by some ledger entry") < draft.index("label mismatch"))

    # ---- what did NOT fire, said out loud ----------------------------------------------------------
    v["THE_NON_FIRING_RULES_ARE_REPORTED"] = (
        "L1" not in rules and "L2" not in rules
        and "not fabricated and not shuffled" in draft
        and "neither fires here" in draft)

    # ---- the gap claim, against his live source -----------------------------------------------------
    v["CONTROL_his_checker_was_actually_fetched"] = "C01" in checker and len(checker) > 4000
    v["his_suite_really_does_not_read_the_ledger_or_git"] = not (
        "CHANGELOG" in checker or re.search(r"\bgit\b", checker))
    v["the_draft_states_that_narrowly"] = "never open `CHANGELOG.jsonl` and never touch git" in draft

    # ---- the remedy was applied, not asserted ---------------------------------------------------------
    v["THE_REMEDY_WAS_TESTED_AND_IT_CLEARS"] = not fixed_findings
    v["the_remedy_adds_exactly_one_hash"] = fixed_n == checked_n + 1
    v["the_draft_reports_that_count"] = (
        "five hashes checked instead of four" in draft and checked_n == 4)
    v["the_draft_says_it_was_tested_not_assumed"] = "I tested it rather than assuming" in draft

    # ---- controls, novelty, caveat ---------------------------------------------------------------------
    v["the_checkers_own_controls_are_described"] = (
        "invented hash must fail" in draft and "at least one real entry must pass" in draft)
    v["the_refusal_conditions_are_described"] = "absent, empty, or records no hashes" in draft
    v["NO_NOVELTY_CLAIM"] = (
        "None of this is a new idea" in draft and "in-toto" in draft and "SLSA" in draft)
    v["the_assumption_behind_the_rule_is_stated"] = (
        "convention rather than a fact" in draft and "every revision" in draft)

    # ---- attribution ---------------------------------------------------------------------------------------
    v["CONTROL_his_comment_was_actually_fetched"] = len(qk) > 200
    v["qingkong66_really_said_CI_cannot_do_this"] = (
        "cannot catch whether the ledger description matches the actual revisions" in qk)
    v["we_credit_him_rather_than_correcting_him_flatly"] = (
        "you are right about the suite as it stands" in draft)

    # ---- house style for THIS thread -------------------------------------------------------------------------
    v["NO_AI_DISCLOSURE_LINE_IN_THIS_THREAD"] = "AI assistance" not in draft
    v["no_personal_name"] = not re.search(r"[Rr]astislav|Draho[sš]", draft)
    v["no_em_or_en_dash"] = not ("—" in draft or "–" in draft or " -- " in draft)
    v["length_is_reasonable"] = 350 < len(draft.split()) < 650

    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "humanizer_receipt.py"),
                        "check", DRAFT], capture_output=True, text=True)
    v["the_humanizer_SKILL_ran_on_THESE_bytes"] = r.returncode == 0
    return v


def main() -> int:
    draft = io.open(DRAFT, encoding="utf-8").read()

    # A FRESH clone at gate time. A stale one would let a fix land upstream without this noticing.
    tmp = tempfile.mkdtemp(prefix="lhgate_")
    repo = os.path.join(tmp, "lh")
    r = subprocess.run(["git", "clone", "-q", REPO, repo], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("REFUSED: could not clone %s: %s" % (REPO, (r.stderr or "").strip()))

    lp = os.path.join(repo, C.LEDGER)
    ledger = [json.loads(l) for l in io.open(lp, encoding="utf-8") if l.strip()]
    known = [l.strip() for l in C.git(repo, "ls-files", "data/shared-audit").splitlines()
             if l.strip().endswith(".jsonl") and "CHANGELOG" not in l]
    hist = {p: C.history(repo, p) for p in known}
    findings, checked = C.audit(repo, ledger, hist, known)

    # THE REMEDY, applied to the real ledger exactly as the draft describes it.
    neg = [p for p in known if "negative" in p][0]
    r1 = [x for x in hist[neg] if x["short"] == "fb267b62"]
    if not r1:
        raise SystemExit("REFUSED: fb267b62 is not in the history of %s any more" % neg)
    fixed = [dict(e) for e in ledger]
    fixed.insert(1, {"ts": "2026-08-21T00:00:00+08:00", "version": "v1.1-r1", "action": "publish",
                     "scope": os.path.basename(neg), "detail": "19 negative records, pre-review",
                     "sha256_after": r1[0]["sha256"], "author": "UID9622"})
    for e in fixed:
        if e.get("version") == "v1.1-r1" and e.get("sha256_after", "").startswith("156d3ebb"):
            e["version"] = "v1.1-r2"
    fixed_findings, fixed_checked = C.audit(repo, fixed, hist, known)

    checker = fetch_checker()
    qk = gh_body(QK_COMMENT)
    if not checker or not qk:
        raise SystemExit("REFUSED: could not fetch his checker or @qingkong66's comment; both "
                         "claims would be unverified")

    v = check(draft, findings, fixed_findings, hist, checker, qk, len(checked), len(fixed_checked))
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))
    passed = sum(1 for x in v.values() if x)
    print("\n  %d/%d checks, %d words, %d findings live, %d after the remedy"
          % (passed, len(v), len(draft.split()), len(findings), len(fixed_findings)))

    if "--mutate" in sys.argv:
        print("\n  MUTATION SELF-TEST")
        muts = [("wrong commit", "fb267b62", "fb267b63"),
                ("wrong hash", "b78c9509", "b78c9510"),
                ("drop the heuristic label", "commit messages are prose",
                 "commit messages are reliable"),
                ("hide what did not fire", "not fabricated and not shuffled",
                 "unreliable throughout"),
                ("overstate the gap", "never open `CHANGELOG.jsonl` and never touch git",
                 "check nothing at all"),
                ("assert the remedy", "I tested it rather than assuming",
                 "it is obvious"),
                ("wrong remedy count", "five hashes checked instead of four",
                 "six hashes checked instead of four"),
                ("drop the controls", "invented hash must fail", "checker is reliable"),
                ("claim novelty", "None of this is a new idea", "This is a new idea"),
                ("drop the caveat", "convention rather than a fact", "fact about ledgers"),
                ("flatten the credit", "you are right about the suite as it stands",
                 "you were wrong"),
                ("add the AI line", "Point it at a clone.",
                 "Point it at a clone. Written with AI assistance."),
                ("em dash", "Point it at a clone.", "Point it at a clone —.")]
        caught = 0
        for label, a, b in muts:
            if a not in draft:
                print("    SKIP   %s: anchor absent, mutation vacuous" % label)
                continue
            mv = check(draft.replace(a, b, 1), findings, fixed_findings, hist, checker, qk,
                       len(checked), len(fixed_checked))
            broke = [k for k in v if v[k] and not mv.get(k)]
            caught += bool(broke)
            print("    %s  %s%s" % ("CAUGHT" if broke else "MISSED", label,
                                    (" -> " + broke[0]) if broke else ""))
        print("    %d/%d mutations caught" % (caught, len(muts)))
        return 0 if (passed == len(v) and caught == len(muts)) else 1
    return 0 if passed == len(v) else 1


if __name__ == "__main__":
    sys.exit(main())
