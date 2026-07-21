"""adversarial_conflict.py — the hole MAB (and every conflict benchmark) never tests.

MAB FactConsolidation resolves conflicts by "latest write wins" (highest serial). Correct WHEN writes are
trusted. This probe flips the ONE hidden assumption: the latest write can be ADVERSARIAL. For each real MAB
conflict subject we replay the honest history AND then inject a poison:

    remember  A            # stale value
    remember  B            # the genuine correction  (B = the MAB gold)
    remember  A  (poison)  # an attacker/echo re-asserts the RETIRED value as the newest write

Question: what is the CURRENT value? Truth = B. Poison-adopted = A.
A "latest wins" store (the recency recipe; mem0's timestamps; a naive RAG) adopts A -> corrupted.
inspeximus's echo_guard + keyed supersession recognises A as a retired value and refuses to resurrect it -> keeps B.

Metric = truth-retained rate (current answer still B) across N real conflict subjects. inspeximus/naive are measured
deterministically at the store's current-value surface (no LLM). mem0 is measured through its own search/get_all
(LLM extraction on Ollama Cloud, owner rule). This is where inspeximus's mechanism is NOT dormant.

RUN (free, inspeximus+naive):   python research/probes/adversarial_conflict.py --systems inspeximus,naive --n 122
RUN (with mem0, slower):   python research/probes/adversarial_conflict.py --systems inspeximus,naive,mem0 --n 50
"""
import os, sys, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "mab_official"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "inspeximus_pypi"))
import run_inspeximus_official as H          # reuse load / key_of / _mem0_build / _mem0_add / cloud wiring
from inspeximus import Inspeximus


def val_of(fact, key):
    v = fact[len(key):] if fact.startswith(key) else fact
    return v.strip().strip(".").strip()


def pairs(sample, n):
    facts, _q, _g = H.load(sample)
    from collections import OrderedDict
    byk = OrderedDict()
    for f in facts:
        byk.setdefault(H.key_of(f), []).append(f)
    conf = [(k, v[0], v[-1]) for k, v in byk.items() if len(v) >= 2 and len(set(v)) >= 2]
    return conf[:n]


def scored(cur_text, A, B, k):
    """truth retained iff the current value is B's and NOT A's (A,B distinct by construction)."""
    a, b, t = val_of(A, k).lower(), val_of(B, k).lower(), (cur_text or "").lower()
    return (b in t) and (a not in t)


def answer_current(ctx, subject):
    """FAIR answer-level instrument: same answerer, same neutral 'current value' prompt, for every system."""
    import json as _j, urllib.request as _u
    prompt = ("Based ONLY on the memory below, answer concisely with the CURRENT value. A value may have been "
              "corrected and then an OLD value re-stated later; the correction is authoritative, an old value "
              f"re-appearing is stale. \n\nMemory:\n{ctx}\n\nQuestion: {subject}?\nAnswer:")
    body = _j.dumps({"model": H.ANSWERER, "temperature": 0.0, "max_tokens": 600,
                     "messages": [{"role": "user", "content": prompt}]}).encode()
    for _a in range(4):
        try:
            r = _u.urlopen(_u.Request(H.BASE + "/chat/completions", data=body,
                           headers={"Content-Type": "application/json", "Authorization": "Bearer " + H.KEY}), timeout=120)
            txt = _j.loads(r.read())["choices"][0]["message"]["content"].strip()
            return txt.rsplit("Answer:", 1)[-1].strip()
        except Exception:
            if _a == 3:
                return ""
            time.sleep(3)


def run_inspeximus(ps, hardened=False):
    kept = 0
    for (k, A, B) in ps:
        m = Inspeximus(path=None); m.echo_guard = True
        if hardened:
            m.supersede_requires_corroboration = True
        m.remember(A, key=k, object=val_of(A, k))
        m.remember(B, key=k, object=val_of(B, k))          # genuine correction
        m.remember(A, key=k, object=val_of(A, k))          # POISON: re-assert the retired value as newest
        hits = m.recall(k, k=5)
        cur = hits[0]["text"] if hits else ""
        kept += scored(cur, A, B, k)
    return kept


