"""Gate for the reply on deepseek-ai/DeepSeek-V3#1591.

Every figure re-derived from the dataset itself, every claim about his rules checked against the
issue text fetched live, the receipt link verified to resolve, and the room checked.

This one carries an extra duty. The first draft was HELD by a red team for doing the easy work --
verifying a hash and eleven field names -- and calling it a contribution, while the load-bearing
finding sat unexamined in the same 12KB file. And a STORM pass found that the provenance mechanism
the draft recommended had a confirmation-oracle flaw and an established name we had not used. So the
gate asserts that both corrections are visible in the outgoing text, not merely that the numbers add
up.

Run:  python probes/gate_deepseek_1591_reply.py
"""

import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DRAFT = os.path.join(REPO, "agora_output", "drafts", "reply_deepseek_1591_dataset_audit.md")
DATA = os.path.join(HERE, "longhun_shared_audit_dataset_v1.0.jsonl")
RECEIPT = os.path.join(HERE, "longhun_shared_audit_dataset_integrity.result.json")
ISSUE = "deepseek-ai/DeepSeek-V3/issues/1591"
PROBE_URL = ("https://raw.githubusercontent.com/DanceNitra/agora/main/probes/"
             "longhun_shared_audit_dataset_integrity.py")

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(f"  {'OK  ' if ok else 'FAIL'}  {name:58s} {detail}")


def gh(path, jq):
    try:
        r = subprocess.run(["gh", "api", path, "--jq", jq], capture_output=True, text=True,
                           timeout=60, encoding="utf-8", errors="replace")
        return (r.stdout or "").strip() if r.returncode == 0 else None
    except Exception:
        return None


