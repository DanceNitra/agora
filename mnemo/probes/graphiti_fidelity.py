"""graphiti_fidelity.py — fill the graphiti FIDELITY cell of the domination matrix (small, feasible).

Ollama is out of quota; graphiti's LLM extraction runs on OpenAI gpt-4o. Full 455-fact ingest is impractical
(455 episodes x multi-call extraction), so we test the SAME conflict-resolution fidelity on N real MAB conflict
subjects: ingest A then B (the correction) as episodes, search the subject, answer with the official FC prompt
(gpt-4o-mini), score vs the gold B. Graphiti LLM-extracts entities/edges, so it is expected to lose the specific
corrected value (like mem0). Directional (small n), OpenAI-backed, neo4j.

RUN:  python mnemo/probes/graphiti_fidelity.py --n 15
"""
import os, sys, json, time, argparse, asyncio
from datetime import datetime, timezone, timedelta
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "mab_official"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "mnemo_pypi"))
import run_mnemo_official as H

_env = {}
for l in open(os.path.join(HERE, "..", "..", "server", ".env"), encoding="utf-8", errors="replace"):
    if "=" in l and not l.startswith("#"):
        k, v = l.split("=", 1); _env[k.strip()] = v.strip()
OPENAI = "https://api.openai.com/v1"
OKEY = _env.get("OPENAI_API_KEY", "")
GRAPH_MODEL = "gpt-4o"           # graphiti extraction
ANSWER_MODEL = "gpt-4o-mini"     # answerer (matches the mem0 fidelity re-verify / published config)


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


def answer(ctx, question):
    import urllib.request
    p = (H.FC_QUERY.format(question=f"what is the current value for: {question}"))
    body = json.dumps({"model": ANSWER_MODEL, "temperature": 0, "max_tokens": 60,
                       "messages": [{"role": "system", "content": H.SYSTEM_MESSAGE},
                                    {"role": "user", "content": ctx + "\n\n" + p}]}).encode()
    for a in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(OPENAI + "/chat/completions", data=body,
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + OKEY}), timeout=90)
            return json.loads(r.read())["choices"][0]["message"]["content"].rsplit("Answer:", 1)[-1].strip()
        except Exception:
            if a == 2:
                return ""
            time.sleep(3)


async def run(ps):
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    from graphiti_core.llm_client.openai_client import OpenAIClient
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from openai import AsyncOpenAI
    os.environ["SEMAPHORE_LIMIT"] = "3"
    os.environ["OPENAI_API_KEY"] = OKEY                # graphiti's default cross-encoder reads this at construction
    llm = OpenAIClient(config=LLMConfig(api_key=OKEY, model=GRAPH_MODEL, small_model=GRAPH_MODEL, base_url=OPENAI))
    emb = OpenAIEmbedder(config=OpenAIEmbedderConfig(embedding_model="nomic-embed-text", embedding_dim=768,
                         base_url="http://localhost:11434/v1", api_key="ollama"),
                         client=AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama"))
    g = Graphiti("bolt://localhost:7687", "neo4j", "testpassword123", llm_client=llm, embedder=emb)
    await g.driver.execute_query("MATCH (n) WHERE n.group_id STARTS WITH 'fid_' DETACH DELETE n")
    correct = 0
    for i, (k, A, B) in enumerate(ps):
        gid = f"fid_{i}"; t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for j, body in enumerate([A, B]):                 # A, then the correction B (gold)
            for attempt in range(3):
                try:
                    await g.add_episode(name=f"fid-{i}-{j}", episode_body=body, source=EpisodeType.text,
                                        source_description="fidelity", reference_time=t0 + timedelta(minutes=j),
                                        group_id=gid); break
                except Exception:
                    if attempt == 2: pass
                    await asyncio.sleep(3)
        try:
            res = await g.search(k, group_ids=[gid], num_results=10)
            ctx = "\n".join(getattr(e, "fact", "") or "" for e in (res or []))
        except Exception:
            ctx = ""
        ans = answer(ctx, k.rstrip(" ."))
        vB, vA = val_of(B, k).lower(), val_of(A, k).lower()
        correct += 1 if (vB in ans.lower()) else 0
        if (i + 1) % 5 == 0:
            print(f"  graphiti fidelity {i+1}/{len(ps)} correct={correct}", flush=True)
    await g.close()
    return correct


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=15); a = ap.parse_args()
    ps = pairs(a.n)
    print(f"GRAPHITI FIDELITY (gpt-4o extract, gpt-4o-mini answerer, neo4j) · n={len(ps)}", flush=True)
    t0 = time.time(); c = asyncio.run(run(ps))
    print(f"\n=== graphiti fidelity: {c}/{len(ps)} = {c/len(ps):.0%}  ({time.time()-t0:.0f}s) ===")
    json.dump({"system": "graphiti", "n": len(ps), "correct": c, "accuracy": c / len(ps),
               "graph_llm": GRAPH_MODEL, "answerer": ANSWER_MODEL},
              open(os.path.join(HERE, "graphiti_fidelity_result.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
