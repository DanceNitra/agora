"""tat_monitor_runner.py — metrics harness for Marat's TAT-Monitor on realnoise_stress_v1 (2026-07-12).

Runs a detection module against agora_output/public_fixtures/realnoise_stress_v1.jsonl (100 rows: REAL
inspeximus-store noise + planted, labeled correction chains; shortcut-family audited — no trivial rule beats
the all-positive baseline). Reports overall accuracy/P/R/F1/AUROC + per-subset recall (revert_natural,
revert_anchored) and per-subset false-positive rates on the three distractor classes.

INTERFACE expected from the module (adapt the import when it arrives):
    predict(candidate: str, context: list[str]) -> float   # score, higher = reopens stale
or a class with .predict(...). Wire it in `load_predictor()` below.

RUN: python research/probes/tat_monitor_runner.py --module path/to/tat_monitor.py
"""
import json, os, sys, argparse, importlib.util, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
FIX = os.path.join(os.path.dirname(__file__), "..", "..", "agora_output", "public_fixtures",
                   "realnoise_stress_v1.jsonl")


def load_predictor(module_path):
    spec = importlib.util.spec_from_file_location("tat_monitor", module_path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    if hasattr(mod, "predict"):
        return mod.predict
    for name in ("TATMonitor", "Monitor", "Detector"):
        if hasattr(mod, name):
            inst = getattr(mod, name)()
            return inst.predict
    raise SystemExit("no predict() or known class found in module")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    a = ap.parse_args()
    predict = load_predictor(a.module)
    rows = [json.loads(l) for l in open(FIX, encoding="utf-8")]
    scores, errs = [], 0
    for r in rows:
        try:
            scores.append(float(predict(r["candidate"], r["context"])))
        except Exception as ex:
            print(f"  [row {r['id']} error: {str(ex)[:80]}]"); scores.append(None); errs += 1
    ok = [(s, r) for s, r in zip(scores, rows) if s is not None]
    ys = [r["reopens_stale"] for _, r in ok]
    ps = [1 if s > a.threshold else 0 for s, _ in ok]
    tp = sum(p and y for p, y in zip(ps, ys)); fp = sum(p and not y for p, y in zip(ps, ys))
    tn = sum((not p) and (not y) for p, y in zip(ps, ys)); fn = sum((not p) and y for p, y in zip(ps, ys))
    prec = tp / (tp + fp) if tp + fp else 0; rec = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    pairs = sorted(zip([s for s, _ in ok], ys)); pos = sum(ys); neg = len(ys) - pos
    rank = sum(i + 1 for i, (s, y) in enumerate(pairs) if y == 1)
    auroc = (rank - pos * (pos + 1) / 2) / (pos * neg) if pos and neg else 0
    print(f"n={len(ok)} errors={errs}")
    print(f"accuracy={ (tp+tn)/len(ok):.4f} precision={prec:.4f} recall={rec:.4f} F1={f1:.4f} AUROC={auroc:.4f}")
    print(f"confusion [tn={tn} fp={fp}; fn={fn} tp={tp}]")
    for sub in sorted(set(r["kind"] for _, r in ok)):
        sub_rows = [(p, r) for p, (_, r) in zip(ps, ok) if r["kind"] == sub]
        hit = sum(p for p, r in sub_rows)
        lab = sub_rows[0][1]["reopens_stale"]
        word = "recall" if lab == 1 else "false-positive rate"
        print(f"  {sub:22s} {word}: {hit if lab==1 else hit}/{len(sub_rows)}")


if __name__ == "__main__":
    main()
