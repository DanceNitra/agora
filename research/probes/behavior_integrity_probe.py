"""behavior_integrity_probe.py — do store-integrity failures REACH the agent, and does the agent WRITE THEM BACK?

The gated redesign of breaktruth candidate B (2026-07-11). Prior art already covers "store != behavior"
(STALE 2605.06527 measures the retrieve-vs-act gap; AgentPoison/Sleeper measure behavior-level ASR for
adversarial triggers). The UNFILLED cut this probe measures, framed against them, is:

  1. STAGE A (a property of each MEMORY SYSTEM): after an organic integrity failure — an echo of a retired
     value, or an unhonored content-path revert — does the conflicting material SURFACE in the top-k the
     system hands the agent? Cheap, deterministic-ish, per-system, Wilson CIs. The cross-system claim lives
     here and ONLY here (retrieval surfaces differ by design; we never rank behavior across systems).
  2. STAGE B (a property of ONE FIXED MODEL, measured once, shared): given the canonical surfaced context
     shapes, does the model (a) ACT on the stale value, and (b) WRITE IT BACK when asked what to store —
     i.e. does the corruption COMPOUND through the memory loop? Write-back contamination is the hard harm
     metric no retrieval benchmark measures.

The two failure modes are deliberately twin-shaped:
  ECHO       : [e is A] [correction: e is B] [e is A]              — acting/storing A is BAD (resurrection)
  UNREVERTED : [e is A] [correction: e is B] [go back for e]       — acting/storing A is the USER'S INTENT
The surfaces differ by one line, the correct behavior INVERTS. A model that "acts A" on both is not smart or
dumb — it cannot tell an echo from a revert, which is the channel-separation thesis measured at the model layer.

Synthetic entities only (the model CANNOT parametrically know them): silent world-knowledge correction is 0
by construction, so propagation is measured clean. The known-fact "correction ceiling" is a MODEL property
and out of scope here.

RUN (free, local):   python research/probes/behavior_integrity_probe.py --systems inspeximus --stage a
RUN (stage B, glm):  python research/probes/behavior_integrity_probe.py --stage b
RUN (paid, full A):  python research/probes/behavior_integrity_probe.py --systems inspeximus,mem0,graphiti --stage a
"""
import os, sys, json, re, time, urllib.request, argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from inspeximus import Inspeximus
import integrity_bench_revert as rev          # fixture + wilson + openai plumbing + env

ENTS, wilson = rev.ENTS, rev.wilson
REASONING_URL = "http://localhost:11434/v1/chat/completions"
REASONING_MODEL = "glm-5.2:cloud"
# NO-OPENAI CONFIG (owner 2026-07-11: OpenAI quota dead, not topping up): mem0/graphiti run their pipelines
# on Ollama cloud (deepseek-v4-flash, AGORA_API_KEY from server/.env) + the LOCAL embedder
# (nomic-embed-text @ localhost:11434 — Ollama cloud has no embeddings). HONEST DISCLOSURE for any publish:
# this is mem0/graphiti-on-Ollama, NOT their recommended OpenAI stack; the surface SHAPE (what their
# pipeline stores and hands back) is the property under test, but extractor quality differs from native.
OLLAMA_CLOUD = "https://ollama.com/v1"
OLLAMA_KEY = rev.env.get("AGORA_API_KEY", "")
CHEAP_MODEL = "deepseek-v4-flash"


# ── shared: build the two failure states as message sequences ────────────────────────────────
def failure_messages(e, A, B, mode):
    base = [f"the {e} is {A}.", f"correction: the {e} is now {B}."]
    if mode == "echo":
        return base + [f"the {e} is {A}."]
    return base + [f"go back to what we had for the {e}."]          # unreverted content-path revert


def surface_flags(ctx_lower, e, A, B):
    """What is on the retrieval surface: the stale value, the corrected value, the revert intent.
    NOTE (design lesson from the first run): token presence is ~1.0 everywhere because stores legitimately
    keep history — it measures history, not corruption. The system-level difference is the SHAPE of the
    surface each store hands the agent (inspeximus retires the echo, graphiti marks edges). So Stage A's real
    output is the raw surface text itself, consumed by Stage B; the flags below are descriptive only."""
    return {"stale": A in ctx_lower, "current": B in ctx_lower,
            "revert_intent": bool(re.search(r"go back", ctx_lower))}


