"""Run Guanghao's V10 adapter (_guanghao_repo/traceai_adapter.py, unmodified) on our three sets.

Each conversation is written as an OTLP JSON trace and scored by his CLI; the per-turn CSV is
read back. Writes v10_results.json. No model calls.
"""
import csv
import json
import os
import subprocess
import sys

import benchmark_20 as B20
import benchmark_r2 as R2
import benchmark_v2 as V2

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "_guanghao_repo")
WORK = os.path.join(HERE, "_v10_work")
os.makedirs(WORK, exist_ok=True)


def otlp(spans):
    def val(v):
        if isinstance(v, int):
            return {"intValue": str(v)}
        return {"stringValue": v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}
    out = [{**s, "attributes": [{"key": k, "value": val(v)} for k, v in s["attributes"].items()]} for s in spans]
    return {"resourceSpans": [{"scopeSpans": [{"spans": out}]}]}


def score(name, spans):
    tp, cp = os.path.join(WORK, name + ".json"), os.path.join(WORK, name + ".csv")
    json.dump(otlp(spans), open(tp, "w", encoding="utf-8"), ensure_ascii=False)
    p = subprocess.run([sys.executable, "-I", os.path.join(REPO, "traceai_adapter.py"), tp, "--out", cp],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=WORK)
    if p.returncode != 0 or not os.path.exists(cp):
        return {"error": (p.stderr or p.stdout)[-400:]}
    rows = list(csv.DictReader(open(cp, encoding="utf-8-sig")))
    return {"turns": [{k: rows[i].get(k) for k in ("turn_id", "U", "D", "A", "H")} for i in range(len(rows))],
            "columns": list(rows[0].keys()) if rows else []}


res = {}
for c in V2.all_variants():
    res["v2|" + c["id"]] = score("v2_" + c["id"], V2.spans(c))
for c in R2.all_variants():
    res["r2|" + c["id"]] = score("r2_" + c["id"], R2.spans(c))
for c in B20.CASES:
    res["b20|%d" % c["id"]] = score("b20_%d" % c["id"], B20.spans(c))
json.dump(res, open(os.path.join(HERE, "v10_results.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
err = [k for k, v in res.items() if "error" in v]
print("scored", len(res) - len(err), "of", len(res), "errors", err[:3])
if err:
    print(res[err[0]]["error"])
print("columns", next(v["columns"] for v in res.values() if "columns" in v))
