"""mnemo on MemoryAgentBench Conflict Resolution (FactConsolidation) — OFFICIAL data + OFFICIAL scoring +
OFFICIAL prompt template, so the number is produced the way the published leaderboard was (mem0 18%,
Zep/Graphiti 7%, GPT-4o full-context 60% on the CR/FactConsolidation axis).

Answerer = Ollama Cloud (deepseek-v4-flash) — NOT OpenAI (owner rule + no OpenAI budget). The leaderboard
used gpt-4o-mini; we therefore report the answerer explicitly and VALIDATE the harness with the benchmark's
own LONG-CONTEXT baseline: if long-context reproduces a sane FactConsolidation number, the answerer swap does
not invalidate the mnemo-vs-leaderboard read.

Conditions (only the memory layer differs; prompt/scoring/answerer identical):
  longcontext — the full numbered fact list in context (the benchmark's own baseline; validates the harness).
  mnemo       — ingest each numbered fact into mnemo with key-supersession (later fact retires the earlier);
                retrieve top-k=10 via mnemo.recall.

Official pieces (verbatim): scoring = mab_score.substring_exact_match max-over-golds; prompt = the
factconsolidation query template ("serial number ... newer fact has larger serial number ... very concise
answer ... Answer:"); answer parsed after "Answer:"; system = the official SYSTEM_MESSAGE.

Run:  python research/probes/mab_official/run_mnemo_official.py --condition longcontext --n 15   (validate first)
      python research/probes/mab_official/run_mnemo_official.py --condition mnemo --n 100
"""
import json, os, re, sys, time, argparse, urllib.request