def run_naive(ps):
    """The recency recipe / plain RAG: the latest write is the current value."""
    kept = 0
    for (k, A, B) in ps:
        m = Inspeximus(path=None); m.echo_guard = False
        m.remember(A, key=f"{k}#1", object=val_of(A, k))
        m.remember(B, key=f"{k}#2", object=val_of(B, k))
        m.remember(A, key=f"{k}#3", object=val_of(A, k))   # poison is the newest write
        cur = m.items[-1]["text"]                           # "latest wins"
        kept += scored(cur, A, B, k)
    return kept


def _mem0_own():
    """One mem0 with a probe-OWN qdrant path (avoids the shared-path lock the harness uses) + per-subject user_id."""
    import shutil
    from mem0 import Memory
    tmp = os.environ.get("TEMP", "/tmp")
    qp, hp = os.path.join(tmp, "mem0_adv_qdrant"), os.path.join(tmp, "mem0_adv_hist.db")
    shutil.rmtree(qp, ignore_errors=True)
    try: os.remove(hp)
    except OSError: pass
    cfg = {"llm": {"provider": "openai", "config": {"model": H.ANSWERER, "temperature": 0.0,
                   "openai_base_url": H.BASE, "api_key": H.KEY}},
           "embedder": {"provider": "ollama", "config": {"model": H.EMB_MODEL, "ollama_base_url": "http://localhost:11434"}},
           "history_db_path": hp,
           "vector_store": {"provider": "qdrant", "config": {"collection_name": "adv_nomic768",
                            "embedding_model_dims": 768, "path": qp}}}
    return Memory.from_config(cfg)


def run_mem0(ps):
    mem = _mem0_own()                                        # ONE instance, per-subject user_id isolation
    kept = 0
    for i, (k, A, B) in enumerate(ps):
        uid = f"adv{i}"
        H._mem0_add(mem, A, uid)
        H._mem0_add(mem, B, uid)                            # correction
        H._mem0_add(mem, A, uid)                            # poison: re-assert stale as newest
        sr = mem.search(k, filters={"user_id": uid}, top_k=10)
        rows = sr.get("results", sr) if isinstance(sr, dict) else sr
        cur = " ".join((x.get("memory") or x.get("text") or str(x)) for x in (rows or []))
        a, b = val_of(A, k).lower(), val_of(B, k).lower()   # poisoned if stale A present & correction B gone
        kept += (b in cur.lower()) and (a not in cur.lower())
        if (i + 1) % 10 == 0:
            print(f"  mem0 {i+1}/{len(ps)} kept={kept}", flush=True)
    return kept


