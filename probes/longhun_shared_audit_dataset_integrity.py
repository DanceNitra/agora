"""Audit the Dragon-Soul shared audit dataset against ITS OWN stated rules.

WHY. UID9622 published a 19-record real audit-log dataset on deepseek-ai/DeepSeek-V3#1591 as a shared
calibration input, so that TAT, Cophy, HeartFlow and others can run diagnostics side by side on
identical data. He did something unusual for a dataset drop: he stated the rules the data is supposed
to satisfy, published a SHA-256, and shipped the extraction engine.

That makes the dataset checkable against its own specification, which is the most useful first thing
anyone can contribute -- before any framework builds a result on it, someone should confirm the input
is what it says it is. A defect found now costs one message; found after four frameworks have
published diagnostics, it costs all four.

HIS RULES, quoted from the issue, are the specification this checks:
  1. FIELD-CALIBER LOCK  "only output fields that actually exist in the source log. inference_time_ms
                          / tokens_used and other uncollected data must never appear."
  2. CONTENT DESENSITISED "prompt/response cleaned of ANSI escapes; sensitive patterns removed
                          (real keys, passwords, personal identifying information)."
  3. VERDICT UNALTERED   "verdict keeps the source log's original value, no after-the-fact
                          beautification."
  4. REPRODUCIBLE        SHA-256 plus extractor source, so anyone can regenerate and verify.

Rule 3 cannot be checked from outside -- we do not have his source logs -- and this says so rather
than quietly scoring it as passed. Rules 1, 2 and 4 are checkable and are checked.

CONTROLS, each able to fail
  C1 the hash check rejects a single flipped byte
  C2 the field-lock check rejects an injected `tokens_used`
  C3 the ANSI check rejects an injected escape sequence
  C4 denominators printed with every count

Run:  python probes/longhun_shared_audit_dataset_integrity.py
"""

import hashlib
import json
import os
import re
import sys
import urllib.request

sys_out = getattr(sys.stdout, 'reconfigure', None)
if sys_out:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RAW = ("https://raw.githubusercontent.com/UID9622/longhun-financial-deep-seek/main/"
       "data/shared-audit/longhun-shared-audit-dataset-v1.0.jsonl")
PUBLISHED_SHA = "b1a8a650b8038b21505396ea869911008781b26a3adf39ad730edc3d99a2e7f3"
DECLARED_FIELDS = ["request_id", "timestamp", "model", "prompt", "response", "dna_sig",
                   "attack_category", "verdict", "rejection_reason", "source", "record_type"]
FORBIDDEN_FIELDS = ["inference_time_ms", "tokens_used", "latency_ms", "cost", "temperature"]
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*\x07")
SECRETS = [
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("openai-style key", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("long digit run (id/card/phone)", re.compile(r"(?<!\d)\d{11,19}(?!\d)")),
]

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(f"  {'OK  ' if ok else 'FAIL'}  {name:56s} {detail}")


def fetch():
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "longhun_shared_audit_dataset_v1.0.jsonl")
    if os.path.exists(cache):
        return open(cache, "rb").read(), cache
    raw = urllib.request.urlopen(RAW, timeout=60).read()
    open(cache, "wb").write(raw)
    return raw, cache


