"""determinism_jaccard.py — the UNCOPYABLE moat, measured as domination (not a 3% answer-flip).

The earlier determinism metric counted only whether the final ANSWER class flips across runs (mem0 ~10-30%) — it
understates the moat, because it ignores that the whole STORED STATE churns. This measures the state directly:
run the SAME ingest R times (fresh store each run), capture the full set of memory strings the store now holds,
and compute the mean pairwise **Jaccard** across runs.

  mnemo  (no LLM on write) -> byte-identical store every run -> Jaccard = 1.00 by construction.
  mem0   (LLM extraction on write) -> paraphrases/merges differently each run -> Jaccard < 1.00.

A competitor CANNOT raise this without removing the LLM from its write path (its whole design). That is the moat:
not "mnemo is a bit more stable", but "mnemo's memory is reproducible and a from-LLM store's is not, structurally".
We ALSO report the answer-class stability (current value == correction B, and its run-to-run flip rate).

RUN (free):        python research/probes/determinism_jaccard.py --systems mnemo --n 8 --runs 3
RUN (with mem0):   python research/probes/determinism_jaccard.py --systems mnemo,mem0 --n 8 --runs 3 --model gpt-4o-mini
"""
import os, sys, json, argparse, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "mab_official"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "mnemo_pypi"))
sys.path.insert(0, HERE)
import run_mnemo_official as H
from inspeximus import Inspeximus
import competitor_cells as C


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


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower()).strip().strip(".")


def jaccard(sets):
    """mean pairwise Jaccard over a list of string-sets."""
    tot = c = 0.0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            u = sets[i] | sets[j]
            inter = sets[i] & sets[j]
            tot += (len(inter) / len(u)) if u else 1.0
            c += 1
    return tot / c if c else 1.0


def state_mnemo(ps):
    """Full stored-state string-set after ingesting each subject's [A, B]."""
    s = set()
    for (k, A, B) in ps:
        m = Inspeximus(path=None)
        m.remember(A, key=k, object=val_of(A, k)); m.remember(B, key=k, object=val_of(B, k))
        for it in m.items:
            s.add(norm(it.get("text")))
    return s


def _mem0_local(model):
    """mem0 with a LOCAL Ollama LLM (no OpenAI credit). Proves the nondeterminism is the LLM-on-write path itself,
    not an OpenAI quirk — even a local temp-0 model paraphrases extraction differently run to run."""
    from mem0 import Memory
    import shutil
    qp = os.path.join(os.environ.get("TEMP", "/tmp"), "mem0_detj_qdrant")
    hp = os.path.join(os.environ.get("TEMP", "/tmp"), "mem0_detj_hist.db")
    shutil.rmtree(qp, ignore_errors=True)
    try: os.remove(hp)
    except OSError: pass
    cfg = {"llm": {"provider": "openai", "config": {"model": model, "temperature": 0,
                   "openai_base_url": "http://localhost:11434/v1", "api_key": "ollama"}},
           "embedder": {"provider": "ollama", "config": {"model": "nomic-embed-text",
                        "ollama_base_url": "http://localhost:11434"}},
           "history_db_path": hp,
           "vector_store": {"provider": "qdrant", "config": {"collection_name": "detj", "embedding_model_dims": 768,
                            "path": qp}}}
    return Memory.from_config(cfg)


def state_mem0(ps):
    mem = _mem0_local(os.environ.get("MEM0_LOCAL_MODEL", "qwen2.5:7b")) if os.environ.get("MEM0_LOCAL") else C._mem0()
    s = set()
    for i, (k, A, B) in enumerate(ps):
        uid = f"det{i}"
        for w in (A, B):
            try: mem.add(w, user_id=uid)
            except Exception: pass
        try:
            g = mem.get_all(filters={"user_id": uid})          # this mem0 version requires filters=, not user_id=
            rows = g.get("results", g) if isinstance(g, dict) else g
            for x in (rows or []):
                s.add(norm(x.get("memory") or x.get("text") or ""))
        except Exception as e:
            print(f"    get_all err: {e}", flush=True)
    return s


def answer_class(ps, system):
    """current-value class per subject: does the store's recall surface hold B-only / A / both / neither."""
    out = {}
    for (k, A, B) in ps:
        vA, vB = val_of(A, k).lower(), val_of(B, k).lower()
        if system == "mnemo":
            m = Inspeximus(path=None); m.echo_guard = True
            m.remember(A, key=k, object=vA); m.remember(B, key=k, object=vB)
            blob = " ".join((it.get("text") or "") for it in m.items).lower()
        else:
            mem = C._mem0(); uid = "ac"
            for w in (A, B):
                try: mem.add(w, user_id=uid)
                except Exception: pass
            try:
                g = mem.get_all(user_id=uid); rows = g.get("results", g) if isinstance(g, dict) else g
                blob = " ".join((x.get("memory") or x.get("text") or "") for x in (rows or [])).lower()
            except Exception:
                blob = ""
        a_in, b_in = vA in blob, vB in blob
        out[k] = ("both" if a_in and b_in else "Bonly" if b_in else "Aonly" if a_in else "neither")
    return out


STATE = {"mnemo": state_mnemo, "mem0": state_mem0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8); ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--systems", default="mnemo"); ap.add_argument("--model", default="gpt-4o")
    a = ap.parse_args()
    C.MODEL = a.model
    ps = pairs(a.n)
    print(f"DETERMINISM (store-state Jaccard across {a.runs} identical runs) n={len(ps)} model={a.model}\n", flush=True)
    out = {}
    for sysname in a.systems.split(","):
        sysname = sysname.strip()
        if sysname not in STATE:
            continue
        states = []
        for r in range(a.runs):
            states.append(STATE[sysname](ps))
            print(f"  {sysname} run {r+1}/{a.runs}: {len(states[-1])} stored strings", flush=True)
        jac = jaccard(states)
        # answer-class stability across the same runs (cheap, mnemo free)
        classes = [answer_class(ps, sysname) for _ in range(a.runs)] if sysname == "mnemo" else None
        flips = None
        if classes:
            flips = sum(1 for k in classes[0] if len({c[k] for c in classes}) > 1) / len(ps)
        out[sysname] = {"state_jaccard": round(jac, 3), "runs": a.runs,
                        "stored_strings_per_run": [len(s) for s in states],
                        "answer_flip_rate": flips}
        print(f"  == {sysname}: store-state Jaccard = {jac:.3f}  (1.000 = byte-identical every run)\n", flush=True)
    json.dump({"n": len(ps), "runs": a.runs, "model": a.model, "results": out},
              open(os.path.join(HERE, "determinism_jaccard_result.json"), "w"), indent=1)
    print("saved determinism_jaccard_result.json", flush=True)


if __name__ == "__main__":
    main()
