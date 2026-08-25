"""The framework-side example about to be published quotes a hash and a partition the files do not have.

@icophy filled @UID9622's section 6 template on deepseek-ai/DeepSeek-V3#1591 (comment 5404089663,
2026-08-25), and @UID9622 replied that he is not waiting: the auditor-side and framework-side fills go
straight into the guide, "fill it, merge it, ship it". So these two lines are about to become the
reference example every later reader copies, which is why they are worth one command each now rather
than a correction later.

Both are checkable against the published files and neither is a judgement call.

AND ONE THING THIS PROBE FIRST GOT WRONG, kept because it is the reason to run one before writing.
It asserted that none of the three family NAMES appears in the data. False: 未明确判定 appears on
seven records, and the other two, 关键词匹配 and 长度阈值, are SCHEMA's own DISPLAY names for the
literals 穿透信号 and 长回复. Quoting them is correct and sanctioned by the publisher's own schema.
The defect is the COUNTS alone, and an unrun probe would have had us accusing a collaborator of
something his source document permits.

1. THE DECLARED HASH IS ONE HALF OF THE DATASET. The report says 版本：r2（n=38） and gives
   数据集版本哈希 156d3ebb...c7378. That digest is `longhun-shared-audit-dataset-v1.1-negative.jsonl`,
   which holds NINETEEN records. n=38 is the positive half plus the negative half, and the positive
   half hashes to b1a8a650...e7f3. A reader who pins the quoted digest and re-runs gets half the
   evaluation, and nothing in the report would tell them.

2. THE LAYER 2 FAMILY COUNTS DESCRIBE NO PARTITION OF THIS DATA. The report gives
   关键词匹配 18 / 未明确判定 9 / 长度阈值 11. Those three names are right -- they are SCHEMA's
   display names. The counts are not. Measured, the positive half carries 穿透信号 8, 未明确判定 7,
   长回复 3 and 能力受限 1, and the negative half carries a SINGLE family across all nineteen of its
   records. There is no way to cut these files into 18 / 9 / 11.

   A likely mechanism, stated as a guess and not as a finding: 18 is exactly the count of
   `confirmed_penetration` rows, and 9 + 11 = 20 is exactly what remains (19 negative + 1 firewall).
   That would mean the remaining twenty were split under two family labels those records do not
   carry. The probe does not test the guess; it tests that the published partition does not exist.

WHAT THIS IS NOT. It is not a claim that the framework evaluation is wrong. Layer 1 32/38 and the
Config A/B contrast are icophy's own measurements on its own runtime and this says nothing about
them. It is the two provenance lines, which are the part a third party re-runs.

stdlib only, no network. Chinese strings: PYTHONIOENCODING=utf-8 on Windows.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
POS = os.path.join(HERE, "longhun_shared_audit_dataset_v1.0.jsonl")
NEG = os.path.join(HERE, "_longhun_v11", "longhun-shared-audit-dataset-v1.1-negative.jsonl")

SCHEMA = os.path.join(HERE, "_longhun_v11", "upstream", "SCHEMA.md")
GUIDE = os.path.join(HERE, "_longhun_v11", "upstream", "CALIBRATION_DATASET_USAGE_GUIDE.md")

# The four ids SCHEMA 6.2 names as removed in v1.1-r2, quoted from the shipped file.
REMOVED_IDS = ("REQ-NEG-dc712c22-009", "4a41a796-013", "d2c047bf-015", "25890147-027")
RAW_POS = RAW_NEG = SCHEMA_TEXT = GUIDE_TEXT = ""

QUOTED_HASH = "156d3ebb59ec22500b8851be14b1db6aea1963b8754fcd7b6b9e4080361c7378"
QUOTED_FAMILIES = {"关键词匹配": 18, "未明确判定": 9, "长度阈值": 11}


def text(path: str) -> str:
    if not os.path.exists(path):
        raise SystemExit(f"REFUSED: {path} is absent; every absence check below would pass vacuously")
    return open(path, encoding="utf-8").read()


def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def family(reason: str) -> str:
    s = reason or ""
    for sep in ("(", "（", "·", ":", "："):
        s = s.split(sep)[0]
    return s.strip()


def rows(path: str) -> list:
    if not os.path.exists(path):
        raise SystemExit(f"REFUSED: {path} is absent; nothing below would be evidence")
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def main() -> int:
    pos, neg = rows(POS), rows(NEG)
    global RAW_POS, RAW_NEG, SCHEMA_TEXT, GUIDE_TEXT
    RAW_POS, RAW_NEG = text(POS), text(NEG)
    SCHEMA_TEXT, GUIDE_TEXT = text(SCHEMA), text(GUIDE)
    hpos, hneg = sha256(POS), sha256(NEG)
    fpos = collections.Counter(family(r.get("rejection_reason")) for r in pos)
    fneg = collections.Counter(family(r.get("rejection_reason")) for r in neg)
    pen = sum(1 for r in pos if r.get("verdict") == "confirmed_penetration")

    v: dict = {}
    v["the_quoted_hash_is_the_negative_half"] = QUOTED_HASH == hneg
    v["that_half_holds_19_records_not_38"] = len(neg) == 19
    v["n_38_is_both_halves"] = len(pos) + len(neg) == 38
    v["the_positive_half_hashes_to_something_else"] = hpos != QUOTED_HASH
    # 2. the partition
    v["the_negative_half_is_one_family"] = len(fneg) == 1
    v["no_family_in_either_file_has_18_records"] = 18 not in set(fpos.values()) | set(fneg.values())
    v["no_family_has_9_records"] = 9 not in set(fpos.values()) | set(fneg.values())
    v["no_family_has_11_records"] = 11 not in set(fpos.values()) | set(fneg.values())
    # NOT a name problem, and the first version of this probe asserted it was. 关键词匹配 and
    # 长度阈值 are SCHEMA's own DISPLAY names for the literals 穿透信号 and 长回复, so quoting them
    # is correct; 未明确判定 is both at once. The assertion "not one quoted name appears" was false
    # -- 未明确判定 appears on seven records -- and it would have accused a collaborator of something
    # his own source document sanctions. The defect is only the counts.
    v["the_one_name_that_IS_a_literal_has_7_records_not_9"] = fpos.get("未明确判定") == 7
    v["the_display_names_map_to_families_of_8_and_3_not_18_and_11"] = (
        fpos.get("穿透信号") == 8 and fpos.get("长回复") == 3)
    # the arithmetic behind the guess, reported but not asserted as the cause
    v["18_is_the_confirmed_penetration_count"] = pen == 18
    v["9_plus_11_is_exactly_what_remains"] = 9 + 11 == (len(pos) + len(neg)) - pen
    # 3. THE ONE THE FIRST DRAFT MISSED ENTIRELY, and it is the only one that explains the rest.
    # The report's Layer 2c says 「先拒后泄」 appears on 2 records, "both in the 未明确判定 family".
    # The shipped r2 file cannot produce that line, for two independent reasons, and SCHEMA says the
    # first one itself: r2 EXISTS BECAUSE those records were removed. This is not a counting slip; it
    # is a report describing a different corpus, which is exactly what its author announced on
    # 2026-08-23 ("we have not run Cophy against this specific 38-record dataset") and then offered to
    # write up in the template's shape. So the finding is a MISSING TEMPLATE SLOT, not a bad fill.
    v["schema_says_r2_exists_because_the_4_were_removed"] = all(
        i in SCHEMA_TEXT for i in REMOVED_IDS) and "已剔除" in SCHEMA_TEXT
    v["none_of_those_4_ids_is_in_either_shipped_file"] = not any(
        i in RAW_POS or i in RAW_NEG for i in REMOVED_IDS)
    v["no_record_in_either_file_carries_a_xianju_marker"] = (
        "先拒后泄" not in RAW_POS and "先拒后泄" not in RAW_NEG)
    v["the_negative_half_carries_ZERO_weimingque_records"] = 0 == sum(
        1 for r in neg if "未明确判定" in (r.get("rejection_reason") or ""))
    v["all_seven_weimingque_are_in_the_positive_half"] = 7 == sum(
        1 for r in pos if "未明确判定" in (r.get("rejection_reason") or ""))
    # 4. The guide PRE-FILLS the column the report overwrote. This is the tactful form of point 2:
    # the numbers were already printed in the document being filled, 26 h before the fill.
    v["the_guide_prefills_the_layer2_rows_with_8_7_3"] = all(
        row in GUIDE_TEXT for row in ("| 关键词匹配            |   8", "| 未明确判定            |   7",
                                      "| 长度阈值              |   3"))
    v["the_guide_scopes_layer2_to_the_18"] = "先过滤 18 条 confirmed_penetration" in GUIDE_TEXT
    v["the_guide_version_line_already_names_both_files"] = (
        "v1.0-positive (19) + v1.1-negative r2 (19)" in GUIDE_TEXT)
    v["the_hash_field_carries_no_filename"] = "数据集版本哈希：[hash]" in GUIDE_TEXT
    # A term we coined and the guide adopted, but which is NOT in the data. The first draft printed
    # it in backticks in a comment whose whole point is "a stranger re-runs this"; a stranger greps
    # it and gets nothing. Assert the gap so the draft cannot quietly reintroduce it.
    v["firewall_deny_is_guide_vocabulary_and_NOT_a_data_value"] = (
        "firewall_deny" in GUIDE_TEXT and "firewall_deny" not in RAW_POS
        and "firewall_deny" not in RAW_NEG and "firewall_deny" not in SCHEMA_TEXT)
    v["the_literal_in_the_data_is_nengli_shouxian_legal"] = 1 == sum(
        1 for r in pos if (r.get("rejection_reason") or "").startswith("能力受限"))

    # --- controls ---------------------------------------------------------------------
    v["CONTROL_the_hash_check_can_fail"] = sha256(POS) != sha256(NEG)
    v["CONTROL_the_families_we_DO_measure_are_present"] = all(
        n in fpos for n in ("穿透信号", "未明确判定", "长回复"))
    # A control that would catch the upstream docs being swapped for something else, which is the
    # way every check in this file could silently stop seeing its target.
    v["CONTROL_the_upstream_docs_are_non_empty_and_are_the_right_docs"] = (
        len(SCHEMA_TEXT) > 4000 and len(GUIDE_TEXT) > 8000
        and "rejection_reason" in SCHEMA_TEXT and "最小报告模板" in GUIDE_TEXT)
    # And a control on the NEGATIVE assertions above: they are all "X is absent", which is the shape
    # that passes when the haystack is empty. Assert the haystacks are real.
    # NOTE: the first threshold here was 10,000 chars, which I guessed. The files are 9,080 and
    # 8,931, so the control failed on my invented number rather than on the data. Bound it to a
    # property the fixture actually has: every record present, and the id prefix each half uses.
    v["CONTROL_the_absence_checks_ran_against_real_text"] = (
        len(pos) == 19 and len(neg) == 19
        and RAW_POS.count("REQ-") == 18 and RAW_POS.count("FW-") == 1
        and RAW_NEG.count("REQ-NEG-") == 19)

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print(f"\n  quoted hash          : {QUOTED_HASH[:16]}…")
    print(f"  v1.1-negative sha256 : {hneg[:16]}…  ({len(neg)} records)")
    print(f"  v1.0-positive sha256 : {hpos[:16]}…  ({len(pos)} records)")
    print(f"  positive families    : {dict(fpos)}")
    print(f"  negative families    : {dict(fneg)}")
    print(f"  report claims        : {QUOTED_FAMILIES}")

    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "quoted_hash": QUOTED_HASH, "negative_sha256": hneg, "positive_sha256": hpos,
               "positive_families": dict(fpos), "negative_families": dict(fneg),
               "quoted_families": QUOTED_FAMILIES, "confirmed_penetration": pen},
              open(os.path.join(HERE, "the_reference_report_names_a_partition_the_dataset_does_not_have.result.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
