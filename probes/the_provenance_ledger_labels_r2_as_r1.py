"""The ledger built today to resolve stale hashes maps the negative dataset to the wrong revision.

WHY THIS EXISTS, and it starts with a claim of ours that died. On 2026-08-26 @UID9622 shipped a
tamper-evidence chain to UID9622/longhun-financial-deep-seek: per-record SHA-256, a three-level
Merkle root, a stdlib checker, a CI gate, and an append-only CHANGELOG.jsonl. We drafted a comment
reporting that the file hashes quoted in the thread had gone stale when that commit rewrote the
files. A red team killed it on three counts, all verified here before accepting them: his 07:02
comment already carries the current Merkle roots, his own MANIFEST/archive/CHANGELOG document the
invalidation in the same commit, and our "nineteen minutes" was 14m36s. The staleness was his
disclosure, not our finding.

What survived is one level down, in the ledger itself.

    CHANGELOG.jsonl  v1.1-r1  -> sha256_after 156d3ebb59ec...
    CHANGELOG.jsonl  v1.1-r2  -> no sha256 field at all

Hash every historical byte-state of that file from git and the labels do not line up:

    fb267b62  2026-08-21 04:24  b78c9509...  "add v1.1-negative dataset (19 real rejection records)"
    6aa23b9f  2026-08-21 04:42  156d3ebb...  "v1.1-negative r2 - purge 4 leak-type records"
    dafdd03c  2026-08-26 06:57  5af2f320...  the integrity commit, record_hash added

So `156d3ebb` is the blob at the commit whose OWN message calls it r2. The ledger calls it r1. The
actual r1, `b78c9509`, appears nowhere outside git history, and the one revision that changed record
CONTENT is the one with no hash recorded.

WHY IT MATTERS HERE RATHER THAN AS A TYPO. r1 is the revision that still contained the four
"refuse-then-leak" boundary records; r2 exists precisely because they were purged. The ledger
therefore resolves the negative half BACKWARDS on the single distinction the negative half is for:
anyone looking up 156d3ebb is told they evaluated against the version that still had them.

AND CI CANNOT SEE IT. The shipped checker reads its expected values out of the MANIFEST-META block
and compares them against the current files: a self-consistent pair by construction. Nothing in the
repository checks a historical label against the bytes it names, which is why a green 18/18 and this
defect coexist. That is the same shape as every expensive day we have had -- a guarantee handed an
input it cannot examine its way out of.

THE REASSURING HALF, measured rather than assumed, because a comment that only reports a defect is
worse than useless to someone mid-release: today's rewrite is purely additive. Same 19 records per
file, same request_id sequence, same field order, and no existing value changed. Evaluation results
are unaffected; only byte-level citations moved.

Network only: GitHub API for the history, raw.githubusercontent for the current files. No model.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "UID9622/longhun-financial-deep-seek"
NEG = "data/shared-audit/longhun-shared-audit-dataset-v1.1-negative.jsonl"
CHANGELOG = "data/shared-audit/CHANGELOG.jsonl"


def gh(path: str, jq: str) -> str:
    r = subprocess.run(["gh", "api", path, "--jq", jq],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def blob_at(ref: str, path: str) -> bytes:
    import base64
    c = gh(f"repos/{REPO}/contents/{path}?ref={ref}", ".content")
    return base64.b64decode("".join(c.split())) if c.strip() else b""


def main() -> int:
    hist = [l.split("\t") for l in gh(
        f"repos/{REPO}/commits?path={NEG}",
        '.[] | "\\(.sha)\\t\\(.commit.author.date)\\t\\(.commit.message|split("\\n")[0])"'
    ).strip().split("\n") if l.strip()]
    if len(hist) < 3:
        raise SystemExit("REFUSED: fewer than three commits touch the negative dataset; the "
                         "revision mapping below would have nothing to disagree with")

    rows = []
    for sha, date, msg in hist:
        b = blob_at(sha, NEG)
        if not b:
            raise SystemExit(f"REFUSED: could not fetch the blob at {sha[:8]}")
        rows.append({"sha": sha[:8], "date": date, "msg": msg,
                     "sha256": hashlib.sha256(b).hexdigest(),
                     "records": len([x for x in b.decode("utf-8").split("\n") if x.strip()])})
        r = rows[-1]
        print(f"  {r['sha']}  {r['date'][:19]}  {r['sha256'][:16]}...  {r['records']} recs  "
              f"{r['msg'][:56]}")

    log = [json.loads(l) for l in blob_at("main", CHANGELOG).decode("utf-8").split("\n") if l.strip()]
    by_ver = {e.get("version"): e for e in log}
    r1_claim = (by_ver.get("v1.1-r1") or {}).get("sha256_after", "")
    r2_entry = by_ver.get("v1.1-r2") or {}

    # Which commit does the ledger's r1 hash ACTUALLY correspond to? Ask the bytes, not the label.
    match = next((r for r in rows if r["sha256"] == r1_claim), None)
    oldest = min(rows, key=lambda r: r["date"])

    print(f"\n  CHANGELOG v1.1-r1 claims sha256_after = {r1_claim[:16]}...")
    print(f"  that hash is the blob at {match['sha'] if match else '(no commit)'}"
          f"{'  whose message says: ' + match['msg'][:52] if match else ''}")
    print(f"  the OLDEST byte-state is {oldest['sha']} = {oldest['sha256'][:16]}..., "
          f"published: {'yes' if any(r1_claim == oldest['sha256'] for _ in [0]) else 'nowhere'}")

    v: dict = {}
    v["CONTROL_the_history_has_three_distinct_byte_states"] = len(
        {r["sha256"] for r in rows}) == 3
    v["CONTROL_the_changelog_was_read"] = len(log) >= 3 and bool(r1_claim)
    v["the_r1_hash_in_the_ledger_resolves_to_a_real_commit"] = match is not None
    # THE FINDING.
    v["but_that_commit_calls_itself_r2"] = bool(match) and "r2" in match["msg"].lower()
    v["and_it_is_NOT_the_oldest_byte_state"] = bool(match) and match["sha"] != oldest["sha"]
    v["the_true_r1_hash_appears_nowhere_in_the_ledger"] = not any(
        oldest["sha256"] in json.dumps(e, ensure_ascii=False) for e in log)
    v["the_r2_entry_records_no_hash_at_all"] = not any(
        "sha256" in k for k in r2_entry)
    # The reassuring half must be measured too, or the comment is only an accusation.
    cur = blob_at("main", NEG).decode("utf-8")
    prev = blob_at(match["sha"], NEG).decode("utf-8") if match else ""
    cr = [json.loads(x) for x in cur.split("\n") if x.strip()]
    pr = [json.loads(x) for x in prev.split("\n") if x.strip()]
    v["todays_rewrite_kept_the_record_count"] = len(cr) == len(pr) == 19
    v["it_kept_the_request_id_sequence"] = [r.get("request_id") for r in cr] == [
        r.get("request_id") for r in pr]
    v["it_changed_no_existing_value"] = all(
        all(a.get(k) == b.get(k) for k in b) for a, b in zip(cr, pr))
    v["the_only_difference_is_the_added_field"] = all(
        set(a) - set(b) == {"record_hash"} for a, b in zip(cr, pr))

    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")

    json.dump({"probe": os.path.basename(__file__), "verdicts": v, "history": rows,
               "changelog_v1_1_r1_claims": r1_claim,
               "changelog_v1_1_r2_has_sha": any("sha256" in k for k in r2_entry),
               "true_r1_sha256": oldest["sha256"], "true_r1_commit": oldest["sha"],
               "finding": "CHANGELOG.jsonl labels 156d3ebb as v1.1-r1, but that is the blob at the "
                          "commit whose own message says r2 (purge 4 leak-type records). The true "
                          "r1 is published nowhere and the r2 entry carries no hash.",
               "why_it_matters": "r1 still contained the four refuse-then-leak boundary records and "
                                 "r2 exists because they were purged, so the ledger inverts the one "
                                 "distinction the negative half is for",
               "why_CI_cannot_see_it": "the shipped checker compares the current files against the "
                                       "current MANIFEST-META, a self-consistent pair; no check "
                                       "binds a historical label to the bytes it names",
               "reassuring": "today's rewrite is purely additive: same 19 records, same request_id "
                             "sequence, no existing value changed, record_hash the only new key",
               "killed_first": "our original draft reported the stale file hashes as a finding; his "
                               "MANIFEST, archive/README and CHANGELOG all document that in the "
                               "same commit, and his 07:02 comment carries the current Merkle roots",
               "platform": sys.platform},
              io.open(os.path.join(HERE, "the_provenance_ledger_labels_r2_as_r1.result.json"),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
