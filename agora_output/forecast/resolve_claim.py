"""Crucible Live — resolve a forecast after the replication verdict (protocol step 5).

Usage: python resolve_claim.py <claim_id> <REPRODUCED|FAILED|NOT_COMPUTABLE>
Appends {verdict, resolved_utc, brier_*} to forecasts/<id>.json (in a NEW commit, per protocol).
Brier is computed on P(REPRODUCED) vs the binary outcome, only for computable verdicts;
the frozen trailing base rate stored at forecast time is scored the same way for comparison.
Refuses to resolve twice (append-only).
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    cid, verdict = sys.argv[1], sys.argv[2].upper()
    assert verdict in ("REPRODUCED", "FAILED", "NOT_COMPUTABLE"), verdict
    p = os.path.join(HERE, "forecasts", f"{cid}.json")
    d = json.load(open(p, encoding="utf-8"))
    if "verdict" in d:
        sys.exit(f"REFUSED: {cid} already resolved to {d['verdict']} (append-only)")
    d["verdict"] = verdict
    d["resolved_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if verdict in ("REPRODUCED", "FAILED"):
        y = 1.0 if verdict == "REPRODUCED" else 0.0
        for m, v in d["models"].items():
            if v.get("p_reproduced") is not None:
                v["brier"] = round((v["p_reproduced"] - y) ** 2, 4)
        if d.get("ensemble_p_reproduced") is not None:
            d["brier_ensemble"] = round((d["ensemble_p_reproduced"] - y) ** 2, 4)
        br = d.get("base_rate_comparator_trailing20")
        if br is not None:
            d["brier_base_rate_comparator"] = round((br - y) ** 2, 4)
    else:
        d["note"] = "NOT_COMPUTABLE: excluded from the primary Brier metric (pre-registered)"
    json.dump(d, open(p, "w", encoding="utf-8"), indent=2)
    print(json.dumps(d, indent=2))
    print(f"\nNow commit+push forecasts/{cid}.json (a NEW commit) and update public/forecast.html tally.")

if __name__ == "__main__":
    main()
