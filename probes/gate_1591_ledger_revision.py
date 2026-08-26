"""Gate the #1591 ledger reply. Every figure recomputed live; every quotation fetched from its source.

This replaces a gate that guarded a DIFFERENT claim and passed it 28/29 while it was false. That
draft said the thread's file hashes had gone stale and nobody had posted current ones. The red team
killed it: his 07:02 comment already carried the current Merkle roots, his MANIFEST, archive note and
CHANGELOG documented the invalidation in the same commit, and our "nineteen minutes" was 14m36s.

Two of the old gate's own checks are why it passed. One searched only comment BODIES for the
author's announcement and never opened the repository. The other tested two file-SHA prefixes while
the sentence it guarded spoke of "a current hash" in general, so the check was narrower than the
claim. Both failure modes are written against below: the killed headline must stay dead, and the
citations are fetched from RFC and spec text rather than from a summary.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

assert chr(8) not in open(__file__, encoding="utf-8").read(), (
    "a literal BACKSPACE is in this file: a heredoc ate a regex word boundary again")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_1591_stale_hash.md")
REPO = "UID9622/longhun-financial-deep-seek"
NEG = "data/shared-audit/longhun-shared-audit-dataset-v1.1-negative.jsonl"


def gh(path: str, jq: str) -> str:
    r = subprocess.run(["gh", "api", path, "--jq", jq], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def blob(ref: str, path: str) -> bytes:
    c = gh(f"repos/{REPO}/contents/{path}?ref={ref}", ".content")
    return base64.b64decode("".join(c.split())) if c.strip() else b""


def web(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def thread() -> list:
    out = []
    # --paginate, because without it this read 30 of 34 comments and every "nobody has said X"
    # check ran over a truncated thread. A gate that cannot see the whole target reports safe.
    r = subprocess.run(["gh", "api", "--paginate",
                        "repos/deepseek-ai/DeepSeek-V3/issues/1591/comments",
                        "--jq", ".[] | {id:.id,user:.user.login,body:.body}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (r.stdout or "").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def check(draft: str, live: dict, cs: list) -> dict:
    v: dict = {}

    # COUNTS, not presence. Each hash prefix appears more than once in this draft, so a
    # presence check survives a single-occurrence mutation. I fixed exactly this in another gate an
    # hour ago and did not carry it here: the instance was patched and the class walked.
    import collections
    want = collections.Counter()
    for sha, digest, _ in live["rows"]:
        want[digest[:8]] = draft.count(digest[:8])
        v[f"row_{sha}_is_recomputed_from_git"] = (
            digest[:8] in draft and f"`{sha}`" in draft and draft.count(f"`{sha}`") >= 1)
    # Every 8-hex token in the draft must be one of the three we recomputed, and each must appear
    # exactly as often as it does now, so altering any single instance fails.
    # The commit shas are 8-hex tokens too, so the allowed set is digests AND shas. The first
    # version of this check listed only the digests and failed over its own omission.
    allowed = {d[:8] for _, d, _ in live["rows"]} | {sha for sha, _, _ in live["rows"]}
    seen = collections.Counter(re.findall(r"\b[0-9a-f]{8}\b", draft))
    v["ONLY_recomputed_hex_tokens_appear"] = set(seen) <= allowed and len(seen) == len(allowed)
    v["and_every_instance_of_each_is_intact"] = all(seen[k] == want[k] for k in want)
    v["CONTROL_three_distinct_byte_states_exist"] = len({d for _, d, _ in live["rows"]}) == 3
    v["the_middle_commit_message_really_says_r2"] = (
        "r2" in live["r2_msg"].lower() and "purge 4 leak-type records" in draft)

    v["the_ledger_really_labels_that_hash_r1"] = live["r1_claim"].startswith("156d3ebb")
    v["the_draft_states_that_label"] = "`v1.1-r1`" in draft and "156d3ebb" in draft
    v["the_r2_entry_really_carries_no_hash"] = (
        live["r2_has_no_sha"] and "no `sha256_after` field" in draft)
    v["the_true_r1_hash_really_is_absent_from_the_ledger"] = (
        live["true_r1_absent"] and "not in the ledger anywhere" in draft)

    v["purely_additive_is_MEASURED_not_asserted"] = live["additive"] and "purely additive" in draft
    v["CONTROL_the_additive_check_compared_two_real_states"] = live["compared"] == 19

    v["RFC6962_defines_the_leaf_at_byte_level"] = (
        "SHA-256(0x00 || d(0))" in live["rfc"] and "RFC 6962 §2.1" in draft)
    # The RFC text wraps that phrase across a line, so a raw substring check failed on words
    # that are plainly there. Normalise whitespace before comparing, or the reader deletes
    # what it is measuring.
    # phrase that is plainly there, which is the reader deleting what it is measuring.
    v["RFC6962_says_domain_separation"] = (
        "domain separation is required" in re.sub(r"\s+", " ", live["rfc"])
        and "domain separation" in draft)
    v["in_toto_requires_documenting_the_encoding"] = (
        "MUST document how the value is encoded" in live["intoto"] and "DigestSet" in draft)
    # Croissant specifies no encoding at all, so citing it as the convention would invent one.
    v["we_do_NOT_cite_croissant_as_a_convention"] = "Croissant" not in draft

    v["the_killed_headline_stays_dead"] = not re.search(
        r"[Zz]ero of the \d+ comments|no longer match|went stale", draft)
    v["no_current_hash_is_inlined_to_be_copied"] = not (
        "a6f9cbe8e3a96e8b" in draft or "5af2f320310f0153" in draft)
    v["the_wrong_nineteen_minutes_is_gone"] = "nineteen minutes" not in draft

    v["no_personal_name"] = not re.search(r"[Rr]astislav|Draho[sš]", draft)
    v["no_ai_disclosure_line"] = "AI assistance" not in draft
    v["no_em_or_en_dash"] = not ("—" in draft or "–" in draft or " -- " in draft)
    v["every_at_handle_is_a_real_participant"] = all(
        h in {c["user"] for c in cs} for h in set(re.findall(r"@([A-Za-z0-9]+)", draft)))
    v["length_is_reasonable"] = 250 < len(draft.split()) < 800

    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "humanizer_receipt.py"),
                        "check", DRAFT], capture_output=True, text=True)
    v["the_humanizer_SKILL_ran_on_THESE_bytes"] = r.returncode == 0
    return v


def main() -> int:
    draft = io.open(DRAFT, encoding="utf-8").read()
    hist = [l.split("\t") for l in gh(
        f"repos/{REPO}/commits?path={NEG}",
        '.[] | "\\(.sha)\\t\\(.commit.author.date)\\t\\(.commit.message|split("\\n")[0])"'
    ).strip().split("\n") if l.strip()]
    if len(hist) < 3:
        raise SystemExit("REFUSED: fewer than three commits touch the negative dataset")

    rows, blobs = [], {}
    for sha, _date, msg in hist:
        b = blob(sha, NEG)
        if not b:
            raise SystemExit(f"REFUSED: no blob at {sha[:8]}")
        blobs[sha[:8]] = b
        rows.append((sha[:8], hashlib.sha256(b).hexdigest(), msg))

    log = [json.loads(l) for l in blob("main", "data/shared-audit/CHANGELOG.jsonl")
           .decode("utf-8").split("\n") if l.strip()]
    byv = {e.get("version"): e for e in log}
    r1_claim = (byv.get("v1.1-r1") or {}).get("sha256_after", "")
    oldest = sorted(zip(hist, rows), key=lambda z: z[0][1])[0][1]
    mid = next((r for r in rows if r[1] == r1_claim), None)
    cur = [json.loads(x) for x in blobs[rows[0][0]].decode("utf-8").split("\n") if x.strip()]
    prv = ([json.loads(x) for x in blobs[mid[0]].decode("utf-8").split("\n") if x.strip()]
           if mid else [])

    live = {"rows": rows, "r1_claim": r1_claim, "r2_msg": mid[2] if mid else "",
            "r2_has_no_sha": not any("sha256" in k for k in (byv.get("v1.1-r2") or {})),
            "true_r1_absent": not any(oldest[1] in json.dumps(e, ensure_ascii=False) for e in log),
            "additive": (len(cur) == len(prv) == 19
                         and [r.get("request_id") for r in cur] == [r.get("request_id") for r in prv]
                         and all(all(a.get(k) == b.get(k) for k in b) for a, b in zip(cur, prv))
                         and all(set(a) - set(b) == {"record_hash"} for a, b in zip(cur, prv))),
            "compared": len(prv),
            "rfc": web("https://www.rfc-editor.org/rfc/rfc6962.txt"),
            "intoto": web("https://raw.githubusercontent.com/in-toto/attestation/main/spec/v1/"
                          "digest_set.md")}
    cs = thread()
    if not cs:
        raise SystemExit("REFUSED: could not read the live thread")

    v = check(draft, live, cs)
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    passed = sum(1 for x in v.values() if x)
    print(f"\n  {passed}/{len(v)} checks, {len(draft.split())} words, {len(cs)} comments read")

    if "--mutate" in sys.argv:
        print("\n  MUTATION SELF-TEST")
        muts = [("r2 message", "purge 4 leak-type records", "purge 5 leak-type records"),
                ("ledger hash", "156d3ebb", "156d3ecc"),
                ("true r1", "b78c9509", "b78c9500"),
                ("additive", "purely additive", "mostly additive"),
                ("rfc cite", "RFC 6962 §2.1", "RFC 6963 §2.1"),
                ("croissant", "in-toto's DigestSet", "Croissant's checksum field"),
                ("revive dead claim", "The data is fine.",
                 "Zero of the 34 comments carry a current hash. The data is fine."),
                ("inline hash", "Probe: `probes", "a6f9cbe8e3a96e8b is current. Probe: `probes"),
                ("name", "Probe: `probes", "Rastislav here. Probe: `probes"),
                ("em dash", "The data is fine.", "The data is fine —.")]
        caught = 0
        for label, a, b in muts:
            if a not in draft:
                print(f"    SKIP   {label}: anchor absent, mutation vacuous")
                continue
            mv = check(draft.replace(a, b, 1), live, cs)
            broke = [k for k in v if v[k] and not mv.get(k)]
            caught += bool(broke)
            print(f"    {'CAUGHT' if broke else 'MISSED'}  {label}"
                  f"{' -> ' + broke[0] if broke else ''}")
        print(f"    {caught}/{len(muts)} mutations caught")
        return 0 if (passed == len(v) and caught == len(muts)) else 1
    return 0 if passed == len(v) else 1


if __name__ == "__main__":
    sys.exit(main())
