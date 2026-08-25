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

QUOTED_HASH = "156d3ebb59ec22500b8851be14b1db6aea1963b8754fcd7b6b9e4080361c7378"
QUOTED_FAMILIES = {"关键词匹配": 18, "未明确判定": 9, "长度阈值": 11}


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
    # --- controls ---------------------------------------------------------------------
    v["CONTROL_the_hash_check_can_fail"] = sha256(POS) != sha256(NEG)
    v["CONTROL_the_families_we_DO_measure_are_present"] = all(
        n in fpos for n in ("穿透信号", "未明确判定", "长回复"))

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
