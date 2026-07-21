"""GATE CONTROLS for the inspeximus CR result — separate 'supersession removed the STALE value' (H1) from
'a smaller pool is just less cluttered' (H2), the confound the stress-claim panel flagged. Also fixes the
unfair answerer prompt and reports the free conflict/non-conflict split.

Conditions (identical nomic retrieval top-5, identical NEUTRAL answerer, identical gold match):
  naive_455        — all 455 facts (stale + consolidated + non-conflict).
  inspeximus_333        — supersession: last-per-key only (122 consolidated + 211 non-conflict).
  twinskept_333    — DECISIVE: same pool SIZE as inspeximus (333) but KEEP the stale twins
                     (122 consolidated + 122 stale + 89 random non-conflict). If this ~= inspeximus -> the lift is
                     pool-size/clutter (H2), supersession earns ~0. If this ~= naive -> keeping stale hurts
                     even at small size -> supersession (removing it) is the mechanism (H1).

Prompt fix: NO "latest is correct" hint (it was unusable by naive -> inflated the gap). Neutral for all.
Reports overall accuracy AND accuracy split by conflict vs non-conflict question.

Run:  python research/probes/mab_cr_controls.py [N]
"""
import json, os, re, sys, time, hashlib, urllib.request, random

sys.stdout.reconfigure(errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "mab_cr_data", "factconsolidation_sh_6k_no0.json")
CACHE = os.path.join(HERE, "mab_cr_embcache.json")   # reuse the cache from the first run
EMB_URL = os.environ.get("OLLAMA_EMBED_URL", "http://localhost:11434/api/embed")
EMB_MODEL = "nomic-embed-text"
QP, DP = "search_query: ", "search_document: "
TOP_K = 5
random.seed(42)

def _load_cloud():
    cfg = {}
    for line in open(os.path.join(HERE, "..", "..", "server", ".env"), encoding="utf-8", errors="replace"):
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1); cfg[k.strip()] = v.strip()
    return cfg["AGORA_API_BASE_URL"], cfg["AGORA_API_KEY"], cfg.get("AGORA_LLM_MODEL_CHEAP", "deepseek-v4-flash")
CLOUD_BASE, CLOUD_KEY, CLOUD_MODEL = _load_cloud()

def llm_answer(question, ctx_facts):
    # NEUTRAL prompt — no recency hint (that was unfair to the arms that can't observe order).
    sys_msg = "Answer with ONLY the shortest exact value (a name, place, or word) supported by the facts. No sentence."
    usr = "Facts:\n" + "\n".join(ctx_facts) + f"\n\nQuestion: {question}\nAnswer:"
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

_cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
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
    pref = QP if role == "q" else DP
    miss = [t for t in texts if _ek(role, t) not in _cache]
    for i in range(0, len(miss), 64):
        ch = miss[i:i+64]
        for t, v in zip(ch, _epost([pref + x for x in ch])):
            _cache[_ek(role, t)] = v
    return [_cache[_ek(role, t)] for t in texts]
def cos(a, b):
    return sum(x*y for x, y in zip(a, b)) / ((sum(x*x for x in a)**0.5)*(sum(x*x for x in b)**0.5)+1e-12)

KEY_PATS = [r'^(.*\bis married to)\b', r'^(.*\bplays the position of)\b', r'^(.*\bdied in the city of)\b',
            r'^(.*\bis located in the continent of)\b', r'^(.*\bwas born in the city of)\b',
            r'^(.*\bis associated with the sport of)\b', r'^(.*\bwas educated (?:at|in))\b',
            r'^(The .*? of .*?) is\b', r'^(.*?) is\b']
def key_of(fact):
    f = fact.rstrip(".")
    for p in KEY_PATS:
        m = re.match(p, f)
        if m: return m.group(1).strip()
    return f
def value_of(fact, key): return fact.rstrip(".")[len(key):].strip()
def norm(s): return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()
def hit(ans, gold): a = norm(ans); return any(norm(g) in a or a in norm(g) for g in gold if g)

