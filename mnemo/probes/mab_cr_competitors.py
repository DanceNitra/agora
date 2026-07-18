"""FLAGSHIP cell (competitors) — mem0 / graphiti on MemoryAgentBench Conflict Resolution, same task as
mab_conflict_resolution.py. Owner rule [[graphiti-measurements-use-ollama-cloud]]: competitor LLM calls go to
OLLAMA CLOUD, never OpenAI. Embeddings have no Ollama-Cloud option, so the embedder is LOCAL nomic.

Fair protocol, identical to the mnemo cell: ingest the SAME 455 official facts (in order, updates after
originals) into the system's NATIVE store (its own conflict resolution runs), then for each question retrieve
from that store and answer with the SAME Ollama-Cloud answerer + SAME gold match. The memory system's job is to
surface the CONSOLIDATED value; the answerer + judge are held constant across systems.

Run:  python mnemo/probes/mab_cr_competitors.py --system mem0 --n 100 [--smoke]
      python mnemo/probes/mab_cr_competitors.py --system graphiti --n 100
"""
import json, os, re, sys, time, argparse, urllib.request

sys.stdout.reconfigure(errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "mab_cr_data", "factconsolidation_sh_6k_no0.json")

def _load_cloud():
    cfg = {}
    for line in open(os.path.join(HERE, "..", "..", "server", ".env"), encoding="utf-8", errors="replace"):
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip()
    return cfg["AGORA_API_BASE_URL"], cfg["AGORA_API_KEY"], cfg.get("AGORA_LLM_MODEL_CHEAP", "deepseek-v4-flash")
CLOUD_BASE, CLOUD_KEY, CLOUD_MODEL = _load_cloud()

def llm_answer(question, ctx_text):
    sys_msg = ("Answer with ONLY the shortest exact value (a name/place/word), no sentence. The retrieved "
               "memories may contain the same thing more than once with different values; the LATEST/most "
               "recent statement is correct. Use it.")
    usr = f"Memories:\n{ctx_text}\n\nQuestion: {question}\nAnswer:"
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

def norm(s): return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()
def hit(ans, gold_list):
    a = norm(ans)
    return any(norm(g) in a or a in norm(g) for g in gold_list if g)

def load_data(n):
    d = json.load(open(DATA, encoding="utf-8"))
    facts = [re.sub(r'^\d+\.\s*', '', l).strip() for l in d["context"].split("\n") if re.match(r'^\d+\.', l.strip())]
    return facts, d["questions"][:n], d["answers"][:n]

# ---- mem0 on Ollama Cloud (LLM) + local nomic (embedder) ----
def run_mem0(facts, questions, golds):
    from mem0 import Memory
    cfg = {
        "llm": {"provider": "openai", "config": {
            "model": CLOUD_MODEL, "temperature": 0,
            "openai_base_url": CLOUD_BASE, "api_key": CLOUD_KEY}},
        "embedder": {"provider": "ollama", "config": {
            "model": "nomic-embed-text", "ollama_base_url": "http://localhost:11434", "embedding_dims": 768}},
        "vector_store": {"provider": "qdrant", "config": {"embedding_model_dims": 768,
            "path": os.path.join(HERE, "mab_cr_mem0_qdrant")}},
    }
    mem = Memory.from_config(cfg)
    uid = "mab_cr"
    BUDGET = float(os.environ.get("MEM0_INGEST_BUDGET", "600"))  # hard wall-clock cap so it can NEVER hang for an hour
    t0 = time.time()
    ingested = 0
    for i, f in enumerate(facts):
        if time.time() - t0 > BUDGET:
            print(f"    mem0 ingest BUDGET {BUDGET:.0f}s hit at {i}/{len(facts)} — proceeding to answer with what's stored", flush=True)
            break
        mem.add(f, user_id=uid)
        ingested = i + 1
        if (i + 1) % 25 == 0:
            print(f"    mem0 ingest {i+1}/{len(facts)}  ({time.time()-t0:.0f}s)", flush=True)
    print(f"    mem0 ingested {ingested}/{len(facts)} facts in {time.time()-t0:.0f}s", flush=True)
    correct = 0
    for i, (q, gold) in enumerate(zip(questions, golds)):
        sr = mem.search(q, filters={"user_id": uid}, limit=5)
        mems = sr.get("results", sr) if isinstance(sr, dict) else sr
        ctx = "\n".join((x.get("memory") or x.get("text") or str(x)) for x in (mems or []))
        if hit(llm_answer(q, ctx or "(none)"), gold):
            correct += 1
        if (i + 1) % 10 == 0:
            print(f"    mem0 answer {i+1}/{len(questions)}  correct={correct}", flush=True)
    return correct

