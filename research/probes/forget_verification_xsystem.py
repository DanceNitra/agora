"""forget_verification_xsystem.py — after each system's NATIVE erasure, from HOW MANY of its native surfaces
is the subject's value still recoverable? (Observatory cell: fills the audit report's admitted gap where
forget-verification was a mnemo-only baseline.)

Symmetric, deterministic instrument (no LLM judge): for every system, issue its documented native deletion,
then adversarially attempt recovery of the secret VALUE (verbatim, case-insensitive) from each native surface
the system exposes:

  S1 query        the native retrieval call (recall / search)
  S2 enumerate    the native list-everything call (items / get_all / graph search)
  S3 history      the native history/audit surface (mnemo ledger+receipts / mem0 history DB / graphiti episodes)
  S4 raw storage  the persistence layer itself (mnemo JSON files / Qdrant payloads / neo4j properties)

FORGET-VERIFICATION SCORE per system = fraction of (subject x surface) cells with NO residue (higher = better).
Per-surface breakdown is the point: WHERE erasure stops is the finding, not who "wins". mnemo is graded on the
same four surfaces including its own receipts/ledger files; if the value survives there, that is reported.
Graphiti is bitemporal BY DESIGN (retains invalidated facts); a residue there is a documented trade-off, not a
bug — we measure it rather than assert it.

Honest-harness rule: a competitor's number is reported ONLY from a clean run (0 SDK errors); any per-surface
probe error marks the cell UNMEASURED (None), never a pass or fail.

RUN:  python research/probes/forget_verification_xsystem.py               # mnemo + mem0
      python research/probes/forget_verification_xsystem.py --graphiti    # + graphiti (needs neo4j up)
Part of Agora / mnemo (MIT).
"""
import os
import sys
import json
import tempfile
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus  # noqa: E402

_env = {}
for line in open(os.path.join(os.path.dirname(__file__), "..", "..", "server", ".env"),
                 encoding="utf-8", errors="ignore"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1); _env[k.strip()] = v.strip().strip('"')
OLLAMA_CLOUD = "https://ollama.com/v1"
OLLAMA_KEY = _env.get("AGORA_API_KEY", "")
CHEAP_MODEL = "deepseek-v4-flash"
# GATE re-verify on live gpt-4o (owner 2026-07-18): FVX_MODEL=gpt-4o points mem0/graphiti LLM at OpenAI.
if os.environ.get("FVX_MODEL", "").startswith("gpt"):
    CHEAP_MODEL = os.environ["FVX_MODEL"]
    OLLAMA_CLOUD = "https://api.openai.com/v1"
    OLLAMA_KEY = _env.get("OPENAI_API_KEY", "")

SURFACES = ["query", "enumerate", "history", "raw_storage"]

SUBJECTS = [
    ("alice-42", "Alice", "medical condition", "type-1 diabetes"),
    ("bob-77", "Bob", "home address", "12 Maple Street"),
    ("carol-19", "Carol", "salary", "94000 euro"),
    ("dan-53", "Dan", "religion", "practising Buddhist"),
    ("eve-88", "Eve", "criminal record", "2019 fraud conviction"),
    ("finn-31", "Finn", "orientation", "gay"),
    ("gina-64", "Gina", "biometric id", "fingerprint 9f2a"),
    ("hugo-27", "Hugo", "affiliation", "Green Party member"),
]


def _hit(val, blob):
    return val.lower() in (blob or "").lower()


# ---------------------------------------------------------------- mnemo
def score_mnemo():
    fd, p = tempfile.mkstemp(suffix=".json", prefix="fvx_"); os.close(fd)
    for suf in ("", ".receipts.json"):
        try: os.remove(p + suf)
        except OSError: pass
    m = Inspeximus(path=p)
    per = {s: [] for s in SURFACES}
    for (subj, name, rel, val) in SUBJECTS:
        m.remember(f"{name}'s {rel} is {val}.", key=f"{subj}::{rel}", object=val, source={"doc": subj})
        m.forget_subject(subj, request_id=f"dsar-{subj}")
        m._save()

        hits = m.recall(f"what is the {rel} of {name}?", k=6, mode="lexical")
        per["query"].append(_hit(val, " ".join(h.get("text", "") or "" for h in hits)))

        per["enumerate"].append(_hit(val, " ".join((it.get("text", "") or "") + " " + str(it.get("object", ""))
                                                   for it in m.items)))

        hist_blob = json.dumps(getattr(m, "ledger", [])) + json.dumps(
            [h for it in m.items for h in (it.get("history") or [])])
        per["history"].append(_hit(val, hist_blob))

        raw = ""
        for suf in ("", ".receipts.json"):
            try: raw += open(p + suf, encoding="utf-8", errors="ignore").read()
            except OSError: pass
        per["raw_storage"].append(_hit(val, raw))
    for suf in ("", ".receipts.json"):
        try: os.remove(p + suf)
        except OSError: pass
    return per


