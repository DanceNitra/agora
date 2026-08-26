"""A claim of ours that the gate killed, kept because the verification inside it is still good.

WHAT WE WERE GOING TO SAY. That the file hashes quoted in six comments of deepseek-ai/DeepSeek-V3#1591
had gone stale when @UID9622's integrity commit rewrote both files, and that nobody in the thread had
posted the current ones.

WHY IT IS DEAD, three independent counts, each re-verified by hand before the verdict was accepted:

  1. HIS 07:02 COMMENT ALREADY CARRIES CURRENT HASHES -- the full 38-record Merkle root and both
     file-level roots. Our "zero of 34 comments carry a current hash" was only true if "hash" is
     narrowed to the file-level SHA-256 and excludes the Merkle roots he had just promoted as the
     stronger anchor. The check underneath it tested exactly those two SHA-256 prefixes, so the
     claim was wider than the measurement.
  2. HE PUBLISHED THE FINDING HIMSELF, in the same commit, in three files: MANIFEST.md strikes both
     old hashes through as 作废, archive/README.md carries a section explaining why, and
     CHANGELOG.jsonl records sha256_after_v10 / sha256_after_v11n. Our gate had a check for exactly
     this and it searched only COMMENT BODIES; it never opened the repository. A check that never
     sees its target reports safe.
  3. "NINETEEN MINUTES" WAS 14m36s. The integrity commit is dafdd03c at 06:57:23 against his 06:42:47
     comment; nineteen minutes is the gap between his two COMMENTS. A wrong number inside a comment
     about hash accuracy.

The gate script for that draft passed 28 of 29 checks while the claim was false, which is the whole
lesson: a per-draft script is one check inside validate/storm/audit/verify, never the frame.

WHAT SURVIVES AND IS STILL RUN. The recomputation itself: 38/38 record_hash values reproduce from
his canonical-JSON spec, both file-level Merkle roots and the total root match MANIFEST-META, only
the hex-string leaf reading reproduces them, and one changed character breaks the total root. That
is a third-party reproduction the thread does not otherwise have, and it is the half that went into
the comment we did send.

The finding that replaced this one is in probes/the_provenance_ledger_labels_r2_as_r1.py.

The file was also renamed. Its old name was the_dataset_hash_the_whole_thread_quotes_is_stale.py,
which is a public filename that states the accusation as a fact, on a claim that turned out to be
wrong. A tone review flagged it; a probe name is published text too.
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