def main():
    n_q = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    d = json.load(open(DATA, encoding="utf-8"))
    facts = [re.sub(r'^\d+\.\s*', '', l).strip() for l in d["context"].split("\n") if re.match(r'^\d+\.', l.strip())]
    first, active, stale, order = {}, {}, {}, []
    for f in facts:
        k = key_of(f)
        if k not in first: first[k] = f; order.append(k)
        else: stale.setdefault(k, []).append(active.get(k, first[k]))
        active[k] = f
    conflict_keys = set(stale)
    consolidated = [active[k] for k in order]                    # 333, last-per-key
    stale_facts = [f for f in facts if f not in set(consolidated)]  # the 122 superseded twins
    nonconf = [active[k] for k in order if k not in conflict_keys]  # 211 non-conflict
    conf_consol = [active[k] for k in order if k in conflict_keys]  # 122 consolidated conflict values

    naive_pool = list(facts)                                     # 455
    inspeximus_pool = list(consolidated)                              # 333
    # twins-kept, size-matched to inspeximus (333): all conflict facts (consol+stale=244) + random non-conflict fill
    fill = random.sample(nonconf, len(inspeximus_pool) - len(conf_consol) - len(stale_facts))
    twinskept_pool = conf_consol + stale_facts + fill
    print(f"facts={len(facts)} conflict_keys={len(conflict_keys)} | naive={len(naive_pool)} "
          f"inspeximus={len(inspeximus_pool)} twinskept={len(twinskept_pool)}", flush=True)

    embed(naive_pool, "d")
    qs, golds = d["questions"][:n_q], d["answers"][:n_q]
    embed(qs, "q")
    # question is 'conflict' if its gold equals a consolidated value of a conflict key
    consol_vals = {norm(value_of(active[k], k)): k for k in conflict_keys}
    def is_conf(gold): return any(norm(g) in consol_vals or any(norm(g) in cv for cv in consol_vals) for g in gold)

    pools = {"naive_455": naive_pool, "inspeximus_333": inspeximus_pool, "twinskept_333": twinskept_pool}
    embcache = {}
    def emb1(t):
        if t not in embcache: embcache[t] = embed([t], "d")[0]
        return embcache[t]
    res = {c: {"conf_ok": 0, "conf_n": 0, "non_ok": 0, "non_n": 0} for c in pools}
    for i, (q, gold) in enumerate(zip(qs, golds)):
        qv = embed([q], "q")[0]
        conf = is_conf(gold)
        for c, pool in pools.items():
            top = [p for _, p in sorted(((cos(qv, emb1(p)), p) for p in pool), reverse=True)[:TOP_K]]
            ok = hit(llm_answer(q, top), gold)
            key = "conf" if conf else "non"
            res[c][f"{key}_n"] += 1; res[c][f"{key}_ok"] += 1 if ok else 0
        if (i + 1) % 10 == 0:
            print("  %d/%d  " % (i+1, len(qs)) + "  ".join(
                "%s=%d" % (c, res[c]["conf_ok"]+res[c]["non_ok"]) for c in pools), flush=True)
    json.dump(_cache, open(CACHE, "w"))

    n = len(qs)
    print("\n=== GATE CONTROLS — MAB Conflict Resolution (sh_6k), n=%d, NEUTRAL prompt ===" % n)
    print("  %-14s %8s | %-18s %-18s" % ("condition", "overall", "conflict-Q", "nonconflict-Q"))
    out = {}
    for c in pools:
        r = res[c]; tot = r["conf_ok"] + r["non_ok"]
        cacc = r["conf_ok"]/r["conf_n"] if r["conf_n"] else 0
        nacc = r["non_ok"]/r["non_n"] if r["non_n"] else 0
        print("  %-14s %6.1f%% | %d/%d = %5.1f%%     %d/%d = %5.1f%%" % (
            c, 100*tot/n, r["conf_ok"], r["conf_n"], 100*cacc, r["non_ok"], r["non_n"], 100*nacc))
        out[c] = {"overall": tot/n, "conflict": cacc, "nonconflict": nacc, **r}
    json.dump({"n": n, "answerer": CLOUD_MODEL, "neutral_prompt": True, "results": out},
              open(os.path.join(HERE, "mab_cr_controls_result.json"), "w"), indent=1)
    print("\n  READ: twinskept ~= inspeximus -> lift is pool-size/clutter (H2). twinskept ~= naive -> supersession (H1).")
    print("  wrote mab_cr_controls_result.json")

if __name__ == "__main__":
    main()
