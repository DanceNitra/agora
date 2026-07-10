"""Crucible c002 — severe test of the 'MCP tool-overload cliff at ~20 tools' claim.

THE CLAIM (Towards AI + dev.to + jenova.ai + lunar.dev, quoted as universal): agent tool-selection
accuracy 'falls off a cliff' past ~20 registered tools — a sharp threshold, not a smooth decline.
(Posts quote thresholds anywhere from 5 to 50 — the folklore signature.)

DESIGN (smallest faithful model of MCP tool selection):
  A pool of 100 synthetic MCP-style tools (name + one-line description) across domains,
  deterministic. Per trial: pick a target tool, phrase a user request that unambiguously needs it
  (paraphrased, not verbatim), register N-1 random distractors + the target (shuffled), ask the
  model to reply with ONLY the tool name. Accuracy vs N for N in {5, 10, 20, 30, 50, 80},
  TRIALS per N, two model families (deepseek-v4-flash primary, glm-5.2 secondary at 3 sizes).

VERDICT RULE (pre-stated):
  REPRODUCED if there is a sharp threshold near 20: accuracy plateaus (>=0.90) through N=20 and
    drops by >=25 points by N=30 on the primary model, with the secondary model agreeing on a
    near-20 cliff (threshold location within ~10 tools).
  FAILED if the decline is smooth (no >=25-point single-interval drop anywhere near 20), absent,
    or the threshold location differs strongly by model — i.e. the real effect exists but the
    'cliff at 20' constant is folklore.
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
KEY = env.get("AGORA_API_KEY") or env.get("OLLAMA_API_KEY")   # Ollama cloud only
API_URL = "https://ollama.com/v1/chat/completions"
PRIMARY = "deepseek-v4-flash"
SECONDARY = "glm-5.2"
SIZES = [5, 10, 20, 30, 50, 80]
SIZES_SECONDARY = [10, 30, 50]
TRIALS = int(os.getenv("C002_TRIALS", "40"))
TRIALS_SECONDARY = int(os.getenv("C002_TRIALS2", "25"))

VERBS = ["fetch", "create", "delete", "update", "list", "convert", "validate", "schedule",
         "search", "export"]
OBJS = ["invoice", "calendar event", "customer record", "image thumbnail", "database backup",
        "email draft", "git branch", "support ticket", "sensor reading", "pdf report"]

def build_pool():
    pool = []
    for v in VERBS:
        for o in OBJS:
            name = f"{v}_{o.replace(' ', '_')}"
            desc = f"{v.capitalize()} a {o} in the connected workspace."
            pool.append({"name": name, "desc": desc, "verb": v, "obj": o})
    return pool                                                    # 100 tools

REQ_TMPL = ["I need to {v} the {o}, can you handle that?",
            "please {v} a {o} for me right away",
            "could you go ahead and {v} that {o}?"]

def llm(model, prompt):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 2000, "temperature": 0}).encode()
    for a in range(4):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                API_URL, data=body, headers={"Authorization": f"Bearer {KEY}",
                                             "Content-Type": "application/json"}),
                timeout=120).read())
            return r["choices"][0]["message"]["content"]
        except Exception:
            if a == 3:
                return None
            time.sleep(4 * (a + 1))

def trial(model, pool, N, rng):
    target = rng.choice(pool)
    distract = rng.sample([t for t in pool if t is not target], N - 1)
    tools = distract + [target]
    rng.shuffle(tools)
    listing = "\n".join(f"- {t['name']}: {t['desc']}" for t in tools)
    req = rng.choice(REQ_TMPL).format(v=target["verb"], o=target["obj"])
    p = (f"You are an agent with these tools:\n{listing}\n\n"
         f"User request: \"{req}\"\n"
         f"Reply with ONLY the name of the single most appropriate tool.")
    out = llm(model, p) or ""
    # exact-name match anywhere in the (short) reply, but penalize listing multiple tools
    hits = [t["name"] for t in tools if t["name"] in out]
    return 1 if hits == [target["name"]] else 0

def boot_ci(xs, iters=5000, seed=0):
    rng = random.Random(seed); n = len(xs)
    bs = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return round(bs[int(0.025 * iters)], 3), round(bs[int(0.975 * iters)], 3)

def sweep(model, sizes, trials, pool, seed):
    rng = random.Random(seed)
    curve = {}
    t0 = time.time()
    for N in sizes:
        xs = [trial(model, pool, N, rng) for _ in range(trials)]
        curve[N] = {"acc": round(sum(xs) / len(xs), 3), "CI": boot_ci(xs)}
        print(f"  {model} N={N}: acc={curve[N]['acc']:.3f} CI={curve[N]['CI']} "
              f"({time.time()-t0:.0f}s)", flush=True)
    return curve

def main():
    pool = build_pool()
    out = {"claim_id": "c002-mcp-tool-cliff-at-20", "pool_size": len(pool),
           "trials_per_size": TRIALS, "models": {}}
    out["models"][PRIMARY] = sweep(PRIMARY, SIZES, TRIALS, pool, seed=1)
    out["models"][SECONDARY] = sweep(SECONDARY, SIZES_SECONDARY, TRIALS_SECONDARY, pool, seed=2)
    json.dump(out, open(os.path.join(HERE, "result.json"), "w"), indent=2)
    print("\n" + json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
