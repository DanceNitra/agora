"""Score Guanghao's 20 cases with U/D/A/H, the commitment check, and Future AGI's two rubrics.

U/D/A/H and the commitment check are deterministic and free. The rubrics run as an
LLM judge (JUDGE_MODEL, default claude-opus-5-5) only with --judge; each call is
cached in benchmark_judge_cache.json, so an interrupted run resumes.
Writes benchmark_results.json and prints a progress line per judge call.
"""
import json
import os
import re
import sys
import time
import uuid

import yaml

import benchmark_20 as B
import udah_adapter as A

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "benchmark_judge_cache.json")
MODEL = os.environ.get("JUDGE_MODEL", "claude-opus-5-5")
REPEATS = int(os.environ.get("REPEATS", "3"))
RUBRICS = ("conversation_coherence", "conversation_resolution")
WRAP = ('\n\nReturn only a JSON object: {"score": <a number from 0.0 to 1.0>, '
        '"reason": "<one sentence>"}.')


def deterministic(case):
    rows = A.score_turns(A.build_turns(A.load_spans(json.dumps(B.spans(case)))),
                         use_inspeximus=False, contradictions=True)
    return {"flip_turns": [r["turn"] for r in rows if r["is_flip_point"]],
            "conflict_turns": [r["turn"] for r in rows if r["self_contradiction"]],
            "conflicts": [c for r in rows for c in r["conflicts"]],
            "udah": [{k: r[k] for k in ("turn", "U", "D", "A", "H")} for r in rows]}


def judge_all():
    import anthropic
    env = dict(l.split("=", 1) for l in open(os.path.join(HERE, "..", "..", "..", "server", ".env"),
               encoding="utf-8").read().splitlines() if "=" in l and not l.startswith("#"))
    client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"].strip())
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    todo = [(r, c, k) for r in RUBRICS for c in B.CASES for k in range(REPEATS)]
    t0, done = time.time(), 0
    for rubric, case, rep in todo:
        key = "%s|%s|%d|%d" % (MODEL, rubric, case["id"], rep)
        done += 1
        if key in cache:
            continue
        rule = yaml.safe_load(open(os.path.join(HERE, rubric + ".yaml"), encoding="utf-8"))["config"]["rule_prompt"]
        conv = "\n".join("%s: %s" % m for m in case["msgs"])
        # The rubric and the conversation repeat REPEATS times; only the run id changes. The
        # repeated part goes under a prompt-cache marker, so repeats 2..k read it from the cache.
        # The cache stores the processed prefix, never an answer: each repeat is a new judgement.
        prompt = [{"type": "text", "text": rule.replace("{{conversation}}", conv),
                   "cache_control": {"type": "ephemeral"}},
                  {"type": "text", "text": WRAP + "\n(run id %s)" % uuid.uuid4().hex[:8]}]
        msg = client.messages.create(model=MODEL, max_tokens=2000, messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in msg.content if b.type == "text")
        m = re.search(r"\{.*\}", text, re.S)
        try:
            parsed = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            parsed = {}
        cache[key] = {"score": parsed.get("score"), "reason": parsed.get("reason"), "raw": text[:400],
                      "usage": [msg.usage.input_tokens, msg.usage.output_tokens]}
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("%3d/%d %6.1fs %-24s case %2d rep %d score=%s" % (done, len(todo), time.time() - t0, rubric,
                                                               case["id"], rep + 1, parsed.get("score")), flush=True)
    return cache


def main():
    cache = judge_all() if "--judge" in sys.argv else (
        json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {})
    out = []
    for case in B.CASES:
        row = {"id": case["id"], "label": case["label"], "review": case["review"], "type": case["type"],
               **deterministic(case)}
        for rubric in RUBRICS:
            got = [cache.get("%s|%s|%d|%d" % (MODEL, rubric, case["id"], k)) for k in range(REPEATS)]
            row[rubric] = [g["score"] for g in got if g]
            row[rubric + "_reasons"] = [g["reason"] for g in got if g]
        out.append(row)
    usage = [v["usage"] for k, v in cache.items() if k.startswith(MODEL + "|")]
    json.dump({"judge_model": MODEL, "repeats": REPEATS, "pass_threshold": 0.5,
               "tokens_in": sum(u[0] for u in usage), "tokens_out": sum(u[1] for u in usage), "cases": out},
              open(os.path.join(HERE, "benchmark_results.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for r in out:
        print("%2d %-5s rev=%-5s flip=%-8s conflict=%-8s coh=%s res=%s" % (
            r["id"], r["label"], r["review"], r["flip_turns"], r["conflict_turns"],
            r["conversation_coherence"], r["conversation_resolution"]))


if __name__ == "__main__":
    main()
