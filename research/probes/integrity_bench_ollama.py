"""Cross-system integrity benchmark — Ollama edition (free, local, reproducible; no OpenAI account).

Same value-obscuring-revert and echo-resurrection cells as integrity_bench_{revert,echo}.py, but every LLM
call — the shared blind judge AND each competitor's native extractor/agent — runs on a local Ollama model
instead of gpt-4o-mini. That makes the whole board reproducible at zero cost: anyone with Ollama can re-run
it. The judge is ONE model for every system (gemma2:9b), so the comparison stays fair; embeddings are the
local nomic-embed-text.

    python research/probes/integrity_bench_ollama.py --cell revert --systems inspeximus,mem0,graphiti,letta --n 20
    python research/probes/integrity_bench_ollama.py --cell echo   --systems inspeximus,mem0,graphiti,letta --n 20

Requires: local Ollama serving gemma2:9b + nomic-embed-text; mem0/graphiti installed; a running Letta server
(docker letta/letta on :8283) for the letta system.
"""
import os, sys, json, time, argparse, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus

OLLAMA = "http://localhost:11434"
JUDGE_MODEL = "gemma2:9b"
GEN_MODEL = "qwen3:30b-a3b"      # STRONG extractor for the fair run (weak models cripple LLM-gated dedup)
EMBED_MODEL = "nomic-embed-text"

# ── the shared blind judge, on Ollama ────────────────────────────────────────
def ollama_chat(prompt, model=JUDGE_MODEL, temp=0.0, max_tokens=200):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": temp, "max_tokens": max_tokens}).encode()
    for a in range(5):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                OLLAMA + "/v1/chat/completions", data=body,
                headers={"Authorization": "Bearer ollama", "Content-Type": "application/json"}), timeout=180)
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception:
            if a == 4:
                return None
            time.sleep(2 * (a + 1))


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n; d = 1 + z*z/n; c = p + z*z/(2*n)
    h = z * ((p*(1-p)/n + z*z/(4*n*n)) ** 0.5)
    return (round((c-h)/d, 3), round((c+h)/d, 3))


def surface_verdict(context_text, correct, retired):
    """SURFACE-CLEANLINESS metric (deterministic, LLM-free, judge-independent).

    After a correction (and optional revert), the store's current-memory surface should present ONE
    unambiguous current value. We measure whether it instead still carries the RETIRED value alongside
    the correct one — a contradiction the consumer's LLM then has to resolve (which is where a judge-based
    metric turned out to be model-dependent: a capable judge silently resolves the contradiction, hiding it).

    Reads the raw surface text, no model:
      clean         — the correct value is present and the retired one is NOT (single determinate answer)
      contradictory — BOTH values are present as active memories (the retired value was never cleaned up)
      dropped       — the correct value is absent (a different failure: lost the fact)
    Metric reported = contradiction rate (lower is better)."""
    t = (context_text or "").lower()
    has_c, has_r = correct.lower() in t, retired.lower() in t
    if has_c and has_r:
        return "contradictory"
    if has_c and not has_r:
        return "clean"
    return "dropped"


ENTS = [("cache region", "osaka", "malmo"), ("primary shard", "delta7", "sigma2"),
        ("build target", "arm64", "riscv"), ("default currency", "forint", "guarani"),
        ("route profile", "coastal", "inland"), ("api tier", "bronze", "platinum"),
        ("index locale", "tallinn", "cusco"), ("worker pool", "amber", "cobalt"),
        ("log sink", "vault3", "harbor8"), ("retry policy", "linear", "jitter"),
        ("color theme", "sepia", "slate"), ("scheduler", "roundrobin", "weighted"),
        ("session store", "sticky", "pooled"), ("cdn provider", "fastly", "bunny"),
        ("rate limiter", "tiered", "flat"), ("search engine", "elastic", "sonic"),
        ("email sender", "postmark", "sendy"), ("backup window", "0200utc", "0400utc"),
        ("queue driver", "kafka", "nats"), ("feature flag", "canary", "stable"),
        ("dns resolver", "quad9", "opendns"), ("time source", "chrony", "ntpd"),
        ("hash algo", "blake3", "sha256"), ("compression", "zstd", "brotli")]
REVERTS = ["go back to what we had for the {e}.", "revert that last {e} change.", "undo the {e} correction.",
           "put the {e} back the way it was.", "roll back the {e} change."]
ECHOES = ["by the way, the {e} is {A}.", "reminder: {e} = {A}.", "as noted, the {e} is {A}."]


