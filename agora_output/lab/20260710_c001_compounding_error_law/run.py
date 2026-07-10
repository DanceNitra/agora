"""Crucible c001 — severe test of the viral 'compounding-error law' (R = p^n).

THE CLAIM (MindStudio + 5 vendor blogs, quoted as measured fact, never with data): chaining LLM
agents multiplies per-step error geometrically — at 95% per-step reliability a 5-step pipeline
drops to ~77% end-to-end (0.95^5), ~60% at 10 steps; pipelines are 'mathematically unreliable'
past ~10 steps. The law assumes step errors are INDEPENDENT and UNCORRECTED.

DESIGN (smallest faithful model of a chained agent pipeline):
  Task: JSON state transformation. State = dict of integer fields. Each step = one natural-language
  instruction (compound arithmetic ops) an agent (gpt-4o-mini, temp 0) must apply, returning the new
  JSON. Ground truth is computed in Python, so every step and every chain is exactly checkable.
  Steps are REAL LLM steps whose difficulty naturally yields imperfect per-step accuracy.

  Phase 1 CALIBRATION — per-step accuracy in isolation: n_iso random single steps, each from a fresh
    random state. Gives p_iso (the claim's '95%' analog, measured not assumed).
  Phase 2 CHAINS (naive) — chains of length n in {1,3,5,10}, n_chain chains each. Step i+1 consumes
    the AGENT's (possibly wrong) output — exactly the pipeline the law describes. Measures:
    E2E success, in-situ per-step accuracy, and the law's prediction p^n for comparison.
  Phase 3 CHAINS (self-check) — same, length 5 and 10, but each step gets ONE cheap verify-and-fix
    pass (the trivial correction the law ignores). Tests the 'mathematically doomed' implication.

VERDICT RULE (pre-stated):
  REPRODUCED if naive-chain E2E is statistically consistent with p_insitu^n at n=5 and n=10
    (within the bootstrap 95% CI) AND the self-check arm doesn't rescue it above the law's curve.
  FAILED if E2E deviates from the geometric prediction beyond CIs (either direction: correlated /
    self-masking errors -> slower decay; error cascading -> faster decay), OR if one cheap
    self-check pass pushes E2E far above p^n (the 'doomed' framing fails on its own terms).
  The point estimate comparison at 0.95->0.77 is the claim's own number; the LAW SHAPE is primary.
"""
import json, os, random, sys, time, urllib.request

sys.stdout.reconfigure(errors="replace", line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
env = {}
for line in open(os.path.join(ROOT, "server", ".env"), encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("AGORA_API_KEY") or env.get("OLLAMA_API_KEY")   # Ollama cloud (free credits) — never the paid OpenAI key
MODEL = "deepseek-v4-flash"                                    # our cheap/fast cloud tier
API_URL = "https://ollama.com/v1/chat/completions"
N_ISO = int(os.getenv("C001_NISO", "120"))
N_CHAIN = int(os.getenv("C001_NCHAIN", "40"))
LENGTHS = [1, 3, 5, 10]
FIELDS = list("abcdefgh")

def llm(prompt):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 300, "temperature": 0}).encode()
    for a in range(4):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                API_URL, data=body,
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}),
                timeout=120).read())
            return r["choices"][0]["message"]["content"]
        except Exception:
            if a == 3:
                return None
            time.sleep(4 * (a + 1))

def parse_state(text):
    if not text:
        return None
    try:
        s = text[text.index("{"): text.rindex("}") + 1]
        d = json.loads(s)
        return {k: int(v) for k, v in d.items()} if isinstance(d, dict) else None
    except Exception:
        return None

def rand_state(rng):
    return {f: rng.randint(100, 999) for f in FIELDS}

def rand_step(rng, state):
    """One compound instruction + its ground-truth transform. Difficulty tuned toward the claim's
    ~95% per-step regime: v1 (2 simple ops) measured p_iso = 1.000 on deepseek-v4-flash (n=100) —
    too easy to engage the law. v2 uses 3 chained ops with cross-references and a conditional,
    which forces sequential in-head arithmetic where the intermediate values matter."""
    f, g, h = rng.sample(FIELDS, 3)
    k1, k2 = rng.randint(11, 99), rng.randint(3, 9)
    kind = rng.randrange(4)
    if kind == 0:
        instr = f"add {k1} to '{f}', then set '{g}' to the updated '{f}' plus '{h}'"
        def gt(s): s = dict(s); s[f] += k1; s[g] = s[f] + s[h]; return s
    elif kind == 1:
        instr = f"multiply '{f}' by {k2}, then set '{g}' to the updated '{f}' minus '{h}'"
        def gt(s): s = dict(s); s[f] *= k2; s[g] = s[f] - s[h]; return s
    elif kind == 2:
        instr = f"set '{f}' to the sum of '{g}' and '{h}', then subtract {k1} from the updated '{f}'"
        def gt(s): s = dict(s); s[f] = s[g] + s[h]; s[f] -= k1; return s
    else:
        instr = f"swap '{f}' and '{g}', then add the swapped '{f}' to '{h}'"
        def gt(s): s = dict(s); s[f], s[g] = s[g], s[f]; s[h] += s[f]; return s
    return instr, gt