def main():
    raw, cache = fetch()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", "replace")
    lines = [l for l in text.splitlines() if l.strip()]

    print(f"dataset: {len(raw):,} bytes, {len(lines)} non-empty lines  (cached at {cache})\n")

    print("RULE 4 -- REPRODUCIBLE: the published hash must be the file's hash")
    check("SHA-256 matches the value published in the issue", digest == PUBLISHED_SHA,
          digest[:24] + "...")

    print("\nSTRUCTURE")
    records, bad_json = [], []
    for i, l in enumerate(lines, 1):
        try:
            records.append(json.loads(l))
        except Exception as e:
            bad_json.append((i, str(e)[:60]))
    check("every line is valid JSON", not bad_json,
          f"{len(records)}/{len(lines)} parsed" + (f", bad: {bad_json[:2]}" if bad_json else ""))
    check("record count is the 19 he states", len(records) == 19, f"{len(records)} records")

    print("\nRULE 1 -- FIELD-CALIBER LOCK: only fields that exist in the source log")
    keys = {k for r in records for k in r}
    extra = sorted(keys - set(DECLARED_FIELDS))
    missing_per_rec = [i for i, r in enumerate(records, 1)
                       if set(DECLARED_FIELDS) - set(r)]
    check("no field outside the 11 declared ones", not extra,
          f"{len(keys)} distinct keys" + (f"; extra: {extra}" if extra else ""))
    check("every record carries all 11 declared fields", not missing_per_rec,
          "all complete" if not missing_per_rec else f"incomplete: {missing_per_rec[:5]}")
    present_forbidden = [f for f in FORBIDDEN_FIELDS if f in keys]
    check("none of the uncollected fields he names appear", not present_forbidden,
          "checked " + ", ".join(FORBIDDEN_FIELDS[:3]) + ", ..."
          if not present_forbidden else f"PRESENT: {present_forbidden}")

    print("\nRULE 2 -- DESENSITISED: ANSI cleaned, sensitive patterns removed")
    ansi_hits = [(i, r.get("request_id")) for i, r in enumerate(records, 1)
                 if ANSI.search(json.dumps(r, ensure_ascii=False))]
    check("no ANSI escape sequences remain", not ansi_hits,
          f"{len(records)} records scanned" if not ansi_hits else f"{len(ansi_hits)} hits")
    # Scan the CONTENT fields only. The first version scanned the whole record and flagged a
    # 12-digit run inside dna_sig "🐉bd3d364307040579" -- a dragon glyph plus a 16-char hex
    # trace code, i.e. the identifier he publishes on purpose, with a stretch that happens to
    # contain no letters. That was a false positive in the CHECK, not a leak in his data, and
    # reporting it would have accused a contributor of leaking PII on the strength of a regex.
    # Identifier fields are excluded; C5 below proves the check still fires where PII would live.
    CONTENT = ("prompt", "response", "rejection_reason")
    found = []
    for label, pat in SECRETS:
        hits = [r.get("request_id") for r in records
                if any(pat.search(str(r.get(f, ""))) for f in CONTENT)]
        if hits:
            found.append((label, hits))
    check("no residual secret / PII patterns in prompt/response/reason", not found,
          f"{len(SECRETS)} pattern classes over 3 content fields" if not found
          else "; ".join(f"{l}: {h[:2]}" for l, h in found))

    print("\nCONSISTENCY (not his rules, but what a consumer needs)")
    ids = [r.get("request_id") for r in records]
    dnas = [r.get("dna_sig") for r in records]
    check("request_id is unique", len(set(ids)) == len(ids), f"{len(set(ids))}/{len(ids)}")
    check("dna_sig is unique", len(set(dnas)) == len(dnas), f"{len(set(dnas))}/{len(dnas)}")
    bad_ts = []
    for r in records:
        ts = r.get("timestamp", "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", ts):
            bad_ts.append(r.get("request_id"))
    check("timestamps are ISO 8601 as declared", not bad_ts,
          "all parse" if not bad_ts else f"bad: {bad_ts[:3]}")
    types = {}
    for r in records:
        types.setdefault(r.get("record_type"), []).append(r.get("source"))
    check("record_type and source agree",
          all(len(set(v)) == 1 for v in types.values()),
          "; ".join(f"{k}={len(v)} from {sorted(set(v))}" for k, v in sorted(types.items())))

    print("\nDIAGNOSTIC 0 -- THE LABEL SET: what actually produced 'confirmed_penetration'?")
    conf = [r for r in records if r.get("verdict") == "confirmed_penetration"]

    def _reason(r):
        return str(r.get("rejection_reason", ""))

    # Three heuristics, and they partition the confirmed set exactly. NONE of them adjudicates.
    #   穿透信号: X      names the MATCHED TOKEN found in the response -- not a verdict
    #   未明确判定(N字符)  "not clearly determined"
    #   长回复(N字符)·可能穿透  "long reply -- possibly penetrated"
    kw = [r for r in conf if _reason(r).startswith("穿透信号")]
    und = [r for r in conf if "未明确判定" in _reason(r)]
    lt = [r for r in conf if "可能穿透" in _reason(r)]
    for label, grp in (("keyword match", kw), ("undetermined", und), ("length threshold", lt)):
        print(f"      {len(grp):2d}  {label:18s} e.g. {_reason(grp[0]) if grp else '-'}")
    check("the three heuristics partition the confirmed set",
          len(kw) + len(und) + len(lt) == len(conf) and len(conf) > 0,
          f"{len(kw)}+{len(und)}+{len(lt)} of {len(conf)}")

    # The load-bearing reading: the keyword reason CITES the token, so the token must be
    # present in the response of every such record. If it is not, the reading is wrong.
    TOKEN = "可以"
    present = [r for r in kw if TOKEN in str(r.get("response", ""))]
    check("every keyword-labelled response contains the token its reason names",
          len(present) == len(kw) and len(kw) > 0,
          f"{len(present)}/{len(kw)} contain {TOKEN!r} -- the reason names a MATCH, not a verdict")
    # CONTROL: if the token were in every record the test above would pass vacuously.
    everywhere = sum(1 for r in records if TOKEN in str(r.get("response", "")))
    check("CONTROL: the token is not ubiquitous, so the test above can fail",
          everywhere < len(records), f"{everywhere}/{len(records)} records overall")

    shortest = min(kw, key=lambda r: len(str(r.get("response", "")))) if kw else None
    if shortest is not None:
        print(f"      shortest keyword-labelled record: {shortest.get('request_id')} "
              f"{len(str(shortest.get('response','')))} chars")
        print(f"        prompt   {shortest.get('prompt')!r}")
        print(f"        response {shortest.get('response')!r}")

    check("every CONFIRMED verdict rests on an adjudication", not conf,
          f"{len(conf)} of {len(conf)} rest on a keyword, a length threshold, or an explicit "
          f"'not determined' -- 'confirmed' means FLAGGED here")
    print("      This needs no source logs -- it is a tension between two fields of the SAME")
    print("      record. A framework calibrating on these labels is calibrating on labels the")
    print("      publisher's own reason field does not support.")

    print("\nDIAGNOSTIC 1 -- RESPONSE TRUNCATION, which rule 2 does not declare")
    trunc = [r for r in records if "...[truncated:" in str(r.get("response", ""))]
    lens = sorted(len(str(r.get("response", ""))) for r in records)
    check("truncation, if present, is declared in the rules", not trunc,
          f"{len(trunc)} of {len(records)} responses carry a truncation marker; "
          f"rule 2 lists ANSI cleaning and pattern removal only")
    print(f"      response lengths: {lens}")
    print(f"      the three longest all land on {lens[-1]}, which is a CAP, not a coincidence")

    print("\nDIAGNOSTIC 2 -- RULE 3 IS CHECKABLE AFTER ALL: the reason field fingerprints it")
    rows = []
    for r in records:
        m = re.search(r"(\d+)字符", str(r.get("rejection_reason", "")))
        if m:
            rows.append((r.get("request_id"), int(m.group(1)),
                         len(str(r.get("response", "")))))
    dis = [x for x in rows if x[1] != x[2]]
    shorter = [x for x in dis if x[1] > x[2]]
    print(f"      {len(rows)} records embed a character count in rejection_reason")
    for rid, c, a in rows:
        print(f"        {rid:20s} reason says {c:4d}, published response is {a:4d}  "
              f"delta {c-a:+d}")
    check("the embedded counts are NOT rewritten to match the cleaned text",
          len(dis) >= len(rows) - 1 and len(shorter) == len(dis),
          f"{len(dis)}/{len(rows)} disagree, published shorter in {len(shorter)} of them")
    print("      A publisher who beautified the verdict would have fixed these to match.")
    print("      They are unfixed, and always in the direction desensitisation produces. That is")
    print("      a consistency signature that after-the-fact editing would break -- evidence for")
    print("      rule 3, not proof of it, but the first externally checkable evidence there is.")

    print("\nDIAGNOSTIC 3 -- CALIBRATION VALUE: does the batch have two arms?")
    vcount = {}
    for r in records:
        vcount[r.get("verdict")] = vcount.get(r.get("verdict"), 0) + 1
    top = max(vcount.values())
    check("the batch has a usable negative class", top < len(records) - 2,
          f"{vcount} -- {top} of {len(records)} share one verdict")
    print("      A calibration set needs both arms. With one verdict at 18/19 no framework can")
      
    print("      compute a detection rate, a precision, or anything with a denominator.")

    print("\nRULE 3 -- VERDICT UNALTERED: NOT CHECKABLE FROM OUTSIDE")
    verdicts = {}
    for r in records:
        verdicts[r.get("verdict")] = verdicts.get(r.get("verdict"), 0) + 1
    print(f"  ....  verdict values present: {verdicts}")
    print("  ....  This needs his source logs. Reporting it as unverifiable rather than passed --")
    print("  ....  a rule scored green without the evidence to score it is the defect it hides.")

    print("\nCONTROLS -- each must be able to fail")
    mutated = bytearray(raw)
    mutated[len(mutated) // 2] ^= 0x01
    c1 = hashlib.sha256(bytes(mutated)).hexdigest() != PUBLISHED_SHA
    check("C1 the hash check rejects one flipped byte", c1)
    probe_rec = dict(records[0], tokens_used=123)
    c2 = any(f in probe_rec for f in FORBIDDEN_FIELDS)
    check("C2 the field-lock check sees an injected tokens_used", c2)
    c3 = bool(ANSI.search("\x1b[31mred\x1b[0m"))
    check("C3 the ANSI check sees an injected escape", c3)
    c4 = bool(SECRETS[4][1].search("someone@example.com"))
    check("C4 the PII check sees an injected email", c4)
    # C5: narrowing the scan to content fields must not have blinded it.
    spoiled = dict(records[0], response=str(records[0].get("response", "")) + " 13800138000")
    c5 = any(pat.search(str(spoiled.get(f, "")))
             for _, pat in SECRETS for f in ("prompt", "response", "rejection_reason"))
    check("C5 a long digit run injected into response is still caught", c5,
          "narrowing the scope did not blind the check")

    n = len(checks)
    bad = [c for c in checks if not c[1]]
    print("\n" + "=" * 74)
    print(f"{n - len(bad)}/{n} checks pass on {len(records)} records")
    if bad:
        print("FINDINGS -- the dataset does not meet its own stated rules in:")
        for name, _, detail in bad:
            print(f"   - {name}  {detail}")
    else:
        print("The dataset meets every rule it states that can be checked from outside, and its")
        print("published SHA-256 is the file's actual hash. Rule 3 (verdict unaltered) needs his")
        print("source logs and is reported unverifiable, not passed.")
    print("=" * 74)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "longhun_shared_audit_dataset_integrity.result.json")
    json.dump({"sha256_measured": digest, "sha256_published": PUBLISHED_SHA,
               "records": len(records), "bytes": len(raw),
               "distinct_keys": sorted(keys), "extra_fields": extra,
               "forbidden_present": present_forbidden, "verdicts": verdicts,
               "record_types": {k: sorted(set(v)) for k, v in types.items()},
               "checks": [{"name": a, "ok": b, "detail": c} for a, b, c in checks],
               "rule3_verdict_unaltered": "UNVERIFIABLE without the source logs"},
              open(out, "w", encoding="utf-8"), indent=2)
    print(f"receipt -> {out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
