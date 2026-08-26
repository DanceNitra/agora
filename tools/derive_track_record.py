"""Derive the forecasting numbers the public page publishes, into a committed artifact.

WHY THIS EXISTS. The Crucible numbers on our pages are checkable in CI because the ledger they come
from -- public/crucible/crucible.json -- is committed. The FORECAST numbers are not: the prediction
ledger lives at server/.predictions.json, which .gitignore excludes as runtime state. So the one page
whose whole proposition is "we publish our own record" had its central number unverifiable by
anything, and it drifted.

MEASURED 2026-08-18: the live page said "20 forecasts on record" and "no Brier score to report yet",
dated 2026-07-12. The ledger at that moment held 249 forecasts, 241 resolved, 46 correct -- a hit
rate of 19.1% with a Brier of 0.304. The markdown beside the HTML had been updated on 2026-08-10 and
said so; the HTML, which is what the site serves, had not. Five weeks, and the number our credibility
rests on was understated by an order of magnitude in our own favour.

This writes public/track-record.json from the live ledger so the page has a derived, committed source
that check_public_counts.py can hold it to. Run it whenever the page is republished.

    python tools/derive_track_record.py            # write the artifact
    python tools/derive_track_record.py --print    # show the numbers, write nothing

The baselines are included deliberately. A Brier of 0.304 next to nothing invites "that sounds close
to 0.25, so roughly a coin flip". It is not: on the same resolved set, always answering UP scores
39.4%, and agreement expected by chance under our OWN marginal distribution is 34.7% against an
observed 19.1%. Publishing the score without the baseline would be the flattering half.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "server" / ".predictions.json"
OUT = ROOT / "public" / "track-record.json"


def load_resolved():
    if not LEDGER.exists():
        raise SystemExit(
            "no prediction ledger at %s -- this tool must run where the brain's state lives, "
            "not in CI. CI verifies the PAGE against the artifact this writes." % LEDGER)
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    recs = data if isinstance(data, list) else (data.get("predictions") or data.get("records") or [])
    resolved = [r for r in recs if r.get("actual") not in (None, "", "pending")]
    return recs, resolved


def derive() -> dict:
    recs, res = load_resolved()
    n = len(res)
    if n == 0:
        raise SystemExit("ledger holds no resolved forecasts -- nothing to publish")

    correct = sum(1 for r in res if r.get("direction") == r.get("actual"))
    briers = [r.get("brier") for r in res if isinstance(r.get("brier"), (int, float))]
    brier = round(sum(briers) / len(briers), 3) if briers else None

    called: dict = {}
    actual: dict = {}
    for r in res:
        called[r.get("direction")] = called.get(r.get("direction"), 0) + 1
        actual[r.get("actual")] = actual.get(r.get("actual"), 0) + 1

    # always-X baselines on the SAME resolved set
    baselines = {d: round(actual[d] / n, 4) for d in sorted(actual)}
    best_label = max(baselines, key=lambda d: baselines[d])

    # agreement expected by chance, using our own marginals
    labels = set(called) | set(actual)
    exp = sum((called.get(d, 0) / n) * (actual.get(d, 0) / n) for d in labels) * n
    var = sum((called.get(d, 0) / n) * (actual.get(d, 0) / n)
              * (1 - (called.get(d, 0) / n) * (actual.get(d, 0) / n)) for d in labels) * n
    z = (correct - exp) / math.sqrt(var) if var > 0 else 0.0

    return {
        "generated_by": "tools/derive_track_record.py",
        "total": len(recs),
        "resolved": n,
        "correct": correct,
        "hit_rate": round(correct / n, 4),
        "brier": brier,
        "called": {k: v for k, v in sorted(called.items())},
        "actual": {k: v for k, v in sorted(actual.items())},
        "always_baselines": baselines,
        "best_always_baseline": {"label": best_label, "rate": baselines[best_label]},
        "chance_agreement": round(exp / n, 4),
        "z_vs_chance": round(z, 2),
        "note": ("hit_rate is measured against the same resolved set as the baselines. A Brier near "
                 "0.25 is not 'about a coin flip' here: chance agreement under our own marginals is "
                 "%s and the best always-one-answer baseline is %s, both far above the observed "
                 "%s." % (round(exp / n, 4), baselines[best_label], round(correct / n, 4))),
    }


def main(argv) -> int:
    d = derive()
    if "--print" in argv:
        print(json.dumps(d, indent=1, ensure_ascii=False))
        return 0
    OUT.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote %s" % OUT)
    print("  resolved=%(resolved)d correct=%(correct)d hit_rate=%(hit_rate).4f brier=%(brier)s" % d)
    print("  best always-baseline=%s (%.4f)  chance=%.4f  z=%.2f"
          % (d["best_always_baseline"]["label"], d["best_always_baseline"]["rate"],
             d["chance_agreement"], d["z_vs_chance"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
