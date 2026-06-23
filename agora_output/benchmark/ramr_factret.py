"""RAMR FACT-RETENTION task family. Memory systems increasingly store a COMPILED/summarized 'knowledge object'
instead of (or alongside) raw chunks (RAGFlow's compiled layer, Mastra working-memory summaries, mem0 fact
extraction). The untested claim our RAGFlow exchange landed on: 'the compiled object should AUGMENT, not REPLACE,
raw data' -- because compilation DROPS facts. This makes that a measured benchmark metric.

Setup: M independent atomic facts ('The <attr> of the <entity> is <value>.', distinct entity+attr, distinct
values -> uncontaminated, unambiguous). Two contexts, same probe questions (one per fact, asking the value):
  RAW      : all M raw fact sentences (perfect store) -> accuracy ceiling (~1.0)
  COMPILED : the M facts compressed by the model into <= S sentences (a realistic compiled knowledge object)
FACT-RETENTION = compiled accuracy; RETENTION-LOSS = raw - compiled. Sweep M (compression pressure rises with
M/S). FALSIFIER (pre-registered): if compiled accuracy ~= raw at every M (loss < 0.10 even at the highest M),
compilation is lossless and the 'augment-not-replace' claim is FALSE for this model. Cloud-free default (local
qwen); a cloud cross-check can be added via RAMR_MODEL. ASCII prints."""
import os, sys, json, time, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramr_v0_conversion as v0
from concurrent.futures import ThreadPoolExecutor

MODEL = os.getenv("RAMR_MODEL", "qwen3-coder:30b")
M_LEVELS = [int(x) for x in os.getenv("RAMR_M", "12,24,48").split(",")]
S_SENT = int(os.getenv("RAMR_SENT", "6"))     # compiled-summary sentence budget (fixed -> compression rises with M)
N_SETS = int(os.getenv("RAMR_SETS", "3"))
PROBE_CAP = 18                                  # probes sampled per (set, M) to bound cost
rng = np.random.default_rng(53)

ENTITIES = ["payment API","auth service","search index","billing job","cache layer","upload queue","report engine",
            "email worker","session store","rate limiter","image CDN","audit log","webhook relay","config loader",
            "metrics sink","backup task","login flow","export tool","notification bus","schema migrator","token vault",
            "feature flag svc","data lake","shard router","pdf renderer","geo lookup","fraud check","recommend svc",
            "chat gateway","trace collector"]
ATTRS = ["retry limit","timeout seconds","max batch size","cache TTL minutes","concurrency cap"]


def gen_facts(r, M):
    pairs = [(e, a) for e in ENTITIES for a in ATTRS]; r.shuffle(pairs); pairs = pairs[:M]
    vals = list(range(11, 11 + 300)); r.shuffle(vals)                 # distinct values -> unambiguous probes
    facts = []
    for i, (e, a) in enumerate(pairs):
        v = vals[i]
        facts.append({"text": f"The {a} of the {e} is {v}.", "q": f"What is the {a} of the {e}?", "val": str(v)})
    return facts


CBUDGET = int(os.getenv("RAMR_CBUDGET", "0"))    # hard character budget for the compiled object (0 = sentence-budget mode)


def compile_kb(model, facts, s):
    if CBUDGET > 0:
        # FAIR information-budget mode: same packing guidance to every model + a HARD char cap enforced in code,
        # so retention measures genuine compression at a fixed memory size (not gameable summarization style).
        sysmsg = (f"Compress the following facts into the most compact lookup form possible (a terse "
                  f"'entity attr=value' list is ideal). You have a HARD budget of ~{CBUDGET} characters and CANNOT "
                  f"keep them all -- pack as many as fit and drop the rest.")
    else:
        sysmsg = (f"You are compressing a knowledge base for later lookup. Summarize ALL of the following facts into "
                  f"at most {s} sentences. Be concise; you cannot keep every detail.")
    usr = "Facts:\n" + "\n".join(f["text"] for f in facts)
    body = {"model": model, "temperature": 0.0, "max_tokens": int(os.getenv("RAMR_CTOK","600")),
            "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": usr}]}
    # retry until we get a NON-EMPTY summary (reasoning models occasionally return empty content -- that is a
    # measurement failure, NOT 0% retention, so we must not score it). Return None if persistently empty.
    for _ in range(6):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                v0.OLL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=240).read())
            out = (r["choices"][0]["message"].get("content") or "").strip()
            if out:
                return out[:CBUDGET] if CBUDGET > 0 else out      # hard cap -> same memory size for every model
            time.sleep(1.0)                                       # empty -> retry
        except Exception:
            time.sleep(1.0)
    return None                                                    # persistent failure -> caller excludes this set


def probe(model, ctx_text, q):
    sysmsg = ("Answer using ONLY the provided context; if the context does not contain the answer, say UNKNOWN. "
              "End with exactly:\nANSWER: <short answer>")
    usr = "Context:\n" + ctx_text + "\n\nQuestion: " + q
    body = {"model": model, "temperature": 0.0, "max_tokens": int(os.getenv("RAMR_PTOK","200")),
            "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": usr}]}
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                v0.OLL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=180).read())
            return r["choices"][0]["message"].get("content") or ""
        except Exception:
            time.sleep(0.8)
    return ""


