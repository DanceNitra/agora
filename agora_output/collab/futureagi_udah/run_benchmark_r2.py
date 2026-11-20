"""Round 2 runner: per-turn reference labels, four Future AGI rubrics, and U/D/A/H, on 17 cases x 2 variants.

Judge calls (claude-opus-5-5) are cached in r2_judge_cache.json, so a stopped run resumes.
- labels: one call per conversation and repeat; the judge rates each assistant turn for
  hedging (0-1), drift from the conversation's goal (0-1) and self-correction (true/false).
- rubrics: conversation_coherence, persona_consistency, customer_agent_clarification_seeking,
  customer_agent_loop_detection, rule text unchanged, one call per conversation.
Writes r2_results.json.
"""
import json
import os
import re
import sys
import time
import uuid

import yaml

import importlib
import udah_adapter as A

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.environ.get("BENCH", "benchmark_r2")  # benchmark_r2 or benchmark_v2
R = importlib.import_module(BENCH)
TAG = "r2" if BENCH == "benchmark_r2" else BENCH.replace("benchmark_", "")
CACHE = os.path.join(HERE, "%s_judge_cache.json" % TAG)
MODEL = os.environ.get("JUDGE_MODEL", "claude-opus-5-5")
LABEL_REPEATS = int(os.environ.get("LABEL_REPEATS", "3"))
RUBRICS = {"conversation_coherence": "conversation_coherence.yaml", "persona_consistency": "r2_persona_consistency.yaml",
           "clarification_seeking": "r2_customer_agent_clarification_seeking.yaml",
           "loop_detection": "r2_customer_agent_loop_detection.yaml"}
LABEL_PROMPT = """Below is a conversation. Rate EACH assistant turn on three things, judging only that turn
against what came before it:
- hedging: 0.0 if the turn commits plainly, 1.0 if it is full of uncertainty, qualifiers or hesitation.
- drift: 0.0 if the turn stays on the conversation's established goal, role and tone, 1.0 if it moves away
  from them without being asked.
- self_correction: true if the turn retracts or revises something the assistant said earlier.

Assistant turns are numbered in order, starting at 1.

<conversation>
{conv}
</conversation>

Return only a JSON list, one object per assistant turn:
[{{"turn": 1, "hedging": 0.0, "drift": 0.0, "self_correction": false}}, ...]
(run id {nonce})"""


USAGE_CACHE = [0, 0]   # prompt-cache tokens this run: [read, written]


def conv_text(case):
    out, n = [], 0
    for role, text in case["msgs"]:
        if role == "assistant":
            n += 1
            out.append("assistant (turn %d): %s" % (n, text))
        else:
            out.append("user: %s" % text)
    return "\n".join(out)


def cached_content(prompt, cut):
    """Splits the prompt after `cut` and marks the first part for the prompt cache.

    The label prompt repeats the same instructions and conversation LABEL_REPEATS times; only
    the format line and the run id change. With the marker, repeats 2..k read the shared part
    from the cache. The cache stores the processed prefix, never an answer, so every repeat is
    still a new judgement. A prefix under 512 tokens (Opus 5.5) is not cached and costs nothing
    extra.
    """
    i = prompt.find(cut)
    if i < 0:
        return prompt
    i += len(cut)
    return [{"type": "text", "text": prompt[:i], "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": prompt[i:]}]


def ask(client, prompt):
    msg = client.messages.create(model=MODEL, max_tokens=3000, messages=[{"role": "user", "content": prompt}])
    u = msg.usage
    USAGE_CACHE[0] += u.cache_read_input_tokens or 0
    USAGE_CACHE[1] += u.cache_creation_input_tokens or 0
    return "".join(b.text for b in msg.content if b.type == "text"), [msg.usage.input_tokens, msg.usage.output_tokens]


