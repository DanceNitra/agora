"""FLAGSHIP cell — inspeximus on MemoryAgentBench's Conflict Resolution (CR) competency.

CR = FactConsolidation (Hu/Wang/McAuley, arXiv:2507.05257, ICLR 2026): a long list of facts where the SAME
subject-relation is stated twice with DIFFERENT values; the LATER value is the consolidated truth and the gold
answer. This is exactly inspeximus's supersession-by-key. We measure the value of that mechanism cleanly:

  naive     — all facts live in the pool (no supersession). A near-duplicate stale fact competes with the
              consolidated one at retrieval, so the answering LLM can pick the stale value.
  inspeximus     — each fact ingested with key = subject-relation; a later fact SUPERSEDES the earlier one, so only
              the consolidated value is retrievable.

Everything else is held identical: same nomic embedder + same top-k retrieval + same Ollama-Cloud answerer +
same gold match. The lift (inspeximus - naive) is the CR-competency value of supersession, on the OFFICIAL MAB data.

This is flagship STEP 1 (inspeximus vs its own no-supersession control on the real CR task). It is NOT yet a
published SOTA claim: that needs the competitors (mem0/zep/graphiti) and the standing gate. No number leaves
this repo until then.

Run:  python research/probes/mab_conflict_resolution.py [N_QUESTIONS]
Env:  reads Ollama-Cloud base/key/model from server/.env (never echoed). OLLAMA_EMBED_URL for the local embedder.
"""
import json, os, re, sys, time, hashlib, urllib.request

sys.stdout.reconfigure(errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))  # repo root, to import inspeximus if needed
DATA = os.path.join(HERE, "mab_cr_data", "factconsolidation_sh_6k_no0.json")
CACHE = os.path.join(HERE, "mab_cr_embcache.json")
EMB_URL = os.environ.get("OLLAMA_EMBED_URL", "http://localhost:11434/api/embed")
EMB_MODEL = "nomic-embed-text"
QP, DP = "search_query: ", "search_document: "
TOP_K = 5

# ---- Ollama-Cloud answerer (read config from server/.env inside the script; never echo the key) ----
def _load_cloud():
    envp = os.path.join(HERE, "..", "..", "server", ".env")
    cfg = {}
    for line in open(envp, encoding="utf-8", errors="replace"):
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip()
    return (cfg["AGORA_API_BASE_URL"], cfg["AGORA_API_KEY"], cfg.get("AGORA_LLM_MODEL_CHEAP", "deepseek-v4-flash"))
CLOUD_BASE, CLOUD_KEY, CLOUD_MODEL = _load_cloud()

def llm_answer(question, context_facts):
    ctx = "\n".join(context_facts)
    sys_msg = ("Answer with ONLY the shortest exact value (a name/place/word), no sentence. The facts may list "
               "the same thing more than once with different values; the LATEST/most recent statement is the "
               "correct one. Use it.")
    usr = f"Facts:\n{ctx}\n\nQuestion: {question}\nAnswer:"
    body = json.dumps({"model": CLOUD_MODEL, "temperature": 0,
                       "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": usr}]}).encode()
    for a in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                CLOUD_BASE + "/chat/completions", data=body,
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + CLOUD_KEY}), timeout=120)
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception:
            if a == 3:
                return ""
            time.sleep(3)

# ---- embedder (local nomic, cached) ----
_cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
_dirty = 0
def _ek(role, t): return hashlib.sha1(f"{EMB_MODEL}|{role}|{t[:600]}".encode()).hexdigest()
def _epost(inputs):
    inputs = [(s if s.strip() else " ") for s in inputs]
    body = json.dumps({"model": EMB_MODEL, "input": inputs}).encode()
    for a in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                EMB_URL, data=body, headers={"Content-Type": "application/json"}), timeout=300)
            return json.loads(r.read())["embeddings"]
        except Exception:
            if a == 2: raise
            time.sleep(2)
def embed(texts, role):
    global _dirty
    pref = QP if role == "q" else DP
    miss = [t for t in texts if _ek(role, t) not in _cache]
    for i in range(0, len(miss), 64):
        ch = miss[i:i+64]
        for t, v in zip(ch, _epost([pref + x for x in ch])):
            _cache[_ek(role, t)] = v
        _dirty += len(ch)
    return [_cache[_ek(role, t)] for t in texts]
def cos(a, b):
    return sum(x*y for x, y in zip(a, b)) / ((sum(x*x for x in a)**0.5)*(sum(x*x for x in b)**0.5)+1e-12)

