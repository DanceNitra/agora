"""Assert every factual claim in the #1591 auditor-side comment against the artifacts it cites.

Written after a number in that comment survived three independent verifiers and was still wrong.
The verifier's own gloss said "7 of 8" where the directory holds nine non-signature files, and I
copied the gloss instead of counting. The core claim it rested on was correct; the arithmetic laid
on top of it was not. That is this session's recurring shape -- a verified fact with an unverified
inference sitting on it -- so the fix is to stop asserting counts in prose that nothing recomputes.

Every check below reads the BODY TEXT of the draft and the artifact, and compares them. A claim
that is not present in the text fails loudly rather than passing quietly, so editing the draft
without editing this file breaks the build rather than silently un-checking a line.

Sources, in the order the comment cites them:
  * the dataset            probes/longhun_shared_audit_dataset_v1.0.jsonl (sha256 asserted)
  * the vendored upstream  probes/_longhun_v11/upstream/*  (blob shas asserted by the sibling probe)
  * the live directory     for the signature count only, since that is a property of the repo
                           rather than of any file we hold

stdlib plus `gh` for the directory listing. PYTHONIOENCODING=utf-8 on Windows.

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check
inside VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and
storm when the claim rests on literature. Owner, 2026-08-26, after I called a file like
this one "the gate" three times in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO
HOVEN." tools/send_approved.py now refuses to publish without a receipt from each skill,
bound to the draft's bytes, so this file cannot stand in for them any more.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(os.path.dirname(HERE), "agora_output", "drafts",
                     "reply_1591_auditor_side_report.md")
DATA = os.path.join(HERE, "longhun_shared_audit_dataset_v1.0.jsonl")
UP = os.path.join(HERE, "_longhun_v11", "upstream")
SHA = "b1a8a650b8038b21505396ea869911008781b26a3adf39ad730edc3d99a2e7f3"
REPO = "UID9622/longhun-financial-deep-seek"


def body() -> str:
    """Only what gets posted: everything after the first standalone --- line."""
    t = open(DRAFT, encoding="utf-8").read()
    marker = "\n---\n"
    if marker not in t:
        raise SystemExit("REFUSED: no provenance separator in the draft; cannot isolate the body")
    return t.split(marker, 1)[1]


def main() -> int:
    b = body()
    rows = [json.loads(x) for x in open(DATA, encoding="utf-8") if x.strip()]
    docs = {n: open(os.path.join(UP, n), encoding="utf-8").read()
            for n in os.listdir(UP) if not n.endswith(".txt")}

    trunc, deltas = [], []
    for r in rows:
        raw_m = re.search(r"\((\d+)字符\)", r.get("rejection_reason") or "")
        resp = r.get("response") or ""
        if raw_m:
            deltas.append((r["request_id"], int(raw_m.group(1)), len(resp),
                           int(raw_m.group(1)) - len(resp)))
        m = re.search(r"\.\.\.\[truncated:(\d+)chars\]", resp)
        if m and raw_m:
            trunc.append((r["request_id"], resp.index("...[truncated"),
                          int(raw_m.group(1)), int(m.group(1))))
    ds = sorted(d for _, _, _, d in deltas)

    # the live directory, for the signature claim only
    out = subprocess.run(["gh", "api", f"repos/{REPO}/contents/data/shared-audit", "--jq",
                          ".[].name"], capture_output=True, text=True)
    names = [x.strip() for x in (out.stdout or "").splitlines() if x.strip()]
    if not names:
        raise SystemExit("REFUSED: could not list the upstream directory; the signature claim "
                         "would be unchecked and this file exists to stop exactly that")
    sigs = {n[:-4] for n in names if n.endswith(".asc")}
    nonsig = [n for n in names if not n.endswith(".asc")]
    signed = [n for n in nonsig if n in sigs]
    unsigned = [n for n in nonsig if n not in sigs]

    v: dict[str, bool] = {}
    v["dataset_digest_matches"] = hashlib.sha256(open(DATA, "rb").read()).hexdigest() == SHA
    # --- claims stated in the body, each recomputed ---
    v["body_says_19_records_and_there_are_19"] = "19 条" in b and len(rows) == 19
    v["the_elided_sha_head_and_tail_are_real"] = (
        "`b1a8a650…c3d99a2e7f3`" in b and SHA.startswith("b1a8a650") and SHA.endswith("c3d99a2e7f3"))
    v["the_full_sha_in_the_command_is_the_files"] = SHA in b
    v["body_says_15_and_10_checks"] = "15 项检查" in b and "只跑 10 项" in b
    v["family_counts_in_the_command_match_the_file"] = all(
        f'--expect-family "{name}={n}"' in b and sum(
            1 for r in rows if (r.get("rejection_reason") or "").startswith(name)) == n
        for name, n in (("穿透信号", 8), ("未明确判定", 7), ("长回复", 3)))
    v["the_three_truncated_ids_in_the_command_are_the_truncated_records"] = (
        {i for i, _, _, _ in trunc} == {"REQ-55072cb7-001", "REQ-c9613162-002", "REQ-b59745a2-005"}
        and all(f"--expect-truncated {i}" in b for i, _, _, _ in trunc))
    v["the_utf8_byte_counts_428_877_412_are_right"] = (
        "428、877、412" in b and [len((r.get("response") or "")[:400].encode("utf-8"))
                                  for r in rows
                                  if "...[truncated" in (r.get("response") or "")] == [428, 877, 412])
    v["bodies_are_400_code_points"] = all(x == 400 for _, x, _, _ in trunc) and "400 code points" in b
    v["the_generator_lines_are_30_and_51"] = (
        "Line 30 and line 51" in b
        and docs["lh_shared_audit_extract.py"].splitlines()[29].startswith("RESP_MAX = 400")
        and "truncated:{}chars" in docs["lh_shared_audit_extract.py"].splitlines()[50])
    v["the_three_expected_markers_named_in_the_body_are_the_raw_counts"] = all(
        f"truncated:{raw}chars" in b for _, _, raw, _ in trunc)
    v["all_three_actually_read_500"] = all(st == 500 for _, _, _, st in trunc)
    # THE ONE THAT SLIPPED: recompute the signature count instead of quoting a gloss
    v["signature_count_in_the_body_matches_the_directory"] = (
        f"Eight of the nine" in b and (len(signed), len(nonsig)) == (8, 9))
    v["exactly_one_unsigned_file_and_it_is_the_extractor"] = unsigned == ["lh_shared_audit_extract.py"]
    v["the_delta_list_in_the_body_is_the_real_one"] = str(ds).replace(" ", "") in b.replace(" ", "")
    v["ten_records_carry_a_count"] = len(deltas) == 10 and "all ten records" in b
    v["schema_table_span_133_to_242"] = (
        "133 to 242" in b and [d for d in ds if d > 100] == [133, 212, 242])
    v["the_zero_delta_record_is_named_correctly"] = (
        "`REQ-9bd5cb4a-016` is 67 → 67" in b
        and [(i, w, p) for i, w, p, d in deltas if d == 0] == [("REQ-9bd5cb4a-016", 67, 67)])
    v["eleven_of_nineteen_carry_only_wufenlei"] = (
        "11 of 19" in b and sum(1 for r in rows if r.get("attack_category") == ["未分类"]) == 11)
    six = ["REQ-092f07cc-007", "REQ-48e69b0a-008", "REQ-c3ed0a88-010", "REQ-07040579-011",
           "REQ-082959a1-003", "REQ-d7258422-004"]
    cats = [next(r for r in rows if r["request_id"] == i).get("attack_category") for i in six]
    v["the_six_split_four_one_one"] = (
        sum(1 for c in cats if c == ["未分类"]) == 4
        and cats.count(["数据泄露"]) == 1 and cats.count(["伪装权威"]) == 1
        and "four carry only" in b)
    # Stated as "two" in an earlier draft because a verifier handed me a Counter over category
    # TUPLES (2 records sharing one pair, 1 record with another) and I read the 2 as a record
    # count. Second number in this comment taken from a gloss instead of recomputed, so the gate
    # now derives the word from the data rather than checking a word I chose.
    n_multi = sum(1 for r in rows if len(r.get("attack_category") or []) == 2)
    v["multi_category_count_matches_the_word_in_the_body"] = (
        {2: "two", 3: "three", 4: "four"}[n_multi] + " of them carry two values" in b)
    v["quoted_schema_strings_are_present_upstream"] = all(
        q in docs["SCHEMA.md"] for q in ("3–242 字符", "发布版始终更短",
                                          "方向固定：发布版更短",
                                          "发布版 response 长度 ≤ rejection_reason 中字符数"))
    # --- controls -------------------------------------------------------------------
    v["CONTROL_a_wrong_signature_count_would_fail"] = "Seven of the eight" not in b
    v["CONTROL_the_body_is_not_the_provenance_block"] = "STATUS:" not in b and "RECEIPTS:" not in b
    v["CONTROL_a_missing_claim_fails_rather_than_passes"] = "this string is not in the draft" not in b

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    bad = [k for k, ok in v.items() if not ok]
    print(f"\n  {len(v) - len(bad)}/{len(v)} claims recomputed from source")
    if bad:
        print("  FAILED: " + ", ".join(bad))
    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "non_signature_files": len(nonsig), "signed": len(signed), "unsigned": unsigned},
              open(os.path.join(HERE, "gate_1591_auditor_report_body.result.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
