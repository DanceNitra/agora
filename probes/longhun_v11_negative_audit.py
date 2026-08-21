"""Audit longhun v1.1-negative r2 -- and the previous version of THIS PROBE, which was too weak.

The first version of this file passed 19/19 and three of those passes were worth nothing.
An adversarial review found it, and every fault below was then confirmed against r1, which
is still in the author's git history at fb267b626740:

  1. A VACUOUS CHECK. It asserted that the four record ids the author named as removed were
     absent from r2. One of them, `REQ-NEG-25890147-027`, WAS NEVER IN r1 -- the record he
     actually removed is `-019`. An absence check on an id that never existed cannot fail.
     Ids here are positional and 14 of 19 were renumbered between revisions, so identity is
     the wrong key entirely; content is the right one.

  2. A COUNT THAT HID THE CHANGE. "19 records, as stated" passed on both revisions. By
     content, r1 -> r2 kept 15 responses, dropped 4 and ADDED 4. It was a substitution, and
     a check on the total could not see it.

  3. A LEAK SEARCH WITH 2/4 RECALL ON ITS OWN SOURCE RECORDS. The seven literal strings were
     copied from the author's prose description of the four records he removed. Two of those
     four do not contain them: he wrote `P0熔断` where the record says `P0条件立即熔断`, and
     `所有请求必须与CSDN...` where the record says `所有请求都必须与CSDN...` -- one inserted
     character defeats a literal. The old control planted a marker into a string WE
     concatenated and found it, which proves only that `in` works.

     The control that means something is RECALL ON THE REAL REMOVED RECORDS: the detector
     must find all four of the records the author himself judged to be leaking, or it has no
     standing to report zero on the nineteen that remain.

So this version fetches r1 as well as r2, compares by content, and gates its own detector on
the four records that are known-positive. It also runs the control a practitioner would ask
for before any scoring -- can the CLASS be predicted from surface features alone -- and
reports the answer even though it does not support the reading we expected.

Nothing here judges whether the seven survivors that carry an internal-configuration
fragment are "leaks". That is the author's standard to set; the probe reports what is there.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import sys
from collections import Counter

RAW = "https://raw.githubusercontent.com/UID9622/longhun-financial-deep-seek"
R2_REF, R1_REF = "main", "fb267b626740"
DIR = "data/shared-audit"
NEG = "longhun-shared-audit-dataset-v1.1-negative.jsonl"
POS = "longhun-shared-audit-dataset-v1.0.jsonl"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_longhun_v11")
SHA_R2 = "156d3ebb59ec22500b8851be14b1db6aea1963b8754fcd7b6b9e4080361c7378"
SHA_R1 = "b78c9509b70831504860f1b32e3f25e2fcb56fc59162e64628658a24c30e6e9f"

DECLARED = {"request_id", "timestamp", "model", "prompt", "response", "verdict",
            "rejection_reason", "attack_category", "dna_sig", "record_type", "source"}
DROPPED_MODEL = "longhun-v42-sys:q4"

# Core fragments rather than whole sentences, matched against whitespace-stripped text.
# The list is validated below against the four records the author removed; if it does not
# recall all four, the probe refuses to report anything about the survivors.
LEAK_CORE = ["家法", "熔断", "情绪容错", "留痕", "KPI更新", "为人民服务", "个人主权",
             "系统提示", "systemprompt", "CSDN", "LoRA", "微调", "基座"]

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PII = [("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
       ("long digit run", re.compile(r"\d{11,}")),
       ("private key", re.compile(r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY"))]

rows: list[tuple[bool, str, str]] = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))


def measure(label, detail):
    rows.append((None, label, detail))


def fetch(ref: str, name: str) -> bytes:
    os.makedirs(CACHE, exist_ok=True)
    dst = os.path.join(CACHE, f"{ref[:8]}_{name}")
    if not os.path.exists(dst):
        r = subprocess.run(["curl", "-sf", f"{RAW}/{ref}/{DIR}/{name}"], capture_output=True)
        if r.returncode != 0:
            return b""
        open(dst, "wb").write(r.stdout)
    return open(dst, "rb").read()


def recs(raw: bytes) -> list[dict]:
    return [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]


def flat(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def leaks(rec: dict) -> list[str]:
    body = flat(rec.get("response"))
    return [c for c in LEAK_CORE if flat(c) in body]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p, d = k / n, 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def main() -> int:
    # The console here is cp1250; the records are Chinese. Without this the probe dies
    # on its own output rather than on its measurement.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    n2_raw, n1_raw, p_raw = fetch(R2_REF, NEG), fetch(R1_REF, NEG), fetch(R2_REF, POS)
    ck(all([n2_raw, n1_raw, p_raw]), "r2, r1 and the positive set all fetched",
       f"r2={len(n2_raw)}B r1={len(n1_raw)}B pos={len(p_raw)}B")
    if not (n2_raw and n1_raw):
        return 2
    n2, n1, pos = recs(n2_raw), recs(n1_raw), recs(p_raw)

    ck(hashlib.sha256(n2_raw).hexdigest() == SHA_R2, "r2 hash is the published value")
    ck(hashlib.sha256(n1_raw).hexdigest() == SHA_R1, "and the file at fb267b62 is r1, "
       "so the revision really is recoverable")

    # --- 1. what actually changed, by CONTENT ------------------------------------------------
    c1, c2 = {r["response"] for r in n1}, {r["response"] for r in n2}
    dropped = [r for r in n1 if r["response"] not in c2]
    added = [r for r in n2 if r["response"] not in c1]
    measure("r1 -> r2 by content", f"kept {len(c1 & c2)}, dropped {len(dropped)}, ADDED {len(added)}")
    ck(len(dropped) == 4, "four records were dropped, as he states", str(len(dropped)))
    measure("record count is unchanged at 19 either way",
            "which is why a count check cannot see a substitution")
    ids1, ids2 = {r["request_id"] for r in n1}, {r["request_id"] for r in n2}
    measure("request_ids that differ between revisions",
            f"{len(ids1 ^ ids2) // 2} of {len(n2)} -- ids are positional, so identity is the wrong key")
    named = ["REQ-NEG-dc712c22-009", "REQ-NEG-4a41a796-013",
             "REQ-NEG-d2c047bf-015", "REQ-NEG-25890147-027"]
    never = [i for i in named if i not in ids1]
    measure("ids he named that never existed in r1", str(never) or "none")
    ck(all(i not in ids2 for i in named), "none of the ids he named is present in r2",
       "true, but vacuous for any id that never existed -- see above")

    # --- 2. THE CONTROL THAT GATES EVERYTHING BELOW -------------------------------------------
    recall = [r["request_id"] for r in dropped if leaks(r)]
    ck(len(recall) == len(dropped),
       "CONTROL: the detector finds EVERY record the author judged to be leaking",
       f"{len(recall)}/{len(dropped)} -- the previous literal list scored 2/4")
    detector_valid = len(recall) == len(dropped)

    # --- 3. only now, the survivors -------------------------------------------------------------
    if detector_valid:
        surv = {r["request_id"]: (leaks(r), r["model"]) for r in n2 if leaks(r)}
        measure("survivors carrying an internal-configuration fragment",
                f"{len(surv)} of {len(n2)}")
        for k, (f, m) in list(surv.items())[:8]:
            measure(f"    {k}", f"{m}  {f}")
        measure("NOT a verdict",
                "whether these count as leaks is the author's standard, not the probe's")
    else:
        ck(False, "survivors not reported -- the detector failed its own control")

    trunc = [r["request_id"] for r in n2 if "[truncated" in (r.get("response") or "")]
    measure("survivors whose response is truncated",
            f"{trunc} -- the search only sees the kept part")

    # --- 4. the plain integrity checks ------------------------------------------------------------
    ck(all(set(r) == DECLARED for r in n2), "every record carries exactly the 11 declared fields")
    ck(all(r["verdict"] == "rejected" for r in n2), "every verdict is 'rejected'")
    ids = [r["request_id"] for r in n2]
    ck(len(set(ids)) == len(ids), "request_id unique within r2", f"{len(set(ids))}/{len(ids)}")
    models = Counter(r["model"] for r in n2)
    ck(DROPPED_MODEL not in models, f"{DROPPED_MODEL} contributes nothing", str(len(models)) + " models")
    ck(not any(ANSI.search(json.dumps(r, ensure_ascii=False)) for r in n2), "no ANSI escapes")
    ck(not [1 for r in n2 for _, rx in PII for f in ("prompt", "response", "rejection_reason")
            if rx.search(r.get(f) or "")], "no residual secret or PII patterns")

    # --- 5. comparability, and the control that did NOT support our reading ----------------------
    pm, nm = sorted({r.get("model") for r in pos}), sorted({r["model"] for r in n2})
    measure("positive-class models", str(pm))
    measure("negative-class models", str(nm))
    measure("models shared by both classes", f"{sorted(set(pm) & set(nm))} of {len(set(pm) | set(nm))}")
    measure("distinct timestamps", f"positives {len({r.get('timestamp') for r in pos})}, "
                                   f"negatives {len({r['timestamp'] for r in n2})}")
    shared = {r.get("prompt") for r in pos} & {r["prompt"] for r in n2}
    pp = [r for r in pos if r.get("prompt") in shared]
    np_ = [r for r in n2 if r["prompt"] in shared]
    measure("attack prompts in BOTH classes",
            f"{len(shared)} prompts -> {len(pp)} positive records and {len(np_)} negative records")
    undet = [r for r in pp if "未明确判定" in (r.get("rejection_reason") or "")]
    measure("of those positives, how many the pipeline itself called UNDETERMINED",
            f"{len(undet)} of {len(pp)} -- for those the two classes are not opposite outcomes")

    data = [(1, r) for r in pos] + [(0, r) for r in n2]
    F = {"response length": lambda r: len(r.get("response") or ""),
         "prompt length": lambda r: len(r.get("prompt") or ""),
         "newlines": lambda r: (r.get("response") or "").count("\n"),
         "digits": lambda r: sum(c.isdigit() for c in (r.get("response") or ""))}

    def loo(fn):
        xs = [(fn(r), y) for y, r in data]
        good = 0
        for i, (v, y) in enumerate(xs):
            tr = [xs[j] for j in range(len(xs)) if j != i]
            mp = statistics.median([a for a, b in tr if b == 1])
            mn = statistics.median([a for a, b in tr if b == 0])
            good += ((1 if (v > (mp + mn) / 2) == (mp > mn) else 0) == y)
        return good, len(xs)

    best = max(((loo(fn), n) for n, fn in F.items()), key=lambda t: t[0][0])
    (k, n), fname = best
    lo, hi = wilson(k, n)
    measure("CONTROL: can the CLASS be predicted from surface features alone?",
            f"best single feature '{fname}' {k}/{n} = {k / n:.3f}, 95% Wilson [{lo:.3f}, {hi:.3f}]")
    measure("    chance is 0.500, so this interval",
            "EXCLUDES chance" if lo > 0.5 else "INCLUDES chance -- it does NOT show the classes "
                                              "are trivially separable by provenance")

    out = {"probe": "longhun_v11_negative_audit", "r2_sha": hashlib.sha256(n2_raw).hexdigest(),
           "content_kept": len(c1 & c2), "content_dropped": len(dropped), "content_added": len(added),
           "ids_named_that_never_existed": never,
           "detector_recall_on_removed": f"{len(recall)}/{len(dropped)}",
           "survivors_with_config_fragment": sorted(
               [r["request_id"] for r in n2 if leaks(r)]) if detector_valid else None,
           "models_positive": pm, "models_negative": nm, "models_shared": sorted(set(pm) & set(nm)),
           "shared_prompts": len(shared), "positive_records_on_shared": len(pp),
           "negative_records_on_shared": len(np_), "undetermined_positives_on_shared": len(undet),
           "surface_control": {"feature": fname, "correct": k, "n": n,
                               "acc": round(k / n, 3), "wilson95": [round(lo, 3), round(hi, 3)]},
           "checks": [{"pass": p, "label": l, "detail": d} for p, l, d in rows]}
    json.dump(out, open(os.path.join(HERE, "longhun_v11_negative_audit.result.json"), "w",
                        encoding="utf-8"), indent=2, ensure_ascii=False)

    for p, l, d in rows:
        tag = "    " if p is None else ("PASS" if p else "FAIL")
        print(f"  {tag}  {l}" + (f"   [{d}]" if d else ""))
    hard = [r for r in rows if r[0] is not None]
    ok = sum(1 for p, _, _ in hard if p)
    print(f"\n{ok}/{len(hard)} checks pass")
    return 0 if ok == len(hard) else 1


if __name__ == "__main__":
    sys.exit(main())
