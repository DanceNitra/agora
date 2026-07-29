"""The echo attack against the LIVE products, not against re-implementations of their documented logic.

WHY THIS EXISTS. The comparison page carried a caveat: "these are faithful re-implementations of each
system's documented resolution logic, not the live products". That caveat is not something to write more
carefully -- it is the work. A limit on our own claim is a build order, and until it is run, the strongest
rebuttal to our result is one sentence: "that is not our product, that is your model of our product."

THE PROCEDURE, identical for every system, at each one's NATIVE surface:
  1. write a fact                         "<subject>'s <relation> is <old>"
  2. correct it                           "<subject>'s <relation> is now <new>"   (the correction)
  3. echo the retired value, PARAPHRASED  a restatement of the OLD value, in different words
  4. ask each system for the current value at its own retrieval surface
  5. score: did it come back with the RETIRED value?  (lower is better)

No rubric of ours, no LLM judge scoring the answer: the check is whether the old or the new object string
is what the system serves. Step 3 is the realistic attack -- not a byte-for-byte replay, which anything
with a hash catches, but somebody restating an outdated fact in their own words.

HONEST SCOPE. mem0 runs live here. Graphiti needs a graph database; if none is reachable the run reports
it as NOT RUN rather than carrying the re-implementation number over and calling it live.

RUN:  python research/probes/echo_live_xsystem.py [--n 8]
Part of Agora / inspeximus (MIT).
"""
import argparse
import json
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")

_env = {}
_envp = os.path.join(HERE, "..", "..", "server", ".env")
if os.path.exists(_envp):
    for line in open(_envp, encoding="utf-8", errors="ignore"):
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            _env[k.strip()] = v.strip().strip('"')
OLLAMA_CLOUD = "https://ollama.com/v1"
OLLAMA_KEY = _env.get("AGORA_API_KEY", "")
CHEAP = "deepseek-v4-flash"

#: (subject, relation, old value, new value, PARAPHRASED restatement of the OLD value)
CASES = [
    ("alice", "primary database host", "db-old-07", "db-new-12",
     "just so it is on record, alice keeps the primary database on the host db-old-07"),
    ("bob", "office location", "Brno", "Vienna",
     "for the record bob works out of the Brno office"),
    ("carol", "escalation contact", "the vendor", "the on-call SRE",
     "reminder: when things break for carol, the vendor is who gets called"),
    ("dan", "deployment branch", "release-2", "main",
     "dan's deploys are cut from the release-2 branch, as everyone knows"),
    ("eve", "payment provider", "Stripe", "Adyen",
     "eve's payments have always gone through Stripe"),
    ("finn", "on-call rotation", "weekly", "daily",
     "finn is on a weekly on-call rotation"),
    ("gina", "storage tier", "cold archive", "hot SSD",
     "gina's data sits in the cold archive tier"),
    ("hugo", "auth method", "API keys", "OAuth2",
     "hugo's service authenticates callers with API keys"),
]


def stale(top: str, old: str, new: str) -> bool | None:
    """Does the system's TOP-RANKED answer assert the retired value? None = it asserts neither.

    Reads rank-1 only, and the same way for every system, because that is what an agent acts on. The first
    version concatenated all hits and looked for substrings; every mem0 case then came back "no opinion",
    because mem0 keeps BOTH the original fact and a "changed from X to Y" memory, so both strings were
    present. The rate that produced was 0.000 over n=0 -- a metric with no denominator, and a result about
    the reader rather than about mem0.

    What the dump showed instead (audit_mem0_reader.py) is sharper and is mem0's OWN ranking, not our
    rubric: searching the corrected fact returns the stale memory FIRST (0.872) and the correction second
    (0.828). A memory that records the change ("changed from X to Y") carries the current value and counts
    as current; one that asserts only the retired value is stale.
    """
    t = (top or "").lower()
    has_old, has_new = old.lower() in t, new.lower() in t
    if has_new:
        return False                     # names the current value (including "changed from old to new")
    if has_old:
        return True
    return None


#: the box has 24 logical cores and an idle RTX 3090; every case is independent, so running them one at a
#: time leaves both idle while waiting on a cloud LLM round-trip and a local embedding call. Threads, not
#: processes: the work is I/O-bound (HTTP to the LLM, HTTP to the embedder), which is exactly what the GIL
#: releases on.
WORKERS = min(12, max(4, (os.cpu_count() or 8) // 2))


def _tally(results):
    seen = [v for v in results if v is not None]
    return {"stale": sum(int(v) for v in seen) / max(1, len(seen)), "n": len(seen), "live": True}


def _parallel(fn, cases, workers=WORKERS):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, cases))