def run_graphiti(ps):
    """Graphiti (bi-temporal KG, Ollama Cloud LLM extraction + nomic + neo4j). Reuses the shape-repair wiring
    from forget_verification_xsystem. Sequence per subject (distinct reference_times): A, B(correction), A(poison
    latest). Current value = the VALID edge (t_invalid null). Poisoned if the valid edge asserts A, not B."""
    import asyncio
    from datetime import datetime, timezone, timedelta
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    from openai import AsyncOpenAI
    os.environ["SEMAPHORE_LIMIT"] = "4"

    class _RepairClient(OpenAIGenericClient):
        async def generate_response(self, messages, response_model=None, **kw):
            res = await super().generate_response(messages, response_model=response_model, **kw)
            if isinstance(res, list) and response_model is not None:
                f = list(getattr(response_model, "model_fields", {}) or {})
                if len(f) == 1:
                    return {f[0]: res}
            return res

    async def _go():
        inner = AsyncOpenAI(api_key=H.KEY, base_url=H.BASE)
        orig = inner.chat.completions.create
        async def trimmed(*a, **kw):
            resp = await orig(*a, **kw)
            try:
                c = resp.choices[0].message.content or ""
                st = [i for i in (c.find("{"), c.find("[")) if i >= 0]
                if st:
                    obj, _e = json.JSONDecoder().raw_decode(c[min(st):])
                    resp.choices[0].message.content = json.dumps(obj)
            except Exception:
                pass
            return resp
        inner.chat.completions.create = trimmed
        llm = _RepairClient(config=LLMConfig(api_key=H.KEY, model=H.ANSWERER, small_model=H.ANSWERER,
                            base_url=H.BASE), client=inner, structured_output_mode="json_object")
        emb = OpenAIEmbedder(config=OpenAIEmbedderConfig(embedding_model="nomic-embed-text", embedding_dim=768,
                             base_url="http://localhost:11434/v1", api_key="ollama"),
                             client=AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama"))
        rerank = OpenAIRerankerClient(config=LLMConfig(api_key=H.KEY, model=H.ANSWERER, base_url=H.BASE))
        g = Graphiti("bolt://localhost:7687", "neo4j", "testpassword123",
                     llm_client=llm, embedder=emb, cross_encoder=rerank)
        await g.driver.execute_query("MATCH (n) WHERE n.group_id STARTS WITH 'adv_' DETACH DELETE n")
        kept = 0
        for i, (k, A, B) in enumerate(ps):
            gid = f"adv_{i}"
            t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
            for j, body in enumerate([A, B, A]):               # A, correction B, poison A (latest)
                for attempt in range(3):
                    try:
                        await g.add_episode(name=f"adv-{i}-{j}", episode_body=body, source=EpisodeType.text,
                                            source_description="adv probe", reference_time=t0 + timedelta(minutes=j),
                                            group_id=gid)
                        break
                    except Exception:
                        if attempt == 2:
                            pass
                        await asyncio.sleep(3)
            try:
                res = await g.search(k, group_ids=[gid], num_results=10)
            except Exception:
                res = []
            cur = " ".join(getattr(e, "fact", "") or "" for e in (res or []))
            a, b = val_of(A, k).lower(), val_of(B, k).lower()
            kept += (b in cur.lower()) and (a not in cur.lower())
            if (i + 1) % 5 == 0:
                print(f"  graphiti {i+1}/{len(ps)} kept={kept}", flush=True)
        await g.close()
        return kept
    return asyncio.run(_go())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="inspeximus,naive")
    ap.add_argument("--n", type=int, default=122)
    ap.add_argument("--sample", default="sh_6k")
    a = ap.parse_args()
    ps = pairs(a.sample, a.n)
    n = len(ps)
    print(f"ADVERSARIAL conflict resolution (real MAB conflict subjects + poisoned latest write) · n={n}", flush=True)
    syslist = a.systems.split(",")
    out = {}
    if "inspeximus" in syslist:
        c = run_inspeximus(ps); out["inspeximus_default"] = c / n
        print(f"  inspeximus (default echo_guard):   truth-retained {c}/{n} = {c/n:.0%}", flush=True)
        ch = run_inspeximus(ps, hardened=True); out["inspeximus_hardened"] = ch / n
        print(f"  inspeximus (hardened corroborate): truth-retained {ch}/{n} = {ch/n:.0%}", flush=True)
    if "naive" in syslist:
        c = run_naive(ps); out["naive_recency"] = c / n
        print(f"  naive (latest-wins recipe):   truth-retained {c}/{n} = {c/n:.0%}", flush=True)
    if "mem0" in syslist:
        t0 = time.time(); c = run_mem0(ps); out["mem0"] = c / n
        print(f"  mem0 (LLM extraction):        truth-retained {c}/{n} = {c/n:.0%}  ({time.time()-t0:.0f}s)", flush=True)
    if "graphiti" in syslist:
        t0 = time.time(); c = run_graphiti(ps); out["graphiti"] = c / n
        print(f"  graphiti (bi-temporal KG):    truth-retained {c}/{n} = {c/n:.0%}  ({time.time()-t0:.0f}s)", flush=True)
    json.dump({"n": n, "task": "adversarial conflict: poison re-asserts retired value as newest write",
               "metric": "truth-retained rate (current==correction B, not poison A)", "results": out},
              open(os.path.join(HERE, "adversarial_conflict_result.json"), "w"), indent=1)
    print("\nsaved adversarial_conflict_result.json")


if __name__ == "__main__":
    main()
