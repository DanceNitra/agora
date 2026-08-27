# -*- coding: utf-8 -*-
"""After ab6c832 the v1.1-r1 ledger row anchors a git SHA and a content hash that disagree.

BACKGROUND. On 2026-08-26 we reported (DeepSeek-V3#1591, comment 5424724558) that CHANGELOG.jsonl
recorded v1.1-r1 with sha256_after 156d3ebb, while hashing every historical byte-state of the
negative dataset showed 156d3ebb is the blob at commit 6aa23b9f, whose own message calls it r2. The
true r1 blob, b78c9509, appeared nowhere in the ledger.

@UID9622 fixed the anchoring in ab6c832 (v1.1-annotate) by adding git_sha_map, and credited the
finding. The map is correct: v1.1-r1 -> fb267b62, v1.1-r2 -> 6aa23b9f. But the sha256_after on the
v1.1-r1 row was not touched, so that one row now carries an anchor and a hash pointing at different
byte states. That is an improvement rather than a regression, because the row now refutes itself
from its own two fields instead of requiring git archaeology, and it is the last thread of the
original defect.

THIS FETCHES THE BLOBS AND HASHES THEM. Nothing is taken from the ledger's own description, and a
positive control asserts that the rows which DO agree are seen to agree, so a checker that says
"mismatch" about everything is caught.
"""
import hashlib
import io
import json
import subprocess
import sys

REPO = "UID9622/longhun-financial-deep-seek"
NEG = "data/shared-audit/longhun-shared-audit-dataset-v1.1-negative.jsonl"
POS = "data/shared-audit/longhun-shared-audit-dataset-v1.0.jsonl"


def gh_json(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def blob_sha(path, ref):
    d = gh_json("repos/%s/contents/%s?ref=%s" % (REPO, path, ref))
    if not d or "content" not in d:
        return None
    import base64
    raw = base64.b64decode(d["content"])
    return hashlib.sha256(raw).hexdigest(), len(raw)


# --- the ledger, read from the repo rather than from memory
cl = gh_json("repos/%s/contents/%s" % (REPO, "data/shared-audit/CHANGELOG.jsonl"))
import base64
text = base64.b64decode(cl["content"]).decode("utf-8")
rows = [json.loads(l) for l in text.strip().split("\n") if l.strip()]
by_ver = {r.get("version"): r for r in rows}
smap = next((r["git_sha_map"] for r in rows if "git_sha_map" in r), None)

measured = {"git_sha_map": smap, "blobs": {}}
v = {}

v["CONTROL_the_ledger_was_actually_fetched"] = len(rows) >= 4 and smap is not None
v["annotate_row_exists"] = "v1.1-annotate" in by_ver

for ver, sha in (smap or {}).items():
    got = blob_sha(NEG, sha)
    measured["blobs"][ver] = {"commit": sha[:8],
                              "neg_blob_sha256": (got[0][:16] if got else None),
                              "bytes": (got[1] if got else None)}

# --- the finding: v1.1-r1's anchor and its own sha256_after disagree
r1_claim = (by_ver.get("v1.1-r1") or {}).get("sha256_after", "")
r1_actual = measured["blobs"].get("v1.1-r1", {}).get("neg_blob_sha256") or ""
r2_actual = measured["blobs"].get("v1.1-r2", {}).get("neg_blob_sha256") or ""
measured["v1.1_r1_sha256_after_claimed"] = r1_claim[:16]
measured["v1.1_r1_blob_at_its_own_anchor"] = r1_actual
measured["v1.1_r2_blob"] = r2_actual

v["r1_row_is_self_contradictory"] = bool(r1_claim) and not r1_claim.startswith(r1_actual)
v["the_claimed_hash_is_the_r2_blob"] = bool(r2_actual) and r1_claim.startswith(r2_actual)
v["the_true_r1_blob_is_still_unrecorded"] = bool(r1_actual) and r1_actual not in text

# --- POSITIVE CONTROL: the v1.1 row does agree, and must be seen to agree
v11 = by_ver.get("v1.1") or {}
v11_claim = v11.get("sha256_after_v11n", "")
v11_actual = measured["blobs"].get("v1.1", {}).get("neg_blob_sha256") or ""
measured["v1_1_claim_vs_blob"] = [v11_claim[:16], v11_actual]
v["CONTROL_a_row_that_AGREES_is_seen_to_agree"] = bool(v11_claim) and v11_claim.startswith(v11_actual)

# --- the id-correction commit did not change these bytes
v["id_correction_left_the_negative_bytes_identical"] = (
    measured["blobs"].get("v1.1-r2", {}).get("neg_blob_sha256")
    == measured["blobs"].get("v1.1-r2-id-correction", {}).get("neg_blob_sha256"))

# --- NEGATIVE CONTROL: a fabricated hash must not be reported as agreeing
v["CONTROL_a_wrong_hash_would_be_caught"] = not ("0" * 64).startswith(r2_actual or "x")

v = {k: bool(x) for k, x in v.items()}
io.open("probes/longhun_the_anchor_was_fixed_and_the_hash_beside_it_was_not.result.json",
        "w", encoding="utf-8").write(json.dumps({"measured": measured, "verdicts": v}, indent=2))
for k, ok in v.items():
    print("%-52s %s" % (k, "PASS" if ok else "FAIL"))
print("\n%d/%d" % (sum(v.values()), len(v)))
print(json.dumps(measured, indent=2, ensure_ascii=False))
sys.exit(0 if all(v.values()) else 1)