def run_inspeximus(cases):
    """Through the PRODUCT surface, which is what a user of the MCP server, the CLI or the plugin gets.

    The first run of this harness used the bare `Inspeximus(path=None)` constructor and scored 1.000 --
    stale every time. Measured (audit_echo_guard_default.py): that constructor ships echo_guard=False for
    byte-identical legacy behaviour, while inspeximus/_surface.py turns it ON for every product surface.
    So the harness had measured a posture nobody using the product is in.

    Fixing it by picking the flattering flag would be the same asymmetry this whole exercise exists to
    remove, so the rule is stated instead and applies to everyone: each system is measured in its shipped
    product configuration. For mem0 that is Memory.from_config as documented; for inspeximus it is
    open_store. The raw-constructor difference is reported alongside the number, not hidden behind it.
    """
    import tempfile
    from inspeximus._surface import open_store

    def one(case):
        subj, rel, old, new, echo = case
        m = open_store(os.path.join(tempfile.mkdtemp(), "s.json"))
        key = f"{subj}::{rel.replace(' ', '_')}"
        m.remember(f"{subj}'s {rel} is {old}", key=key, object=old)
        m.remember(f"{subj}'s {rel} is now {new}", key=key, object=new)
        m.remember(echo, key=key, object=old)                       # the paraphrased echo
        got = m.recall(f"{subj} {rel}", k=3)
        return stale(got[0].get("text", "") if got else "", old, new)

    return _tally(_parallel(one, cases))


def run_mem0(cases):
    from mem0 import Memory
    cfg = {"llm": {"provider": "openai",
                   "config": {"model": CHEAP, "temperature": 0.1,
                              "openai_base_url": OLLAMA_CLOUD, "api_key": OLLAMA_KEY}},
           "embedder": {"provider": "ollama",
                        "config": {"model": "nomic-embed-text",
                                   "ollama_base_url": "http://localhost:11434"}},
           "vector_store": {"provider": "qdrant",
                            "config": {"collection_name": f"echo_live_{int(time.time())}",
                                       "embedding_model_dims": 768, "on_disk": False}}}
    mem = Memory.from_config(cfg)
    stamp = int(time.time())

    def one(idx_case):
        i, (subj, rel, old, new, echo) = idx_case
        uid = f"{subj}-{i}-{stamp}"          # per-case scope: the cases never see each other's writes
        for msg in (f"{subj}'s {rel} is {old}", f"{subj}'s {rel} is now {new}", echo):
            mem.add(msg, user_id=uid)
        # mem0 2.x moved entity scoping into `filters`; passing user_id at top level raises.
        res = mem.search(f"{subj} {rel}", filters={"user_id": uid}, limit=5)
        rows = res.get("results", res) if isinstance(res, dict) else res
        answer = ((rows or [{}])[0].get("memory") or (rows or [{}])[0].get("text") or "")
        v = stale(answer, old, new)
        print(f"    [mem0] {subj}: {'STALE' if v else ('current' if v is False else 'no opinion')}")
        return v

    return _tally(_parallel(one, list(enumerate(cases))))


