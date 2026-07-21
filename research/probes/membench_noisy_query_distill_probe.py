"""membench_noisy_query_distill_probe.py — how much does query distillation recover on noisy agent queries?

MemBench v2 finding: on the `noisy` split (the real question buried in ~4 sentences of small-talk
distractors) retrieval hit@5 collapses from ~1.0 (clean) to ~0.52-0.56 for BOTH plain cosine and mnemo.
That's the realistic regime — users don't ask clean questions. This measures the obvious lever, honestly:
extract the core question with a cheap LLM, recall on THAT.

Arms (retrieval-level hit@k against the gold evidence turn, target_step_id[0] = flat index):
  raw       - recall on the full noisy query (the ~0.55 baseline)
  distill_X - recall on an LLM-distilled core question, per model family (deepseek/kimi/glm)
  marker    - a no-LLM heuristic: keep the text after the last "what I ...want/mean/ask/clarify..." marker
              (brittle; a free lower bound on how much of the loss is just the trailing real question)

This is NOT a novelty claim — query rewriting/distillation is standard IR practice. The point is the MEASURED
recovery on this specific noisy-agent-memory regime, to decide whether a `distill` preprocessing helper earns
its place in mnemo. Cross-family so the number isn't tied to one distiller. Own embed + distill caches.
RUN: python -u research/probes/membench_noisy_query_distill_probe.py
"""
import json, os, sys, re, time, hashlib, urllib.request
sys.stdout.reconfigure(errors="replace")

DATA = "agora_output/lab/data/membench/noisy.json"
ECACHE = "research/probes/membench_noisy_embcache_v1.json"
DCACHE = "research/probes/membench_noisy_distill_cache.json"
EMB_URL = os.environ.get("OLLAMA_EMBED_URL", "http://localhost:11434/api/embed")
CHAT_URL = "https://ollama.com/v1/chat/completions"
EMBM = "nomic-embed-text"; QP, DP = "search_query: ", "search_document: "
KS = (1, 5, 10); N = 80
MODELS = ["deepseek-v4-flash", "kimi-k2.7-code", "glm-5.2"]
env = {}
for line in open("server/.env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("AGORA_API_KEY") or env.get("OLLAMA_API_KEY")

_ec = json.load(open(ECACHE)) if os.path.exists(ECACHE) else {}
_dc = json.load(open(DCACHE)) if os.path.exists(DCACHE) else {}
def _ek(role, t): return hashlib.sha1(f"{EMBM}|{role}|{t[:2000]}".encode()).hexdigest()
def _embpost(inp):
    body = json.dumps({"model": EMBM, "input": inp}).encode()
    for a in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(EMB_URL, data=body,
                headers={"Content-Type": "application/json"}), timeout=180)
            return json.loads(r.read())["embeddings"]
        except Exception:
            if a == 2: raise
            time.sleep(2)
def embed(texts, role):
    pref = QP if role == "q" else DP
    miss = [t for t in texts if _ek(role, t) not in _ec]
    for i in range(0, len(miss), 64):
        ch = miss[i:i+64]
        for t, v in zip(ch, _embpost([pref+t for t in ch])): _ec[_ek(role, t)] = v
    return [_ec[_ek(role, t)] for t in texts]
def cos(a, b): return sum(x*y for x, y in zip(a, b))/((sum(x*x for x in a)**0.5)*(sum(x*x for x in b)**0.5)+1e-12)

def distill(model, q):
    key = f"{model}|{hashlib.sha1(q.encode()).hexdigest()}"
    if key in _dc: return _dc[key]
    prompt = ("The following user message is mostly small-talk and distractions with one real question "
              "buried in it. Reply with ONLY the core question, rewritten as a clean standalone query. "
              f"No preamble.\n\nMessage: {q}")
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 16000, "temperature": 0.0}).encode()
    for a in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(CHAT_URL, data=body,
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}), timeout=120)
            out = json.loads(r.read())["choices"][0]["message"]["content"].strip().strip('"')
            _dc[key] = out; return out
        except Exception:
            if a == 2: return None
            time.sleep(3)

_MARK = re.compile(r"(what (i|I)[^?]*?(want|mean|ask|clarify|wondering)[^?]*?(is|,))", re.I)
def marker_split(q):
    ms = list(_MARK.finditer(q))
    return q[ms[-1].end():].strip() if ms else q

def main():
    d = json.load(open(DATA, encoding="utf-8"))
    items = []
    for cat in ("roles", "events"):
        for t in d[cat][:N//2]:
            flat = [m["user_message"] for s in t["message_list"] for m in s]
            gt = sorted({a for a, _ in t["QA"]["target_step_id"] if a < len(flat)})
            if gt: items.append((flat, t["QA"]["question"], gt))
    print(f"noisy items: {len(items)}", flush=True)
    arms = ["raw", "marker"] + [f"distill_{m}" for m in MODELS]
    hit = {(arm, k): [] for arm in arms for k in KS}
    t0 = time.time()
    for n, (flat, q, gt) in enumerate(items):
        dvecs = embed(flat, "d")
        queries = {"raw": q, "marker": marker_split(q)}
        for m in MODELS:
            dq = distill(m, q); queries[f"distill_{m}"] = dq if dq else q
        for arm, qq in queries.items():
            qv = embed([qq], "q")[0]
            order = sorted(range(len(flat)), key=lambda i: -cos(qv, dvecs[i]))
            for k in KS:
                top = set(order[:k])
                hit[(arm, k)].append(1.0 if any(g in top for g in gt) else 0.0)
        if (n+1) % 20 == 0:
            json.dump(_ec, open(ECACHE, "w")); json.dump(_dc, open(DCACHE, "w"))
            print(f"  ... {n+1}/{len(items)} ({time.time()-t0:.0f}s)", flush=True)
    json.dump(_ec, open(ECACHE, "w")); json.dump(_dc, open(DCACHE, "w"))
    nq = len(items)
    print(f"\nMEASURED noisy-query recovery (n={nq}, hit@k retrieval)")
    out = {}
    for arm in arms:
        row = " ".join(f"hit@{k}={sum(hit[(arm,k)])/nq:.3f}" for k in KS)
        print(f"  {arm:16s} {row}")
        out[arm] = {f"hit@{k}": round(sum(hit[(arm,k)])/nq, 4) for k in KS}
    json.dump(out, open("research/probes/membench_noisy_query_distill_probe_result.json", "w"), indent=2)
    print("-> research/probes/membench_noisy_query_distill_probe_result.json")

if __name__ == "__main__":
    main()
