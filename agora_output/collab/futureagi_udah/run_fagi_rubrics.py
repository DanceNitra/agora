"""Run Future AGI's own Conversation Coherence and Conversation Resolution rubrics as an LLM judge.

The rubric text (rule_prompt) is read unchanged from future-agi/future-agi
futureagi/model_hub/system_evals/agent/*.yaml. Their platform uses its own judge
model and output wrapper; this script uses deepseek-v4-flash on Ollama cloud and
asks for {"score", "reason"} JSON, so the numbers are a proxy with their rubric.
Writes fagi_rubric_results.json and prints one line per call.
"""
import json
import os
import re
import sys
import time
import urllib.request
import uuid

import yaml

import make_refund_trace as T

ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "server", ".env")
env = dict(l.split("=", 1) for l in open(ENV, encoding="utf-8").read().splitlines() if "=" in l and not l.startswith("#"))
BASE, KEY = env["AGORA_API_BASE_URL"].strip(), env["AGORA_API_KEY"].strip()
MODEL = os.environ.get("JUDGE_MODEL", "deepseek-v4.1-flash")
REPEATS = int(os.environ.get("REPEATS", "3"))

CONTROL_A3 = ("I understand. Since it has been 8 days, you are well inside the 30-day window, "
              "so the full refund is approved and I have started it.")
DIALOGUES = {
    "refund_contradiction": [(T.U1, T.A1), (T.U2, T.A2), (T.U3, T.A3)],
    "control_consistent": [(T.U1, T.A1), (T.U2, T.A2), (T.U3, CONTROL_A3)],
}
WRAP = ('\n\nReturn only a JSON object: {"score": <a number from 0.0 to 1.0>, '
        '"reason": "<one sentence>"}.')


def conversation(pairs):
    return "\n".join("user: %s\nassistant: %s" % p for p in pairs)


def call(prompt):
    if MODEL.startswith("claude-"):
        import anthropic
        client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"].strip())
        msg = client.messages.create(model=MODEL, max_tokens=2000, messages=[{"role": "user", "content": prompt}])
        USAGE.append((msg.usage.input_tokens, msg.usage.output_tokens))
        return "".join(b.text for b in msg.content if b.type == "text"), msg.stop_reason
    return call_ollama(prompt)


USAGE = []


def call_ollama(prompt):
    body = json.dumps({"model": MODEL, "max_tokens": 16000,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(BASE.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.load(r)
    return out["choices"][0]["message"]["content"] or "", out["choices"][0].get("finish_reason")


rows, t0 = [], time.time()
total = 2 * len(DIALOGUES) * REPEATS
for name in ("conversation_coherence", "conversation_resolution"):
    rule = yaml.safe_load(open(name + ".yaml", encoding="utf-8"))["config"]["rule_prompt"]
    for dname, pairs in DIALOGUES.items():
        for rep in range(REPEATS):
            nonce = uuid.uuid4().hex[:8]  # a unique prompt per call, so no cache hit
            prompt = rule.replace("{{conversation}}", conversation(pairs)) + WRAP + "\n(run id %s)" % nonce
            text, fin = call(prompt)
            m = re.search(r"\{.*\}", text, re.S)
            try:
                parsed = json.loads(m.group(0)) if m else {}
            except json.JSONDecodeError:
                parsed = {}
            rows.append({"rubric": name, "dialogue": dname, "repeat": rep + 1, "score": parsed.get("score"),
                         "reason": parsed.get("reason"), "finish_reason": fin, "raw": text[:500]})
            print("%2d/%d %5.1fs %-24s %-22s score=%s" % (len(rows), total, time.time() - t0, name, dname,
                                                          parsed.get("score")), flush=True)
print("tokens in/out:", sum(u[0] for u in USAGE), sum(u[1] for u in USAGE))
json.dump({"model": MODEL, "endpoint": "anthropic" if MODEL.startswith("claude-") else BASE, "usage": USAGE, "repeats": REPEATS, "rows": rows},
          open("fagi_rubric_results_%s.json" % MODEL.replace(":", "_"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