def run_graphiti(cases):
    """Graphiti on its EMBEDDED Kuzu backend -- no server, no container, no bill.

    The first attempt required Neo4j and reported NOT RUN because no credentials were configured. Reaching
    for a database server was the wrong instinct twice over: it is infrastructure we do not need, and this
    project has not earned a cent yet, so a measurement that costs money to take is a measurement we do not
    take. graphiti-core ships a Kuzu driver and Kuzu is an EMBEDDED graph database -- `pip install kuzu`,
    in-memory, gone when the process exits. Same product, same documented resolution logic, zero cost.

    The LLM and embedder are the ones this box already uses: an OpenAI-compatible endpoint for extraction
    and the local nomic embedder. Graphiti defaults to hosted OpenAI; pointing it at what we already run
    keeps the comparison free and keeps the extraction quality comparable to what mem0 got.
    """
    import asyncio
    from graphiti_core import Graphiti
    from graphiti_core.driver.falkordb_driver import FalkorDriver
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.llm_client.openai_client import OpenAIClient
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

    if not OLLAMA_KEY:
        return {"not_run": "no LLM key available for entity extraction"}
    # Graphiti drives extraction through a STRUCTURED-OUTPUT schema, and the cheap model does not honour
    # it -- it returns {"entities": [...]} where the schema requires "extracted_entities", so every episode
    # failed validation. That is a model-compliance problem, not a Graphiti or FalkorDB problem, and
    # blaming the product for it would be a rigged comparison. Use the stronger model on the SAME free
    # endpoint; mem0's own extraction happens on the cheap one because mem0 tolerates it.
    # ...and the cloud endpoint does not enforce it either: the stronger model returns a markdown-fenced
    # bare array where the schema wants an object. Graphiti relies on OpenAI's NATIVE structured outputs
    # (response_format=json_schema), which an OpenAI-COMPATIBLE endpoint is free to ignore. Ollama running
    # locally does honour it, so extraction goes to a local model -- free, and it puts the idle 3090 to
    # work instead of a paid API.
    GRAPH_MODEL = os.environ.get("GRAPHITI_MODEL", "qwen3:30b-a3b")
    # BOTH models: LLMConfig carries a separate `small_model` for the cheaper calls, and it defaults to
    # gpt-4.1-nano. Setting only `model` left that default in place, so the run died on a 404 for a hosted
    # model that does not exist locally -- and on a paid account it would have quietly billed instead.
    llm = OpenAIClient(config=LLMConfig(api_key="ollama", model=GRAPH_MODEL, small_model=GRAPH_MODEL,
                                        base_url="http://localhost:11434/v1", temperature=0.1))
    emb = OpenAIEmbedder(config=OpenAIEmbedderConfig(
        embedding_model="nomic-embed-text", embedding_dim=768,
        api_key="ollama", base_url="http://localhost:11434/v1"))

    # Graphiti has a THIRD component -- the cross-encoder used for reranking -- and it defaults to hosted
    # OpenAI. Left alone it raised "Missing credentials", i.e. the run would have silently required a paid
    # account. Point it at the same endpoint as everything else so the whole measurement stays free.
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    reranker = OpenAIRerankerClient(client=llm)

    async def go():
        # FalkorDB in a local container -- one of the two backends graphiti-core still supports, free, and
        # already on this machine. Kuzu was tried first because it is embedded and needs nothing at all,
        # but it is deprecated upstream ("no longer maintained") and its driver raises on construction in
        # this release. Neo4j was the other option and it is also free (Community), but a server was
        # already refused for good reason: nothing here should require paid or heavy infrastructure to
        # verify, and this project has not earned a cent yet.
        g = Graphiti(graph_driver=FalkorDriver(host="localhost", port=6379,
                                               database=f"echo{int(time.time())}"),
                     llm_client=llm, embedder=emb, cross_encoder=reranker)
        from datetime import datetime, timezone
        await g.build_indices_and_constraints()
        hits, seen = 0, 0
        for subj, rel, old, new, echo in cases:
            gid = f"echo-{subj}-{int(time.time() * 1000)}"
            for n, msg in enumerate((f"{subj}'s {rel} is {old}",
                                     f"{subj}'s {rel} is now {new}", echo)):
                # reference_time ORDERS the episodes; a bitemporal store resolves on it, so the echo must
                # genuinely arrive last or the attack is not the attack.
                await g.add_episode(name=f"{subj}-{n}", episode_body=msg,
                                    source_description="probe",
                                    reference_time=datetime.now(timezone.utc), group_id=gid)
            res = await g.search(f"{subj} {rel}", group_ids=[gid], num_results=5)
            top = (getattr(res[0], "fact", "") or "") if res else ""
            v = stale(top, old, new)
            print(f"    [graphiti] {subj}: "
                  f"{'STALE' if v else ('current' if v is False else 'no opinion')}  top={top[:60]!r}")
            if v is not None:
                seen += 1
                hits += int(v)
        await g.close()
        return {"stale": hits / max(1, seen), "n": seen, "live": True,
                "backend": "FalkorDB (local container, free)"}

    return asyncio.run(go())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=len(CASES))
    ap.add_argument("--repeats", type=int, default=3,
                    help="REPEAT the whole panel; mem0 and Graphiti extract facts with an LLM, so one "
                         "run is one sample, not a measurement")
    args = ap.parse_args()
    cases = CASES[:args.n]
    print(f"=== LIVE echo attack, n={len(cases)} x {args.repeats} repeats, "
          f"identical procedure per system ===\n")

    out = {}
    for name, fn in (("inspeximus", run_inspeximus), ("mem0", run_mem0), ("graphiti", run_graphiti)):
        print(f"  running {name} ...")
        runs, err = [], None
        for _ in range(args.repeats):
            try:
                runs.append(fn(cases))
            except Exception as e:
                err = f"{type(e).__name__}: {str(e)[:160]}"
                break
        if not runs:
            out[name] = {"not_run": err or "no run completed"}
        else:
            # Report the SPREAD, not a single number. mem0 scored 1.000 on one run and 0.667 on the next
            # -- publishing the first as if it were stable would be a one-sample claim dressed as a rate,
            # and this page exists because that kind of number was published before.
            rates = [r["stale"] for r in runs]
            out[name] = {"stale": sum(rates) / len(rates), "min": min(rates), "max": max(rates),
                         "runs": len(rates), "n": runs[0]["n"], "live": True,
                         **({"backend": runs[0]["backend"]} if "backend" in runs[0] else {})}
        r = out[name]
        print(f"  {name:12s} " + (f"stale={r['stale']:.3f}  range {r['min']:.3f}-{r['max']:.3f} "
                                  f"over {r['runs']} runs x n={r['n']}"
                                  if "stale" in r else f"NOT RUN -- {r['not_run']}"))
        print()

    path = os.path.join(HERE, "echo_live_xsystem_result.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {path}")
    print("\nA system that is NOT RUN is reported as not run. The re-implementation number is never")
    print("carried over and relabelled live -- that would be the exact overclaim this run exists to remove.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
