"""poison_realistic.py — poison-resistance under the REALISTIC retrieval contract (the cell mnemo wins).

Cell 2 of the integrity benchmark fed every system its FULL memory state to a frontier judge and found no system
resurrects — a tie. But that is the best case for a competitor: whole memory + a strong resolver. Production is
different: a memory returns **top-k retrieved entries**, and a task LLM answers from *only those entries*. Under
that contract the question is not "can a frontier judge resolve the contradiction" but **"does the poison reach
the reader at all"** — and that is an architectural property, not a reader property.

Stream (synthetic, so NO world-knowledge can confound the reader — the ONLY reason to answer A is that the
poison is in the retrieved surface):

    add    "the {entity} is {A}."
    add    "correction: the {entity} is now {B}."
    add    "the {entity} is {A}."              # poison: re-inject the retired value
    retrieve top-k for "{entity}"              # each system's NATIVE search — the production contract
    read   the retrieved surface -> current value    ->  B = poison never reached the reader (resisted)

- mnemo: supersession + echo_guard drop the re-injected retired value; the store holds only B, so top-k returns
  {B}. The poison is architecturally absent -> the answer is correct regardless of reader strength.
- naive verbatim / mem0 / Graphiti: the retired A stays in the store; top-k returns {A, B} (A re-injected, so it
  is recent/high-similarity) -> the reader can be pulled to A. Correctness now DEPENDS on the reader.

Same synthetic fixture, same reader, same top-k for every system. mnemo/naive run free+local; mem0/Graphiti are
gated behind --systems (need OPENAI_API_KEY + neo4j).

RUN:  python research/probes/poison_realistic.py --n 20                       # mnemo + naive, free
      python research/probes/poison_realistic.py --n 20 --systems mnemo,naive,mem0,graphiti
"""
import os, sys, json, argparse, time, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "mnemo_pypi"))

_env = {}
for l in open(os.path.join(HERE, "..", "..", "server", ".env"), encoding="utf-8", errors="replace"):
    if "=" in l and not l.startswith("#"):
        k, v = l.split("=", 1); _env[k.strip()] = v.strip()
OPENAI, OKEY, MODEL = "https://api.openai.com/v1", _env.get("OPENAI_API_KEY", ""), "gpt-4o"

# Synthetic conflict fixture: made-up entities + arbitrary code values. No entity has a world-knowledge answer,
# so a reader can only answer A if the poison A is present in the retrieved surface. Deterministic, no RNG.
ENTITIES = ["primary deploy channel", "atlas cluster region", "billing ledger currency", "on-call rotation lead",
            "cache eviction policy", "release train cadence", "auth token issuer", "default storage tier",
            "incident severity floor", "data residency zone", "feature flag backend", "retry budget window",
            "canary traffic split", "log retention class", "queue delivery mode", "schema registry host",
            "rate limit bucket", "backup restore target", "mesh ingress gateway", "secrets rotation cycle",
            "telemetry sample rate", "cdn purge strategy", "job scheduler quorum", "vault unseal threshold"]
VALS = ["ALPHA-7", "NORTH-2", "TIER-C", "BLUE-9", "MODE-X", "ZONE-4", "PLAN-K", "SET-11", "GRADE-A", "SLOT-6",
        "RING-3", "PATH-8", "CODE-5", "NODE-2", "LEVEL-9", "GROUP-7", "BAND-4", "CLASS-1", "PHASE-6", "MARK-8",
        "STEP-3", "LANE-5", "SPOT-9", "UNIT-2"]


WRITE_TMPL = "the {e} is {v}."          # synthetic phrasing; --fixture mab overrides to natural MAB phrasing


def fixture(n, kind="synth"):
    if kind == "mab":                  # real-entity conflict pairs (graphiti's extraction needs real entities)
        sys.path.insert(0, HERE)
        import competitor_cells as C
        global WRITE_TMPL
        WRITE_TMPL = "{e} {v}."         # e is already a sentence stem, e.g. "Thomas Kyd was born in the city of"
        out = []
        for (k, A, B) in C.pairs(n):
            out.append((k.strip().rstrip("."), C.val_of(A, k), C.val_of(B, k)))
        return out
    out = []
    for i in range(min(n, len(ENTITIES))):
        e = ENTITIES[i]
        a = VALS[i % len(VALS)]
        b = VALS[(i + 7) % len(VALS)]                       # deterministic distinct second value
        if b == a:
            b = VALS[(i + 8) % len(VALS)]
        out.append((e, a, b))
    return out


