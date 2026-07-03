"""Severe-test: does DECOMPOSITION help on SUBTLE / ENTANGLED reasoning errors at MATCHED compute?

The clean-arithmetic version of the atomic-decomposition law was REFUTED as a token-budget confound
(atomic_decomposition_calibration_law.py). This tests the ONE regime that refutation left open: SUBTLE,
entangled invalid steps where a holistic judge with AMPLE tokens may still fail because it ANCHORS on a
plausible conclusion and glides over a locally-invalid step — the effect Theoria (2607.01223) reports for
hidden premises.

TASK: chained propositional arguments (~STEPS derivation steps). VALID arguments use only modus ponens
(from 'P' and 'if P then Q', conclude Q). INVALID arguments plant exactly ONE affirming-the-consequent step
(from 'if P then Q' and 'Q', fallaciously conclude 'P') whose conclusion is still a PLAUSIBLE sentence, so
the fallacy hides in a coherent narrative. Ground truth is FORMAL (we know each step's rule), independent of
content plausibility.

THREE judges, all at AMPLE tokens (so this is NOT a compute confound — today's lesson):
  HOLISTIC:            'is every step valid? YES/NO'   (one call)
  DECOMPOSED:          per step, 'is THIS step valid? YES/NO', aggregate valid iff all YES  (STEPS calls)
  SCAFFOLDED-HOLISTIC: 'go through EACH step and check it, then answer YES/NO'  (one call) -- THE CONTROL

Three honest outcomes:
  - decomposed >> holistic AND decomposed >> scaffolded  -> decomposition (per-step ISOLATION) genuinely
    helps beyond compute and beyond a step-by-step prompt. A real, non-trivial effect.
  - scaffolded ~ decomposed >> holistic  -> the win is 'force step scrutiny', achievable in ONE call with
    the right prompt; decomposition per se buys nothing (a prompt fix, not a structural one).
  - all ~ equal  -> decomposition doesn't help even here; the whole apparent advantage was compute/prompting.

Cross-family (deepseek-v4-flash + kimi-k2.6) + Claude inline (owner rule: don't conclude on one family).
temperature 0 where allowed, ample tokens, 429 backoff. MIT.
Run: python mnemo/probes/decomposition_subtle_errors.py"""
import os, re, json, time, random, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

random.seed(20260703)
STEPS = 4
N = 24                     # 12 valid + 12 invalid
_ENVP = os.path.join(os.path.dirname(__file__), "..", "..", "server", ".env")
_env = {}
for ln in open(_ENVP, encoding="utf-8"):
    m = re.match(r'\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$', ln)
    if m:
        _env[m.group(1)] = m.group(2).strip().strip('"').strip("'")

# plausible atomic statements (cause/effect flavored so affirming-the-consequent is tempting)
POOL = [
    "the database is corrupted", "queries return errors", "the cache was flushed", "latency spiked",
    "the deploy failed", "the health check is red", "the disk is full", "writes are rejected",
    "the certificate expired", "clients see TLS warnings", "the queue is backed up", "consumers lag",
    "a migration ran", "the schema changed", "the load balancer drained a node", "traffic shifted",
    "an index was dropped", "a scan went full-table", "the feature flag is on", "the new path executes",
    "memory is leaking", "the pod restarted", "the token is invalid", "auth returns 401",
]