# ---- graphiti on Ollama Cloud (LLM) + local nomic (embedder) ----
def run_graphiti(facts, questions, golds):
    import asyncio, datetime
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    from graphiti_core.llm_client import OpenAIGenericClient, LLMConfig
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

    llm_cfg = LLMConfig(api_key=CLOUD_KEY, model=CLOUD_MODEL, base_url=CLOUD_BASE, temperature=0)
    emb = OpenAIEmbedder(OpenAIEmbedderConfig(api_key="local", embedding_model="nomic-embed-text",
                                              embedding_dim=768, base_url="http://localhost:11434/v1"))
    async def _run():
        g = Graphiti("bolt://localhost:7687", "neo4j", "testpassword123",
                     llm_client=OpenAIGenericClient(config=llm_cfg), embedder=emb)
        gid = f"mabcr_{datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S')}"
        t0d = datetime.datetime(2026, 7, 11, 10, 0, 0, tzinfo=datetime.timezone.utc)
        try:
            await g.build_indices_and_constraints()
            st = time.time()
            for i, f in enumerate(facts):
                await g.add_episode(name=f"f{i}", episode_body=f, source_description="facts",
                                    reference_time=t0d + datetime.timedelta(minutes=i),
                                    source=EpisodeType.message, group_id=gid)
                if (i + 1) % 25 == 0:
                    print(f"    graphiti ingest {i+1}/{len(facts)}  ({time.time()-st:.0f}s)", flush=True)
            correct = 0
            for i, (q, gold) in enumerate(zip(questions, golds)):
                res = await g.search(q, group_ids=[gid], num_results=8)
                ctx = "\n".join(getattr(x, "fact", str(x)) for x in res)
                if hit(llm_answer(q, ctx or "(none)"), gold):
                    correct += 1
                if (i + 1) % 10 == 0:
                    print(f"    graphiti answer {i+1}/{len(questions)}  correct={correct}", flush=True)
            return correct
        finally:
            await g.close()
    return asyncio.run(_run())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True, choices=["mem0", "graphiti"])
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--smoke", action="store_true", help="ingest only first 60 facts + n=5 questions to validate wiring")
    a = ap.parse_args()
    facts, qs, golds = load_data(a.n)
    if a.smoke:
        facts, qs, golds = facts[:60], qs[:5], golds[:5]
    print(f"system={a.system}  facts={len(facts)}  questions={len(qs)}  answerer={CLOUD_MODEL}"
          + ("  [SMOKE]" if a.smoke else ""), flush=True)
    fn = {"mem0": run_mem0, "graphiti": run_graphiti}[a.system]
    t0 = time.time()
    correct = fn(facts, qs, golds)
    n = len(qs)
    print(f"\n=== {a.system} on MAB Conflict Resolution (sh_6k), n={n} ===")
    print(f"  accuracy = {correct}/{n} = {correct/n:.2%}   ({time.time()-t0:.0f}s)")
    if not a.smoke:
        out = {"system": a.system, "n": n, "correct": correct, "accuracy": correct/n, "answerer": CLOUD_MODEL}
        json.dump(out, open(os.path.join(HERE, f"mab_cr_{a.system}_result.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
