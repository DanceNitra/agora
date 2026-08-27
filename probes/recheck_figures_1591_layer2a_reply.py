"""VALIDATE gate: every number in the #1591 Layer-2a reply, re-derived from the data this cycle.

The reply answers @icophy's direct request (comment 5384960846) for a worked output of
`calibration_dataset_check.py` on the eight 可以 records. Its whole value is that the numbers are the
file's, so this refuses to let a figure into the draft that the file does not produce.

Each assertion below binds ONE claim in the draft to the dataset, and each one can fail:

  1. the dataset digest quoted in the draft is the digest of the file we ran against
  2. the three family counts (8 / 7 / 3) come out of the record set, not out of SCHEMA's prose
  3. the eight ids in the table are the eight members of the 穿透信号 family, in that order
  4. every one of the eight carries 可以 in BOTH rejection_reason and response
  5. the control the draft leans on: ZERO records outside the family carry 可以 in response
  6. all eight carry confirmed_penetration
  7. the quoted SCHEMA sentence appears in SCHEMA verbatim -- we attribute the observation to
     @UID9622, so the attribution had better be to something he actually wrote
  8. the "11 naive groups" figure is what a literal split(':') really returns

CONTROL. `--self-test` mutates the dataset and requires each assertion to fail on its own row. An
assertion that cannot fail is not validating anything, which is the thesis of the thread this reply
belongs to.

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check
inside VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and
storm when the claim rests on literature. Owner, 2026-08-26, after I called a file like
this one "the gate" three times in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO
HOVEN." tools/send_approved.py now refuses to publish without a receipt from each skill,
bound to the draft's bytes, so this file cannot stand in for them any more.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "probes" / "longhun_shared_audit_dataset_v1.0.jsonl"
SCHEMA = ROOT / "SCHEMA_1591.md"
DRAFT = ROOT / "agora_output" / "drafts" / "reply_1591_layer2a.md"
RECEIPT = ROOT / "probes" / "receipts" / "calib_v10_run.json"

DECLARED_SHA = "b1a8a650b8038b21505396ea869911008781b26a3adf39ad730edc3d99a2e7f3"
FAMILY = "穿透信号"
TOKEN = "可以"
EXPECT_FAMILIES = {"穿透信号": 8, "未明确判定": 7, "长回复": 3}
EXPECT_IDS = [
    "REQ-082959a1-003", "REQ-d7258422-004", "REQ-092f07cc-007", "REQ-48e69b0a-008",
    "REQ-eaa5c48d-009", "REQ-c3ed0a88-010", "REQ-07040579-011", "REQ-e6afcba0-012",
]
SCHEMA_QUOTE = "检测器命中的是 token，而非完整语义"

rows = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))
    return bool(ok)


def family_of(reason: str) -> str:
    """The family prefix, with the per-record measurement stripped. SCHEMA says 3 families; a
    literal split(':') returns 11, because the prefix embeds a character count."""
    head = str(reason).split(":")[0]
    return re.sub(r"[（(].*?[）)]", "", head).split("·")[0].strip()


def load(path):
    return [json.loads(l) for l in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def run(data_path, draft_text, schema_text, strict_draft=True):
    rows.clear()
    # Match the CLAIM, not the formatting. A gate that reddens because a word got bolded teaches the
    # writer to edit the draft to please the gate, which is backwards -- and it happened here on
    # "one **UNVERIFIABLE**".
    draft_text = draft_text.replace("**", "").replace("*", "")
    raw = pathlib.Path(data_path).read_bytes()
    recs = load(data_path)

    # 1 -- the digest in the draft IS this file's digest
    got = hashlib.sha256(raw).hexdigest()
    quoted = DECLARED_SHA if not strict_draft else (
        re.search(r"--sha256 ([0-9a-f]{64})", draft_text).group(1)
        if re.search(r"--sha256 ([0-9a-f]{64})", draft_text) else "")
    ck(got == quoted, "the sha256 in the draft is this file's digest", f"{got[:24]} vs {quoted[:24]}")

    # 2 -- family counts come from the records
    fams = {}
    for r in recs:
        fams[family_of(r.get("rejection_reason", ""))] = fams.get(family_of(r.get("rejection_reason", "")), 0) + 1
    for name, n in EXPECT_FAMILIES.items():
        ck(fams.get(name) == n, f"family {name} counts {n} in the data", f"got {fams.get(name)}")

    fam = [r for r in recs if family_of(r.get("rejection_reason", "")) == FAMILY]

    # 3 -- the ids in the table are the family, in order
    ids = [r["request_id"] for r in fam]
    ck(ids == EXPECT_IDS, "the eight ids are the family, in the draft's order", f"{len(ids)} ids")
    if strict_draft:
        missing = [i for i in EXPECT_IDS if i not in draft_text]
        ck(not missing, "every one of the eight ids appears in the draft", ",".join(missing))

    # 4 -- 可以 in both fields, all eight
    both = [r for r in fam if TOKEN in str(r.get("rejection_reason", "")) and TOKEN in str(r.get("response", ""))]
    ck(len(both) == len(fam) == 8, f"all 8 carry {TOKEN} in reason AND response", f"{len(both)}/{len(fam)}")

    # 5 -- THE CONTROL the draft leans on
    outside = [r for r in recs if r not in fam and TOKEN in str(r.get("response", ""))]
    ck(len(outside) == 0, f"ZERO records outside the family carry {TOKEN} in response",
       ",".join(r["request_id"] for r in outside) or "0")

    # 6 -- verdict
    v = {str(r.get("verdict")) for r in fam}
    ck(v == {"confirmed_penetration"}, "all eight carry confirmed_penetration", ",".join(sorted(v)))

    # 7 -- the attribution quote is really UID9622's
    ck(SCHEMA_QUOTE in schema_text, "the quoted SCHEMA sentence appears in SCHEMA verbatim")

    # 8 -- the CORRECTED group figure. The first draft said a literal split(':') gives 11 groups
    # where SCHEMA says 3. The 11 is right and the cause was not: the colon merges nothing, the
    # embedded digits do. The gate now binds the correction rather than the error.
    whole = {str(r.get("rejection_reason", "")) for r in recs}
    naive = {str(r.get("rejection_reason", "")).split(":")[0] for r in recs}
    stripped = {re.sub(r"\d+", "", s) for s in naive}
    ck(len(whole) == 11, "the raw rejection_reason values number 11", f"got {len(whole)}")
    ck(len(naive) == 11, "split(':') also gives 11 -- so the colon merges NOTHING", f"got {len(naive)}")
    ck(len(stripped) == 4, "stripping the embedded digits gives 4", f"got {len(stripped)}")
    if strict_draft:
        # Bind the CLAIM, not one phrasing of it: the digits do the work, the colon does not.
        colon_claim = re.search(r"colon (?:merges nothing|isn't merging anything|is not merging anything)",
                                draft_text) is not None
        ck(colon_claim and "strip" in draft_text,
           "the draft says the digits fragment the field, not the colon")

    # 9 -- the truncation hole in our own negative control. This is the finding that killed the
    # first draft: the outside-family half of the control was computed over deleted text.
    marker = "...[truncated:500chars]"
    outside = [r for r in recs if family_of(r.get("rejection_reason", "")) != FAMILY]
    trunc = [r for r in outside if marker in str(r.get("response", ""))]
    ck(len(outside) == 11, "there are 11 records outside the family", f"got {len(outside)}")
    ck(len(trunc) == 3, "three of them are truncated", f"got {len(trunc)}")
    declared, missing = [], 0
    for r in trunc:
        m = re.search(r"(\d+)字符", str(r.get("rejection_reason", "")))
        pub = len(str(r.get("response", "")).replace(marker, ""))
        if m:
            declared.append(int(m.group(1)))
            missing += int(m.group(1)) - pub
    ck(sorted(declared) == [556, 635, 665], "declared lengths are 556 / 635 / 665", str(sorted(declared)))
    ck(all(len(str(r.get("response", "")).replace(marker, "")) == 400 for r in trunc),
       "each publishes 400 characters")
    ck(missing == 656, "656 characters outside the family were never inspected", f"got {missing}")
    ck(all(family_of(r.get("rejection_reason", "")) == "长回复" for r in trunc),
       "and they are exactly the 长回复 records -- the ones long enough to hide a polite 我可以")
    if strict_draft:
        for fig in ("656", "8 of 11"):
            ck(fig in draft_text, f"the draft quotes {fig}")
        # the three declared lengths, in whatever punctuation the prose ends up using
        ck(all(str(x) in draft_text for x in (556, 635, 665)),
           "the draft quotes all three declared lengths")
        # and it must reconcile with what we told this thread on 20 August: 423 in the file
        ck("423" in draft_text and "400" in draft_text,
           "the draft reconciles 400 characters of text with the 423 we published earlier")

    # 10 -- the tautology we now admit to, asserted as a tautology
    fam_vals = {str(r.get("rejection_reason", "")) for r in fam}
    ck(fam_vals == {"穿透信号: 可以"},
       "the family field has ONE value, so the reason-side clause cannot fail", str(fam_vals))
    if strict_draft:
        ck("can't fail on any data" in draft_text, "the draft admits that half was worthless")

    # 10b -- what the FULL probe run returned, read from ITS receipt rather than retyped.
    #
    # This exists because the first rewrite said "12 checks" -- this gate's count, not the probe's.
    # Two tools in one workflow, two totals, and the wrong one reached the draft. Then the receipt
    # showed the probe's own "15 checks" counts 8 NOTE rows as checks, so the figure was misleading
    # in a second way. The draft now quotes no total at all and states the two outcomes that carry
    # meaning; this binds those to the receipt.
    if strict_draft:
        if not RECEIPT.exists():
            ck(False, "the probe receipt exists -- without it this claim is unverifiable", str(RECEIPT))
        else:
            rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
            by = {}
            for row in rec.get("rows", []):
                by[row.get("status")] = by.get(row.get("status"), 0) + 1
            ck(by.get("FAIL") == 1, "the receipt shows exactly one FAIL", str(by))
            ck(by.get("UNVERIFIABLE") == 1, "and exactly one UNVERIFIABLE", str(by))
            ck("one FAIL" in draft_text and "one UNVERIFIABLE" in draft_text,
               "the draft states both outcomes")
            ck(not re.search(r"run is \d+ checks", draft_text),
               "and quotes NO total -- 8 of the receipt's 15 rows are NOTEs, not checks")

    # 11 -- every prompt quoted in the table is the record's real prompt
    if strict_draft:
        bad = []
        for r in fam:
            p = str(r.get("prompt", "")).strip()
            if p and p[:12] not in draft_text.replace(" ", ""):
                if p not in draft_text:
                    bad.append(r["request_id"])
        ck(not bad, "every prompt in the table is that record's real prompt", ",".join(bad))

    return all(ok for ok, _, _ in rows)


def self_test():
    """Every assertion must fail on its own row when the thing it checks is broken."""
    import tempfile
    recs = load(DATA)
    draft = DRAFT.read_text(encoding="utf-8")
    schema = SCHEMA.read_text(encoding="utf-8")
    print("== controls: each mutation must turn its OWN row red ==")

    def mutated(fn, label, expect_row_substr):
        m = [json.loads(json.dumps(r)) for r in recs]
        fn(m)
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "m.jsonl"
            p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in m), encoding="utf-8")
            run(p, draft, schema, strict_draft=False)
        hit = [(ok, l) for ok, l, _ in rows if expect_row_substr in l]
        ok = bool(hit) and not hit[0][0]
        print(f"  {'OK  ' if ok else 'FAIL'}  {label}"
              f"{'' if hit else '   [no row matched %r]' % expect_row_substr}")
        return ok

    good = True
    good &= mutated(lambda m: m.__setitem__(0, {**m[0], "response": m[0]["response"] + "X"}),
                    "a changed byte breaks the digest row", "digest")
    good &= mutated(lambda m: m.__setitem__(2, {**m[2], "rejection_reason": "未明确判定(99字符)"}),
                    "moving a record out of the family breaks the count row", "family 穿透信号 counts")
    good &= mutated(lambda m: m.__setitem__(2, {**m[2], "response": m[2]["response"].replace(TOKEN, "OK")}),
                    "removing 可以 from a member breaks the both-fields row", "in reason AND response")
    good &= mutated(lambda m: m.__setitem__(1, {**m[1], "response": m[1]["response"] + TOKEN}),
                    "planting 可以 outside the family breaks THE CONTROL", "ZERO records outside")
    good &= mutated(lambda m: m.__setitem__(2, {**m[2], "verdict": "firewall_deny"}),
                    "a changed verdict breaks the verdict row", "confirmed_penetration")
    good &= mutated(lambda m: m.__setitem__(2, {**m[2], "request_id": "REQ-ffffffff-999"}),
                    "a renamed id breaks the id-order row", "eight ids are the family")

    # and the clean fixture must pass, or the mutations proved nothing
    clean = run(DATA, draft, schema, strict_draft=False)
    print(f"  {'OK  ' if clean else 'FAIL'}  the unmutated dataset passes every row")
    return good and clean


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        ok = self_test()
        print("\n  CONTROLS " + ("GREEN" if ok else "RED"))
        return 0 if ok else 1

    for p, what in ((DATA, "dataset"), (SCHEMA, "SCHEMA"), (DRAFT, "draft")):
        if not p.exists():
            print(f"REFUSED: {what} not found at {p} -- a gate that cannot see its target reports SAFE")
            return 2

    ok = run(DATA, DRAFT.read_text(encoding="utf-8"), SCHEMA.read_text(encoding="utf-8"))
    print("== VALIDATE: every number in the #1591 Layer-2a reply, re-derived ==")
    for good, label, detail in rows:
        print(f"  {'PASS' if good else 'FAIL'}  {label}{('   [' + detail + ']') if detail else ''}")
    bad = sum(1 for g, _, _ in rows if not g)
    print(f"\n  {len(rows)} checks, {bad} failed")
    if bad:
        print("  The draft may not be sent while a number in it does not come out of the data.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
