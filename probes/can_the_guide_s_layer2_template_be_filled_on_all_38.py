"""Can §6's Layer 2 family table actually be filled over n=38? Measured: no, over 18 of 38.

@UID9622's usage-guide draft (deepseek-ai/DeepSeek-V3#1591, comment 5382799952) tells a reader to
report Layer 1 over `n=38` and then, in the SAME report, stratify Layer 2 into the three
`rejection_reason` families. Both halves of the dataset are on disk, so this is checkable rather
than arguable, and our own rule says a template that cannot be filled is a defect found by trying.

Three claims, each asserted against the published files:

  1. The three declared families live ENTIRELY in the positive half's confirmed_penetration rows.
     The negative half carries one single family string for all 19 of its records, and the positive
     half's one firewall row carries a fourth. So the stratifiable population is 18, not 38.

  2. §4 names the families with SCHEMA's DISPLAY names (关键词匹配, 长度阈值). The field carries
     different literal prefixes (穿透信号, 长回复). SCHEMA §1 maps them; §4 does not, and §4 is the
     section that hands the reader a pandas filter. Neither display name occurs in either file.

  3. §4 describes the length family as "响应超过长度限制 -> 拒绝" and its risk as "误拒合理长响应".
     SCHEMA says the opposite direction: the row is MARKED 可能穿透, and every such row carries
     verdict confirmed_penetration, not a rejection. The failure mode is a false penetration flag.

Every assertion below fails loudly if the files stop saying this. stdlib only, no network.
"""
from __future__ import annotations

import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
POS = os.path.join(HERE, "longhun_shared_audit_dataset_v1.0.jsonl")
NEG = os.path.join(HERE, "_longhun_v11", "longhun-shared-audit-dataset-v1.1-negative.jsonl")

DISPLAY_NAMES = ["\u5173\u952e\u8bcd\u5339\u914d", "\u957f\u5ea6\u9608\u503c"]   # 关键词匹配, 长度阈值
LITERAL = ["\u7a7f\u900f\u4fe1\u53f7", "\u672a\u660e\u786e\u5224\u5b9a", "\u957f\u56de\u590d"]  # 穿透信号/未明确判定/长回复


def load(path: str) -> list[dict]:
    if not os.path.exists(path):
        raise SystemExit(f"REFUSED: {path} is absent, so nothing below would be evidence")
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def family(reason: str) -> str:
    """SCHEMA embeds a per-record measurement in the prefix, so cut at the first of ( . :"""
    s = reason or ""
    for sep in ("(", "\uff08", "\u00b7", ":", "\uff1a"):
        s = s.split(sep)[0]
    return s.strip()


def main() -> int:
    pos, neg = load(POS), load(NEG)
    pf = collections.Counter(family(r.get("rejection_reason")) for r in pos)
    nf = collections.Counter(family(r.get("rejection_reason")) for r in neg)
    pen = [r for r in pos if r.get("verdict") == "confirmed_penetration"]

    v: dict[str, bool] = {}
    v["the_two_halves_are_19_and_19"] = (len(pos), len(neg)) == (19, 19)
    v["the_guide_s_n_38_is_their_sum"] = len(pos) + len(neg) == 38
    # 1. the stratifiable population
    v["the_negative_half_is_ONE_family"] = len(nf) == 1
    v["the_three_declared_families_are_8_7_3"] = [
        pf.get(k, 0) for k in LITERAL] == [8, 7, 3]
    v["they_cover_exactly_the_18_penetration_rows"] = sum(
        pf.get(k, 0) for k in LITERAL) == len(pen) == 18
    v["so_layer2_is_fillable_on_18_of_38_not_38"] = (
        sum(pf.get(k, 0) for k in LITERAL) == 18 and len(pos) + len(neg) == 38)
    # 2. display names vs literal prefixes
    blob = open(POS, encoding="utf-8").read() + open(NEG, encoding="utf-8").read()
    v["neither_display_name_occurs_in_either_file"] = not any(d in blob for d in DISPLAY_NAMES)
    v["every_literal_prefix_does_occur"] = all(k in blob for k in LITERAL)
    # 3. the length family's direction
    long_rows = [r for r in pos if family(r.get("rejection_reason")) == LITERAL[2]]
    v["every_long_response_row_is_flagged_penetration"] = bool(long_rows) and all(
        r.get("verdict") == "confirmed_penetration" for r in long_rows)
    v["none_of_them_is_a_rejection"] = all(r.get("verdict") != "rejected" for r in long_rows)
    # control: the assertions above must be capable of failing on a mutated frame
    mutated = [dict(r, rejection_reason="\u5173\u952e\u8bcd\u5339\u914d: x") for r in pos]
    v["CONTROL_a_renamed_prefix_breaks_the_8_7_3_count"] = [
        collections.Counter(family(r.get("rejection_reason")) for r in mutated).get(k, 0)
        for k in LITERAL] != [8, 7, 3]

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print(f"\n  positive families: {dict(pf)}")
    print(f"  negative families: {dict(nf)}")
    print(f"  stratifiable into the three declared families: {sum(pf.get(k,0) for k in LITERAL)}"
          f" of {len(pos)+len(neg)} records")
    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "positive_families": dict(pf), "negative_families": dict(nf),
               "stratifiable": sum(pf.get(k, 0) for k in LITERAL),
               "total": len(pos) + len(neg)},
              open(os.path.join(HERE, "can_the_guide_s_layer2_template_be_filled_on_all_38.result.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
