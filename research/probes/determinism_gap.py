"""determinism_gap.py — the FAIR, architecture-intrinsic mnemo win the whole 2026-07-17/18 session converged on.

Every competitor puts an LLM on the WRITE path (mem0 extraction, Graphiti/Cognee cognify, Letta self-edit),
which makes the stored state NON-DETERMINISTIC: the same input, ingested twice, can yield a different memory.
mnemo's core write path has NO LLM -> identical input always yields the identical store.

We MEASURE it (discipline: don't assert). R independent runs, the SAME conflict facts (raw text, A then
corrected to B), fresh store each run. For each subject we read back what value the store now holds for it
(substring of A=stale vs B=correction in its retrieved memories -> class in {B-only, A-only, both, neither}).

  NONDETERMINISM RATE = fraction of subjects whose read-back CLASS is not identical across all R runs.
  ACCURACY (current==B) per run + its spread across runs.

mnemo (deterministic core, plain keyed remember) is expected 0.0 nondeterminism by architecture; the NUMBER we
care about is mem0's. Fair: identical raw input, identical read instrument, run-to-run stability is exactly the
property claimed. mem0 CANNOT be deterministic without removing its extraction (its whole design).

RUN (free, mnemo):    python research/probes/determinism_gap.py --systems mnemo --n 30 --runs 5
RUN (with mem0):      python research/probes/determinism_gap.py --systems mnemo,mem0 --n 25 --runs 5
"""
import os, sys, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "mab_official"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "mnemo_pypi"))
import run_mnemo_official as H
from inspeximus import Inspeximus
import adversarial_conflict as ADV


def val_of(fact, key):
    v = fact[len(key):] if fact.startswith(key) else fact
    return v.strip().strip(".").strip()


def pairs(sample, n):
    facts, _q, _g = H.load(sample)
    from collections import OrderedDict
    byk = OrderedDict()
    for f in facts:
        byk.setdefault(H.key_of(f), []).append(f)
    conf = [(k, v[0], v[-1]) for k, v in byk.items() if len(v) >= 2 and len(set(v)) >= 2]
    return conf[:n]


def klass(blob, vA, vB):
    a, b = vA.lower() in blob.lower(), vB.lower() in blob.lower()
    return "both" if (a and b) else "Bonly" if b else "Aonly" if a else "neither"


def read_mnemo(ps):
    out = {}
    for (k, A, B) in ps:
        m = Inspeximus(path=None)                                  # deterministic core, keyed supersession, NO LLM
        m.remember(A, key=k, object=val_of(A, k))
        m.remember(B, key=k, object=val_of(B, k))
        blob = " ".join(h["text"] for h in m.recall(k, k=5))
        out[k] = klass(blob, val_of(A, k), val_of(B, k))
    return out


def read_mem0(ps, run):
    mem = ADV._mem0_own()                                     # fresh qdrant each run
    out = {}
    for i, (k, A, B) in enumerate(ps):
        uid = f"det{run}_{i}"
        ADV.H._mem0_add(mem, A, uid)
        ADV.H._mem0_add(mem, B, uid)
        sr = mem.search(k, filters={"user_id": uid}, top_k=10)
        rows = sr.get("results", sr) if isinstance(sr, dict) else sr
        blob = " ".join((x.get("memory") or x.get("text") or str(x)) for x in (rows or []))
        out[k] = klass(blob, val_of(A, k), val_of(B, k))
    return out


def analyze(runs, ps):
    keys = [k for (k, _a, _b) in ps]
    nondet = sum(1 for k in keys if len({r[k] for r in runs}) > 1)
    accs = [sum(1 for k in keys if r[k] == "Bonly") / len(keys) for r in runs]
    return {"nondeterminism_rate": nondet / len(keys), "unstable_subjects": nondet, "n": len(keys),
            "accuracy_per_run": [round(a, 3) for a in accs],
            "accuracy_spread": round(max(accs) - min(accs), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="mnemo")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--sample", default="sh_6k")
    a = ap.parse_args()
    ps = pairs(a.sample, a.n)
    print(f"DETERMINISM GAP · same input x{a.runs} runs · n={len(ps)} subjects · systems={a.systems}", flush=True)
    out = {}
    for s in a.systems.split(","):
        runs = []
        for r in range(a.runs):
            t0 = time.time()
            runs.append(read_mnemo(ps) if s == "mnemo" else read_mem0(ps, r))
            print(f"  {s} run {r+1}/{a.runs} done ({time.time()-t0:.0f}s)", flush=True)
        out[s] = analyze(runs, ps)
        print(f"  == {s}: nondeterminism {out[s]['nondeterminism_rate']:.0%} "
              f"({out[s]['unstable_subjects']}/{out[s]['n']}) · acc/run {out[s]['accuracy_per_run']} "
              f"· spread {out[s]['accuracy_spread']:.0%}", flush=True)
    json.dump({"runs": a.runs, "results": out}, open(os.path.join(HERE, "determinism_gap_result.json"), "w"), indent=1)
    print("\nsaved determinism_gap_result.json")


if __name__ == "__main__":
    main()