# ── inspeximus (no LLM; judge reads its native recall) ───────────────────────
def run_inspeximus(cases, cell):
    res = []
    for (e, A, B, extra) in cases:
        m = Inspeximus(path=None); m.echo_guard = True
        m.remember(f"the {e} is {A}", key=e, object=A)
        m.remember(f"correction: the {e} is now {B}", key=e, object=B)
        if cell == "revert":
            m.route(extra, policy="safe")
            hits = m.recall(e, k=6); ctx = "\n".join(h["text"] for h in hits)
            res.append(surface_verdict(ctx, A, B))          # revert: correct=A, retired=B
        else:  # echo: re-state the stale A, then read
            m.remember(extra, key=e, object=A)
            hits = m.recall(e, k=6); ctx = "\n".join(h["text"] for h in hits)
            res.append(surface_verdict(ctx, B, A))          # echo: correct=B, retired=A
    return res


# ── mem0 on Ollama ───────────────────────────────────────────────────────────
def run_mem0(cases, cell):
    import tempfile
    from mem0 import Memory
    # nomic-embed-text is 768-dim; mem0's default Qdrant collection is 1536 (OpenAI), so declare the dims AND
    # a fresh collection/path or the vectors won't fit the store.
    qpath = tempfile.mkdtemp(prefix="mem0_ollama_")
    cfg = {"llm": {"provider": "ollama", "config": {"model": GEN_MODEL, "ollama_base_url": OLLAMA}},
           "embedder": {"provider": "ollama",
                        "config": {"model": EMBED_MODEL, "ollama_base_url": OLLAMA, "embedding_dims": 768}},
           "vector_store": {"provider": "qdrant",
                            "config": {"collection_name": f"itg_{cell}", "embedding_model_dims": 768,
                                       "path": qpath, "on_disk": True}}}
    try:
        mem = Memory.from_config(cfg)
    except Exception as ex:
        print(f"    [mem0 init FAILED: {str(ex)[:140]}]", flush=True); return ["error"] * len(cases)
    res = []
    for i, (e, A, B, extra) in enumerate(cases):
        try:
            uid = f"o_{cell}_{i}"
            mem.add(f"the {e} is {A}", user_id=uid)
            mem.add(f"correction: the {e} is now {B}", user_id=uid)
            mem.add(extra, user_id=uid)
            ga = mem.get_all(filters={"user_id": uid}, top_k=30)
            mems = ga.get("results", ga) if isinstance(ga, dict) else ga
            ctx = "\n".join((x.get("memory") or x.get("text") or str(x)) for x in (mems or []))
            res.append(surface_verdict(ctx, A, B) if cell == "revert" else surface_verdict(ctx, B, A))
        except Exception as ex:
            print(f"    [mem0 case {i} error: {str(ex)[:90]}]", flush=True); res.append("error")
        if (i + 1) % 5 == 0:
            print(f"    mem0 {i+1}/{len(cases)}", flush=True)
    return res


# ── graphiti on Ollama (OpenAI-compatible client at the Ollama endpoint) ─────
def run_graphiti(cases, cell):
    import asyncio, datetime
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    from graphiti_core.llm_client.openai_client import OpenAIClient
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

    cfg = LLMConfig(api_key="ollama", model=GEN_MODEL, small_model=GEN_MODEL, base_url=OLLAMA + "/v1")
    llm = OpenAIClient(config=cfg)
    emb = OpenAIEmbedder(config=OpenAIEmbedderConfig(api_key="ollama", embedding_model=EMBED_MODEL,
                                                     base_url=OLLAMA + "/v1"))
    # graphiti's THIRD component: the reranker/cross-encoder also defaults to OpenAI — point it at Ollama too.
    rer = OpenAIRerankerClient(config=cfg)

    async def _run():
        g = Graphiti("bolt://localhost:7687", "neo4j", "testpassword123", llm_client=llm, embedder=emb,
                     cross_encoder=rer)
        out = []
        try:
            await g.build_indices_and_constraints()
            for i, (e, A, B, extra) in enumerate(cases):
                try:
                    gid = f"o{cell}_{i}_{datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S%f')}"
                    t0 = datetime.datetime(2026, 7, 22, 10, 0, 0, tzinfo=datetime.timezone.utc)
                    msgs = [f"the {e} is {A}", f"correction: the {e} is now {B}", extra]
                    for j, msg in enumerate(msgs):
                        await g.add_episode(name=f"m{j}", episode_body=msg, source_description="chat",
                                            reference_time=t0 + datetime.timedelta(minutes=j),
                                            source=EpisodeType.message, group_id=gid)
                    r = await g.search(f"what is the current {e}?", group_ids=[gid], num_results=10)
                    ctx = "\n".join(getattr(x, "fact", str(x)) for x in r)
                    out.append(surface_verdict(ctx, A, B) if cell == "revert" else surface_verdict(ctx, B, A))
                except Exception as ex:
                    print(f"    [graphiti case {i} error: {str(ex)[:90]}]", flush=True); out.append("error")
                if (i + 1) % 5 == 0:
                    print(f"    graphiti {i+1}/{len(cases)}", flush=True)
        finally:
            await g.close()
        return out
    return asyncio.run(_run())


