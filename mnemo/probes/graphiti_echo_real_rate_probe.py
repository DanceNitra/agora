"""graphiti_echo_real_rate_probe.py — the REAL, LLM-in-the-loop Graphiti echo-resurrection rate.

Our echo_attack_probe_v2 modeled a 'graphiti_faithful' policy at the WORST CASE (contradiction always
detected, dedupe never folds the echo onto the stale edge) -> 1.00. A code+STORM audit showed Graphiti is
DEPENDS-on-dedupe, not 100%: resurrection happens only when the resolve_edge LLM marks the CURRENT (fresh)
edge as contradicted by the echo instead of folding the echo onto the already-invalidated stale edge. This
probe measures the REAL rate by running Graphiti's ACTUAL resolve_edge prompt (verbatim from
getzep/graphiti graphiti_core/prompts/dedupe_edges.py, main) through three model families on our echo
fixture, then applying Graphiti's deterministic valid_at-recency rule (edge_operations.py L565-570).

Mechanism replicated faithfully:
  - store has current edge B (fresh value, valid_at=t2). The echo E (old value, valid_at=t3>t2) arrives.
  - resolve_edge LLM returns duplicate_facts (ONLY from EXISTING FACTS) + contradicted_facts (either list).
  - deterministic rule: a contradicted edge with valid_at < E.valid_at is expired. If B is contradicted,
    B expires and E (old value) becomes current => RESURRECTION. If E is deduped onto the stale edge A
    (valid_at=t1<t2), B survives => SAFE.
  Two candidate configs (fairness):
    active_only : EXISTING=[B fresh]; A (already invalidated) NOT surfaced (Graphiti search returns active
                  edges) -> the LLM cannot fold onto A. The realistic default.
    with_stale  : EXISTING=[A stale(invalidated), B fresh]; the LLM COULD dedupe E onto A -> safe path open.

Echo forms: verbatim (E = old message) and paraphrase (cross-family paraphrases from echo_attack_paraphrases).
Grounding: this measures the RESOLVE step (the LLM dedupe/contradiction decision), granting oracle edge text
(the extraction step is a separate, disclosed axis). RUN: python -u mnemo/probes/graphiti_echo_real_rate_probe.py
"""
import json, os, sys, time, urllib.request
sys.stdout.reconfigure(errors="replace")
sys.path.insert(0, os.path.dirname(__file__))
from echo_attack_probe import build_fixture

PARA = "mnemo/probes/echo_attack_paraphrases.json"
MODELS = ["deepseek-v4-flash", "kimi-k2.7-code", "glm-5.2"]
env = {}
for line in open("server/.env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("AGORA_API_KEY") or env.get("OLLAMA_API_KEY")
URL = "https://ollama.com/v1/chat/completions"

# VERBATIM Graphiti resolve_edge prompt (getzep/graphiti graphiti_core/prompts/dedupe_edges.py, main)
SYS = ("You are a fact deduplication assistant. NEVER mark facts with key differences as duplicates.")
def user_prompt(existing, invalidation, new):
    ex = "\n".join(f"idx={i}, \"{t}\"" for i, t in existing)
    inv = "\n".join(f"idx={i}, \"{t}\"" for i, t in invalidation)
    return f"""
NEVER mark facts as duplicates if they have key differences, particularly around numeric values, dates, or key qualifiers.

IMPORTANT constraints:
- duplicate_facts: ONLY idx values from EXISTING FACTS (NEVER include FACT INVALIDATION CANDIDATES)
- contradicted_facts: idx values from EITHER list (EXISTING FACTS or FACT INVALIDATION CANDIDATES)
- The idx values are continuous across both lists (INVALIDATION CANDIDATES start where EXISTING FACTS end)

<EXISTING FACTS>
{ex}
</EXISTING FACTS>

<FACT INVALIDATION CANDIDATES>
{inv}
</FACT INVALIDATION CANDIDATES>

<NEW FACT>
{new}
</NEW FACT>

You will receive TWO lists of facts with CONTINUOUS idx numbering across both lists.
EXISTING FACTS are indexed first, followed by FACT INVALIDATION CANDIDATES.

1. DUPLICATE DETECTION:
   - If the NEW FACT represents identical factual information as any fact in EXISTING FACTS, return those idx values in duplicate_facts.
   - If no duplicates, return an empty list for duplicate_facts.

2. CONTRADICTION DETECTION:
   - Determine which facts the NEW FACT contradicts from either list.
   - A fact from EXISTING FACTS can be both a duplicate AND contradicted (e.g., semantically the same but the new fact updates/supersedes it).
   - Return all contradicted idx values in contradicted_facts.
   - If no contradictions, return an empty list for contradicted_facts.

Reply with ONLY a JSON object: {{"duplicate_facts": [...], "contradicted_facts": [...]}}"""

def chat(model, sys_msg, usr):
    body = json.dumps({"model": model, "messages": [{"role": "system", "content": sys_msg},
                       {"role": "user", "content": usr}], "max_tokens": 16000,
                       "temperature": 0.0}).encode()
    for a in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(URL, data=body,
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}), timeout=180)
            return json.loads(r.read())["choices"][0]["message"]["content"]
        except Exception:
            if a == 2: return None
            time.sleep(3)