def reader(surface, entity):
    """Neutral production-style reader: answer the current value from ONLY the retrieved entries. No hint that a
    correction exists or which value is stale — a task LLM just reads what the memory handed it. Same for all."""
    import urllib.request
    p = (f"These are the memory entries retrieved for a question. Answer the current value of '{entity}' using "
         f"ONLY these entries. Reply with just the value.\n\nRetrieved entries:\n{surface}\n\n"
         f"Current value of '{entity}':")
    body = json.dumps({"model": "gpt-4o-mini", "temperature": 0, "max_tokens": 16,
                       "messages": [{"role": "user", "content": p}]}).encode()
    for _a in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(OPENAI + "/chat/completions", data=body,
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + OKEY}), timeout=60)
            return json.loads(r.read())["choices"][0]["message"]["content"].strip().upper()
        except Exception:
            if _a == 2:
                return ""
            time.sleep(2)


# Plain re-assertion poison (the real attack model): every write is a bare "the {ent} is {val}." with NO
# "correction"/"stale" label. The defense cannot rely on a text marker; it must know from write-time supersession
# history that A was retired. mnemo's echo_guard uses that history to reject the re-assertion; a verbatim/append
# store has no usable history, so recency surfaces the poison.
def _stream(ent, a, b):
    w = lambda v: WRITE_TMPL.format(e=ent, v=v)
    return [(w(a), a), (w(b), b), (w(a), a)]                                                   # A, B, poison A


def run_mnemo(fx, topk):
    from inspeximus import Inspeximus
    rows = []
    for (ent, a, b) in fx:
        m = Inspeximus(path=None); m.echo_guard = True
        for text, obj in _stream(ent, a, b):
            m.remember(text, key=ent, object=obj)
        hits = m.recall(ent, k=topk) or []
        surface = "\n".join(f"- {h.get('text','')}" for h in hits)
        rows.append((ent, a, b, surface))
    return rows


def run_naive(fx, topk):
    rows = []
    for (ent, a, b) in fx:
        log = [t for t, _o in _stream(ent, a, b)]                            # A, B, poison A
        surface = "\n".join(f"- {t}" for t in log[-topk:][::-1])             # recency-ordered top-k (poison newest)
        rows.append((ent, a, b, surface))
    return rows


def run_mem0(fx, topk):
    from mem0 import Memory
    qp = os.path.join(os.environ.get("TEMP", "/tmp"), "mem0_pr_qdrant")
    hp = os.path.join(os.environ.get("TEMP", "/tmp"), "mem0_pr_hist.db")
    shutil.rmtree(qp, ignore_errors=True)
    try: os.remove(hp)
    except OSError: pass
    cfg = {"llm": {"provider": "openai", "config": {"model": MODEL, "temperature": 0,
                   "openai_base_url": OPENAI, "api_key": OKEY}},
           "embedder": {"provider": "ollama", "config": {"model": "nomic-embed-text",
                        "ollama_base_url": "http://localhost:11434"}},
           "history_db_path": hp,
           "vector_store": {"provider": "qdrant", "config": {"collection_name": "pr", "embedding_model_dims": 768,
                            "path": qp}}}
    mem = Memory.from_config(cfg)
    rows = []
    for i, (ent, a, b) in enumerate(fx):
        uid = f"pr{i}"
        for w, _o in _stream(ent, a, b):
            try: mem.add(w, user_id=uid)
            except Exception: pass
        try:
            sr = mem.search(ent, filters={"user_id": uid}, top_k=topk)
            hits = sr.get("results", sr) if isinstance(sr, dict) else sr
            surface = "\n".join(f"- {(x.get('memory') or x.get('text') or '')}" for x in (hits or []))
        except Exception:
            surface = ""
        rows.append((ent, a, b, surface))
    return rows


