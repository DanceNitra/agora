"""RECHECK THE FIGURES in the #1591 ledger reply, against live sources at run time.

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check inside
VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and storm when the claim
rests on literature. Owner, 2026-08-26, after I called a file like this one "the gate" three times
in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO HOVEN." tools/send_approved.py now refuses
to publish without a receipt from each skill, bound to the draft's bytes, so this file cannot stand
in for them any more.

WHAT IT RECOMPUTES, and every one of these is fetched or re-derived rather than trusted:

  * the two announcement comments, their ids, authors, hashes, the 作废 string and the eighteen
    minutes between them, from the live GitHub API;
  * the ledger's current state, from a FRESH clone at run time, because the whole comment is about
    a defect its author may fix at any moment and has fixed everything else within hours;
  * the two Chinese sentences quoted from his README and MANIFEST, byte-present in the live files;
  * the remedy, APPLIED to a copy and re-run, never asserted;
  * the shallow-clone refusal, by actually cloning at depth 1 and reading the exit code directly,
    not through a pipe;
  * that the probe the comment points at RESOLVES on our public default branch. An earlier comment
    of ours cited a probe that 404'd for every reader who followed it.
"""
from __future__ import annotations

import base64
import datetime as dt
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
API = "repos/UID9622/longhun-financial-deep-seek"
OURS = "probes/does_the_ledger_match_the_history.py"
R1_ANNOUNCE, R2_ANNOUNCE = "5365183869", "5365297051"

sys.path.insert(0, HERE)
import does_the_ledger_match_the_history as C  # noqa: E402


