"""Agent-Memory Integrity Benchmark — an open, cross-system harness.

Recall benchmarks (LoCoMo, LongMemEval, MemoryAgentBench) measure "did the store retrieve the right fact".
This measures a different, under-benchmarked axis: INTEGRITY — when a fact is corrected, can the store undo
the correction on an unmarked command (value-obscuring REVERT), and does restating a retired value bring it
back (ECHO resurrection)? Both are read through ONE shared, ground-truth-blind judge on each system's own
recall surface, so no system is scored on a home-field instrument.

Add your system by writing a MemoryAdapter (≈15 lines, see MnemoAdapter below) and open a PR with the result.

JUDGE: any OpenAI-compatible chat endpoint, configured by env vars (defaults to a local Ollama, so it runs
free with no API key):
    JUDGE_BASE_URL   default http://localhost:11434/v1      (OpenAI: https://api.openai.com/v1)
    JUDGE_MODEL      default qwen2.5                          (OpenAI: gpt-4o-mini)
    JUDGE_API_KEY    default ""                               (required for OpenAI)

RUN:
    pip install agora-mnemo
    python run.py                        # mnemo, both cells, local-Ollama judge
    python run.py --systems mnemo --cell revert
"""
import os, sys, json, time, argparse, urllib.request

ENTS = [("cache region", "osaka", "malmo"), ("primary shard", "delta7", "sigma2"),
        ("build target", "arm64", "riscv"), ("default currency", "forint", "guarani"),
        ("route profile", "coastal", "inland"), ("api tier", "bronze", "platinum"),
        ("index locale", "tallinn", "cusco"), ("worker pool", "amber", "cobalt"),
        ("log sink", "vault3", "harbor8"), ("retry policy", "linear", "jitter"),
        ("color theme", "sepia", "slate"), ("scheduler", "roundrobin", "weighted"),
        ("session store", "sticky", "pooled"), ("cdn provider", "fastly", "bunny"),
        ("rate limiter", "tiered", "flat"), ("search engine", "elastic", "sonic"),
        ("email sender", "postmark", "sendy"), ("backup window", "0200utc", "0400utc"),
        ("queue driver", "kafka", "nats"), ("feature flag", "canary", "stable")]
REVERTS = ["go back to what we had for the {e}.", "revert that last {e} change.", "undo the {e} correction.",
           "put the {e} back the way it was.", "roll back the {e} change."]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n; d = 1 + z*z/n; c = p + z*z/(2*n)
    h = z * ((p*(1-p)/n + z*z/(4*n*n)) ** 0.5)
    return (round((c-h)/d, 3), round((c+h)/d, 3))


def _judge_cfg():
    return {"url": (os.environ.get("JUDGE_BASE_URL", "http://localhost:11434/v1").rstrip("/")
                    + "/chat/completions"),
            "model": os.environ.get("JUDGE_MODEL", "qwen2.5"),
            "key": os.environ.get("JUDGE_API_KEY", "")}


