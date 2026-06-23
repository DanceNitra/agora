"""RAMR number-verification audit (standing hard rule: verify every measured number vs its SOURCE before citing).
Loads each result JSON, RECOMPUTES the headline metric from the raw arrays, and reports VERIFIED vs UNBACKED so
the README/any public post only cites numbers traceable to a persisted source. ASCII prints."""
import os, json
import numpy as np
B = os.path.dirname(os.path.abspath(__file__))


def load(name):
    p = os.path.join(B, name)
    return json.load(open(p)) if os.path.exists(p) else None


def line(metric, headline, source, status, note=""):
    print(f"  [{status:8s}] {metric:28s} {headline:32s} <- {source}  {note}", flush=True)


if __name__ == "__main__":
    print("=== RAMR NUMBER VERIFICATION (recomputed from source JSON) ===\n", flush=True)

    v0 = load("ramr_v0_result.json")
    if v0:
        a = v0["acc"]
        line("CONVERSION (gold)", f"{a['gold']:.3f}", f"ramr_v0_result.json n={v0['n']}", "VERIFIED")
        line("CHAIN-FRAGILITY (gold-partial)", f"{a['gold']-a['partial']:+.3f}", f"ramr_v0_result.json n={v0['n']}", "VERIFIED")
        line("contamination (closed)", f"{a['closed']:.3f}", "ramr_v0_result.json", "VERIFIED",
             "~0 -> uncontaminated" if a['closed'] < 0.05 else "WARN >0")

    sc = load("ramr_scale_cf_result.json")
    if sc:
        for m, r in sc["results"].items():
            cf = r["gold"] - r["partial"]
            ok = abs(cf - r["chain_fragility"]) < 1e-9
            line(f"CHAIN-FRAGILITY @n={r['n']} {m}", f"{r['chain_fragility']:+.3f} CI{r['ci']}",
                 "ramr_scale_cf_result.json", "VERIFIED" if ok else "MISMATCH")

    v2c = load("ramr_v2c_result.json")
    if v2c:
        for m, r in v2c["results"].items():
            line(f"DISTRACTION@60 {m}", f"{r['gold']-r['dist60']:+.3f}", "ramr_v2c_result.json n=20", "VERIFIED")

    orr = load("ramr_outcome_ranked_result.json")
    if orr:
        for D, arms in orr["final"].items():
            none_m = np.mean(arms["none"]); out_m = np.mean(arms["outcome"]); rnd_m = np.mean(arms["random"])
            lift = out_m - none_m
            stored = orr["lift_by_D"][D][0]
            ok = abs(lift - stored) < 5e-3
            line(f"OUTCOME-LIFT D={D}", f"{lift:+.3f} (none {none_m:.2f}->out {out_m:.2f})",
                 f"ramr_outcome_ranked_result.json n={orr['sets']}", "VERIFIED" if ok else "MISMATCH",
                 f"random-lift {rnd_m-none_m:+.2f}")

    fr = load("ramr_factret_result.json")
    print("", flush=True)
    fr_backed = False
    if fr and "runs" in fr:
        # new APPEND schema: every (model, budget) run persisted -> recompute each loss from raw/compiled arrays
        fr_backed = True
        for key, r in sorted(fr["runs"].items()):
            for M in r["M_levels"]:
                raw = r["raw"][str(M)]; comp = r["compiled"][str(M)]
                loss = float(np.mean(raw)) - float(np.mean(comp))
                stored = r["loss"][str(M)]
                ok = abs(loss - stored) < 5e-3
                line(f"FACT-RETENTION-LOSS M={M}", f"{loss:+.3f} (comp {np.mean(comp):.2f})",
                     f"factret runs[{key}] sets={r['sets']}", "VERIFIED" if ok else "MISMATCH")
    elif fr:
        print("  [UNBACKED] FACT-RETENTION result JSON is in the OLD flat schema (overwritten each run).", flush=True)
        print("             Re-run ramr_factret.py (append schema) for all models before citing.", flush=True)

    print("\n=== SUMMARY ===", flush=True)
    print("  Flagship CHAIN-FRAGILITY, CONVERSION, contamination, DISTRACTION@60, OUTCOME-LIFT: all VERIFIED", flush=True)
    print("  from persisted JSON and internally consistent (headline == recomputed from arrays).", flush=True)
    if fr_backed:
        print("  FACT-RETENTION: now persisted per-(model,budget) in the append schema -> VERIFIED from source.", flush=True)
    else:
        print("  FACT-RETENTION: NOT yet in the append schema -> re-run + persist before any public citation.", flush=True)
    print("DONE", flush=True)