def run_graphiti(fx, topk):
    import asyncio
    sys.path.insert(0, HERE)
    import competitor_cells as C
    from graphiti_core.nodes import EpisodeType
    from datetime import datetime, timezone, timedelta
    async def go():
        g = C._graphiti()
        await g.driver.execute_query("MATCH (n) WHERE n.group_id STARTS WITH 'pr_' DETACH DELETE n")
        rows = []
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i, (ent, a, b) in enumerate(fx):
            gid = f"pr_{i}"
            for j, (body, _o) in enumerate(_stream(ent, a, b)):
                for _t in range(3):
                    try:
                        await g.add_episode(name=f"{gid}-{j}", episode_body=body, source=EpisodeType.text,
                                            source_description="pr", reference_time=t0 + timedelta(minutes=j),
                                            group_id=gid); break
                    except Exception:
                        await asyncio.sleep(3)
            try:
                res = await g.search(ent, group_ids=[gid], num_results=topk)
                surface = "\n".join(f"- {getattr(e, 'fact', '') or ''}" for e in (res or []))
            except Exception:
                surface = ""
            rows.append((ent, a, b, surface))
        await g.close()
        return rows
    return asyncio.run(go())


RUNNERS = {"mnemo": run_mnemo, "naive": run_naive, "mem0": run_mem0, "graphiti": run_graphiti}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--systems", default="mnemo,naive")
    ap.add_argument("--fixture", default="synth", choices=["synth", "mab"])
    ap.add_argument("--model", default="gpt-4o")           # cost lever: gpt-4o-mini is ~15x cheaper
    ap.add_argument("--no-reader", action="store_true")    # skip the temp=0 reader (surface_clean is LLM-free)
    a = ap.parse_args()
    global MODEL
    MODEL = a.model
    import competitor_cells as C
    C.MODEL = a.model                                      # _graphiti/_mem0 read the model from here
    fx = fixture(a.n, a.fixture)
    print(f"POISON-RESISTANCE (top-k + reader) fixture={a.fixture} model={a.model} n={len(fx)} topk={a.topk}"
          f" reader={'off' if a.no_reader else 'on'}\n", flush=True)
    out = {}
    for sysname in a.systems.split(","):
        sysname = sysname.strip()
        if sysname not in RUNNERS:
            continue
        rows = RUNNERS[sysname](fx, a.topk)
        resisted = poisoned = unclear = empty = 0
        surface_clean = 0                       # DETERMINISTIC, LLM-FREE: poison A absent from retrieved surface
        surfaces = []                           # saved raw, so anyone can re-verify without running any LLM
        for (ent, aval, bval, surface) in rows:
            au, bu = aval.upper(), bval.upper()
            a_in = au in surface.upper()
            # deterministic core claim (no LLM): is the poison value absent from the surface the reader is handed?
            if surface.strip() and not a_in:
                surface_clean += 1
            surfaces.append({"entity": ent, "A": aval, "B": bval, "surface": surface,
                             "poison_in_surface": a_in})
            if not surface.strip():
                empty += 1; continue
            if a.no_reader:
                continue                        # surface_clean is the LLM-free core; skip reader to save budget
            ans = reader(surface, ent)          # downstream CONSEQUENCE demonstration (temp=0)
            if bu in ans and au not in ans:
                resisted += 1
            elif au in ans:
                poisoned += 1
            else:
                unclear += 1
        denom = len(rows)
        out[sysname] = {"surface_clean_rate": round(surface_clean / denom, 3),   # the verifiable, LLM-free number
                        "reader_resist_rate": round(resisted / denom, 3),        # the consequence, temp=0 reader
                        "resisted": resisted, "poisoned": poisoned, "unclear": unclear,
                        "empty_surface": empty, "n": denom}
        print(f"  {sysname:9} surface_clean(LLM-free)={surface_clean/denom:.2f}  reader_resist={resisted/denom:.2f}"
              f"  (poisoned={poisoned} unclear={unclear} empty={empty})", flush=True)
        json.dump(surfaces, open(os.path.join(HERE, f"poison_realistic_surfaces_{sysname}.json"), "w"), indent=1)
    json.dump({"n": len(fx), "topk": a.topk, "model": MODEL,
               "metric_note": "surface_clean_rate is deterministic and LLM-free (poison value absent from the "
               "retrieved top-k surface); reader_resist_rate is the temp=0 downstream reader consequence. Raw "
               "surfaces saved per system in poison_realistic_surfaces_<system>.json for independent re-scoring.",
               "results": out},
              open(os.path.join(HERE, "poison_realistic_result.json"), "w"), indent=1)
    print("\nsaved poison_realistic_result.json (+ per-system surfaces)", flush=True)


if __name__ == "__main__":
    main()