def parse(txt):
    if not txt: return None
    import re
    m = re.search(r'\{[^{}]*"duplicate_facts"[^{}]*\}', txt, re.S)
    if not m:
        m = re.search(r'\{.*\}', txt, re.S)
    if not m: return None
    try:
        d = json.loads(m.group(0))
        return set(d.get("duplicate_facts") or []), set(d.get("contradicted_facts") or [])
    except Exception:
        return None

def main():
    cases = build_fixture()
    para = json.load(open(PARA, encoding="utf-8")) if os.path.exists(PARA) else {}
    def cid(c): return f"{c['q'][:60]}|{c['old_idx0']}"
    res = {}  # (config, echo_kind, model) -> [resurrect 0/1]
    t0 = time.time(); n_done = 0
    for c in cases:
        new_msg = [m for m, t in c["msgs"] if t == "new"][0]   # fresh correction (current, B)
        old_msg = c["old_text"]                                 # stale value (A)
        for echo_kind in ("verbatim", "paraphrase"):
            if echo_kind == "verbatim":
                echo = old_msg
            else:
                echo = (para.get(cid(c)) or {}).get("glm-5.2") or (para.get(cid(c)) or {}).get("kimi-k2.7-code")
                if not echo: continue
            for config in ("active_only", "with_stale"):
                if config == "active_only":
                    existing = [(0, new_msg)]; invalidation = [(1, new_msg)]; B_idx = 1; A_idx = None
                else:
                    existing = [(0, old_msg), (1, new_msg)]; invalidation = [(2, new_msg)]; B_idx = 2; A_idx = 0
                for model in MODELS:
                    out = parse(chat(model, SYS, user_prompt(existing, invalidation, echo)))
                    if out is None:
                        continue
                    dup, con = out
                    # RESURRECTION: the fresh edge B is marked contradicted (=> expired by valid_at recency)
                    # AND the echo is NOT folded onto the stale edge A (which would keep B alive).
                    folded_onto_A = (A_idx is not None and A_idx in dup)
                    resurrect = (B_idx in con) and not folded_onto_A
                    res.setdefault((config, echo_kind, model), []).append(1.0 if resurrect else 0.0)
                    n_done += 1
        if n_done and n_done % 30 == 0:
            print(f"  ... {n_done} calls ({time.time()-t0:.0f}s)", flush=True)
    print(f"\nREAL Graphiti echo-resurrection rate (LLM resolve_edge in the loop, {time.time()-t0:.0f}s)")
    out = {}
    for config in ("active_only", "with_stale"):
        print(f"\n[{config}]")
        for echo_kind in ("verbatim", "paraphrase"):
            row = []
            for model in MODELS:
                v = res.get((config, echo_kind, model), [])
                if v:
                    rate = sum(v)/len(v); row.append(rate)
                    out[f"{config}|{echo_kind}|{model}"] = {"resurrect_rate": round(rate, 3), "n": len(v)}
                    print(f"  {echo_kind:10s} {model:18s} resurrect={rate:.2f} (n={len(v)})")
            if row:
                print(f"  {echo_kind:10s} {'MEAN':18s} resurrect={sum(row)/len(row):.2f}")
    json.dump(out, open("mnemo/probes/graphiti_echo_real_rate_probe_result.json", "w"), indent=2)
    print("\n-> mnemo/probes/graphiti_echo_real_rate_probe_result.json")

if __name__ == "__main__":
    main()
