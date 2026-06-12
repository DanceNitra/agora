"""
Ollama Cloud model benchmark for Agora — find a model cheaper than deepseek-v4-pro but
better than deepseek-v4-flash on Agora's actual workload.

Two representative tasks:
  R) Brain reasoning/synthesis: judge a claim, give a falsifiable analysis (the loop's core work).
  J) Dungeon structured-output: emit STRICT JSON for a quest plan (the dungeon's core work).

Metrics per (model, task): latency s, completion tokens (usage), output text (for quality judging),
and JSON-valid flag for task J. Costs are token-based; per-model price filled from web research.
"""
import json, time, urllib.request, os, re, sys

BASE = "https://ollama.com/v1/chat/completions"
KEY = None
for line in open(os.path.join(os.path.dirname(__file__), "..", "server", ".env"), encoding="utf-8"):
    m = re.match(r"AGORA_API_KEY=(\S+)", line)
    if m: KEY = m.group(1)
assert KEY, "no key"

MODELS = [
    "deepseek-v4-flash",   # lower anchor
    "deepseek-v4-pro",     # upper anchor (current)
    "deepseek-v3.2",
    "glm-4.6",
    "glm-4.7",
    "qwen3-next:80b",
    "gpt-oss:120b",
    "gemini-3-flash-preview",
    "nemotron-3-super",
    "minimax-m2.5",
]

TASK_R = (
    "You are a rigorous research analyst. Claim: 'Adding more independent reviewers to a decision "
    "always improves accuracy.' In <=140 words: state ONE precise condition under which the claim "
    "FAILS, name the mechanism, and give a concrete falsifiable test (a measurable quantity and the "
    "direction that would refute the claim). Be specific and quantitative; no preamble."
)
TASK_J = (
    "Output ONLY valid minified JSON (no markdown, no prose) for a dungeon quest plan with keys: "
    "title (string), steps (array of exactly 3 strings), difficulty (one of 'easy','medium','hard'), "
    "reward_xp (integer 10-100). Quest theme: a scout mapping an abandoned data-center."
)
TASKS = [("R", TASK_R, 320), ("J", TASK_J, 220)]

def call(model, prompt, max_tokens):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": False,
    }).encode()
    req = urllib.request.Request(BASE, data=body, headers={
        "Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=120)
        d = json.load(r)
        dt = time.time() - t0
        txt = (d.get("choices", [{}])[0].get("message", {}) or {}).get("content", "") or ""
        usage = d.get("usage", {}) or {}
        return {"ok": True, "s": round(dt, 1), "ctok": usage.get("completion_tokens"),
                "ptok": usage.get("prompt_tokens"), "text": txt.strip()}
    except Exception as e:
        return {"ok": False, "s": round(time.time()-t0, 1), "err": str(e)[:200]}

def json_valid(txt):
    s = txt.strip()
    s = re.sub(r"^```(json)?|```$", "", s, flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if not m: return False, None
    try:
        obj = json.loads(m.group(0))
        ok = (isinstance(obj.get("title"), str) and isinstance(obj.get("steps"), list)
              and len(obj["steps"]) == 3 and obj.get("difficulty") in ("easy","medium","hard")
              and isinstance(obj.get("reward_xp"), int) and 10 <= obj["reward_xp"] <= 100)
        return ok, obj
    except Exception:
        return False, None

results = {}
for model in MODELS:
    results[model] = {}
    for tid, prompt, mt in TASKS:
        res = call(model, prompt, mt)
        if tid == "J" and res.get("ok"):
            jv, _ = json_valid(res["text"])
            res["json_valid"] = jv
        results[model][tid] = res
        flag = "OK" if res.get("ok") else "ERR"
        extra = f" jsonOK={res.get('json_valid')}" if tid == "J" and res.get("ok") else ""
        print(f"{model:24s} [{tid}] {flag} {res.get('s'):>5}s ctok={res.get('ctok')}{extra}"
              + ("" if res.get("ok") else f"  {res.get('err')}"))
        sys.stdout.flush()

out = os.path.join(os.path.dirname(__file__), "..", "agora_output", "model_bench_results.json")
json.dump(results, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nsaved", out)