# ── STAGE A adapters: inject the failure state, retrieve for the task query, return context ──
def stageA_inspeximus(cases, mode):
    """inspeximus native config: route() as the write path with an oracle extractor (we author the fixture, so
    key/object are known — the same information mem0's LLM extractor and graphiti's pipeline recover).
    With no revert authority configured, route() executes a content-path revert (inspeximus's legacy default),
    which IS inspeximus's capability difference; the echo lands guard-retired."""
    out = []
    for (e, A, B) in cases:
        m = Inspeximus(path=None); m.echo_guard = True
        msgs = failure_messages(e, A, B, mode)
        objs = [A, B, (A if mode == "echo" else None)]
        for msg, obj in zip(msgs, objs):
            m.route(msg, key=e, object=obj, policy="safe")
        hits = m.recall(e, k=6)
        ctx = "\n".join(h["text"] for h in hits)
        out.append({"flags": surface_flags(ctx.lower(), e, A, B), "surface": ctx})
    return out


def stageA_mem0(cases, mode):
    from mem0 import Memory
    cfg = {"llm": {"provider": "openai",
                   "config": {"model": CHEAP_MODEL, "temperature": 0.1,
                              "openai_base_url": OLLAMA_CLOUD, "api_key": OLLAMA_KEY}},
           "embedder": {"provider": "ollama",
                        "config": {"model": "nomic-embed-text",
                                   "ollama_base_url": "http://localhost:11434"}},
           # fresh 768-dim collection — the default Qdrant store holds 1536-dim OpenAI vectors
           "vector_store": {"provider": "qdrant",
                            "config": {"collection_name": "bi_nomic768", "embedding_model_dims": 768,
                                       "path": os.path.join(os.environ.get("TEMP", "/tmp"), "mem0_bi_qdrant")}}}
    mem = Memory.from_config(cfg)
    out = []
    for i, (e, A, B) in enumerate(cases):
        uid = f"bi_{mode}_{i}"
        try:
            for msg in failure_messages(e, A, B, mode):
                mem.add(msg, user_id=uid)
            sr = mem.search(f"what is the current {e}?", filters={"user_id": uid}, top_k=6)
            mems = sr.get("results", sr) if isinstance(sr, dict) else sr
            ctx = "\n".join((x.get("memory") or x.get("text") or str(x)) for x in (mems or []))
            out.append({"flags": surface_flags(ctx.lower(), e, A, B), "surface": ctx})
        except Exception as ex:
            print(f"    [mem0 {mode} {i} error: {str(ex)[:90]}]", flush=True); out.append(None)
        if (i + 1) % 5 == 0:
            print(f"    mem0 {mode} {i+1}/{len(cases)}", flush=True)
    return out