# ---- fact parsing + supersession key (subject-relation; later value wins) ----
KEY_PATS = [r'^(.*\bis married to)\b', r'^(.*\bplays the position of)\b', r'^(.*\bdied in the city of)\b',
            r'^(.*\bis located in the continent of)\b', r'^(.*\bwas born in the city of)\b',
            r'^(.*\bis associated with the sport of)\b', r'^(.*\bwas educated (?:at|in))\b',
            r'^(The .*? of .*?) is\b', r'^(.*?) is\b']
def key_of(fact):
    f = fact.rstrip(".")
    for p in KEY_PATS:
        m = re.match(p, f)
        if m:
            return m.group(1).strip()
    return f
def value_of(fact, key):
    return fact.rstrip(".")[len(key):].strip()

def main():
    n_q = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    d = json.load(open(DATA, encoding="utf-8"))
    facts = [re.sub(r'^\d+\.\s*', '', l).strip() for l in d["context"].split("\n") if re.match(r'^\d+\.', l.strip())]
    # supersession: for each key keep the LAST fact (inspeximus's later-wins). Track stale values per key too.
    active_by_key, stale_by_key = {}, {}
    for f in facts:
        k = key_of(f)
        if k in active_by_key:
            stale_by_key.setdefault(k, []).append(value_of(active_by_key[k], k))
        active_by_key[k] = f
    naive_pool = list(facts)                       # every statement, stale + consolidated
    inspeximus_pool = list(active_by_key.values())      # consolidated only (later-wins supersession)
    print(f"facts={len(facts)}  conflict-keys={len(stale_by_key)}  "
          f"naive_pool={len(naive_pool)}  inspeximus_pool={len(inspeximus_pool)}")

    # pre-embed pools + questions
    embed(naive_pool, "d")
    qs = d["questions"][:n_q]
    golds = d["answers"][:n_q]
    embed(qs, "q")

    def norm(s): return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()
    def hit(ans, gold_list):
        a = norm(ans)
        return any(norm(g) in a or a in norm(g) for g in gold_list if g)

    def retrieve(pool, qv):
        scored = sorted(((cos(qv, embed([p], "d")[0]), p) for p in pool), reverse=True)
        return [p for _, p in scored[:TOP_K]]

    res = {"naive": {"correct": 0, "stale_in_ctx": 0}, "inspeximus": {"correct": 0, "stale_in_ctx": 0}}
    conflict_q = 0
    for i, (q, gold) in enumerate(zip(qs, golds)):
        qv = embed([q], "q")[0]
        # is this question about a conflict key? (gold == a consolidated value whose key had a stale value)
        is_conflict = any(any(norm(gg) in norm(value_of(active_by_key[k], k)) for gg in gold) for k in stale_by_key)
        if is_conflict:
            conflict_q += 1
        for cond, pool in (("naive", naive_pool), ("inspeximus", inspeximus_pool)):
            ctx = retrieve(pool, qv)
            ans = llm_answer(q, ctx)
            if hit(ans, gold):
                res[cond]["correct"] += 1
            # stale-resurrection: any stale value for a matched key present in the retrieved ctx
            ctx_join = " ".join(ctx)
            for k, svals in stale_by_key.items():
                if any(norm(sv) and norm(sv) in norm(ctx_join) for sv in svals) and norm(value_of(active_by_key[k], k)) in norm(ctx_join):
                    res[cond]["stale_in_ctx"] += 1
                    break
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(qs)}  naive={res['naive']['correct']}  inspeximus={res['inspeximus']['correct']}")
    json.dump(_cache, open(CACHE, "w"))

    n = len(qs)
    print("\n=== MemoryAgentBench Conflict Resolution (FactConsolidation sh_6k), n=%d questions ===" % n)
    for cond in ("naive", "inspeximus"):
        c = res[cond]
        print(f"  {cond:6s}  accuracy={c['correct']}/{n}={c['correct']/n:.2%}   "
              f"stale-in-retrieved-context={c['stale_in_ctx']}/{n}")
    lift = (res["inspeximus"]["correct"] - res["naive"]["correct"]) / n
    print(f"  LIFT (inspeximus supersession - naive): {lift:+.2%}  |  conflict questions ~{conflict_q}/{n}")
    out = {"dataset": "MemoryAgentBench/Conflict_Resolution/factconsolidation_sh_6k_no0", "n": n,
           "top_k": TOP_K, "answerer": CLOUD_MODEL, "results": res, "lift": lift,
           "conflict_keys": len(stale_by_key)}
    json.dump(out, open(os.path.join(HERE, "mab_cr_result.json"), "w"), indent=1)
    print("  wrote mab_cr_result.json")

if __name__ == "__main__":
    main()