def make_problem(invalid, rng):
    """Build a STEPS-step CHAINED argument that derives p1..pK from the given fact p0. Step i concludes p_i
    using p_{i-1} (given or prior-derived) and a conditional between them.
      MP-valid step i:  Rule 'If p_{i-1} then p_i' + p_{i-1}  =>  p_i        (modus ponens)
      AC-invalid step i: Rule 'If p_i then p_{i-1}' (REVERSED) + p_{i-1}  =>  p_i   (affirming the consequent)
    The conclusion p_i is FRESH at each step (not otherwise given) and FEEDS the rest of the chain, so an
    invalid step is entangled in a coherent narrative yet its ground truth is unambiguous. At most one AC."""
    props = rng.sample(POOL, STEPS + 1)          # p0..pSTEPS, all distinct
    premises, steps, rules = [f"Fact: {props[0].capitalize()}."], [], []
    fallacy_at = rng.randrange(STEPS) if invalid else -1
    for i in range(STEPS):
        ante, cons = props[i], props[i + 1]      # the chain goes ante -> cons; step concludes `cons`
        if i == fallacy_at:
            premises.append(f"Rule: If {cons}, then {ante}.")     # REVERSED rule
            steps.append(f"Therefore, {cons}.")                    # conclude cons from ante + (cons->ante) = AC
            rules.append("AC-invalid")
        else:
            premises.append(f"Rule: If {ante}, then {cons}.")      # forward rule
            steps.append(f"Therefore, {cons}.")                    # conclude cons from ante + (ante->cons) = MP
            rules.append("MP-valid")
    # DISTRACTOR rules over FRESH props (not in the chain) -> pure clutter that raises the premise-matching
    # load without changing ground truth (they can never license a chain step). 3 of them.
    used = set(props)
    spare = [p for p in POOL if p not in used]
    rng.shuffle(spare)
    for k in range(0, min(6, len(spare)) - 1, 2):
        premises.append(f"Rule: If {spare[k]}, then {spare[k+1]}.")
    # shuffle the Rule premises (keep the Fact first) so the judge must MATCH each step to its rule
    fact, rulep = premises[0], premises[1:]
    rng.shuffle(rulep)
    premises = [fact] + rulep
    return premises, steps, rules


def render(premises, steps):
    body = "\n".join(premises)
    dsteps = "\n".join(f"Step {i+1}: {s}" for i, s in enumerate(steps))
    return f"Premises:\n{body}\n\nDerivation:\n{dsteps}"


# ── backends (ample tokens) ──
def deepseek_ask(prompt, mx=1500):
    body = json.dumps({"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": mx, "temperature": 0}).encode()
    return _post(_env["AGORA_API_BASE_URL"].rstrip("/") + "/chat/completions",
                 {"Authorization": f"Bearer {_env['AGORA_API_KEY']}", "Content-Type": "application/json"}, body, "ds")


def kimi_ask(prompt, mx=3000):
    body = json.dumps({"model": "kimi-k2.6:cloud", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": mx, "temperature": 0}).encode()
    return _post("http://localhost:11434/v1/chat/completions",
                 {"Authorization": f"Bearer {_env.get('AGORA_REASONING_KEY','local')}", "Content-Type": "application/json"}, body, "ds")


def _post(url, headers, body, kind, tries=5):
    for i in range(tries):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=180).read())
            return (r["choices"][0]["message"]["content"] or "").strip()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < tries - 1:
                time.sleep(2 * (i + 1) + random.random()); continue
            raise
        except Exception:
            if i < tries - 1:
                time.sleep(1.5 * (i + 1)); continue
            raise
    return ""


BACKENDS = {"deepseek-v4-flash": deepseek_ask, "kimi-k2.6": kimi_ask}


def yesno(txt):
    t = txt.strip().lower()
    m = re.findall(r"\b(yes|no|valid|invalid)\b", t)
    if m:
        last = m[-1]
        return last in ("yes", "valid")
    return None


# HINT-FREE prompts (v2): do NOT name the fallacy — naming it makes holistic detection trivial and hides
# any anchoring effect. Just ask whether the inference(s) are logically valid. Same wording across arms so
# the only difference is holistic-whole vs scaffolded-in-one-call vs decomposed-per-step.
def holistic_prompt(premises, steps):
    return (render(premises, steps) + "\n\nDoes each step follow by valid logical deduction from the premises "
            "and the earlier steps? Answer with exactly one word: YES (every step is logically valid) or "
            "NO (at least one step does not logically follow).")


def scaffold_prompt(premises, steps):
    return (render(premises, steps) + "\n\nCheck EACH step one at a time: does it follow by valid logical "
            "deduction from the premises and earlier steps? After checking every step, answer on a final line "
            "with exactly one word: YES (all valid) or NO (at least one does not follow).")


def step_prompt(premises, steps, i):
    body = "\n".join(premises)
    prior = "\n".join(f"Step {k+1}: {s}" for k, s in enumerate(steps[:i]))
    return (f"Premises:\n{body}\n" + (f"\nEstablished so far:\n{prior}\n" if prior else "") +
            f"\nProposed step: {steps[i]}\n\nDoes this proposed step follow by valid logical deduction from the "
            "premises and what is established so far? Answer with exactly one word: YES (valid) or NO (does not follow).")