def agent_step(state, instr):
    p = (f"Current state (JSON): {json.dumps(state)}\n"
         f"Apply this instruction exactly: {instr}.\n"
         f"Reply with ONLY the full updated JSON object (all fields, integers).")
    return parse_state(llm(p))

def selfcheck_step(state, instr, out):
    p = (f"State before (JSON): {json.dumps(state)}\nInstruction: {instr}\n"
         f"Proposed result: {json.dumps(out) if out else 'INVALID'}\n"
         f"Verify the result is exactly correct. Reply with ONLY the correct full updated JSON object.")
    fixed = parse_state(llm(p))
    return fixed if fixed is not None else out

def boot_ci(xs, iters=5000, seed=0):
    rng = random.Random(seed); n = len(xs)
    bs = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return round(bs[int(0.025 * iters)], 3), round(bs[int(0.975 * iters)], 3)

def main():
    rng = random.Random(20260710)
    t0 = time.time()
    # Phase 1: isolation calibration
    iso = []
    for i in range(N_ISO):
        s = rand_state(rng); instr, gt = rand_step(rng, s)
        out = agent_step(s, instr)
        iso.append(1 if out == gt(s) else 0)
        if (i + 1) % 20 == 0:
            print(f"  iso {i+1}/{N_ISO} p={sum(iso)/len(iso):.3f} ({time.time()-t0:.0f}s)", flush=True)
    p_iso = sum(iso) / len(iso)
    print(f"PHASE1 p_iso={p_iso:.3f} CI={boot_ci(iso)}", flush=True)

    # Phase 2: naive chains
    results = {}
    step_flags_all = []          # (chain_id, step_idx, correct) for correlation analysis
    for L in LENGTHS:
        e2e, insitu = [], []
        for c in range(N_CHAIN):
            s_true = rand_state(rng); s_agent = dict(s_true)
            ok_chain = True
            for t in range(L):
                instr, gt = rand_step(rng, s_agent if not ok_chain else s_true)
                # ground truth evolves from the AGENT's actual state (pipeline semantics):
                expected = gt(s_agent)
                out = agent_step(s_agent, instr)
                correct = out == expected
                insitu.append(1 if correct else 0)
                step_flags_all.append((f"L{L}c{c}", t, correct))
                s_agent = out if out is not None else s_agent
                # E2E: final agent state equals the state you'd get applying ALL steps correctly
                # from the ORIGINAL state — recompute the true trajectory:
                if t == 0:
                    s_ref = gt(s_true)
                else:
                    s_ref = gt(s_ref)
                if s_agent != s_ref:
                    ok_chain = False
            e2e.append(1 if ok_chain and s_agent == s_ref else 0)
        p_e2e = sum(e2e) / len(e2e)
        results[L] = {"e2e": round(p_e2e, 3), "e2e_CI": boot_ci(e2e),
                      "p_insitu": round(sum(insitu) / len(insitu), 3),
                      "law_pred_from_iso": round(p_iso ** L, 3)}
        print(f"PHASE2 L={L}: E2E={p_e2e:.3f} CI={results[L]['e2e_CI']} "
              f"law(p_iso^{L})={p_iso**L:.3f} p_insitu={results[L]['p_insitu']:.3f} "
              f"({time.time()-t0:.0f}s)", flush=True)

    # Phase 3: self-check chains at L=5,10
    sc = {}
    N_SC = int(os.getenv("C001_NSC", "25"))       # self-check arm is 2 calls/step — smaller n
    for L in (5, 10):
        e2e = []
        for c in range(N_SC):
            s_true = rand_state(rng); s_agent = dict(s_true); s_ref = None
            for t in range(L):
                instr, gt = rand_step(rng, s_agent)
                out = agent_step(s_agent, instr)
                out = selfcheck_step(s_agent, instr, out)      # ONE cheap verify-and-fix pass
                s_agent = out if out is not None else s_agent
                s_ref = gt(s_ref) if s_ref is not None else gt(s_true)
            e2e.append(1 if s_agent == s_ref else 0)
        sc[L] = {"e2e": round(sum(e2e) / len(e2e), 3), "e2e_CI": boot_ci(e2e)}
        print(f"PHASE3 self-check L={L}: E2E={sc[L]['e2e']:.3f} CI={sc[L]['e2e_CI']} "
              f"vs law {p_iso**L:.3f} ({time.time()-t0:.0f}s)", flush=True)

    out = {"claim_id": "c001-compounding-error-law", "model": MODEL,
           "n_iso": N_ISO, "n_chains_per_length": N_CHAIN, "lengths": LENGTHS,
           "p_step_isolation": round(p_iso, 3), "p_iso_CI": boot_ci(iso),
           "naive_chains": results, "self_check_chains": sc,
           "law": "R = p^n (independent, uncorrected errors)",
           "runtime_s": round(time.time() - t0)}
    json.dump(out, open(os.path.join(HERE, "result.json"), "w"), indent=2)
    print("\n" + json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