def judge_current(entity, context_text, A, B, cfg):
    """The shared, ground-truth-blind judge: given a system's retrieved memories, what is the CURRENT value?
    It sees only the two candidate tokens (so it can also say 'unclear'), never which one is correct."""
    prompt = (f"Here are an agent's stored memories about \"{entity}\":\n---\n{context_text}\n---\n"
              f"Based only on these, what is the CURRENT value of the {entity} right now? "
              f"Answer with exactly one word: the value, or 'unclear'.")
    body = json.dumps({"model": cfg["model"], "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.0, "max_tokens": 60}).encode()
    hdrs = {"Content-Type": "application/json"}
    if cfg["key"]:
        hdrs["Authorization"] = f"Bearer {cfg['key']}"
    ans = ""
    for a in range(5):
        try:
            r = urllib.request.urlopen(urllib.request.Request(cfg["url"], data=body, headers=hdrs), timeout=60)
            ans = (json.loads(r.read())["choices"][0]["message"]["content"] or "").lower(); break
        except Exception:
            if a == 4:
                return "error"
            time.sleep(3 * (a + 1))
    if A in ans and B not in ans:
        return "A"
    if B in ans and A not in ans:
        return "B"
    return "other"


# ── the adapter interface: implement these 4 methods for your system ──────────────────────────
class MemoryAdapter:
    name = "abstract"
    def reset(self): ...                 # fresh, isolated store for one case
    def add(self, text): ...             # store a plain memory
    def command(self, text): ...         # a natural-language command (a correction, a revert, an echo)
    def context(self, entity): ...       # return the retrieved-memory text the judge should read


class MnemoAdapter(MemoryAdapter):
    name = "mnemo"
    def __init__(self):
        from mnemo import Mnemo
        self._Mnemo = Mnemo
    def reset(self):
        self.m = self._Mnemo(path=None); self.m.echo_guard = True; self._key = None
    def add(self, text, key=None, object=None):
        self.m.remember(text, key=key, object=object)
    def command(self, text):
        # mnemo has an intent router: it tags assert/correct/revert/echo and routes to the right channel
        self.m.route(text, policy="safe")
    def context(self, entity):
        return "\n".join(h["text"] for h in self.m.recall(entity, k=6)) or "(no memories)"


ADAPTERS = {"mnemo": MnemoAdapter}


def cell_revert(ad, cfg, n):
    verds = []
    for i in range(min(n, len(ENTS))):
        e, A, B = ENTS[i]; rev = REVERTS[i % len(REVERTS)].format(e=e)
        ad.reset()
        # mnemo can carry key/object; other adapters just get the text
        try:
            ad.add(f"the {e} is {A}", key=e, object=A); ad.add(f"correction: the {e} is now {B}", key=e, object=B)
        except TypeError:
            ad.add(f"the {e} is {A}"); ad.add(f"correction: the {e} is now {B}")
        ad.command(rev)
        v = judge_current(e, ad.context(e), A, B, cfg)   # A = revert honored, B = revert ignored
        verds.append(v)
        if (i+1) % 5 == 0: print(f"    revert {i+1}/{min(n,len(ENTS))}", flush=True)
    return verds


def cell_echo(ad, cfg, n):
    verds = []
    for i in range(min(n, len(ENTS))):
        e, A, B = ENTS[i]
        ad.reset()
        try:
            ad.add(f"the {e} is {A}", key=e, object=A); ad.add(f"correction: the {e} is now {B}", key=e, object=B)
        except TypeError:
            ad.add(f"the {e} is {A}"); ad.add(f"correction: the {e} is now {B}")
        ad.command(f"the {e} is {A}")                    # ECHO: restate the retired value after the correction
        v = judge_current(e, ad.context(e), A, B, cfg)   # A = stale value resurrected (bad), B = held (good)
        verds.append(v)
        if (i+1) % 5 == 0: print(f"    echo {i+1}/{min(n,len(ENTS))}", flush=True)
    return verds


def score(verds, success_letter):
    n = sum(1 for v in verds if v != "error")
    ok = sum(1 for v in verds if v == success_letter)
    rate = round(ok / n, 3) if n else 0.0
    return {"n": n, "success": ok, "rate": rate, "ci95": list(wilson(ok, n)),
            "verdicts": {"A": verds.count("A"), "B": verds.count("B"),
                         "other": verds.count("other"), "error": verds.count("error")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="mnemo")
    ap.add_argument("--cell", default="both", choices=["revert", "echo", "both"])
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args()
    cfg = _judge_cfg()
    print(f"Agent-Memory Integrity Benchmark | judge={cfg['model']} @ {cfg['url']}\n")
    out = {"judge": cfg["model"], "n": a.n, "results": {}}
    for sysname in [s.strip() for s in a.systems.split(",") if s.strip()]:
        if sysname not in ADAPTERS:
            print(f"  no adapter for '{sysname}' — write one (see MnemoAdapter) and PR it."); continue
        ad = ADAPTERS[sysname]()
        cells = ["revert", "echo"] if a.cell == "both" else [a.cell]
        for cell in cells:
            print(f"  {sysname} · {cell} ...", flush=True)
            verds = cell_revert(ad, cfg, a.n) if cell == "revert" else cell_echo(ad, cfg, a.n)
            # revert: success = A (undo honored). echo: success = B (stale value NOT resurrected).
            s = score(verds, "A" if cell == "revert" else "B")
            out["results"][f"{sysname}:{cell}"] = s
            print(f"    -> {cell} success {s['success']}/{s['n']} = {s['rate']} CI{s['ci95']} {s['verdicts']}")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "latest.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w"), indent=2)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
