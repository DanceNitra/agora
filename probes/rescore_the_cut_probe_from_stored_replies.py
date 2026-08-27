"""Re-score the cut probe's STORED replies. No sessions, no network, and no new claims.

WHY THIS EXISTS. The 2026-08-25 run of `the_cut_measured_by_what_the_index_DOES_not_what_it_says.py`
wrote its artifact while the entry-id regex contained a literal BACKSPACE (0x08) where `\b` was
meant. The pattern compiled, matched nothing, and every trial scored as a miss, so the committed
`.result.json` says `named_ever` all false, `last_kept_lower_bound: null`, `admissible_trials: []`.

I then fixed the regex, re-scored in a shell, reported 168, and wrote a commit message saying "Both
runs land on 168" -- over an artifact on disk that says the opposite. A receipt that contradicts its
own commit message is worse than no receipt, because the commit message is what gets quoted.

This regenerates the artifact from the replies the run actually recorded, so the file on disk says
what the evidence says. It is a RE-SCORE, not a re-measurement, and it is labelled as one in the
output. It cannot invent a trial and it cannot change what a model said.

WHAT THE RE-SCORE DOES NOT RESCUE, stated here because the numbers below are otherwise easy to
over-read:
  * The needle WORD never appears in any stored reply of either run. Run 2's every hit, including
    its positive control at line 3, comes from the entry-id channel alone -- so admissibility and
    finding are not independent, and the control cannot vouch for the channel it rides on.
  * Lines 166 and 167 are never named individually. They are interpolated inside `E0165-E0168`, a
    span the model wrote. The per-line detail is not evidence; only 165 and 168 are.
  * Run 1 stored 400 characters per reply, so its own 168 cannot be re-derived from its artifact.
  * "169 was dropped" does not follow. Absence is not evidence in this instrument, which is the
    probe's own stated rule. The honest result is a LOWER BOUND: last-kept >= 168.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_src = io.open(os.path.join(HERE, "the_cut_measured_by_what_the_index_DOES_not_what_it_says.py"),
               encoding="utf-8").read()
_ns: dict = {"__file__": os.path.join(HERE, "x.py")}
exec(_src.split("def build()")[0].replace(
    "import is_the_cap_counted_in_bytes_or_utf16_units as U", "U = None"), _ns)
seen_at, NEEDLES = _ns["seen_at"], _ns["NEEDLES"]


def rescore(path: str) -> dict:
    d = json.load(io.open(path, encoding="utf-8"))
    trials = d["trials_detail"]
    hits = [{n: seen_at(r["reply"], n) for n in NEEDLES} for r in trials]
    body = [n for n in NEEDLES if n not in (3, 180)]
    ever = {n: any(h[n] for h in hits) for n in NEEDLES}
    adm = [i for i, h in enumerate(hits, 1) if h[3]]
    kept = [n for n in body if ever[n]]
    words_present = sorted(w for w in NEEDLES.values()
                           if any(w.lower() in r["reply"].lower() for r in trials))
    d["rescored_offline"] = {
        "note": "verdicts below recomputed from the stored replies after the 0x08 regex fix; "
                "no session was run",
        "named_ever": {str(k): v for k, v in ever.items()},
        "admissible_trials": adm,
        "last_kept_lower_bound": max(kept) if kept else None,
        "needle_WORDS_present_in_stored_replies": words_present,
        # INDIVIDUALLY named, which is not the same as "scored a hit". A hit may come from inside a
        # range the model wrote (`E0165-E0168`), and interpolating across that range is the probe
        # asserting per-line detail the model never gave. This is the distinction the first version
        # of THIS FILE also blurred, one function after being written to stop blurring it.
        "entry_ids_named_individually": sorted(
            {int(x) for r in trials for x in re.findall(r"\bE0*(\d{1,4})\b", r["reply"])}),
        "entry_id_ranges_the_model_wrote": sorted(
            {(int(a), int(b)) for r in trials for a, b in re.findall(
                r"E0*(\d{1,4})\s*[-–—to]+\s*E0*(\d{1,4})", r["reply"])}),
        "replies_truncated_at_400_chars": all(len(r["reply"]) <= 400 for r in trials),
    }
    json.dump(d, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return d["rescored_offline"]


def main() -> int:
    for name in ("the_cut_measured_by_what_the_index_DOES_not_what_it_says.result.json",
                 "the_cut_measured_by_what_the_index_DOES_not_what_it_says.run1.result.json"):
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            print(f"REFUSED: {p} is absent")
            return 1
        r = rescore(p)
        print(f"\n{name}")
        for k, v in r.items():
            if k != "note":
                print(f"  {k}: {v}")
    print("\nRE-SCORE ONLY. The lower bound is 168 and there is no upper bound from this probe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