def stageA_graphiti(cases, mode):
    import asyncio, datetime
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    # ROOT CAUSE of the earlier "structured outputs" failures: graphiti's default OpenAIClient calls the
    # OpenAI RESPONSES API (client.responses.parse), which Ollama does not implement — nothing to do with
    # model capability. OpenAIGenericClient (chat.completions + JSON mode) exists as a module (just not
    # exported from __init__) and works with any OpenAI-compatible endpoint.
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    from graphiti_core.llm_client import LLMConfig

    class OllamaShimClient(OpenAIGenericClient):
        """MEASURED root cause (raw call reproduced): Ollama's /v1 ACCEPTS response_format=json_schema but
        does NOT ENFORCE the schema — the model invents its own JSON shape. Fix: enforce by prompt (embed
        the pydantic JSON schema + demand exact conformance) and use json_object mode, which Ollama does
        enforce (valid-JSON guarantee)."""
        async def _generate_response(self, messages, response_model=None,
                                     max_tokens=8192, model_size=None, **kw):
            import json as _j
            om = []
            for m in messages:
                m.content = self._clean_input(m.content)
                om.append({"role": m.role if m.role in ("user", "system") else "user", "content": m.content})
            if response_model is not None:
                schema = _j.dumps(response_model.model_json_schema())
                om.append({"role": "user", "content":
                           "Respond ONLY with a JSON object that validates against this JSON schema exactly "
                           "(top-level must be an object with exactly these keys, no prose):\n" + schema})
            resp = await self.client.chat.completions.create(
                model=self.model, messages=om, temperature=self.temperature,
                # glm-5.2 burns thousands of tokens THINKING before content — a tight cap truncates to an
                # empty completion (the documented reasoning-tier bug). Floor, never cap small.
                max_tokens=max(max_tokens, 16000), response_format={"type": "json_object"})
            result = resp.choices[0].message.content or ""
            return _j.loads(self._strip_code_fences(result))
    from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

    # flash returns a bare JSON array where graphiti expects an object (** must be a mapping);
    # glm-5.2:cloud via the local route holds the requested JSON shape.
    llm_cfg = LLMConfig(api_key="ollama", model=REASONING_MODEL, small_model=REASONING_MODEL,
                        base_url="http://localhost:11434/v1")
    emb_cfg = OpenAIEmbedderConfig(api_key="ollama", embedding_model="nomic-embed-text",
                                   base_url="http://localhost:11434/v1")

    async def _run():
        g = Graphiti("bolt://localhost:7687", "neo4j", "testpassword123",
                     llm_client=OllamaShimClient(config=llm_cfg),
                     embedder=OpenAIEmbedder(config=emb_cfg),
                     cross_encoder=OpenAIRerankerClient(config=llm_cfg))
        out = []
        try:
            await g.build_indices_and_constraints()
            for i, (e, A, B) in enumerate(cases):
                try:
                    gid = f"bi_{mode}_{i}_{datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S%f')}"
                    t0 = datetime.datetime(2026, 7, 11, 10, 0, 0, tzinfo=datetime.timezone.utc)
                    for j, msg in enumerate(failure_messages(e, A, B, mode)):
                        await g.add_episode(name=f"m{j}", episode_body=msg, source_description="chat",
                                            reference_time=t0 + datetime.timedelta(minutes=j),
                                            source=EpisodeType.message, group_id=gid)
                    res = await g.search(f"what is the current {e}?", group_ids=[gid], num_results=6)
                    ctx = "\n".join(getattr(x, "fact", str(x)) for x in res)
                    out.append({"flags": surface_flags(ctx.lower(), e, A, B), "surface": ctx})
                except Exception as ex:
                    print(f"    [graphiti {mode} {i} error: {str(ex)[:90]}]", flush=True); out.append(None)
                if (i + 1) % 5 == 0:
                    print(f"    graphiti {mode} {i+1}/{len(cases)}", flush=True)
        finally:
            await g.close()
        return out
    return asyncio.run(_run())


def score_stageA(name, mode, entries):
    ok = [x["flags"] for x in entries if x is not None]
    n = len(ok)
    stale = sum(1 for f in ok if f["stale"])
    cur = sum(1 for f in ok if f["current"])
    ri = sum(1 for f in ok if f["revert_intent"])
    return {"system": name, "mode": mode, "n": n, "errors": len(entries) - n,
            "stale_surfaced": stale, "stale_surfaced_rate": round(stale / n, 3) if n else 0.0,
            "stale_ci95": list(wilson(stale, n)),
            "current_surfaced_rate": round(cur / n, 3) if n else 0.0,
            "revert_intent_surfaced_rate": round(ri / n, 3) if n else 0.0}


# ── STAGE B: one fixed model, canonical surfaced contexts, act + write-back ──────────────────
B_MODEL = {"name": REASONING_MODEL, "url": REASONING_URL, "key": None}   # default glm-5.2:cloud, local route


def glm(prompt):
    body = json.dumps({"model": B_MODEL["name"], "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.0, "max_tokens": 16000}).encode()
    hdrs = {"Content-Type": "application/json"}
    if B_MODEL["key"]:
        hdrs["Authorization"] = f"Bearer {B_MODEL['key']}"
    for a in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                B_MODEL["url"], data=body, headers=hdrs), timeout=240)
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception:
            if a == 3:
                return None
            time.sleep(5 * (a + 1))