def main():
    draft = " ".join(open(DRAFT, encoding="utf-8").read().split())
    recs = [json.loads(l) for l in open(DATA, encoding="utf-8") if l.strip()]
    rec = json.load(open(RECEIPT, encoding="utf-8"))

    print("OURS -- re-derived from the dataset, not from the receipt's summary")
    conf = [r for r in recs if r.get("verdict") == "confirmed_penetration"]
    hedge = ("可能", "未明确判定")
    hedged = [r for r in conf if any(h in str(r.get("rejection_reason", "")) for h in hedge)]
    check("10 of 18 confirmed verdicts have a hedging reason",
          len(hedged) == 10 and len(conf) == 18 and "Ten of your eighteen" in draft,
          f"{len(hedged)}/{len(conf)}")
    kinds = {}
    for r in conf:
        kinds[re.sub(r"\d+", "N", str(r.get("rejection_reason", "")))] = \
            kinds.get(re.sub(r"\d+", "N", str(r.get("rejection_reason", ""))), 0) + 1
    check("the 8 / 7 / 3 breakdown is correct",
          sorted(kinds.values(), reverse=True) == [8, 7, 3]
          and "| 8 |" in draft and "| **7** |" in draft and "| **3** |" in draft,
          str(sorted(kinds.values(), reverse=True)))

    lens = sorted(len(str(r.get("response", ""))) for r in recs)
    check("the response-length list is quoted exactly",
          ", ".join(str(x) for x in lens) in draft, f"max {lens[-1]}, three at {lens[-1]}")
    trunc = [r for r in recs if "...[truncated:" in str(r.get("response", ""))]
    check("three truncated responses, marker quoted",
          len(trunc) == 3 and "...[truncated:500chars]" in draft, f"{len(trunc)} truncated")

    rows = []
    for r in recs:
        m = re.search(r"(\d+)字符", str(r.get("rejection_reason", "")))
        if m:
            rows.append((int(m.group(1)), len(str(r.get("response", "")))))
    dis = [x for x in rows if x[0] != x[1]]
    deltas = [a - b for a, b in dis]
    check("nine of ten counts disagree, quoted as such",
          len(rows) == 10 and len(dis) == 9 and "nine of the ten" in draft,
          f"{len(dis)}/{len(rows)}")
    check("the delta range 3 to 242 is correct",
          min(deltas) == 3 and max(deltas) == 242 and "3 to 242 characters" in draft,
          f"{min(deltas)}..{max(deltas)}")
    check("the paired examples are quoted correctly",
          "556 vs 423" in draft and "635 vs 423" in draft and "665 vs 423" in draft
          and "171 vs 162" in draft)

    check("SHA-256 prefix matches the receipt", rec["sha256_measured"].startswith("b1a8a650")
          and rec["sha256_measured"] == rec["sha256_published"] and "b1a8a650" in draft)
    check("19 records, 11 fields, uniqueness quoted",
          rec["records"] == 19 and len(rec["distinct_keys"]) == 11
          and "19/19 unique" in draft and "11 declared fields" in draft)
    check("the false positive is quoted with the real value",
          "\U0001f409bd3d364307040579" in draft and "REQ-07040579-011" in draft
          and any(r.get("dna_sig") == "\U0001f409bd3d364307040579" for r in recs))
    check("no negative class, with the counts",
          "18 of 19 sharing a verdict" in draft
          and sum(1 for r in recs if r.get("verdict") == "confirmed_penetration") == 18)

    print("\nTHEIRS -- checked against the issue text, live")
    body = gh(f"repos/{ISSUE}", ".body")
    if not body:
        check("fetched the issue", False, "gh unavailable, cannot verify what he wrote")
    else:
        b = " ".join(body.split())
        check("he really states the four rules we audit against",
              "口径锁" in b and "ANSI" in b and "SHA-256" in b)
        check("rule 2 really does NOT mention truncation",
              "ANSI" in b and "截断" not in b and "truncat" not in b.lower(),
              "so calling truncation undeclared is fair")
        check("he really invites frameworks to run diagnostics",
              "TAT" in b and "Cophy" in b and "HeartFlow" in b)
        check("the published SHA-256 in the issue is the one we checked",
              rec["sha256_published"] in b)

    print("\nRED-TEAM AND STORM FIXES")
    check("RT1 the label-set finding LEADS, not the hash check",
          draft.index("Ten of your eighteen") < draft.index("SHA-256"),
          "the load-bearing finding is first")
    check("RT2 the false positive leads with OUR error",
          "A defect in my check, not in your data" in draft
          or "My scanner was wrong once" in draft)
    check("STORM1 the confirmation-oracle flaw is named and corrected",
          "confirmation oracle" in draft and "keyed hash (HMAC)" in draft
          and "a published salt does not help" in draft)
    check("STORM2 the established mechanism is named, not invented",
          "Merkle inclusion proof" in draft and "RFC 6962" in draft
          and "RFC 9162" in draft and "Schneier and Kelsey" in draft)
    check("STORM3 we withdraw our own bad advice explicitly",
          "it would have been bad advice" in draft)
    check("STORM4 prior art is named without belittling 19 records",
          "JailbreakBench" in draft and "garak" in draft
          and "That is your contribution" in draft)
    check("we do not assert what we did not verify",
          "evidence rather than proof" in draft)

    print("\nTHE LINK AND THE ROOM")
    code = subprocess.run(["curl", "-sL", "-o", os.devnull, "-w", "%{http_code}", PROBE_URL],
                          capture_output=True, text=True).stdout.strip()
    check("the receipt link resolves", code == "200", f"HTTP {code}")
    state = gh(f"repos/{ISSUE}", ".state")
    ncom = gh(f"repos/{ISSUE}", ".comments")
    check("issue is open", state == "open", f"state={state}")
    check("we are still first, or know we are not", ncom is not None,
          f"{ncom} comments now (was 0 when measured)")

    n = len(checks)
    bad = [c for c in checks if not c[1]]
    print("\n" + "=" * 76)
    print(f"{n - len(bad)}/{n} checks pass")
    if bad:
        print("BLOCKED -- do not send:")
        for name, _, detail in bad:
            print(f"   - {name}  {detail}")
    else:
        print("GATE PASSES. Requires the owner's approval of this exact text before sending.")
    print("=" * 76)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