def gh(*args: str) -> str:
    r = subprocess.run(["gh", "api", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def comment(cid: str) -> dict:
    out = gh("repos/deepseek-ai/DeepSeek-V3/issues/comments/" + cid)
    return json.loads(out) if out else {}


def repo_file(path: str) -> str:
    out = gh(f"{API}/contents/{path}", "--jq", ".content")
    return base64.b64decode(out).decode("utf-8", "replace") if out.strip() else ""


def check(draft: str, a1: dict, a2: dict, ledger: list, hist: dict, neg: str,
          readme: str, manifest: str, workflow: str, remedy: tuple, shallow_rc: int,
          ours_size: int) -> dict:
    v: dict = {}
    b1, b2 = a1.get("body", ""), a2.get("body", "")
    R1 = [r for r in hist[neg] if r["short"] == "fb267b62"]
    R2 = [r for r in hist[neg] if r["short"] == "6aa23b9f"]

    # ---- the two announcements, live -----------------------------------------------------------
    v["CONTROL_both_announcements_were_fetched"] = bool(b1) and bool(b2)
    v["both_are_his"] = a1.get("user", {}).get("login") == "UID9622" == a2.get("user", {}).get(
        "login")
    v["he_announced_b78c9509_first"] = "b78c9509b708" in b1 and "156d3ebb" not in b1
    v["he_announced_156d3ebb_second_and_voided_the_first"] = (
        "156d3ebb59ec" in b2 and "b78c9509" in b2 and "作废" in b2)
    gap = (dt.datetime.fromisoformat(a2["created_at"].replace("Z", "+00:00"))
           - dt.datetime.fromisoformat(a1["created_at"].replace("Z", "+00:00")))
    v["the_gap_really_is_eighteen_minutes"] = (
        abs(gap.total_seconds() - 18 * 60) < 90 and "eighteen minutes later" in draft)
    v["the_draft_cites_both_comment_ids"] = R1_ANNOUNCE in draft and R2_ANNOUNCE in draft
    v["the_draft_quotes_the_void_string"] = "原 b78c9509... 作废" in draft and "作废" in b2

    # ---- the ledger as it stands right now -------------------------------------------------------
    by_ver = {e.get("version"): e for e in ledger}
    v["THE_DEFECT_IS_STILL_LIVE_r1_carries_r2s_hash"] = (
        by_ver.get("v1.1-r1", {}).get("sha256_after", "").startswith("156d3ebb"))
    v["AND_r2_still_carries_no_hash"] = not any(
        k.startswith("sha256_after") for k in by_ver.get("v1.1-r2", {}))
    v["the_draft_says_both"] = (
        "puts `156d3ebb…` under `v1.1-r1`" in draft and "gives `v1.1-r2` no hash at all" in draft)

    # ---- the history, re-derived ------------------------------------------------------------------
    v["fb267b62_really_produced_b78c9509"] = bool(R1) and R1[0]["sha256"].startswith("b78c9509")
    v["6aa23b9f_really_produced_156d3ebb"] = bool(R2) and R2[0]["sha256"].startswith("156d3ebb")
    v["no_entry_carries_the_r1_state"] = not any(
        R1[0]["sha256"] in json.dumps(e) for e in ledger)
    v["the_draft_names_both_commits"] = "fb267b62" in draft and "6aa23b9f" in draft

    # ---- his own words, byte-present ---------------------------------------------------------------
    v["CONTROL_his_readme_and_manifest_were_fetched"] = len(readme) > 400 and len(manifest) > 400
    v["the_readme_quote_is_byte_present"] = (
        "修订链（append-only）" in readme and "每次发布/剔除/升级有据可查" in readme
        and "修订链（append-only）" in draft and "每次发布/剔除/升级有据可查" in draft
        and "data/shared-audit/README.md" in draft)
    v["the_manifest_quote_is_byte_present"] = (
        "变更全程记录于 `CHANGELOG.jsonl`（append-only）" in manifest
        and "变更全程记录于 `CHANGELOG.jsonl`（append-only）" in draft
        and "data/shared-audit/MANIFEST.md" in draft)

    # ---- the remedy, applied not asserted ----------------------------------------------------------
    findings_after, checked_after, labels = remedy
    v["THE_REMEDY_WAS_APPLIED_AND_IT_CLEARS"] = not findings_after
    v["the_remedy_checks_five_hashes"] = checked_after == 5 and "five hashes checked" in draft
    v["the_remedy_makes_no_duplicate_label"] = (
        len(labels) == len(set(labels)) and "no duplicate labels" in draft)
    v["the_remedy_adds_no_entry"] = len(labels) == len(ledger) and "no new entry" in draft
    v["the_draft_says_it_was_applied_to_a_copy"] = "applied it to a copy rather than assuming" in draft

    # ---- the caveats the draft states against itself -------------------------------------------------
    v["THE_SHALLOW_CLONE_NOW_REFUSES"] = shallow_rc != 0
    v["the_draft_reports_what_it_did_before"] = (
        "two false findings on genuine hashes" in draft and "every one of its controls reported "
        "green" in draft)
    v["their_workflow_really_sets_no_fetch_depth"] = (
        "actions/checkout" in workflow and "fetch-depth" not in workflow
        and "fetch-depth: 0" in draft)
    v["the_rewritable_history_caveat_is_stated"] = (
        "lint over a mutable substrate, not an attestation" in draft)

    # ---- prior art, named correctly -------------------------------------------------------------------
    v["the_property_is_named_completeness"] = (
        "completeness, or omission detection" in draft
        and not re.search(r"(?<!and )consistency proof(?!s and neither)", draft))
    v["CT_is_described_correctly"] = (
        "inclusion and consistency proofs and neither is this one" in draft
        and "leaves it to monitors" in draft)
    v["the_paper_is_cited_in_full"] = all(
        s in draft for s in ("Torres-Arias", "Ammula", "Curtmola", "Cappos",
                             "On Omitting Commits and Committing Omissions",
                             "USENIX Security 2016", "Reference State Log"))
    v["and_where_it_stops_short_is_stated"] = "only from adoption onward" in draft

    # ---- the pointer must resolve ----------------------------------------------------------------------
    v["THE_PROBE_WE_POINT_AT_IS_PUBLIC"] = ours_size > 0
    v["the_draft_names_that_path"] = OURS in draft

    # ---- house style for THIS thread ---------------------------------------------------------------------
    v["NO_AI_DISCLOSURE_LINE_IN_THIS_THREAD"] = "AI assistance" not in draft
    v["no_personal_name"] = not re.search(r"[Rr]astislav|Draho[sš]", draft)
    v["no_em_or_en_dash"] = not ("—" in draft or "–" in draft or " -- " in draft)
    v["length_is_reasonable"] = 350 < len(draft.split()) < 650

    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "humanizer_receipt.py"),
                        "status", DRAFT], capture_output=True, text=True)
    v["ALL_THREE_SKILL_RECEIPTS_EXIST"] = r.returncode == 0
    return v