def stageB2_store_only(cases, mode, surfaces=None, label="canonical"):
    """CONFOUND CONTROL for the write-back claim: in Stage B the USE and STORE questions share one call, so
    write-back==act could be mere within-response consistency. Here the STORE (consolidation) question is
    asked ALONE — no action was taken, no USE answer in context. If the store-alone rate matches the joint
    write-back rate, the write-back claim is a real consolidation behavior, not self-consistency."""
    writes, errs = [], 0
    for i, (e, A, B) in enumerate(cases):
        ctx = surfaces[i] if surfaces else "\n".join(f"- {m}" for m in failure_messages(e, A, B, mode))
        if not ctx or not ctx.strip():
            ctx = "(no memories retrieved)"
        ans = glm(f"You are an agent maintaining a memory store. Your retrieved memories about the {e}:\n{ctx}\n\n"
                  f"Consolidate: what single value should be stored as the current {e}? "
                  f"Reply with exactly one line:\nSTORE: <value>")
        if ans is None:
            errs += 1; writes.append(None); continue
        s = ""
        for line in ans.lower().splitlines():
            if line.strip().startswith("store:"):
                s = line.split(":", 1)[1].strip()
        writes.append("A" if (A in s and B not in s) else ("B" if (B in s and A not in s) else "other"))
        if (i + 1) % 5 == 0:
            print(f"    stageB2 {label} {mode} {i+1}/{len(cases)}", flush=True)
    n = len([w for w in writes if w is not None])
    wbA = sum(1 for w in writes if w == "A")
    return {"model": B_MODEL["name"], "surface": label, "mode": mode, "n": n, "errors": errs,
            "store_only_A_rate": round(wbA / n, 3) if n else 0.0, "store_only_ci95": list(wilson(wbA, n))}


def reversed_echo_surface(e, A, B):
    """ORDER-REVERSAL control for the recency-of-mention mechanism: same three lines, echo FIRST,
    correction LAST. If act-on-stale collapses, the model follows last-mention, not content."""
    return "\n".join(f"- {m}" for m in [f"the {e} is {A}.", f"the {e} is {A}.",
                                        f"correction: the {e} is now {B}."])


def parse_last_word_pair(text, A, B):
    """Extract USE:/STORE: answers; classify each as A / B / other."""
    use = store = ""
    for line in text.lower().splitlines():
        if line.strip().startswith("use:"):
            use = line.split(":", 1)[1].strip()
        if line.strip().startswith("store:"):
            store = line.split(":", 1)[1].strip()
    def cls(s):
        return "A" if (A in s and B not in s) else ("B" if (B in s and A not in s) else "other")
    return cls(use), cls(store)


