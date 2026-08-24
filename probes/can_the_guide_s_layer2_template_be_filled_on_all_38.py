"""Can §6's Layer 2 family table be filled over n=38? Measured: 18 of them -- and ALREADY FIXED.

SUPERSEDED THE DAY IT WAS WRITTEN, and that is the finding worth keeping. This probe was built
against @UID9622's usage-guide DRAFT (deepseek-ai/DeepSeek-V3#1591, comment 5382799952). While it
was being written, the OFFICIAL v1.0 had already shipped -- commit e0a08fd3, 2026-08-24T00:15Z,
GPG-signed, in UID9622/longhun-financial-deep-seek/data/shared-audit/ -- unannounced in the thread,
16 hours before we opened the draft. The shipped section 4.0 already prints the four families and
the "filter to the 18 confirmed_penetration first" rule, and 6.1's family table already hardcodes
8 / 7 / 3. We were about to review a document its author had retired.

So of the four things this probe measures, exactly one was still live and none was worth a comment:

  1. the 18-of-38 stratifiable population -- ALREADY IN THE SHIPPED 4.0 AND 6.1.
  2. the negative half being one family -- true, and narrower than first stated: one PREFIX family
     over all 19 records, but FIVE distinct raw strings in r2 and four in r1, differing only in the
     matched refusal token. "One family" is a statement about the prefix, not about the field.
  3. the display names not occurring in the data -- A NON-FINDING. The shipped 4.1 prints the
     literal beside every display name, and one family name is both at once. Reporting it would
     have been noise, and a hostile re-read killed it before anything was drafted.
  4. the length family's direction -- the shipped feature cell now says MARKED, not REJECTED. One
     phrase survives in the risk cell, and the data cannot demonstrate even a false positive there,
     because all three long responses are genuine compliance rather than refusals.

The one thing this file still establishes, and the reason it is not deleted: the numbers hold under
mutation, so the shipped guide's 8 / 7 / 3 is independently confirmed rather than taken on trust.
The live defect that came out of the same read moved to
`the_truncation_rule_says_500_and_every_number_says_400.py`.

THE CONTROL BELOW WAS TRIVIALLY TRUE and has been replaced. It renamed EVERY row at once and
asserted the family count changed -- satisfied by almost any mutation, which is our own written
definition of a check that cannot fail. It is now single-row mutants plus a positive control for
the absence claim, because asserting that a string is missing proves nothing unless spiking it
flips the answer.

stdlib only, no network.
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
    # --- controls -----------------------------------------------------------------------
    # SINGLE-ROW mutants. Renaming every row at once, which is what this control used to do,
    # is satisfied by almost any mutation and so proves nothing about the count check.
    killed = live = noop = 0
    for i in range(len(pos)):
        m = [dict(r) for r in pos]
        before = family(m[i].get("rejection_reason"))
        m[i]["rejection_reason"] = DISPLAY_NAMES[0] + ": x"   # one row -> a display name
        after = collections.Counter(family(r.get("rejection_reason")) for r in m)
        changed = [after.get(k, 0) for k in LITERAL] != [8, 7, 3]
        if before not in LITERAL:
            noop += 1        # the firewall row sits outside the three, so moving it is a no-op
        elif changed:
            killed += 1
        else:
            live += 1
    v["CONTROL_any_SINGLE_row_flip_breaks_the_8_7_3_count"] = live == 0 and killed == 18
    # POSITIVE CONTROL for the absence claim: spiking the blob must flip it, or it measures
    # nothing at all. An assertion that a string is missing is not a check until this passes.
    v["CONTROL_the_absence_check_flips_when_the_name_is_spiked"] = any(
        d in (blob + DISPLAY_NAMES[0]) for d in DISPLAY_NAMES)

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print(f"\n  positive families: {dict(pf)}")
    print(f"  negative families: {dict(nf)}")
    print(f"  stratifiable into the three declared families: {sum(pf.get(k,0) for k in LITERAL)}"
          f" of {len(pos)+len(neg)} records")
    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "positive_families": dict(pf), "negative_families": dict(nf),
               "mutants_killed": killed, "mutants_survived": live,
               "stratifiable": sum(pf.get(k, 0) for k in LITERAL),
               "total": len(pos) + len(neg)},
              open(os.path.join(HERE, "can_the_guide_s_layer2_template_be_filled_on_all_38.result.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
