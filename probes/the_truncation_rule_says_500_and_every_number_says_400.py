"""SCHEMA says the cut is at 500 characters. Both numbers its own authors published say 400.

@UID9622's SCHEMA.md §2 (v1.0-schema-rev3, shipped 2026-08-24 in
UID9622/longhun-financial-deep-seek/data/shared-audit/) states the rule as: responses over 500
characters are cut AT character 500 and the suffix `...[truncated:500chars]` is appended. The
emitted suffix says 500 too, and that suffix is what a downstream parser reads.

Measured against the published file: the body is 400 characters, the suffix is 23, the record is
423. The rule text is wrong by 100 characters, and so is the string it emits.

The reason this is worth one comment rather than a shrug is that the AUTHORS' OWN PUBLISHED
NUMBERS are already computed from 400, in two different documents:

  * SCHEMA §2's warning gives the published-vs-raw delta range as "3-242 characters". 242 is
    exactly 665 - 423. At the 500-char cut the rule text describes, the largest delta would be 142.
  * The usage guide's §6.2 negative-control statement gives "656 characters unchecked" across the
    three truncated records. 1856 - 3*400 = 656 exactly. At a 500-char body it would be 356.

So the pipeline cuts at 400, the two impact figures were computed from 400, and only the prose and
the emitted marker say 500. This is the shape we keep meeting: the text asserts a value, the
numbers beside it were derived from a different one, and nothing cross-checks the two.

CONTROLS, because the first version of the sibling probe shipped one that could not fail. That
control renamed EVERY row at once and asserted a count changed, which is true of almost any
mutation. Here each check gets a mutant that changes ONE record, plus a positive control for the
absence claim -- an assertion that a string is missing is worthless unless spiking it flips.

stdlib only, no network. The dataset digest is asserted, so this fails loudly rather than quietly
if the file is revised under us.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
POS = os.path.join(HERE, "longhun_shared_audit_dataset_v1.0.jsonl")
DIGEST = "b1a8a650b8038b21505396ea869911008781b26a3adf39ad730edc3d99a2e7f3"
MARKER = "...[truncated:500chars]"
SCHEMA_STATED_CUT = 500          # SCHEMA.md §2, rule text AND the emitted suffix
SCHEMA_STATED_MAX_DELTA = 242    # SCHEMA.md §2, "3-242 characters"
GUIDE_UNCHECKED_CHARS = 656      # usage guide §6.2, "656 字符未检查"


def load(path: str) -> list[dict]:
    if not os.path.exists(path):
        raise SystemExit(f"REFUSED: {path} is absent, so nothing below would be evidence")
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def bodies(rows: list[dict]) -> list[tuple[str, int, int]]:
    """(request_id, body length before the marker, declared raw length) for truncated records."""
    out = []
    for r in rows:
        resp = r.get("response") or ""
        if MARKER not in resp:
            continue
        raw = r.get("rejection_reason") or ""
        digits = "".join(c for c in raw.split("(")[-1].split(")")[0] if c.isdigit())
        out.append((r["request_id"], resp.index(MARKER), int(digits)))
    return out


def main() -> int:
    rows = load(POS)
    got = hashlib.sha256(open(POS, "rb").read()).hexdigest()
    trunc = bodies(rows)
    body_lens = {b for _, b, _ in trunc}
    raws = [w for _, _, w in trunc]
    actual_cut = min(body_lens) if body_lens else -1

    v: dict[str, bool] = {}
    v["the_file_is_the_one_we_measured"] = got == DIGEST
    v["exactly_three_records_carry_the_marker"] = len(trunc) == 3
    v["every_body_is_cut_at_the_SAME_length"] = len(body_lens) == 1
    v["that_length_is_400_not_the_stated_500"] = actual_cut == 400 != SCHEMA_STATED_CUT
    v["the_emitted_marker_itself_states_500"] = "500" in MARKER
    # the two published figures, each reconstructed from the actual cut and from the stated one
    v["SCHEMAs_own_max_delta_reconstructs_at_400"] = (
        max(w - (400 + len(MARKER)) for w in raws) == SCHEMA_STATED_MAX_DELTA)
    v["SCHEMAs_own_max_delta_does_NOT_reconstruct_at_500"] = (
        max(w - (500 + len(MARKER)) for w in raws) != SCHEMA_STATED_MAX_DELTA)
    v["the_guides_656_reconstructs_at_400"] = sum(raws) - 3 * 400 == GUIDE_UNCHECKED_CHARS
    v["the_guides_656_does_NOT_reconstruct_at_500"] = sum(raws) - 3 * 500 != GUIDE_UNCHECKED_CHARS

    # --- controls -------------------------------------------------------------------
    # SINGLE-ROW mutants. The sibling probe's control renamed every row at once, which almost any
    # mutation satisfies; a control has to be defeatable by the smallest real change.
    killed = live = 0
    for i in range(len(rows)):
        m = [dict(r) for r in rows]
        resp = m[i].get("response") or ""
        if MARKER not in resp:
            continue
        m[i]["response"] = resp[:390] + MARKER          # one record cut 10 chars shorter
        t = bodies(m)
        if len({b for _, b, _ in t}) != 1:
            killed += 1
        else:
            live += 1
    v["CONTROL_one_shortened_record_breaks_the_same_length_check"] = killed == 3 and live == 0

    # POSITIVE CONTROL for the reconstruction checks: move the cut and the equalities must fail.
    v["CONTROL_the_656_check_fails_if_the_cut_moves_by_one"] = (
        sum(raws) - 3 * 401 != GUIDE_UNCHECKED_CHARS)
    v["CONTROL_the_delta_check_fails_if_the_cut_moves_by_one"] = (
        max(w - (401 + len(MARKER)) for w in raws) != SCHEMA_STATED_MAX_DELTA)

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print(f"\n  truncated records: {[(i, b, w) for i, b, w in trunc]}")
    print(f"  body {actual_cut} + marker {len(MARKER)} = {actual_cut + len(MARKER)} chars on disk")
    print(f"  SCHEMA rule text and the emitted marker both say {SCHEMA_STATED_CUT}")
    print(f"  their own figures reconstruct at 400: max delta {SCHEMA_STATED_MAX_DELTA}, "
          f"unchecked {GUIDE_UNCHECKED_CHARS}")
    json.dump({"probe": os.path.basename(__file__), "verdicts": v, "sha256": got,
               "truncated": [{"request_id": i, "body": b, "declared_raw": w} for i, b, w in trunc],
               "actual_cut": actual_cut, "stated_cut": SCHEMA_STATED_CUT,
               "mutants_killed": killed, "mutants_survived": live},
              open(os.path.join(HERE, "the_truncation_rule_says_500_and_every_number_says_400.result.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
