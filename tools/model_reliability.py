"""
Reliability benchmark — what the first benchmark MISSED: tail latency + failure rate under
repeated load. A model can have a great mean and still stall past the caller's timeout on the
p95 call, which is exactly what breaks the dungeon (timeout -> empty -> LLM_quests=0).

For each candidate: fire N sequential realistic calls (a short planning JSON task, like the
dungeon's own), record EVERY latency, count timeouts/empties/invalid-JSON. Report p50/p90/p95/max
and a verdict against the dungeon's 45s per-call timeout.
"""
import json, time, urllib.request, urllib.error, re, statistics as st

KEY = [re.match(r"AGORA_API_KEY=(\S+)", l).group(1)
       for l in open("server/.env", encoding="utf-8") if l.startswith("AGORA_API_KEY=")][0]

DUNGEON_TIMEOUT = 45          # the dungeon's real per-call timeout (mcp_server.py:658)
N = 12                        # calls per model
CANDIDATES = ["deepseek-v4-flash", "glm-4.7", "gemini-3-flash-preview", "qwen3-next:80b", "gpt-oss:120b"]

PROMPT = ("You are an agent in a research dungeon. Output ONLY minified JSON: "
          '{"quests":[{"title":str,"goal":str}]} with exactly 2 short quests about mapping '
          "knowledge gaps. No prose, no markdown.")


def call(model, timeout):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": PROMPT}],
                       "max_tokens": 300, "temperature": 0.4, "stream": False}).encode()
    req = urllib.request.Request("https://ollama.com/v1/chat/completions", data=body,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout + 25)   # measure true latency even past dungeon timeout
        d = json.load(r)
        dt = time.time() - t0
        txt = (d.get("choices", [{}])[0].get("message", {}) or {}).get("content", "") or ""
        ok_json = bool(re.search(r'"quests"\s*:\s*\[', txt))
        return dt, ("empty" if not txt.strip() else ("ok" if ok_json else "badjson"))
    except Exception as e:
        return time.time() - t0, f"err:{str(e)[:40]}"


print(f"reliability: {N} calls/model, dungeon timeout = {DUNGEON_TIMEOUT}s\n")
print(f"{'model':24s} {'p50':>6} {'p90':>6} {'p95':>6} {'max':>6}  {'timeouts':>8} {'empties':>7} {'badjson':>7}")
results = {}
for m in CANDIDATES:
    lats, states = [], []
    for _ in range(N):
        dt, state = call(m, DUNGEON_TIMEOUT)
        lats.append(dt); states.append(state)
    lats_sorted = sorted(lats)
    def pct(p): return lats_sorted[min(len(lats_sorted) - 1, int(p / 100 * len(lats_sorted)))]
    timeouts = sum(1 for l in lats if l > DUNGEON_TIMEOUT) + sum(1 for s in states if s.startswith("err"))
    empties = sum(1 for s in states if s == "empty")
    badjson = sum(1 for s in states if s == "badjson")
    results[m] = {"p50": pct(50), "p95": pct(95), "max": max(lats),
                  "timeouts": timeouts, "empties": empties, "badjson": badjson}
    print(f"{m:24s} {pct(50):6.1f} {pct(90):6.1f} {pct(95):6.1f} {max(lats):6.1f}  "
          f"{timeouts:8d} {empties:7d} {badjson:7d}")

print("\nverdict (dungeon needs p95 well under 45s + 0 timeouts/empties + valid JSON):")
for m, r in results.items():
    fails = r["timeouts"] + r["empties"]
    ok = r["p95"] < 25 and fails == 0 and r["badjson"] <= 1
    print(f"  {m:24s} {'SUITABLE' if ok else 'RISKY'}  (p95={r['p95']:.1f}s, "
          f"{r['timeouts']} timeouts, {r['empties']} empties, {r['badjson']} badjson)")