sys.stdout.reconfigure(errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", ".."))
from mab_score import substring_exact_match_score, drqa_metric_max_over_ground_truths  # noqa: E402
from inspeximus import Inspeximus  # noqa: E402

DATA_DIR = os.path.join(HERE, "..", "mab_cr_data")
EMB_URL = os.environ.get("OLLAMA_EMBED_URL", "http://localhost:11434/api/embed")
EMB_MODEL = "nomic-embed-text"
RETRIEVE_NUM = 100                 # MAB mem0 config: retrieve_num=100 (main() can override via --retrieve-num)
CHUNK_SIZE = 4096                  # MAB mem0 config: agent_chunk_size=4096 (main() can override via --chunk-size)
TEMP = 0.0                         # main() sets 0.7 for the faithful gpt-4o-mini reproduction (MAB temperature)
MAX_TOKENS = 600                   # deepseek is a reasoning model — a tight cap yields EMPTY content; parse the answer out
                                    # long gold like "University of California, Berkeley" is not clipped.

SYSTEM_MESSAGE = "You are a helpful assistant that can read the context and memorize it for future retrieval."
# The OFFICIAL factconsolidation query template (utils/templates.py), verbatim:
FC_QUERY = ("Pretend you are a knowledge management system. Each fact in the knowledge pool is provided with a "
            "serial number at the beginning, and the newer fact has larger serial number. \n You need to solve "
            "the conflicts of facts in the knowledge pool by finding the newest fact with larger serial number. "
            "You need to answer a question based on this rule. You should give a very concise answer without "
            "saying other words for the question **only** from the knowledge pool you have memorized rather than "
            "the real facts in real world. \n\nFor example:\n\n [Knowledge Pool] \n\n Question: Based on the "
            "provided Knowledge Pool, what is the name of the current president of Russia? \nAnswer: Donald Trump "
            "\n\n Now Answer the Question: Based on the provided Knowledge Pool, {question} \nAnswer:")


def _envcfg():
    cfg = {}
    for line in open(os.path.join(HERE, "..", "..", "..", "server", ".env"), encoding="utf-8", errors="replace"):
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip()
    return cfg
_ENVCFG = _envcfg()
# BASE/KEY/ANSWERER are mutable module state; main() can flip them to the OpenAI gpt-4o-mini backend (--llm openai)
# to FAITHFULLY reproduce the published leaderboard config (mem0 ~18% under chunked ingest + gpt-4o-mini).
BASE = _ENVCFG["AGORA_API_BASE_URL"]
KEY = _ENVCFG["AGORA_API_KEY"]
ANSWERER = _ENVCFG.get("AGORA_LLM_MODEL_CHEAP", "deepseek-v4-flash")
def use_openai():
    global BASE, KEY, ANSWERER
    BASE, KEY, ANSWERER = "https://api.openai.com/v1", _ENVCFG["OPENAI_API_KEY"], "gpt-4o-mini"


def _mem0_build():
    """mem0 with LLM extraction on Ollama Cloud (owner rule: competitor measurements use Ollama Cloud, never
    block on OpenAI) + local nomic embedder + a fresh qdrant. Same recipe that ran in our integrity benchmark."""
    import shutil
    from mem0 import Memory
    tmp = os.environ.get("TEMP", "/tmp")
    qpath = os.path.join(tmp, "mem0_mabcr_qdrant")
    hpath = os.path.join(tmp, "mem0_mabcr_history.db")
    shutil.rmtree(qpath, ignore_errors=True)
    try: os.remove(hpath)
    except OSError: pass
    cfg = {"llm": {"provider": "openai", "config": {"model": ANSWERER, "temperature": TEMP,
                   "openai_base_url": BASE, "api_key": KEY}},
           "embedder": {"provider": "ollama", "config": {"model": EMB_MODEL,
                        "ollama_base_url": "http://localhost:11434"}},
           "history_db_path": hpath,
           "vector_store": {"provider": "qdrant", "config": {"collection_name": "mabcr_nomic768",
                            "embedding_model_dims": 768, "path": qpath}}}
    return Memory.from_config(cfg)


def _mem0_add(mem, text, uid):
    for a in range(6):                                          # exponential backoff so 429 throttling doesn't
        try:                                                    # silently empty the store (contaminated determinism run)
            mem.add(text, user_id=uid)
            return True
        except Exception:
            if a == 5:
                return False                                    # genuinely refused; caller can count the failure
            time.sleep(3 * (2 ** a))                            # 3,6,12,24,48s


def parse_output(text, prefix="Answer:"):
    """The official parse_output: extract the text after the last 'Answer:' if present."""
    if prefix in text:
        return text.rsplit(prefix, 1)[1].strip()
    return text.strip()


def answer(knowledge_pool, question):
    user = knowledge_pool + "\n\n" + FC_QUERY.format(question=question)
    body = json.dumps({"model": ANSWERER, "temperature": TEMP, "max_tokens": MAX_TOKENS,
                       "messages": [{"role": "system", "content": SYSTEM_MESSAGE},
                                    {"role": "user", "content": user}]}).encode()
    for a in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                BASE + "/chat/completions", data=body,
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY}), timeout=120)
            return parse_output(json.loads(r.read())["choices"][0]["message"]["content"].strip())
        except Exception:
            if a == 3:
                return ""
            time.sleep(3)


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


def _embed(texts):
    body = json.dumps({"model": EMB_MODEL, "input": [t if t.strip() else " " for t in texts]}).encode()
    for a in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                EMB_URL, data=body, headers={"Content-Type": "application/json"}), timeout=300)
            return json.loads(r.read())["embeddings"]
        except Exception:
            if a == 2:
                raise
            time.sleep(2)


# The Ollama embed endpoint has a ~2.1s FIXED per-request overhead (GPU stays ~idle), so 455 one-at-a-time
# embeds = 16 min. Batching amortizes it (n=100 -> 27ms/item). We pre-embed every text mnemo will need in a few
# batched calls and serve mnemo a cache-lookup embedder; anything unforeseen falls back to a live (slow) call.
_CACHE = {}
_LIVE = [0]
def warm(texts):
    todo = [t for t in dict.fromkeys(texts) if t not in _CACHE]
    for i in range(0, len(todo), 128):
        chunk = todo[i:i + 128]
        for t, v in zip(chunk, _embed(chunk)):
            _CACHE[t] = v