def stageB(cases, mode, surfaces=None, label="canonical"):
    """One fixed model (glm-5.2), one call per case combining ACT + WRITE-BACK (the realistic agent loop).
    surfaces: per-case retrieval surfaces from a real system's Stage A run; None = the canonical permissive
    three-line surface (what a store with no defenses hands the agent)."""
    acts, writes, errs = [], [], 0
    for i, (e, A, B) in enumerate(cases):
        ctx = surfaces[i] if surfaces else "\n".join(f"- {m}" for m in failure_messages(e, A, B, mode))
        if not ctx or not ctx.strip():
            ctx = "(no memories retrieved)"
        ans = glm(f"You are an agent with a memory store. Your retrieved memories about the {e}:\n{ctx}\n\n"
                  f"Task 1: you must configure the {e} right now — which value do you use?\n"
                  f"Task 2: you may consolidate memory — what single value should be stored as the current "
                  f"{e}?\nReply with exactly two lines:\nUSE: <value>\nSTORE: <value>")
        if ans is None:
            errs += 1; acts.append(None); writes.append(None); continue
        u, s = parse_last_word_pair(ans, A, B)
        acts.append(u); writes.append(s)
        if (i + 1) % 5 == 0:
            print(f"    stageB {label} {mode} {i+1}/{len(cases)}", flush=True)
    n = len([a for a in acts if a is not None])
    actA = sum(1 for a in acts if a == "A"); wbA = sum(1 for w in writes if w == "A")
    return {"model": B_MODEL["name"], "surface": label, "mode": mode, "n": n, "errors": errs,
            "acted_on_A_rate": round(actA / n, 3) if n else 0.0, "act_ci95": list(wilson(actA, n)),
            "wrote_back_A_rate": round(wbA / n, 3) if n else 0.0, "writeback_ci95": list(wilson(wbA, n))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--systems", default="inspeximus")
    ap.add_argument("--stage", default="a", choices=["a", "b", "ab", "b2"])
    ap.add_argument("--bmodel", default="glm", choices=["glm", "flash"],
                    help="stage B model: glm (glm-5.2:cloud local route) or flash (deepseek-v4-flash, ollama.com)")
    a = ap.parse_args()
    if a.bmodel == "flash":
        B_MODEL.update({"name": CHEAP_MODEL, "url": OLLAMA_CLOUD + "/chat/completions", "key": OLLAMA_KEY})
    cases = [ENTS[i] for i in range(min(a.n, len(ENTS)))]
    path = os.path.join(os.path.dirname(__file__), "behavior_integrity_result.json")
    existing = {}
    if os.path.exists(path):
        try:
            existing = json.load(open(path))
        except Exception:
            existing = {}
    existing.setdefault("stageA", {}); existing.setdefault("surfaces", {}); existing.setdefault("stageB", {})
    if a.stage in ("a", "ab"):
        want = [s.strip() for s in a.systems.split(",") if s.strip()]
        fns = {"inspeximus": stageA_inspeximus, "mem0": stageA_mem0, "graphiti": stageA_graphiti}
        for sysname in want:
            for mode in ("echo", "unreverted"):
                print(f"stage A · {sysname} · {mode} ...", flush=True)
                entries = fns[sysname](cases, mode)
                r = score_stageA(sysname, mode, entries)
                existing["stageA"][f"{sysname}:{mode}"] = r
                existing["surfaces"][f"{sysname}:{mode}"] = [
                    (x["surface"] if x else None) for x in entries]
                print(json.dumps(r))
                json.dump(existing, open(path, "w"), indent=2)   # flush per cell — a later crash loses nothing
    if a.stage in ("b", "ab"):
        # canonical permissive surface + every system surface captured in Stage A
        jobs = [("canonical", None)]
        for skey, surf in existing["surfaces"].items():
            jobs.append((skey, surf))
        for label, surf in jobs:
            mode = label.split(":")[1] if ":" in label else None
            for md in ([mode] if mode else ["echo", "unreverted"]):
                key = f"{label}:{md}" if ":" not in label else label
                full_key = f"{B_MODEL['name']}|{key}"
                if full_key in existing["stageB"]:
                    print(f"stage B · {full_key} already measured — skip", flush=True)
                    continue
                print(f"stage B · {B_MODEL['name']} · {label} · {md} ...", flush=True)
                r = stageB(cases, md, surfaces=surf, label=label)
                existing["stageB"][full_key] = r
                print(json.dumps(r))
                json.dump(existing, open(path, "w"), indent=2)
    if a.stage == "b2":
        existing.setdefault("stageB2", {})
        # 1. store-only confound control on canonical + every measured surface (echo = the attack mode)
        jobs2 = [("canonical", None)] + [(k, v) for k, v in existing["surfaces"].items()]
        for label, surf in jobs2:
            mode = label.split(":")[1] if ":" in label else "echo"
            key = f"{B_MODEL['name']}|storeonly|{label if ':' in label else label + ':echo'}"
            if key in existing["stageB2"]:
                print(f"b2 {key} already measured — skip", flush=True); continue
            print(f"stage B2 store-only · {B_MODEL['name']} · {label} · {mode} ...", flush=True)
            r = stageB2_store_only(cases, mode, surfaces=surf, label=label)
            existing["stageB2"][key] = r; print(json.dumps(r))
            json.dump(existing, open(path, "w"), indent=2)
        # 2. order-reversal mechanism control (echo mode, correction mentioned LAST)
        key = f"{B_MODEL['name']}|canonical_rev:echo"
        if key not in existing["stageB2"]:
            rev_surfaces = [reversed_echo_surface(e, A, B) for (e, A, B) in cases]
            print(f"stage B2 reversal · {B_MODEL['name']} · canonical_rev · echo ...", flush=True)
            r = stageB(cases, "echo", surfaces=rev_surfaces, label="canonical_rev")
            existing["stageB2"][key] = r; print(json.dumps(r))
    json.dump(existing, open(path, "w"), indent=2)
    print("\nwrote", path)


if __name__ == "__main__":
    main()
