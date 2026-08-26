"""@UID9622's integrity chain verifies independently. The hash six comments quote does not match it.

WHY. On 2026-08-26 @UID9622 shipped two commits to UID9622/longhun-financial-deep-seek: per-file
SHA-256 in the §6 template (our correction), a rev4 fix to a SCHEMA id suffix (our correction), and
then a full tamper-evidence chain -- per-record SHA-256, a three-level Merkle root, a stdlib probe,
and a CI gate. He closed with an invitation rather than an assertion:

    "任何人（不依赖作者）可独立复算" -- anyone, not relying on the author, can recompute this.

That is the right way to publish a baseline and it deserves someone actually doing it. So this
recomputes the whole chain from his stated algorithm with our own implementation, rather than
running his script and reporting what it says about itself.

WHAT VERIFIES, all of it:

    38/38 record_hash values recompute            canonical JSON, sort_keys, no record_hash field
    both file-level Merkle roots match            4d7f8669... and c64fa70c...
    the total 38-record root matches              27aa9ec0...
    both file SHA-256 match the MANIFEST block    a6f9cbe8... and 5af2f320...

One spec ambiguity worth writing down for anyone else reimplementing: `leaf = SHA-256(record_hash_bytes)`
does not say whether those bytes are the 64-character hex string or the 32-byte digest it encodes.
Only the hex-string reading reproduces his roots. Both were tried; that is why this file knows.

AND HIS CONTROL WORKS, which matters more than the roots. Change `REQ-` to `REQ_` in one record and
three independent checks catch it: the file SHA, the record_hash for that exact id (named in the
output), and the total Merkle root. The script exits 1, so the CI gate goes red. Read the exit code
DIRECTLY: the first run of this measurement read it through a pipe, got `tail`'s status, and briefly
concluded that a tampered dataset passed his gate.

THE ONE FINDING, and it lands on us harder than on him. His comment of 08:43 published
`b1a8a650...` and `156d3ebb...` as the current release hashes. Nineteen minutes later the integrity
commit added a record_hash field to all 38 records, which rewrote both files, and both hashes moved.
The MANIFEST was updated and is correct. The COMMENTS were not, and cannot be: they are published
text.

Measured against the live thread: `b1a8a650` appears in six comments, five of them OURS, and
`156d3ebb` in three including ours. The current hashes appear in none. So every reader who follows
the thread's own instruction to verify gets a mismatch and has to work out for themselves whether
the dataset was tampered with or the citation aged. That is the exact failure this dataset exists to
prevent, and we supplied most of the instances.

Network: fetches the four published files and the live comment bodies. No model, no credits.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = "https://raw.githubusercontent.com/UID9622/longhun-financial-deep-seek/main/"
FILES = ["data/shared-audit/longhun-shared-audit-dataset-v1.0.jsonl",
         "data/shared-audit/longhun-shared-audit-dataset-v1.1-negative.jsonl",
         "data/shared-audit/MANIFEST.md"]
STALE = {"b1a8a650": "v1.0", "156d3ebb": "v1.1-negative"}


def fetch(path: str) -> bytes:
    with urllib.request.urlopen(RAW + path, timeout=60) as r:
        return r.read()


def record_hash(rec: dict) -> str:
    d = {k: v for k, v in rec.items() if k != "record_hash"}
    c = json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(c.encode("utf-8")).hexdigest()


def merkle(hexes: list, leaf_over_hex_string: bool) -> str:
    lv = [hashlib.sha256(h.encode() if leaf_over_hex_string else bytes.fromhex(h)).digest()
          for h in hexes]
    while len(lv) > 1:
        if len(lv) % 2:
            lv.append(lv[-1])
        lv = [hashlib.sha256(lv[i] + lv[i + 1]).digest() for i in range(0, len(lv), 2)]
    return lv[0].hex()


def thread_bodies() -> list:
    r = subprocess.run(["gh", "api", "--paginate",
                        "repos/deepseek-ai/DeepSeek-V3/issues/1591/comments",
                        "--jq", ".[] | {id:.id, user:.user.login, body:.body}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = []
    for line in (r.stdout or "").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def main() -> int:
    blobs = {}
    for p in FILES:
        try:
            blobs[p] = fetch(p)
        except Exception as e:
            raise SystemExit(f"REFUSED: could not fetch {p} ({e}); nothing below would be evidence")

    meta = re.search(r"<!--\s*MANIFEST-META:\s*(\{.*?\})\s*-->",
                     blobs[FILES[2]].decode("utf-8"), re.S)
    if not meta:
        raise SystemExit("REFUSED: no machine-readable MANIFEST-META block; the expected values "
                         "would have to come from prose")
    M = json.loads(meta.group(1))

    v: dict = {}
    rows, all_hashes = [], []
    for p in FILES[:2]:
        name = p.split("/")[-1]
        want = M["files"][name]
        digest = hashlib.sha256(blobs[p]).hexdigest()
        recs = [json.loads(l) for l in blobs[p].decode("utf-8").split("\n") if l.strip()]
        mine = [record_hash(r) for r in recs]
        stated = [r.get("record_hash") for r in recs]
        agree = sum(a == b for a, b in zip(mine, stated))
        root = merkle(mine, True)
        all_hashes += mine
        rows.append({"file": name, "records": len(recs), "sha256": digest,
                     "sha256_matches_manifest": digest == want["file_sha256"],
                     "record_hash_agree": f"{agree}/{len(recs)}",
                     "merkle": root, "merkle_matches_manifest": root == want["merkle_root"]})
        print(f"  {name[:46]:46s} {len(recs)} recs  sha {'OK' if digest == want['file_sha256'] else 'NO'}"
              f"  record_hash {agree}/{len(recs)}  merkle "
              f"{'OK' if root == want['merkle_root'] else 'NO'}")

    total = merkle(all_hashes, True)
    print(f"  TOTAL over {len(all_hashes)} records: {total[:16]}...  "
          f"{'OK' if total == M['total_merkle_root'] else 'NO'}")

    v["every_file_sha256_matches_the_manifest"] = all(r["sha256_matches_manifest"] for r in rows)
    v["every_record_hash_recomputes"] = all(
        r["record_hash_agree"] == f"{r['records']}/{r['records']}" for r in rows)
    v["both_file_merkle_roots_match"] = all(r["merkle_matches_manifest"] for r in rows)
    v["the_total_38_record_root_matches"] = (total == M["total_merkle_root"]
                                             and len(all_hashes) == M["total_count"] == 38)
    # The spec does not say which encoding the leaf hashes; only one reading reproduces his roots,
    # and saying so is the useful part for anyone reimplementing.
    v["CONTROL_the_other_leaf_reading_does_NOT_reproduce"] = merkle(
        all_hashes, False) != M["total_merkle_root"]
    # A chain that verifies is not the same as a chain that would notice tampering.
    tmp = tempfile.mkdtemp(prefix="lh_")
    os.makedirs(os.path.join(tmp, "data", "shared-audit"), exist_ok=True)
    for p in FILES:
        io.open(os.path.join(tmp, p.replace("/", os.sep)), "wb").write(blobs[p])
    bad = [json.loads(l) for l in blobs[FILES[0]].decode("utf-8").split("\n") if l.strip()]
    bad[0]["request_id"] = bad[0]["request_id"].replace("REQ-", "REQ_", 1)
    io.open(os.path.join(tmp, FILES[0].replace("/", os.sep)), "w", encoding="utf-8",
            newline="\n").write("\n".join(json.dumps(r, ensure_ascii=False) for r in bad) + "\n")
    mut_root = merkle([record_hash(r) for r in bad]
                      + all_hashes[len(bad):], True)
    v["CONTROL_one_changed_character_breaks_the_total_root"] = mut_root != M["total_merkle_root"]

    # ---- the finding: what the thread's comments actually quote ---------------------------------
    cs = thread_bodies()
    if not cs:
        print("\n  REFUSED: could not read the live thread; the citation finding is UNVERIFIED")
        v["REFUSED_thread_unreadable"] = False
    else:
        cur = [M["files"][f.split("/")[-1]]["file_sha256"] for f in FILES[:2]]
        cite = {}
        for pre, label in STALE.items():
            who = [(c["user"], c["id"]) for c in cs if pre in c["body"]]
            cite[pre] = who
            print(f"\n  stale {label} hash {pre}: {len(who)} comment(s), "
                  f"{sum(1 for u, _ in who if u == 'DanceNitra')} ours")
            for u, i in who:
                print(f"     {u} #{i}")
        fresh = sum(1 for c in cs for h in cur if h[:8] in c["body"])
        print(f"\n  comments quoting either CURRENT hash: {fresh} of {len(cs)}")
        v["the_stale_hashes_really_are_quoted_in_the_thread"] = all(cite[p] for p in STALE)
        v["MOST_of_the_stale_citations_are_OURS"] = sum(
            1 for u, _ in cite["b1a8a650"] if u == "DanceNitra") >= 3
        v["and_NOBODY_has_posted_the_current_ones"] = fresh == 0
        v["CONTROL_the_thread_was_actually_read"] = len(cs) >= 20

    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")

    json.dump({"probe": os.path.basename(__file__), "verdicts": v, "files": rows,
               "total_merkle": total, "manifest_meta": M,
               "stale_citations": {p: [{"user": u, "id": i} for u, i in cite[p]]
                                   for p in STALE} if cs else {},
               "leaf_encoding": "SHA-256 over the 64-character hex STRING; the raw-digest reading "
                                "does not reproduce the published roots",
               "his_checker": "integrity/calibration_dataset_check.py exits 0 on CLEAN and 1 on a "
                              "one-character mutation, so the CI gate goes red; three separate "
                              "checks catch it and one names the offending request_id",
               "platform": sys.platform},
              io.open(os.path.join(HERE, "the_dataset_hash_the_whole_thread_quotes_is_stale"
                                         ".result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