def cached_embed(t):
    v = _CACHE.get(t)
    if v is None:
        _LIVE[0] += 1
        v = _embed([t])[0]
        _CACHE[t] = v
    return v


def load(sample):
    d = json.load(open(os.path.join(DATA_DIR, f"factconsolidation_{sample}_no0.json"), encoding="utf-8"))
    facts = [re.sub(r'^\d+\.\s*', '', l).strip() for l in d["context"].split("\n") if re.match(r'^\d+\.', l.strip())]
    return facts, d["questions"], d["answers"]


try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENC = None
def chunk_ctx(numbered, max_tokens):
    """Replicate MAB's REAL ingestion: split the numbered context into `max_tokens`-token chunks — the MAB
    mem0 config uses agent_chunk_size=4096 (NOT atomic facts). A 4096-tok chunk holds ~300 facts, so a memory
    system that LLM-extracts (mem0) is stressed exactly as the leaderboard stresses it; a verbatim store keeps
    the facts. tiktoken cl100k matches gpt-4o-mini's tokenizer."""
    text = "\n".join(numbered)
    if _ENC is None:                                          # char proxy: ~4 chars/token
        step = max_tokens * 4
        return [text[i:i + step] for i in range(0, len(text), step)]
    toks = _ENC.encode(text)
    return [_ENC.decode(toks[i:i + max_tokens]) for i in range(0, len(toks), max_tokens)]


def run(condition, facts, questions, golds, seed=0, ingest="atomic"):
    numbered = [f"{i}. {f}" for i, f in enumerate(facts)]     # serial numbers — the prompt's rule needs them
    # ingest="chunk" replicates MAB's REAL protocol (512-token chunks, ~25-30 facts each). A verbatim store
    # keeps every fact; an LLM-extracting store (mem0) must survive multi-fact chunks — the true stress test.
    # ingest="atomic" (one clean fact per unit) is the unrealistic easy mode that flattered mem0 to 88%.
    units = chunk_ctx(numbered, CHUNK_SIZE) if ingest == "chunk" else numbered
    if condition != "longcontext":
        warm(units + list(questions))
        print(f"  [warm] cached {len(_CACHE)} embeddings · ingest={ingest} · units={len(units)}", flush=True)
    m = None
    mem0obj = None
    if condition == "mnemo":
        m = Inspeximus(path=None, embed=cached_embed)
        m.echo_guard = True
        if ingest == "chunk":
            for c in units:                                   # verbatim chunk store — mnemo does NOT LLM-extract
                m.remember(c)
        else:
            for i, f in enumerate(facts):
                m.remember(f"{i}. {f}", key=key_of(f), object=f)  # keyed supersession keeps the latest per subject
    elif condition == "naive":
        m = Inspeximus(path=None, embed=cached_embed)
        m.echo_guard = False
        if ingest == "chunk":
            for c in units:
                m.remember(c)
        else:
            for i, f in enumerate(facts):
                m.remember(f"{i}. {f}", key=f"row-{i}", object=f)
    elif condition == "naive_drop":
        keys = [key_of(f) for f in facts]
        n_super = len(facts) - len({k: None for k in keys})
        s = (seed * 1103515245 + 12345) & 0x7fffffff
        drop = set()
        while len(drop) < n_super:
            s = (s * 1103515245 + 12345) & 0x7fffffff
            drop.add(s % len(facts))
        m = Inspeximus(path=None, embed=cached_embed)
        m.echo_guard = False
        for i, f in enumerate(facts):
            if i in drop:
                continue
            m.remember(f"{i}. {f}", key=f"row-{i}", object=f)
    elif condition == "mem0":
        mem0obj = _mem0_build()                                # LLM extraction on Ollama Cloud (owner rule), nomic embed
        for i, c in enumerate(units):                          # MAB feeds 512-token chunks; mem0 extracts its way
            _mem0_add(mem0obj, c, "mab_cr")
            if (i + 1) % 25 == 0:
                print(f"  [mem0 ingest] {i+1}/{len(units)}", flush=True)
    correct = 0
    for i, (q, gold) in enumerate(zip(questions, golds)):
        if condition == "longcontext":
            pool = "\n".join(numbered)
        elif condition == "mem0":
            sr = mem0obj.search(q, filters={"user_id": "mab_cr"}, top_k=RETRIEVE_NUM)
            rows = sr.get("results", sr) if isinstance(sr, dict) else sr
            pool = "\n".join((x.get("memory") or x.get("text") or str(x)) for x in (rows or []))
        else:
            hits = m.recall(q, k=RETRIEVE_NUM)
            pool = "\n".join(h["text"] for h in hits)
        pred = answer(pool, q)
        if drqa_metric_max_over_ground_truths(substring_exact_match_score, pred, gold):
            correct += 1
        if (i + 1) % 10 == 0:
            print(f"  {condition} {i+1}/{len(questions)}  correct={correct}", flush=True)
    return correct