def run_judge():
    import anthropic
    env = dict(l.split("=", 1) for l in open(os.path.join(HERE, "..", "..", "..", "server", ".env"),
               encoding="utf-8").read().splitlines() if "=" in l and not l.startswith("#"))
    client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"].strip())
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    variants = R.all_variants()
    todo = [("labels", v, k) for v in variants for k in range(LABEL_REPEATS)] + \
           [(r, v, 0) for r in RUBRICS for v in variants]
    t0 = time.time()
    for i, (kind, v, rep) in enumerate(todo, 1):
        key = "%s|%s|%s|%d" % (MODEL, kind, v["id"], rep)
        if key in cache:
            continue
        if kind == "labels":
            prompt = cached_content(LABEL_PROMPT.format(conv=conv_text(v), nonce=uuid.uuid4().hex[:8]),
                                    "</conversation>\n")
        else:
            rule = yaml.safe_load(open(os.path.join(HERE, RUBRICS[kind]), encoding="utf-8"))["config"]["rule_prompt"]
            conv = "\n".join("%s: %s" % tuple(m) for m in v["msgs"])
            prompt = (rule.replace("{{conversation}}", conv) +
                      '\n\nReturn only a JSON object: {"result": <your score, choice or Passed/Failed>, '
                      '"reason": "<one sentence>"}.\n(run id %s)' % uuid.uuid4().hex[:8])
        text, usage = ask(client, prompt)
        m = re.search(r"\[.*\]" if kind == "labels" else r"\{.*\}", text, re.S)
        try:
            parsed = json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            parsed = None
        cache[key] = {"parsed": parsed, "raw": text[:600], "usage": usage}
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("%3d/%d %6.1fs %-22s %-7s rep %d ok=%s cache read %d write %d" % (
            i, len(todo), time.time() - t0, kind, v["id"], rep + 1, parsed is not None,
            USAGE_CACHE[0], USAGE_CACHE[1]), flush=True)
    return cache


def spearman(x, y):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2.0
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (vx * vy) if vx and vy else None


def main():
    cache = run_judge() if "--judge" in sys.argv else json.load(open(CACHE, encoding="utf-8"))
    rows, pairs_u, pairs_d = [], [], []
    for v in R.all_variants():
        scored = A.score_turns(A.build_turns(A.load_spans(json.dumps(R.spans(v)))))
        labels = [cache.get("%s|labels|%s|%d" % (MODEL, v["id"], k), {}).get("parsed") for k in range(LABEL_REPEATS)]
        labels = [l for l in labels if isinstance(l, list)]
        for s in scored:
            got = [x for l in labels for x in l if isinstance(x, dict) and x.get("turn") == s["turn"]]
            if got:
                h = sum(float(x["hedging"]) for x in got) / len(got)
                d = sum(float(x["drift"]) for x in got) / len(got)
                sc = sum(bool(x["self_correction"]) for x in got) / len(got)
                pairs_u.append((s["U"], h))
                pairs_d.append((s["D"], d))
                s.update(label_hedging=round(h, 3), label_drift=round(d, 3), label_self_correction=round(sc, 3))
        rub = {r: cache.get("%s|%s|%s|0" % (MODEL, r, v["id"]), {}).get("parsed") for r in RUBRICS}
        rows.append({"id": v["id"], "turns": scored, "rubrics": {k: (x or {}).get("result") for k, x in rub.items()},
                     "rubric_reasons": {k: (x or {}).get("reason") for k, x in rub.items()}})
    usage = [c["usage"] for k, c in cache.items() if k.startswith(MODEL + "|")]
    summary = {"judge_model": MODEL, "cases": len(R.CASES), "variants": len(rows),
               "turns_with_labels": len(pairs_u),
               "spearman_U_vs_hedging": spearman([a for a, b in pairs_u], [b for a, b in pairs_u]),
               "spearman_D_vs_drift": spearman([a for a, b in pairs_d], [b for a, b in pairs_d]),
               "flip_points": sum(t["is_flip_point"] for r in rows for t in r["turns"]),
               "tokens_in": sum(u[0] for u in usage), "tokens_out": sum(u[1] for u in usage)}
    json.dump({"summary": summary, "rows": rows}, open(os.path.join(HERE, "%s_results.json" % TAG), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
