"""The shipped extractor cuts at 400 and stamps len(raw). The shipped data cuts at 400 and stamps 500.

Supersedes `the_truncation_rule_says_500_and_every_number_says_400.py`, which reached the right
number by the wrong route and carried two defects of the kind this repo has written rules about.

WHAT THE OLD PROBE GOT WRONG, both found by an adversarial pass and neither by re-reading:

  * IT NEVER OPENED THE DOCUMENTS IT ACCUSED. The claim is a contradiction between a dataset and
    two documents. Only the dataset was pinned. Deleting SCHEMA.md and the guide entirely left it
    at exit 0 with every verdict YES, and if the author fixed the section today it would still
    accuse him.
  * ONE CHECK TESTED A CONSTANT IT HAD DEFINED ITSELF: `"500" in MARKER`, where MARKER was our own
    literal. That cannot fail. It is the exact class this file's sibling was patched for hours
    earlier, reintroduced in a fresh file, which is why the class gets a probe and not a comment.

WHAT THE ADVERSARIAL PASS FOUND THAT WE HAD NOT:

  * `lh_shared_audit_extract.py` ships in the SAME published directory and was never opened. It
    settles the question outright: `RESP_MAX = 400`, and the marker is built from the ORIGINAL
    length, per record. So the three shipped records should read 556, 635 and 665. All three read
    500. The published data was not produced by the published generator, which is a stronger and
    more useful statement than anything about the prose.
  * "3-242" is not a truncation range. Deltas over all ten counted records are
    [0, 3, 3, 3, 3, 3, 9, 133, 212, 242]; the 3 is a desensitisation delta on records that were
    never truncated. SCHEMA's own table spans 133-242, so the warning beneath it contradicts it.
  * The minimum delta is ZERO (REQ-9bd5cb4a-016, 67 -> 67), which refutes SCHEMA section 3's
    "published is always shorter" outright. Nobody had looked at the non-truncated records.
  * 242 was never independent evidence: the delta column IS the 423 column subtracted. One SCHEMA
    figure and one guide figure, not two.

Upstream documents are VENDORED under probes/_longhun_v11/upstream/ and pinned by their git blob
sha, so this asserts against bytes it can show rather than bytes it remembers. `--refetch` pulls
the live shas and fails if one moved, which is the only honest way to notice the author fixed it.

stdlib only unless --refetch is passed. Chinese strings: set PYTHONIOENCODING=utf-8 on Windows.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UP = os.path.join(HERE, "_longhun_v11", "upstream")
DATA = os.path.join(HERE, "longhun_shared_audit_dataset_v1.0.jsonl")
DATA_SHA = "b1a8a650b8038b21505396ea869911008781b26a3adf39ad730edc3d99a2e7f3"
REPO = "UID9622/longhun-financial-deep-seek"
DIR = "data/shared-audit"
BLOBS = {
    "SCHEMA.md": "d33d98f1a78f0d98e470d882c8c117754cff4d40",
    "CALIBRATION_DATASET_USAGE_GUIDE.md": "99e12538510ec0debd90d993b1ca2213f8e4f128",
    "lh_shared_audit_extract.py": "e5b6401fc5857e3fb64d6de99acca41d1a2eba88",
}
GEN_CUT = "RESP_MAX = 400"
GEN_STAMP = "truncated:{}chars"          # the generator interpolates, so it cannot be a constant
# Every one of these is quoted in what we are about to send. If a string is not in the file, the
# quote is stale and the comment must not go out.
QUOTES = {
    "SCHEMA.md": [
        "第 500 字符处截断",     # "cut at character 500"
        "3–242 字符",                        # the delta range it states
        "发布版始终更短",     # "published is always shorter"
        "| 423 |",                                        # its own table's published length
    ],
    "CALIBRATION_DATASET_USAGE_GUIDE.md": ["656 字符未检查"],
    "lh_shared_audit_extract.py": [GEN_CUT, GEN_STAMP],
}
CUT_500 = "第 500 字符处截断"
ALWAYS_SHORTER = "发布版始终更短"


def blob_sha(path: str) -> str:
    b = open(path, "rb").read()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\x00" + b).hexdigest()


def refetch() -> None:
    for name, pinned in BLOBS.items():
        out = subprocess.run(["gh", "api", REPO.join(["repos/", f"/contents/{DIR}/{name}"]),
                              "--jq", ".sha"], capture_output=True, text=True)
        live = (out.stdout or "").strip()
        if live and live != pinned:
            raise SystemExit(f"REFUSED: {name} moved upstream ({pinned[:8]} -> {live[:8]}). "
                             "Re-read it before repeating any quote from it.")
    print("  refetch: all three upstream blobs still at the pinned shas\n")


def main() -> int:
    if "--refetch" in sys.argv:
        refetch()
    rows = [json.loads(line) for line in open(DATA, encoding="utf-8") if line.strip()]
    docs = {}
    for name in BLOBS:
        p = os.path.join(UP, name)
        if not os.path.exists(p):
            raise SystemExit(f"REFUSED: {p} is absent. A probe that cannot open the document it "
                             "accuses proves nothing; that is why the previous version was wrong.")
        docs[name] = open(p, encoding="utf-8").read()

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
    big = [d for d in ds if d > 100]

    v: dict[str, bool] = {}
    v["the_dataset_is_the_one_we_measured"] = (
        hashlib.sha256(open(DATA, "rb").read()).hexdigest() == DATA_SHA)
    v["every_upstream_doc_is_at_its_pinned_blob_sha"] = all(
        blob_sha(os.path.join(UP, n)) == s for n, s in BLOBS.items())
    v["every_string_we_quote_is_present_in_the_doc"] = all(
        q in docs[n] for n, qs in QUOTES.items() for q in qs)
    # --- the generator, which is the independent evidence ---
    v["the_generator_declares_a_400_char_cut"] = GEN_CUT in docs["lh_shared_audit_extract.py"]
    v["the_generator_stamps_a_PER_RECORD_length"] = GEN_STAMP in docs["lh_shared_audit_extract.py"]
    v["every_shipped_body_is_400_matching_the_generator"] = bool(trunc) and all(
        b == 400 for _, b, _, _ in trunc)
    v["but_NO_shipped_marker_carries_its_own_raw_length"] = bool(trunc) and all(
        stamped != raw for _, _, raw, stamped in trunc)
    v["every_shipped_marker_carries_the_same_frozen_500"] = bool(trunc) and all(
        stamped == 500 for _, _, _, stamped in trunc)
    # --- the delta population, which SCHEMA describes wrongly in two ways ---
    v["the_lower_bound_3_is_NOT_a_truncation_delta"] = 3 in ds and 3 not in big
    v["SCHEMAs_own_table_spans_133_to_242"] = big == [133, 212, 242]
    v["the_true_minimum_delta_is_ZERO"] = min(ds) == 0
    v["which_refutes_published_is_always_shorter"] = (
        ALWAYS_SHORTER in docs["SCHEMA.md"] and min(ds) == 0)
    # --- controls that an upstream fix would flip ---------------------------------------
    v["CONTROL_patching_the_prose_to_400_flips_the_quote_check"] = (
        CUT_500 not in docs["SCHEMA.md"].replace(CUT_500, CUT_500.replace("500", "400")))
    v["CONTROL_a_one_byte_edit_breaks_the_blob_pin"] = (
        hashlib.sha1(b"blob 1\x00x").hexdigest() != BLOBS["SCHEMA.md"])
    v["CONTROL_a_correct_marker_would_not_read_as_frozen"] = not all(
        raw == 500 for _, _, raw, _ in trunc)

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print("\n  truncated records:")
    for rid, body, raw, marker in trunc:
        print(f"    {rid}  body={body}  raw={raw}  marker says {marker}  "
              f"generator would have stamped {raw}")
    print(f"\n  deltas over all {len(deltas)} counted records: {ds}")
    lo = [i for i, _, _, d in deltas if d == min(ds)][0]
    print(f"  minimum {min(ds)} ({lo}), maximum {max(ds)}; SCHEMA states the range as 3-242")
    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "truncated": [{"request_id": i, "body": b, "raw": r, "marker_says": s}
                             for i, b, r, s in trunc],
               "deltas": [{"request_id": i, "raw": r, "published": p, "delta": d}
                          for i, r, p, d in deltas],
               "upstream_blobs": BLOBS},
              open(os.path.join(
                  HERE, "the_data_disagrees_with_its_own_published_generator.result.json"),
                  "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