# ---------------------------------------------------------------- mem0
def score_mem0():
    from mem0 import Memory
    qpath = os.path.join(os.environ.get("TEMP", "/tmp"), "mem0_fvx_qdrant")
    hpath = os.path.join(os.environ.get("TEMP", "/tmp"), "mem0_fvx_history.db")
    import shutil
    shutil.rmtree(qpath, ignore_errors=True)
    try: os.remove(hpath)
    except OSError: pass
    cfg = {"llm": {"provider": "openai", "config": {"model": CHEAP_MODEL, "temperature": 0.1,
                   "openai_base_url": OLLAMA_CLOUD, "api_key": OLLAMA_KEY}},
           "embedder": {"provider": "ollama", "config": {"model": "nomic-embed-text",
                        "ollama_base_url": "http://localhost:11434"}},
           "history_db_path": hpath,
           "vector_store": {"provider": "qdrant", "config": {"collection_name": "fvx_nomic768",
                            "embedding_model_dims": 768, "path": qpath}}}
    mem = Memory.from_config(cfg)
    per = {s: [] for s in SURFACES}
    for (subj, name, rel, val) in SUBJECTS:
        uid = f"fvx_{subj}"
        mem.add(f"{name}'s {rel} is {val}.", user_id=uid)
        allm = mem.get_all(filters={"user_id": uid})
        rows = allm.get("results", allm) if isinstance(allm, dict) else allm
        ids = [r["id"] for r in (rows or [])]
        for rid in ids:
            mem.delete(rid)                          # documented native erasure

        sr = mem.search(f"what is the {rel} of {name}?", filters={"user_id": uid}, top_k=6)
        mems = sr.get("results", sr) if isinstance(sr, dict) else sr
        per["query"].append(_hit(val, " ".join((x.get("memory") or x.get("text") or str(x))
                                               for x in (mems or []))))

        allm2 = mem.get_all(filters={"user_id": uid})
        rows2 = allm2.get("results", allm2) if isinstance(allm2, dict) else allm2
        per["enumerate"].append(_hit(val, " ".join((x.get("memory") or str(x)) for x in (rows2 or []))))

        hist_blob = ""
        for rid in ids:
            try: hist_blob += json.dumps(mem.history(rid))
            except Exception: pass
        # the history DB file itself is part of the native history surface
        try: hist_blob += open(hpath, "rb").read().decode("utf-8", errors="ignore")
        except OSError: pass
        per["history"].append(_hit(val, hist_blob))

        raw = ""
        for root, _dirs, files in os.walk(qpath):
            for f in files:
                try: raw += open(os.path.join(root, f), "rb").read().decode("utf-8", errors="ignore")
                except OSError: pass
        per["raw_storage"].append(_hit(val, raw))
    return per


