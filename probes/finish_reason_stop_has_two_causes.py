"""`finish_reason: stop` with no content is a BUDGET outcome as often as an INTENT one.

WHY THIS RUNS. On deepseek-ai/DeepSeek-V3#1466, @yun520-1 contributes a "premature-termination
signal" to the cross-framework matrix: `finish_reason=stop` without the promised `tool_call`, read
as a pre-output coherence failure the model committed. We have the same signature in our own logs
from an entirely different cause -- a thinking model given a tight `max_tokens` spends the budget on
reasoning and returns EMPTY content, and the API calls that `stop`, not `length`. A detector that
cannot separate the two attributes a configuration defect to the model.

That is written in our CLAUDE.md as a hard rule from 2026-08-08. A rule in a note is NOT verified
data, and eight days is long enough for a provider to change behaviour, so this re-measures it
against the live endpoint before any of it is said out loud.

WHAT WOULD REFUTE IT: empty completions carrying `finish_reason: length` (the honest code), or no
empties at any budget (the behaviour has changed, and the claim must not be repeated).

Parallel by default -- 24 logical CPUs here, and this is I/O bound. Progress every completion.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ENV = Path("C:/Users/Danculus/agora/server/.env")
cfg = {}
for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")

BASE = cfg.get("AGORA_REASONING_BASE_URL") or cfg.get("AGORA_API_BASE_URL")
MODEL = cfg.get("AGORA_REASONING_MODEL") or cfg.get("AGORA_LLM_MODEL")
KEY = cfg.get("AGORA_API_KEY", "")
BUDGETS = [40, 120, 400, 1200, 3000, 16000]
N = 10
WORKERS = 12

print(f"  endpoint : {BASE}")
print(f"  model    : {MODEL}")
print(f"  design   : {len(BUDGETS)} budgets x {N} samples = {len(BUDGETS) * N} calls, "
      f"{WORKERS} workers\n")


def one(budget: int, i: int) -> dict:
    """A UNIQUE prompt per call: a 0.0 s reply is a cache hit, not an answer."""
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Reply with only the digits."},
            {"role": "user", "content": f"What is {17 + i} + {6 + budget % 7}?"},
        ],
        "temperature": 0.0,
        "max_tokens": budget,
    }).encode()
    req = urllib.request.Request(f"{BASE.rstrip('/')}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {KEY}"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.load(r)
    except Exception as e:
        return {"budget": budget, "i": i, "error": f"{type(e).__name__}: {str(e)[:80]}",
                "secs": round(time.time() - t0, 2)}
    ch = (d.get("choices") or [{}])[0]
    content = ((ch.get("message") or {}).get("content") or "")
    return {"budget": budget, "i": i, "finish_reason": ch.get("finish_reason"),
            "empty": not content.strip(), "chars": len(content.strip()),
            "secs": round(time.time() - t0, 2),
            "usage": (d.get("usage") or {}).get("completion_tokens")}


rows, done = [], 0
t_start = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = [ex.submit(one, b, i) for b in BUDGETS for i in range(N)]
    for f in as_completed(futs):
        rows.append(f.result())
        done += 1
        if done % 10 == 0 or done == len(futs):
            print(f"    {done}/{len(futs)}  ({time.time() - t_start:.0f}s elapsed)", flush=True)

print(f"\n  {'budget':>7} {'empty':>7} {'finish_reason on the EMPTY ones':<38} {'median s':>9}")
print("  " + "-" * 66)
summary = []
for b in BUDGETS:
    got = [r for r in rows if r["budget"] == b and "error" not in r]
    if not got:
        print(f"  {b:>7}  all {N} calls errored: {rows[0].get('error')}")
        continue
    empties = [r for r in got if r["empty"]]
    fr = Counter(r["finish_reason"] for r in empties)
    secs = sorted(r["secs"] for r in got)
    med = secs[len(secs) // 2]
    print(f"  {b:>7} {len(empties):>3}/{len(got):<3} {str(dict(fr)) if fr else '(none empty)':<38} {med:>9.2f}")
    summary.append({"budget": b, "n": len(got), "empty": len(empties),
                    "finish_reason_on_empty": dict(fr), "median_secs": med})

stop_empties = sum(s["finish_reason_on_empty"].get("stop", 0) for s in summary)
len_empties = sum(s["finish_reason_on_empty"].get("length", 0) for s in summary)
print(f"\n  empty completions labelled `stop`   : {stop_empties}")
print(f"  empty completions labelled `length` : {len_empties}   <- the honest code")

verdict = ("REPRODUCED" if stop_empties else
           "NOT REPRODUCED -- do not repeat the claim" if not any(s["empty"] for s in summary)
           else "CHANGED: empties are labelled `length` now, which is the honest code")
print(f"\n  VERDICT: {verdict}")

out = Path(__file__).with_suffix(".result.json")
out.write_text(json.dumps({
    "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "endpoint": BASE, "model": MODEL, "n_per_budget": N,
    "summary": summary, "stop_empties": stop_empties, "length_empties": len_empties,
    "verdict": verdict, "rows": rows}, indent=2), encoding="utf-8")
print(f"  receipt: {out.name}")