if __name__ == "__main__":
    budget_desc = f"~{CBUDGET}-char HARD budget" if CBUDGET > 0 else f"{S_SENT}-sentence budget"
    print(f"compile OK - RAMR FACT-RETENTION ({MODEL}, M={M_LEVELS}, {budget_desc}, sets={N_SETS})", flush=True)
    raw_by_M = {m: [] for m in M_LEVELS}; comp_by_M = {m: [] for m in M_LEVELS}
    for si in range(N_SETS):
        for M in M_LEVELS:
            facts = gen_facts(np.random.default_rng(1000 + si * 17 + M), M)
            raw_ctx = "\n".join(f["text"] for f in facts)
            summary = compile_kb(MODEL, facts, S_SENT)
            if not summary:        # persistent empty/failed summary -> EXCLUDE this set (do not score it 0)
                print(f"  set {si} M={M}: SKIPPED (empty summary after retries -- measurement failure, not counted)", flush=True)
                continue
            idx = list(range(M)); rng.shuffle(idx); idx = idx[:min(PROBE_CAP, M)]
            def one(i):
                f = facts[i]
                return (v0.hit(probe(MODEL, raw_ctx, f["q"]), f["val"]),
                        v0.hit(probe(MODEL, summary, f["q"]), f["val"]))
            with ThreadPoolExecutor(max_workers=3) as pool:
                outs = list(pool.map(one, idx))
            raw_by_M[M].append(float(np.mean([o[0] for o in outs])))
            comp_by_M[M].append(float(np.mean([o[1] for o in outs])))
            print(f"  set {si} M={M}: raw {raw_by_M[M][-1]:.2f} | compiled {comp_by_M[M][-1]:.2f} "
                  f"(summary {len(summary.split())} words for {M} facts)", flush=True)
    n_valid = {M: len(comp_by_M[M]) for M in M_LEVELS}
    print(f"\n  === FACT-RETENTION (valid sets {n_valid} of {N_SETS} requested, {budget_desc}) ===", flush=True)
    print(f"  M facts | RAW acc | COMPILED acc (retention) | RETENTION-LOSS (raw-compiled)", flush=True)
    losses = {}
    for M in M_LEVELS:
        ra = float(np.mean(raw_by_M[M])); ca = float(np.mean(comp_by_M[M])); losses[M] = ra - ca
        print(f"    {M:3d}   |  {ra:.2f}   |  {ca:.2f}                   |  {ra-ca:+.2f}", flush=True)
    # bootstrap CI of the loss at the highest M (over sets)
    M_hi = M_LEVELS[-1]
    d = np.array(raw_by_M[M_hi]) - np.array(comp_by_M[M_hi])
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)]; lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"\n  === VERDICT (pre-registered falsifier) ===", flush=True)
    if losses[M_hi] >= 0.10 and lo > 0:
        trend = "grows with M" if losses[M_hi] > losses[M_LEVELS[0]] + 0.05 else "is roughly flat in M"
        print(f"  COMPILATION DROPS FACTS: at M={M_hi} facts under a {budget_desc}, compiled recall is "
              f"{np.mean(comp_by_M[M_hi]):.2f} vs raw {np.mean(raw_by_M[M_hi]):.2f} -- RETENTION-LOSS {losses[M_hi]:+.2f} "
              f"(CI [{lo:+.2f},{hi:+.2f}], excludes 0), and the loss {trend}. Confirms the 'compiled object should "
              f"AUGMENT, not REPLACE, raw data' claim AS A MEASURED METRIC: a summarized memory layer silently "
              f"discards facts under compression pressure. This is the FACT-RETENTION axis of the benchmark.", flush=True)
    else:
        print(f"  LOSSLESS (claim falsified for this model): compiled recall stays ~= raw even at M={M_hi} "
              f"(loss {losses[M_hi]:+.2f}, CI [{lo:+.2f},{hi:+.2f}]). Compilation did not drop facts at this budget; "
              f"the augment-not-replace claim is not supported here -- report honestly and raise compression "
              f"pressure (lower S / higher M) before concluding.", flush=True)
    # APPEND per-(model, budget) instead of overwriting -> every run's numbers persist + are reproducible.
    budget_key = f"cbudget={CBUDGET}" if CBUDGET > 0 else f"S={S_SENT}"
    run_key = f"{MODEL}|{budget_key}"
    rp = "agora_output/benchmark/ramr_factret_result.json"
    store = {}
    if os.path.exists(rp):
        try:
            prev = json.load(open(rp))
            store = prev if "runs" in prev else {}   # migrate: ignore the old flat schema
        except Exception:
            store = {}
    store.setdefault("runs", {})
    store["runs"][run_key] = {
        "model": MODEL, "budget": budget_key, "M_levels": M_LEVELS,
        "sets": min(n_valid.values()), "sets_requested": N_SETS, "n_valid": n_valid,
        "raw": {str(m): raw_by_M[m] for m in M_LEVELS},
        "compiled": {str(m): comp_by_M[m] for m in M_LEVELS},
        "loss": {str(m): losses[m] for m in M_LEVELS},
    }
    json.dump(store, open(rp, "w"), indent=1)
    print(f"  persisted run '{run_key}' ({len(store['runs'])} runs total in {rp})", flush=True)
    print("DONE", flush=True)