def main():
    global RETRIEVE_NUM, CHUNK_SIZE, TEMP
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", required=True,
                    choices=["mnemo", "longcontext", "naive", "naive_drop", "mem0"])
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--sample", default="sh_6k")
    ap.add_argument("--ingest", default="chunk", choices=["atomic", "chunk"],
                    help="chunk = MAB's real 512-token-chunk protocol (default); atomic = one clean fact per unit")
    ap.add_argument("--llm", default="deepseek", choices=["deepseek", "openai"],
                    help="openai = gpt-4o-mini end-to-end (mem0 extraction + answerer) = faithful published config")
    ap.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help="MAB agent_chunk_size (default 4096)")
    ap.add_argument("--retrieve-num", type=int, default=RETRIEVE_NUM, help="MAB retrieve_num (default 100)")
    ap.add_argument("--temp", type=float, default=None, help="answerer/mem0 temperature; default 0.0, or 0.7 for --llm openai (MAB)")
    a = ap.parse_args()
    RETRIEVE_NUM, CHUNK_SIZE = a.retrieve_num, a.chunk_size
    if a.llm == "openai":
        use_openai()
        TEMP = 0.7 if a.temp is None else a.temp                # MAB mem0 config temperature
    else:
        TEMP = 0.0 if a.temp is None else a.temp
    facts, qs, golds = load(a.sample)
    qs, golds = qs[:a.n], golds[:a.n]
    print(f"MAB Conflict Resolution (FactConsolidation {a.sample}) · OFFICIAL data+scoring+prompt · "
          f"answerer={ANSWERER} · {a.condition} · ingest={a.ingest} · n={len(qs)} · facts={len(facts)}", flush=True)
    t0 = time.time()
    c = run(a.condition, facts, qs, golds, ingest=a.ingest)
    n = len(qs)
    print(f"\n=== {a.condition}: {c}/{n} = {c/n:.1%}  ({time.time()-t0:.0f}s, {_LIVE[0]} live-embed fallbacks) ===")
    print("  published CR single-hop (gpt-4o-mini answerer, arXiv:2507.05257 Tab.2/11): GPT-4o long-ctx 60% "
          "(88% @32K) · HippoRAG-v2 54% · BM25-RAG 56% · mem0 18% (22% @32K). multi-hop: ALL <7%.")
    json.dump({"condition": a.condition, "sample": a.sample, "ingest": a.ingest, "llm": a.llm, "n": n,
               "correct": c, "accuracy": c/n, "answerer": ANSWERER,
               "scoring": "official substring_exact_match max-over-golds",
               "prompt": "official factconsolidation query template"},
              open(os.path.join(HERE, f"result_{a.condition}_{a.sample}_{a.ingest}_{a.llm}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
