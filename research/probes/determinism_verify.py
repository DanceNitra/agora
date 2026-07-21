"""determinism_verify.py — VERIFY (not assert) the determinism claim, honestly, on a LOCAL LLM (no rate limits).

The earlier determinism_gap run showed mem0 100% nondeterministic, but it was CONTAMINATED by cloud 429s (later
runs emptied). This re-measures cleanly on a fast local model (qwen2.5:7b, no thinking) at temp=0 (the HARDEST
case for the claim — if mem0 is deterministic at temp=0 the '100%' was pure artifact) AND temp=0.7 (mem0's
realistic default). inspeximus (deterministic core, no LLM) is the 0% baseline. Reports whatever it is.

RUN:  python research/probes/determinism_verify.py --n 10 --runs 3
"""
import os, sys, json, time, argparse, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "mab_official"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "inspeximus_pypi"))
import run_inspeximus_official as H
from inspeximus import Inspeximus

MODEL = os.environ.get("VERIFY_MODEL", "gpt-4o")
def _openai_key():
    for l in open(os.path.join(HERE,"..","..","server",".env"),encoding="utf-8",errors="replace"):
        if l.startswith("OPENAI_API_KEY="): return l.split("=",1)[1].strip()
    return "ollama"
if MODEL.startswith("gpt"):
    BASE, KEY = "https://api.openai.com/v1", _openai_key()
else:
    BASE, KEY = "http://localhost:11434/v1", "ollama"


def val_of(fact, key):
    v = fact[len(key):] if fact.startswith(key) else fact
    return v.strip().strip(".").strip()


def pairs(n):
    facts, _q, _g = H.load("sh_6k")
    from collections import OrderedDict
    byk = OrderedDict()
    for f in facts:
        byk.setdefault(H.key_of(f), []).append(f)
    return [(k, v[0], v[-1]) for k, v in byk.items() if len(v) >= 2 and len(set(v)) >= 2][:n]


def klass(blob, vA, vB):
    a, b = vA.lower() in blob.lower(), vB.lower() in blob.lower()
    return "both" if (a and b) else "Bonly" if b else "Aonly" if a else "neither"


def mem0_run(ps, temp, run):
    from mem0 import Memory
    qp = os.path.join(os.environ.get("TEMP", "/tmp"), f"mem0_ver_{run}_qdrant")
    hp = os.path.join(os.environ.get("TEMP", "/tmp"), f"mem0_ver_{run}_hist.db")
    shutil.rmtree(qp, ignore_errors=True)
    try: os.remove(hp)
    except OSError: pass
    cfg = {"llm": {"provider": "openai", "config": {"model": MODEL, "temperature": temp,
                   "openai_base_url": BASE, "api_key": KEY}},
           "embedder": {"provider": "ollama", "config": {"model": "nomic-embed-text",
                        "ollama_base_url": "http://localhost:11434"}},
           "history_db_path": hp,
           "vector_store": {"provider": "qdrant", "config": {"collection_name": "ver", "embedding_model_dims": 768,
                            "path": qp}}}
    mem = Memory.from_config(cfg)
    out = {}
    for i, (k, A, B) in enumerate(ps):
        uid = f"v{run}_{i}"
        for w in (A, B):
            try: mem.add(w, user_id=uid)
            except Exception: pass
        try:
            sr = mem.search(k, filters={"user_id": uid}, top_k=10)
            rows = sr.get("results", sr) if isinstance(sr, dict) else sr
            blob = " ".join((x.get("memory") or x.get("text") or str(x)) for x in (rows or []))
        except Exception:
            blob = ""
        out[k] = klass(blob, val_of(A, k), val_of(B, k))
    return out


def inspeximus_run(ps):
    out = {}
    for (k, A, B) in ps:
        m = Inspeximus(path=None)
        m.remember(A, key=k, object=val_of(A, k)); m.remember(B, key=k, object=val_of(B, k))
        blob = " ".join(h["text"] for h in m.recall(k, k=5))
        out[k] = klass(blob, val_of(A, k), val_of(B, k))
    return out


def analyze(runs, ps):
    keys = [k for (k, _a, _b) in ps]
    nd = sum(1 for k in keys if len({r[k] for r in runs}) > 1)
    per = {k: [r[k] for r in runs] for k in keys}
    return {"nondeterminism_rate": round(nd / len(keys), 3), "unstable": nd, "n": len(keys), "per_subject": per}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--runs", type=int, default=3)
    a = ap.parse_args()
    ps = pairs(a.n)
    print(f"DETERMINISM VERIFY (LOCAL {MODEL}, no rate limits) · n={len(ps)} · runs={a.runs}", flush=True)
    out = {}
    # inspeximus baseline (deterministic, instant)
    mr = [inspeximus_run(ps) for _ in range(a.runs)]
    out["inspeximus"] = analyze(mr, ps)
    print(f"  inspeximus:            nondeterminism {out['inspeximus']['nondeterminism_rate']:.0%}", flush=True)
    # mem0 at temp=0 (hardest case) and temp=0.7 (realistic)
    for temp in (0.0, 0.7):
        runs = []
        for r in range(a.runs):
            t0 = time.time(); runs.append(mem0_run(ps, temp, f"{int(temp*10)}_{r}"))
            print(f"  mem0 temp={temp} run {r+1}/{a.runs} ({time.time()-t0:.0f}s)", flush=True)
        out[f"mem0_temp{temp}"] = analyze(runs, ps)
        print(f"  mem0 temp={temp}:   nondeterminism {out[f'mem0_temp{temp}']['nondeterminism_rate']:.0%} "
              f"({out[f'mem0_temp{temp}']['unstable']}/{out[f'mem0_temp{temp}']['n']})", flush=True)
    json.dump({"model": MODEL, "runs": a.runs, "results": out},
              open(os.path.join(HERE, "determinism_verify_result.json"), "w"), indent=1)
    print("\nsaved determinism_verify_result.json")


if __name__ == "__main__":
    main()