# ---------------------------------------------------------------- graphiti
async def _score_graphiti_async():
    # Ollama Cloud LLM (structured-output capable) + local nomic embedder + RRF search (no LLM
    # reranker). The erasure surfaces themselves are deterministic neo4j reads; the LLM only does
    # ingestion extraction. Config disclosed in the report.
    os.environ["SEMAPHORE_LIMIT"] = "4"
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    from datetime import datetime, timezone
    from openai import AsyncOpenAI

    # ollama.com's OpenAI-compat layer does not ENFORCE response_format json_schema (measured: all
    # models return free text/JSON). The client's own documented fallback for such providers is
    # structured_output_mode='json_object' (schema injected into the prompt). On top of that, repair
    # the one common shape slip deterministically: a bare LIST where the response model wraps a
    # single array field (shape repair, never content fabrication).
    class _RepairClient(OpenAIGenericClient):
        async def generate_response(self, messages, response_model=None, **kw):
            res = await super().generate_response(messages, response_model=response_model, **kw)
            if isinstance(res, list) and response_model is not None:
                fields = list(getattr(response_model, "model_fields", {}) or {})
                if len(fields) == 1:
                    return {fields[0]: res}
            return res

    # thinking models append prose AFTER the JSON ("Extra data" parse error): trim the content to
    # the first complete JSON value before graphiti parses it.
    _inner = AsyncOpenAI(api_key=OLLAMA_KEY, base_url=OLLAMA_CLOUD)
    _orig_create = _inner.chat.completions.create

    async def _trimmed_create(*a, **kw):
        resp = await _orig_create(*a, **kw)
        try:
            content = resp.choices[0].message.content or ""
            starts = [i for i in (content.find("{"), content.find("[")) if i >= 0]
            if starts:
                obj, _end = json.JSONDecoder().raw_decode(content[min(starts):])
                resp.choices[0].message.content = json.dumps(obj)
        except Exception:
            pass                                   # leave content as-is; graphiti's retry handles it
        return resp

    _inner.chat.completions.create = _trimmed_create
    # deepseek-v4-flash: its one JSON slip (a bare list) is exactly what _RepairClient fixes;
    # glm-5.2 in json_object mode instead echoes the schema itself (unrepairable without guessing).
    llm = _RepairClient(config=LLMConfig(api_key=OLLAMA_KEY, model=CHEAP_MODEL,
                                         small_model=CHEAP_MODEL, base_url=OLLAMA_CLOUD),
                        client=_inner, structured_output_mode="json_object")
    emb = OpenAIEmbedder(config=OpenAIEmbedderConfig(embedding_model="nomic-embed-text",
                                                     embedding_dim=768,
                                                     base_url="http://localhost:11434/v1",
                                                     api_key="ollama"),
                         client=AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama"))
    # the default cross_encoder builds its own OpenAI client at CONSTRUCTION time and demands
    # OPENAI_API_KEY; point it at Ollama Cloud too (RRF search below never actually invokes it).
    rerank = OpenAIRerankerClient(config=LLMConfig(api_key=OLLAMA_KEY, model=CHEAP_MODEL,
                                                   base_url=OLLAMA_CLOUD))
    g = Graphiti("bolt://localhost:7687", "neo4j", "testpassword123",
                 llm_client=llm, embedder=emb, cross_encoder=rerank)
    _RRF = EDGE_HYBRID_SEARCH_RRF
    per = {s: [] for s in SURFACES}
    import asyncio as _aio
    try:
        # clean slate: purge leftovers from any prior run so neither the positive control nor the
        # residue check can hit stale fvx_* data
        await g.driver.execute_query("MATCH (n) WHERE n.group_id STARTS WITH 'fvx_' DETACH DELETE n")
        for (subj, name, rel, val) in SUBJECTS:
            ep = None
            for attempt in range(3):                  # OpenAI rate-limit pacing (killed a prior n=50 run)
                try:
                    ep = await g.add_episode(name=f"fvx-{subj}", episode_body=f"{name}'s {rel} is {val}.",
                                             source=EpisodeType.text, source_description="fvx probe",
                                             reference_time=datetime.now(timezone.utc),
                                             group_id=f"fvx_{subj}")
                    break
                except Exception as e:
                    if "rate limit" not in str(e).lower() or attempt == 2:
                        raise
                    await _aio.sleep(45 * (attempt + 1))
            # POSITIVE CONTROL (honest harness): the value must be recoverable BEFORE the delete,
            # or this subject proves nothing (ingestion may have extracted nothing).
            pre, _, _ = await g.driver.execute_query(
                "MATCH (n) WHERE n.group_id = $gid "
                "OPTIONAL MATCH (n)-[r]-() RETURN properties(n) AS np, properties(r) AS rp",
                gid=f"fvx_{subj}")
            pre_blob = json.dumps([{"np": dict(r["np"] or {}), "rp": dict(r["rp"] or {})} for r in pre],
                                  default=str)
            if not _hit(val, pre_blob):
                per.setdefault("ingest_failed", []).append(subj)
                continue                              # do NOT count a vacuously-clean subject

            await g.remove_episode(ep.episode.uuid)   # documented native erasure
            await _aio.sleep(3)                       # pace between subjects

            sr = await g.search_(f"what is the {rel} of {name}?", config=_RRF,
                                 group_ids=[f"fvx_{subj}"])
            edges = getattr(sr, "edges", []) or []
            per["query"].append(_hit(val, " ".join(getattr(e, "fact", "") or "" for e in edges)))

            recs, _, _ = await g.driver.execute_query(
                "MATCH (n) WHERE n.group_id = $gid RETURN n", gid=f"fvx_{subj}")
            per["enumerate"].append(_hit(val, json.dumps([dict(r["n"]) for r in recs], default=str)))

            recs2, _, _ = await g.driver.execute_query(
                "MATCH (e:Episodic) WHERE e.group_id = $gid RETURN e.content AS c", gid=f"fvx_{subj}")
            per["history"].append(_hit(val, " ".join(str(r["c"]) for r in recs2)))

            recs3, _, _ = await g.driver.execute_query(
                "MATCH (n) WHERE n.group_id = $gid "
                "OPTIONAL MATCH (n)-[r]-() RETURN properties(n) AS np, properties(r) AS rp", gid=f"fvx_{subj}")
            blob = json.dumps([{"np": dict(r["np"] or {}), "rp": dict(r["rp"] or {})} for r in recs3], default=str)
            per["raw_storage"].append(_hit(val, blob))
    finally:
        await g.close()
    return per


def score_graphiti():
    import asyncio
    return asyncio.run(_score_graphiti_async())


# ---------------------------------------------------------------- report
def summarize(name, per):
    n = len(SUBJECTS)
    failed = per.get("ingest_failed", [])
    n_eff = n - len(failed)                     # honest denominator: subjects with a POSITIVE control
    total_cells = clean_cells = 0
    print(f"\n{name}")
    if failed:
        print(f"  ingestion positive-control FAILED for {len(failed)}/{n}: {failed} (excluded, not counted clean)")
    for s in SURFACES:
        hits = per[s]
        if n_eff == 0 or len(hits) != n_eff:
            print(f"  {s:<12} UNMEASURED"); continue
        k = sum(1 for h in hits if h)
        total_cells += n_eff; clean_cells += (n_eff - k)
        print(f"  {s:<12} residue {k}/{n_eff}" + ("   <-- leaks here" if k else ""))
    score = clean_cells / total_cells if total_cells else None
    print(f"  forget-verification score = {score:.3f}  (n={n_eff})" if score is not None else "  score: n/a")
    return {"per_surface": {s: (sum(per[s]) if n_eff and len(per[s]) == n_eff else None) for s in SURFACES},
            "n": n_eff, "ingest_failed": failed, "score": score}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--graphiti", action="store_true")
    ap.add_argument("--only", type=str, default=None, choices=["mnemo", "mem0", "graphiti"])
    args = ap.parse_args()
    rpath = os.path.join(os.path.dirname(__file__), "forget_verification_xsystem_result.json")
    out = json.load(open(rpath)) if (args.only and os.path.exists(rpath)) else {}
    print("=== CROSS-SYSTEM FORGET-VERIFICATION (native delete -> recovery attempt per native surface) ===")
    print(f"surfaces: {SURFACES}; residue = secret value verbatim-recoverable; deterministic, judge-free.")

    if args.only in (None, "mnemo"):
        out["mnemo"] = summarize("mnemo " + __import__("mnemo").__version__, score_mnemo())
    if args.only in (None, "mem0"):
        try:
            out["mem0"] = summarize("mem0 2.0.11", score_mem0())
        except Exception as e:
            print("\nmem0 FAILED (excluded, honest):", str(e)[:200])
    if args.graphiti or args.only == "graphiti":
        try:
            out["graphiti"] = summarize("graphiti (neo4j, bitemporal by design)", score_graphiti())
        except Exception as e:
            print("\ngraphiti FAILED (excluded, honest):", str(e)[:200])

    json.dump(out, open(rpath, "w"), indent=1)
    print("\nNOTE: the finding is the per-surface breakdown (WHERE erasure stops), not a ranking. Graphiti's")
    print("episode/edge retention is bitemporal design, a documented trade-off. mnemo is graded on the same")
    print("four surfaces including its own ledger/receipts files.")


if __name__ == "__main__":
    main()
