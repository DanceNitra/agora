"""Gate the #1591 stale-hash reply: recompute every hash live, and fetch every quotation live.

Two lessons from this thread are wired in as checks rather than trusted to memory.

  * A previous draft here led with a hash nit that was TRUE and still wrong, because it was
    downstream of something the author had announced publicly two days earlier. So this gate asks
    whether anyone has already published the current hashes, and refuses the finding if they have.
  * The prior-statement gate once caught this draft's author re-asserting a check he had publicly
    RETRACTED earlier in the same thread. Re-reading does not catch that class; a check does.

Every hash in the draft is recomputed from the files as they stand on the remote right now, not
copied from the probe receipt, because the receipt could itself be stale by the time this runs.

Run:  python -X utf8 probes/gate_1591_stale_hash.py
      python -X utf8 probes/gate_1591_stale_hash.py --mutate
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_1591_stale_hash.md")
RAW = "https://raw.githubusercontent.com/UID9622/longhun-financial-deep-seek/main/"
D = "data/shared-audit/"
ISSUE = "repos/deepseek-ai/DeepSeek-V3/issues/1591/comments"


def fetch(p: str) -> bytes:
    with urllib.request.urlopen(RAW + p, timeout=60) as r:
        return r.read()


def rec_hash(rec: dict) -> str:
    d = {k: v for k, v in rec.items() if k != "record_hash"}
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def merkle(hexes: list, over_hex: bool) -> str:
    lv = [hashlib.sha256(h.encode() if over_hex else bytes.fromhex(h)).digest() for h in hexes]
    while len(lv) > 1:
        if len(lv) % 2:
            lv.append(lv[-1])
        lv = [hashlib.sha256(lv[i] + lv[i + 1]).digest() for i in range(0, len(lv), 2)]
    return lv[0].hex()


def thread() -> list:
    r = subprocess.run(["gh", "api", "--paginate", ISSUE,
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


def check(draft: str, live: dict, cs: list) -> dict:
    v: dict = {}
    by = lambda u: " ".join(c["body"] for c in cs if c["user"] == u)
    joined = " ".join(c["body"] for c in cs)

    # ---- every hash in the draft, recomputed from the REMOTE files right now --------------------
    v["v1_0_sha_in_the_draft_is_the_live_file"] = live["sha10"] in draft
    v["v1_1_sha_in_the_draft_is_the_live_file"] = live["sha11"] in draft
    v["total_merkle_in_the_draft_is_recomputed"] = live["total"] in draft
    v["both_file_roots_are_the_ones_we_recomputed"] = (
        live["root10"][:8] in draft and live["root11"][:8] in draft)
    v["the_38_of_38_claim_is_recomputed"] = live["agree"] == 38 and "38/38" in draft
    v["CONTROL_the_manifest_agrees_with_our_recomputation"] = (
        live["sha10"] == live["m10"] and live["sha11"] == live["m11"]
        and live["total"] == live["mtotal"])
    # The leaf-encoding claim must be true in BOTH directions or it is not a finding.
    v["CONTROL_the_digest_leaf_reading_really_fails"] = live["total_raw"] != live["mtotal"]

    # ---- the stale-citation counts, fetched live ------------------------------------------------
    b1 = [c for c in cs if "b1a8a650" in c["body"]]
    b2 = [c for c in cs if "156d3ebb" in c["body"]]
    ours1 = sum(1 for c in b1 if c["user"] == "DanceNitra")
    v["six_comments_and_five_ours_is_live"] = (len(b1) == 6 and ours1 == 5
                                               and "six comments, five of them mine" in draft)
    v["four_comments_for_the_negative_hash_is_live"] = len(b2) == 4 and "four including" in draft
    v["icophy_really_is_among_them"] = any(c["user"] == "icophy" for c in b2) and "@icophy" in draft
    v["the_comment_total_in_the_draft_is_live"] = f"{len(cs)} comments" in draft
    # THE FINDING'S PRECONDITION. If anyone has already posted a current hash, this is not news.
    v["nobody_has_posted_a_current_hash"] = not any(
        live["sha10"][:8] in c["body"] or live["sha11"][:8] in c["body"] for c in cs)

    # ---- everything attributed to another person ------------------------------------------------
    v["UID9622_really_wrote_the_invitation_we_quote"] = "可独立复算" in by("UID9622")
    v["UID9622_really_published_the_stale_hashes"] = ("b1a8a650" in by("UID9622")
                                                      and "156d3ebb" in by("UID9622"))
    v["qingkong66_really_said_anyone_can_clone_and_run"] = (
        "clone and run the same probe" in by("qingkong66")
        and "qingkong66" in draft)
    v["the_spec_line_we_quote_is_in_the_manifest"] = (
        "SHA-256(record_hash_bytes)" in live["manifest"]
        and "SHA-256(record_hash_bytes)" in draft)

    # ---- the two lessons this thread taught, as checks -------------------------------------------
    # 1. Not downstream of an announcement: the author must NOT have said the hashes changed.
    v["the_author_never_announced_the_hash_change"] = not re.search(
        r"(哈希|hash).{0,40}(已更新|changed|updated)", by("UID9622"))
    # 2. Nothing here may re-assert something we publicly retracted in this thread.
    retracted = re.findall(r"REQ-NEG-25890147-027", by("DanceNitra"))
    v["CONTROL_the_retraction_check_has_a_target"] = bool(retracted)
    v["the_draft_does_not_reopen_the_retracted_id"] = "25890147-027" not in draft

    # ---- house style -----------------------------------------------------------------------------
    v["no_em_or_en_dash_survives_the_humanizer_rule"] = not (
        "—" in draft or "–" in draft or " -- " in draft)
    w = len(draft.split())
    v["length_is_reasonable_for_this_thread"] = 200 < w < 700
    v["every_at_handle_is_a_real_participant"] = all(
        h in {c["user"] for c in cs} for h in set(re.findall(r"@([A-Za-z0-9]+)", draft)))
    v["the_ai_disclosure_is_present"] = "AI assistance" in draft
    v["it_says_the_repository_is_not_at_fault"] = "not the repository" in draft
    v["it_owns_that_most_instances_are_ours"] = "most of it is mine" in draft
    return v


def main() -> int:
    if not os.path.exists(DRAFT):
        raise SystemExit(f"REFUSED: {DRAFT} is absent")
    draft = io.open(DRAFT, encoding="utf-8").read()

    f10, f11 = fetch(D + "longhun-shared-audit-dataset-v1.0.jsonl"), \
        fetch(D + "longhun-shared-audit-dataset-v1.1-negative.jsonl")
    man = fetch(D + "MANIFEST.md").decode("utf-8")
    meta = re.search(r"<!--\s*MANIFEST-META:\s*(\{.*?\})\s*-->", man, re.S)
    if not meta:
        raise SystemExit("REFUSED: no MANIFEST-META block; expected values would come from prose")
    M = json.loads(meta.group(1))
    r10 = [json.loads(l) for l in f10.decode("utf-8").split("\n") if l.strip()]
    r11 = [json.loads(l) for l in f11.decode("utf-8").split("\n") if l.strip()]
    h10, h11 = [rec_hash(r) for r in r10], [rec_hash(r) for r in r11]
    names = list(M["files"])
    live = {"sha10": hashlib.sha256(f10).hexdigest(), "sha11": hashlib.sha256(f11).hexdigest(),
            "m10": M["files"][names[0]]["file_sha256"], "m11": M["files"][names[1]]["file_sha256"],
            "root10": merkle(h10, True), "root11": merkle(h11, True),
            "total": merkle(h10 + h11, True), "total_raw": merkle(h10 + h11, False),
            "mtotal": M["total_merkle_root"], "manifest": man,
            "agree": sum(1 for r, h in zip(r10 + r11, h10 + h11) if r.get("record_hash") == h)}
    cs = thread()
    if not cs:
        raise SystemExit("REFUSED: could not read the live thread; attribution unverified")

    v = check(draft, live, cs)
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    passed = sum(1 for x in v.values() if x)
    print(f"\n  {passed}/{len(v)} checks, {len(draft.split())} words, {len(cs)} comments read")

    if "--mutate" in sys.argv:
        print("\n  MUTATION SELF-TEST")
        muts = [("v1.0 hash", live["sha10"], live["sha10"][:-1] + "0" if live["sha10"][-1] != "0"
                 else live["sha10"][:-1] + "1"),
                ("total root", live["total"][:16], live["total"][:15] + "0"),
                ("six/five", "six comments, five of them mine", "seven comments, six of them mine"),
                ("comment total", f"{len(cs)} comments", f"{len(cs) + 5} comments"),
                ("38/38", "38/38", "37/38"),
                ("blame shift", "not the repository", "not our comments"),
                ("ownership", "most of it is mine", "most of it is his"),
                ("em dash", "All of it verifies:", "All of it verifies —:"),
                ("disclosure", "AI assistance", "no assistance")]
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
