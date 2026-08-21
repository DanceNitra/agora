"""Audit longhun v1.1-negative r2 against the rules ITS AUTHOR states for it.

Same standard as our v1.0 audit (17/17 on deepseek-ai/DeepSeek-V3#1591): every check is
against something @UID9622 declared, not against a standard we invented for him. He has
now done two things that deserve checking rather than applause -- he published a negative
class that did not exist in the source logs, and then tightened his own acceptance standard
and removed four records for "refusing while leaking the system prompt", dropping an entire
model because all of its rejections were that shape.

Two questions worth more than re-verifying the hash:

  A. DID THE TIGHTENING HOLD? He fixed four named instances. A fix lands at the instance and
     the class survives -- so the surviving nineteen are searched for the same leak markers
     he named in the four he removed.

  B. ARE THE TWO CLASSES COMPARABLE AT ALL? The set is offered as a calibration set on which
     precision/recall/F1 can be computed. v1.0's positives are historical production records
     from feedback_pool; v1.1's negatives are a fresh adversarial run against local models.
     If the two classes differ in model, collection process and time as well as in label,
     then an F1 computed across them scores the collection difference too. That is not a
     defect in his work -- he declared the provenance honestly -- but it is a boundary any
     framework calibrating on this needs before it quotes a number.

Everything is fetched live and hashed. No model calls.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter

BASE = "https://raw.githubusercontent.com/UID9622/longhun-financial-deep-seek/main/data/shared-audit"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_longhun_v11")
SHA_R2 = "156d3ebb59ec22500b8851be14b1db6aea1963b8754fcd7b6b9e4080361c7378"
SHA_R1 = "b78c9509b70831504860f1b32e3f25e2fcb56fc59162e64628658a24c30e6e9f"

DECLARED_FIELDS = {"request_id", "timestamp", "model", "prompt", "response", "verdict",
                   "rejection_reason", "attack_category", "dna_sig", "record_type", "source"}
# the four he named as removed, verbatim from his r2 comment
REMOVED_IDS = ["REQ-NEG-dc712c22-009", "REQ-NEG-4a41a796-013",
               "REQ-NEG-d2c047bf-015", "REQ-NEG-25890147-027"]
DROPPED_MODEL = "longhun-v42-sys:q4"
# the leak markers he named in those four records, in his words
LEAK_MARKERS = ["家法第一条", "P0熔断", "system prompt", "所有请求必须与CSDN文章内容相关",
                "系统提示", "你的身份是", "以下规则"]
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PII = [("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
       ("long digit run", re.compile(r"\d{11,}")),
       ("api key shape", re.compile(r"(?i)(sk|api[_-]?key|token)[\"'\s:=]{1,4}[A-Za-z0-9_\-]{16,}")),
       ("private key", re.compile(r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY"))]

rows: list[tuple[bool, str, str]] = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))


def fetch(name: str) -> bytes:
    os.makedirs(CACHE, exist_ok=True)
    dst = os.path.join(CACHE, name)
    if not os.path.exists(dst):
        r = subprocess.run(["curl", "-sf", f"{BASE}/{name}"], capture_output=True)
        if r.returncode != 0:
            return b""
        open(dst, "wb").write(r.stdout)
    return open(dst, "rb").read()


def records(raw: bytes) -> list[dict]:
    return [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]


def main() -> int:
    neg_raw = fetch("longhun-shared-audit-dataset-v1.1-negative.jsonl")
    pos_raw = fetch("longhun-shared-audit-dataset-v1.0.jsonl")
    schema = fetch("SCHEMA.md").decode("utf-8", "replace")
    manifest = fetch("MANIFEST.md").decode("utf-8", "replace")
    readme = fetch("README.md").decode("utf-8", "replace")
    sig = fetch("longhun-shared-audit-dataset-v1.1-negative.jsonl.asc")
    ck(bool(neg_raw) and bool(pos_raw), "both datasets fetched",
       f"neg={len(neg_raw)}B pos={len(pos_raw)}B")
    if not neg_raw:
        return 2

    h = hashlib.sha256(neg_raw).hexdigest()
    ck(h == SHA_R2, "SHA-256 is the r2 value he published, not the retracted r1", h[:16])
    ck(h != SHA_R1, "and the superseded r1 hash is genuinely gone")

    neg, pos = records(neg_raw), records(pos_raw)
    ck(len(neg) == 19, "19 records, as stated", str(len(neg)))
    ck(all(set(r) == DECLARED_FIELDS for r in neg),
       "every record carries exactly the 11 declared fields",
       str(sorted(set().union(*[set(r) for r in neg]) - DECLARED_FIELDS) or "no extras"))
    ck(all(r["verdict"] == "rejected" for r in neg), "every verdict is 'rejected', as stated",
       str(Counter(r["verdict"] for r in neg)))
    ids = [r["request_id"] for r in neg]
    ck(len(set(ids)) == len(ids), "request_id unique, which is what he says guarantees uniqueness",
       f"{len(set(ids))}/{len(ids)}")

    # --- A. did the tightening hold? ---------------------------------------------------------
    still_present = [i for i in REMOVED_IDS if i in ids]
    ck(not still_present, "all four records he says he removed are absent",
       str(still_present or "none present"))
    models = Counter(r["model"] for r in neg)
    ck(DROPPED_MODEL not in models,
       f"the model he dropped entirely ({DROPPED_MODEL}) contributes nothing", str(list(models)))
    ck(len(models) == 6, "six models, as he states after the drop", str(len(models)))

    hits = []
    for r in neg:
        for mark in LEAK_MARKERS:
            if mark in (r.get("response") or ""):
                hits.append((r["request_id"], r["model"], mark))
    ck(not hits, "NO surviving record carries a leak marker he named in the four he removed",
       str(hits[:4]) if hits else "0 of 19")

    # a control: the search must be able to find these markers when they are there
    planted = dict(neg[0])
    planted["response"] = planted["response"] + " 家法第一条规则：所有请求必须与CSDN文章内容相关"
    found = any(m in planted["response"] for m in LEAK_MARKERS)
    ck(found, "CONTROL: the leak search finds a planted marker, so the clean result can fail")

    ck(not any(ANSI.search(json.dumps(r, ensure_ascii=False)) for r in neg),
       "no ANSI escapes survive, as rule 2 requires")
    pii = [(name, r["request_id"]) for r in neg for name, rx in PII
           for f in ("prompt", "response", "rejection_reason") if rx.search(r.get(f) or "")]
    ck(not pii, "no residual secret or PII patterns", str(pii[:3]) if pii else "clean")

    trunc = [r["request_id"] for r in neg if "[truncated:" in (r.get("response") or "")]
    ck(not trunc or "truncat" in schema.lower() or "truncat" in readme.lower(),
       "any truncation present is declared in the docs", f"{len(trunc)} truncated records")

    # --- his dna_sig explanation, checked rather than accepted --------------------------------
    dna = Counter(r["dna_sig"] for r in neg)
    repeats = {d: c for d, c in dna.items() if c > 1}
    ck(bool(repeats), "dna_sig does repeat across records, exactly as he warns it will",
       f"{len(dna)} distinct over {len(neg)} records")
    ck(re.search(r"dna_sig", schema) is not None,
       "and SCHEMA.md documents dna_sig, where he says he wrote the explanation")
    same_prompt = all(len({r["prompt"] for r in neg if r["dna_sig"] == d}) == 1 for d in repeats)
    ck(same_prompt, "every repeated dna_sig really does correspond to one attack prompt, "
                    "which is the reason he gives for the repeats")

    # --- B. are the two classes comparable? ----------------------------------------------------
    pos_models, neg_models = {r.get("model") for r in pos}, {r["model"] for r in neg}
    overlap = pos_models & neg_models
    ck(True, "MEASUREMENT positive-class models", str(sorted(pos_models)))
    ck(True, "MEASUREMENT negative-class models", str(sorted(neg_models)))
    ck(True, "MEASUREMENT models shared by both classes",
       str(sorted(overlap)) + f"  ({len(overlap)} of {len(pos_models | neg_models)})")
    pos_src, neg_src = Counter(r.get("source") for r in pos), Counter(r.get("source") for r in neg)
    ck(True, "MEASUREMENT source field, positive class", str(dict(pos_src)))
    ck(True, "MEASUREMENT source field, negative class", str(dict(neg_src)))
    shared_prompts = {r.get("prompt") for r in pos} & {r["prompt"] for r in neg}
    ck(True, "MEASUREMENT attack prompts appearing in BOTH classes",
       f"{len(shared_prompts)} of {len({r.get('prompt') for r in pos})} positive prompts")

    ck(bool(sig), "the detached GPG signature is published beside the data",
       f"{len(sig)}B — NOT verified here: we do not hold his public key")

    out = {
        "probe": "longhun_v11_negative_audit",
        "sha256": h, "records": len(neg),
        "models_negative": dict(models), "models_positive": dict(Counter(r.get("model") for r in pos)),
        "models_shared": sorted(overlap),
        "dna_distinct": len(dna), "leak_marker_hits": hits,
        "prompts_in_both_classes": len(shared_prompts),
        "removed_ids_still_present": still_present,
        "checks": [{"pass": ok, "label": l, "detail": d} for ok, l, d in rows],
    }
    json.dump(out, open(os.path.join(HERE, "longhun_v11_negative_audit.result.json"), "w",
                        encoding="utf-8"), indent=2, ensure_ascii=False)

    for ok, l, d in rows:
        tag = "    " if l.startswith("MEASUREMENT") else ("PASS" if ok else "FAIL")
        print(f"  {tag}  {l}" + (f"   [{d}]" if d else ""))
    real = [r for r in rows if not r[1].startswith("MEASUREMENT")]
    p = sum(1 for ok, _, _ in real if ok)
    print(f"\n{p}/{len(real)} checks pass")
    return 0 if p == len(real) else 1


if __name__ == "__main__":
    sys.exit(main())