# ── Letta on Ollama (agent memory blocks are the recall surface) ─────────────
def run_letta(cases, cell):
    from letta_client import Letta
    c = Letta(base_url="http://localhost:8283")
    res = []
    for i, (e, A, B, extra) in enumerate(cases):
        aid = None
        try:
            a = c.agents.create(
                memory_blocks=[{"label": "human", "value": ""},
                               {"label": "persona", "value": "You track facts the user states and update them on correction."}],
                model="ollama/qwen3:30b-a3b", embedding="ollama/nomic-embed-text:latest")
            aid = a.id
            for msg in [f"the {e} is {A}", f"correction: the {e} is now {B}", extra]:
                c.agents.messages.create(agent_id=aid, messages=[{"role": "user", "content": msg}])
            blocks = c.agents.blocks.list(agent_id=aid)
            ctx = "\n".join(f"{b.label}: {b.value}" for b in blocks if b.value)
            res.append(surface_verdict(ctx, A, B) if cell == "revert" else surface_verdict(ctx, B, A))
        except Exception as ex:
            print(f"    [letta case {i} error: {str(ex)[:100]}]", flush=True); res.append("error")
        finally:
            if aid:
                try: c.agents.delete(aid)
                except Exception: pass
        if (i + 1) % 5 == 0:
            print(f"    letta {i+1}/{len(cases)}", flush=True)
    return res


def score_surface(name, verdicts, n_cases):
    """Contradiction rate = fraction whose current-memory surface carries BOTH values (lower is better)."""
    con = sum(1 for v in verdicts if v == "contradictory")
    clean = sum(1 for v in verdicts if v == "clean")
    drop = sum(1 for v in verdicts if v == "dropped")
    err = sum(1 for v in verdicts if v == "error")
    n = n_cases - err; retained = con + clean
    among = con/retained if retained else 0.0     # integrity signal, retrieval failures excluded
    return {"system": name, "n": n, "retained": retained, "value": round(among, 3),
            "ci95": list(wilson(con, retained)), "among_retained_contradiction": round(among, 3),
            "drop_rate": round(drop/n, 3) if n else 0.0,
            "contradictory": con, "clean": clean, "dropped": drop, "errors": err}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", choices=["revert", "echo"], default="revert")
    ap.add_argument("--systems", default="inspeximus")
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args()
    want = [s.strip() for s in a.systems.split(",") if s.strip()]
    cases = []
    for i in range(min(a.n, len(ENTS))):
        e, A, B = ENTS[i]
        extra = (REVERTS[i % len(REVERTS)].format(e=e) if a.cell == "revert"
                 else ECHOES[i % len(ECHOES)].format(e=e, A=A))
        cases.append((e, A, B, extra))
    print(f"integrity cell={a.cell} · judge={JUDGE_MODEL} (Ollama) · n={len(cases)} · systems={want}\n", flush=True)
    runners = {"inspeximus": run_inspeximus, "mem0": run_mem0, "graphiti": run_graphiti, "letta": run_letta}
    scorer = score_surface
    out = {}
    for s in want:
        print(f"{s}...", flush=True)
        t = time.time()
        verdicts = runners[s](cases, a.cell)
        out[s] = scorer(s, verdicts, len(cases))
        print(json.dumps(out[s]), f"({time.time()-t:.0f}s)\n", flush=True)
    path = os.path.join(os.path.dirname(__file__), f"integrity_bench_ollama_{a.cell}_result.json")
    json.dump({"cell": a.cell, "judge": JUDGE_MODEL + " (Ollama, local)", "embedder": EMBED_MODEL,
               "n": len(cases), "results": out}, open(path, "w"), indent=2)
    print("wrote", path, flush=True)


if __name__ == "__main__":
    main()