def eval_backend(name):
    fn = BACKENDS[name]
    rng = random.Random(hash(name) & 0xffff)
    probs = []
    for j in range(N):
        invalid = (j % 2 == 1)
        premises, steps, rules = make_problem(invalid, rng)
        probs.append((not invalid, premises, steps, rules))   # valid_truth
    def judge_holistic(p): return yesno(fn(holistic_prompt(p[1], p[2])))
    def judge_scaffold(p): return yesno(fn(scaffold_prompt(p[1], p[2])))
    def judge_decomp(p):
        preds = [yesno(fn(step_prompt(p[1], p[2], i))) for i in range(len(p[2]))]
        return all(x is True for x in preds)                  # valid iff every step judged valid
    def run(judge):
        res = [None] * N
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(judge, probs[j]): j for j in range(N)}
            for f in as_completed(futs):
                res[futs[f]] = f.result()
        return res
    hol, sca, dec = run(judge_holistic), run(judge_scaffold), run(judge_decomp)
    def bacc(preds):
        pos = [(probs[j][0], preds[j]) for j in range(N) if probs[j][0]]       # valid args
        neg = [(probs[j][0], preds[j]) for j in range(N) if not probs[j][0]]   # invalid args
        tpr = sum(1 for t, p in pos if p is True) / max(1, len(pos))           # valid called valid
        tnr = sum(1 for t, p in neg if p is False) / max(1, len(neg))          # invalid caught
        return round(0.5 * (tpr + tnr), 3), round(tnr, 3)
    a_h, catch_h = bacc(hol); a_s, catch_s = bacc(sca); a_d, catch_d = bacc(dec)
    return {"acc_holistic": a_h, "acc_scaffold": a_s, "acc_decomposed": a_d,
            "fallacy_catch_holistic": catch_h, "fallacy_catch_scaffold": catch_s, "fallacy_catch_decomposed": catch_d}


results = {}
t0 = time.time()
for name in BACKENDS:
    print(f"\n=== {name} (ample tokens; {N} args, {STEPS} steps) ===", flush=True)
    try:
        results[name] = eval_backend(name)
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {str(e)[:120]}", flush=True); continue
    r = results[name]
    print(f"  balanced acc:   holistic={r['acc_holistic']:.3f}  scaffold={r['acc_scaffold']:.3f}  decomposed={r['acc_decomposed']:.3f}", flush=True)
    print(f"  fallacy-catch:  holistic={r['fallacy_catch_holistic']:.2f}  scaffold={r['fallacy_catch_scaffold']:.2f}  decomposed={r['fallacy_catch_decomposed']:.2f}", flush=True)
    print(f"  (t+{time.time()-t0:.0f}s)", flush=True)

print("\n=== VERDICT ===")
verdicts = {}
for name in results:
    r = results[name]
    dh = r["acc_decomposed"] - r["acc_holistic"]
    ds = r["acc_decomposed"] - r["acc_scaffold"]
    if dh > 0.15 and ds > 0.10:
        v = f"DECOMPOSITION HELPS (real, beyond compute+prompt): dec-hol={dh:+.2f}, dec-scaffold={ds:+.2f}"
    elif dh > 0.15 and ds <= 0.10:
        v = f"PROMPT, NOT DECOMPOSITION: scaffolded holistic ~= decomposed (dec-hol={dh:+.2f} but dec-scaffold={ds:+.2f})"
    else:
        v = f"NO DECOMPOSITION ADVANTAGE even on subtle errors (dec-hol={dh:+.2f})"
    verdicts[name] = v
    print(f"{name}: {v}")

out = {"design": "chained propositional args, planted affirming-the-consequent, holistic vs decomposed vs scaffolded, ample tokens",
       "steps": STEPS, "n": N, "results": results, "verdicts": verdicts}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "decomposition_subtle_errors_result.json"), "w"), indent=1)
print("\nsaved: mnemo/probes/decomposition_subtle_errors_result.json")
