"""Is the token step at the cap the WARNING, or just a fixed toll?

Crossing the auto-memory read limit costs a few tokens more than sitting exactly at it.
I attributed that step to the truncation warning. A method audit pushed back correctly:
the two arms I used trip DIFFERENT branches of the warning, and two different strings
cannot both cost the same, so the attribution was inferred rather than identified.

This identifies it. Every arm loads exactly the same content as its own baseline -- the
first 200 lines, or the first 25,000 units -- so the ONLY difference between an arm and
its baseline is that a warning was appended, and the only difference between arms is how
that warning is worded:

  201 x 60    "is 201 lines (limit: 200)"        line-cap branch, 3-digit count
  1005 x 60   "is 1005 lines and 58.9KB"         both-caps branch, 4-digit count
  202 x 125   "is 202 lines and 24.7KB"          both-caps branch, 3-digit count

If the step tracks the wording, the longer message costs more. If every arm pays the same
regardless of what the message says, the step is not the message and the attribution is
wrong.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from the_cost_curve_across_the_truncation_boundary import build_index, claude_bin  # noqa: E402

ASK = ("Respond with only: WARNING=<verbatim any line saying your index was truncated or "
       "partly loaded; else NO-INDICATOR>")
ARMS = {"base_200x60": (200, 60), "cut_201x60": (201, 60), "cut_1005x60": (1005, 60),
        "base_200x125": (200, 125), "cut_202x125": (202, 125)}
PAIRS = (("base_200x60", "cut_201x60"), ("base_200x60", "cut_1005x60"),
         ("base_200x125", "cut_202x125"))
CLAUDE = None
_t0 = time.time()


def run(cwd: str, prompt: str):
    out = subprocess.run([CLAUDE, "-p", "--output-format", "stream-json", "--verbose"],
                         cwd=cwd, input=prompt, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=900).stdout or ""
    store = ans = None
    tot = None
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            store = (d.get("memory_paths") or {}).get("auto")
        elif d.get("type") == "result":
            u = d.get("usage") or {}
            tot = ((u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
                   + (u.get("cache_read_input_tokens") or 0))
            ans = str(d.get("result") or "")
    return store, tot, ans


def main() -> int:
    global CLAUDE
    CLAUDE = claude_bin()
    root = tempfile.mkdtemp(prefix="warntext_")
    res = {}
    for label, (n, w) in ARMS.items():
        cwd = os.path.join(root, label)
        os.makedirs(cwd, exist_ok=True)
        store, base, _ = run(cwd, "Reply with only: INIT")
        text, _ = build_index(n, w)
        os.makedirs(store, exist_ok=True)
        with open(os.path.join(store, "MEMORY.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        _, tot, ans = run(cwd, ASK)
        mm = re.search(r"WARNING=\s*(.*)", ans or "", re.S)
        wt = (mm.group(1).strip() if mm else "")
        # an EMPTY answer is not a warning: without this, a blank reply reads as "warned"
        warned = bool(wt.strip()) and "NO-INDICATOR" not in wt.upper()
        res[label] = {"lines": n, "width": w, "baseline_total": base, "index_total": tot,
                      "delta": (tot - base) if (tot and base) else None,
                      "warned": warned, "warning": wt[:220],
                      "warning_chars": len(wt) if warned else 0}
        print(f"[{time.time() - _t0:6.1f}s] {label:14s} delta={res[label]['delta']:+6d} "
              f"warn_chars={res[label]['warning_chars']:4d} | {wt[:90]!r}", flush=True)

    steps = {}
    print()
    for b, c in PAIRS:
        steps[c] = res[c]["delta"] - res[b]["delta"]
        print(f"{c:14s} vs {b:14s}: step = {steps[c]:+d} tokens   "
              f"({res[c]['warning_chars']} chars: {res[c]['warning'][:60]!r})")
    v = {
        "every_cut_arm_quoted_its_warning": all(res[c]["warning_chars"] > 40 for _, c in PAIRS),
        "baselines_carry_no_warning": all(not res[b]["warned"] for b, _ in PAIRS),
        "every_cut_arm_warns": all(res[c]["warned"] for _, c in PAIRS),
        "step_is_small_and_positive": all(0 < s < 200 for s in steps.values()),
        "step_tracks_the_wording": len(set(steps.values())) > 1,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "does_the_step_track_the_warning_text.result.json")
    json.dump({"probe": "does_the_step_track_the_warning_text",
               "claude_version": subprocess.run([CLAUDE, "--version"], capture_output=True,
                                                text=True).stdout.strip(),
               "verdicts": v, "steps": steps, "arms": res},
              open(out, "w", encoding="utf-8"), indent=2)
    print("\n=== VERDICTS ===")
    for k, val in v.items():
        print(f"  {'YES' if val else 'no '}  {k}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