def main() -> int:
    draft = io.open(DRAFT, encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="lh1591_")
    full = os.path.join(tmp, "full")
    if subprocess.run(["git", "clone", "-q", REPO, full], capture_output=True).returncode:
        raise SystemExit("REFUSED: could not clone the repository")

    ledger = [json.loads(l) for l in io.open(os.path.join(full, C.LEDGER), encoding="utf-8")
              if l.strip()]
    known = [l.strip() for l in C.git(full, "ls-files", "data/shared-audit").splitlines()
             if l.strip().endswith(".jsonl") and "CHANGELOG" not in l]
    hist = {p: C.history(full, p) for p in known}
    neg = [p for p in known if "negative" in p][0]

    # THE REMEDY, applied to a copy exactly as the draft describes it.
    r1 = [r for r in hist[neg] if r["short"] == "fb267b62"][0]["sha256"]
    r2 = [r for r in hist[neg] if r["short"] == "6aa23b9f"][0]["sha256"]
    patched = [dict(e) for e in ledger]
    for e in patched:
        if e.get("version") == "v1.1-r1":
            e["sha256_after"] = r1
        if e.get("version") == "v1.1-r2":
            e["sha256_after"] = r2
    f_after, c_after = C.audit(full, patched, hist, known)
    remedy = (f_after, len(c_after), [e.get("version") for e in patched])

    # THE SHALLOW REFUSAL, measured. Exit code read directly, never through a pipe.
    shallow = os.path.join(tmp, "shallow")
    subprocess.run(["git", "clone", "-q", "--depth", "1", REPO, shallow], capture_output=True)
    shallow_rc = subprocess.run(
        [sys.executable, os.path.join(HERE, "does_the_ledger_match_the_history.py"), shallow],
        capture_output=True).returncode

    a1, a2 = comment(R1_ANNOUNCE), comment(R2_ANNOUNCE)
    # THE RIGHT FILES. The first version fetched the ROOT README, where neither sentence lives;
    # both are under data/shared-audit/. It would have quoted his own words from a file that
    # does not contain them.
    readme = repo_file("data/shared-audit/README.md")
    manifest = repo_file("data/shared-audit/MANIFEST.md")
    wf = repo_file(".github/workflows/integrity.yml")
    size = gh(f"repos/DanceNitra/agora/contents/{OURS}?ref=main", "--jq", ".size").strip()
    ours_size = int(size) if size.isdigit() else 0

    if not (a1 and a2 and readme and manifest and wf):
        raise SystemExit("REFUSED: a live source could not be fetched; claims resting on it would "
                         "be unverified")

    v = check(draft, a1, a2, ledger, hist, neg, readme, manifest, wf, remedy, shallow_rc, ours_size)
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))
    passed = sum(1 for x in v.values() if x)
    print("\n  %d/%d recomputed, %d words, remedy leaves %d findings, shallow rc=%d, our probe %d B"
          % (passed, len(v), len(draft.split()), len(f_after), shallow_rc, ours_size))
    return 0 if passed == len(v) else 1


if __name__ == "__main__":
    sys.exit(main())
