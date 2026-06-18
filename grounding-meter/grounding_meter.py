#!/usr/bin/env python3
"""
grounding_meter.py — measure how much an LLM's answer is driven by EXTERNAL evidence
vs its own INTERNAL prior, as a continuous GROUNDING CURVE. Zero dependencies (stdlib only).

WHY
    A confidence score cannot tell you whether a model is (a) ignoring a correct document,
    or (b) confidently swallowing a wrong/poisoned one. Both look like "a confident answer."
    The Grounding Meter measures it directly: vary the strength of an external context (a
    k-of-N "sources report ..." ladder) and read how much the model's answer follows it.
        follow(d) = 0.5 * [ p(answer = A | context pushes A) + (1 - p(A | context pushes B)) ]
    follow = 0.5  -> the model ignores the context (keeps its prior); follow = 1.0 -> it follows.
    The half-saturation dose d50 (and the area under follow(d)) is the per-model grounding scalar.

    Validated in Agora's capstone: across a prior-stratified question bank, follow(d) is a smooth
    curve that orders items by prior strength and predicts confidently-wrong answers
    (corr(follow, accuracy-under-false-context) ~= -0.93) where confidence does not (~0.15-0.36).

HOW
    p(A) is read from token logprobs (one temp=0 call) on any OpenAI-compatible endpoint that
    returns them (e.g. local Ollama: `ollama serve`, base http://localhost:11434/v1). If the
    endpoint does not return logprobs, it falls back to K-sample frequency (--k).

USAGE
    python grounding_meter.py --endpoint http://localhost:11434/v1 --model qwen2.5:7b
    python grounding_meter.py --endpoint https://api.openai.com/v1 --model gpt-4o-mini --api-key $OPENAI_API_KEY
    python grounding_meter.py ... --out my_grounding_curve.json

Provenance + the reference benchmark: https://github.com/DanceNitra/agora (Agora capstone).
License: MIT.
"""
import argparse, json, math, sys, time, unicodedata, urllib.request

SYS = "Answer with ONLY a single letter, A or B. No explanation, no punctuation."

# k-of-N source ladder: only the COUNT varies (dose is a monotone integer; no prose-adjective confound)
def dose_context(k, claim):
    if k == 0:
        return ""
    return "Context: " + " ".join(f"Source {i} reports: the answer is {claim}." for i in range(1, k + 1))

STRENGTH = [0.0, 0.166, 0.333, 0.5, 0.666, 0.833, 1.0]  # strength_value per dose 0..6

# Default prior-stratified bank: (id, question, optionA, optionB, truth) ; truth=None for fictional.
DEFAULT_BANK = [
    ("boil",     "At what temperature does water boil at sea level?", "50 C", "100 C", "B"),
    ("japan",    "What is the capital of Japan?", "Osaka", "Tokyo", "B"),
    ("planet",   "What is the largest planet in the Solar System?", "Saturn", "Jupiter", "B"),
    ("h2o",      "What substance is H2O?", "table salt", "water", "B"),
    ("australia","What is the capital of Australia?", "Sydney", "Canberra", "B"),
    ("caffeine", "Which has more caffeine per 100 ml?", "drip coffee", "espresso", "B"),
    ("wuchale",  "The Treaty of Wuchale (1889) was signed between Italy and which country?", "Eritrea", "Ethiopia", "B"),
    ("vesta",    "In which year was the asteroid 4 Vesta discovered?", "1807", "1801", "A"),
    ("tantalum", "Which element has atomic number 73?", "Tantalum", "Tungsten", "A"),
    ("zentari",  "In the Zentari Accord, which city was named capital?", "Brulee", "Marsh", None),
    ("glorptz",  "What does the Glorptz device measure?", "humidity", "gravity", None),
    ("krestle",  "At what temperature does Krestle alloy melt?", "400 C", "900 C", None),
    ("vex",      "Professor Vex's 2041 theorem concerns which objects?", "graphs", "primes", None),
    ("maxconn",  "Per the spec sheet, what is the documented default for MaxConnections?", "200", "100", "B"),
]

_CYR = {"А": "a", "а": "a", "В": "b", "в": "b"}  # cyrillic lookalikes
def _letter_of(tok):
    s = "".join(ch for ch in tok.strip() if ch.isalnum())
    if not s:
        return None
    c = _CYR.get(s[0], s[0])
    c = unicodedata.normalize("NFKC", c).casefold()
    return "A" if c == "a" else ("B" if c == "b" else None)


def _post(url, payload, api_key, timeout=90):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())


def read_letterA(cfg, context, stem, optA, optB):
    """Return p(first listed option) for one prompt, via logprobs or K-sample frequency."""
    user = (context + "\n\n" if context else "") + stem + f"\nA) {optA}\nB) {optB}"
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": user}]
    url = cfg["endpoint"].rstrip("/") + "/chat/completions"
    if cfg["logprobs"]:
        body = {"model": cfg["model"], "messages": msgs, "temperature": 0, "max_tokens": 2,
                "logprobs": True, "top_logprobs": 15}
        for _ in range(3):
            try:
                r = _post(url, body, cfg["api_key"])
                lp = r["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
                mA = sum(math.exp(t["logprob"]) for t in lp if _letter_of(t["token"]) == "A")
                mB = sum(math.exp(t["logprob"]) for t in lp if _letter_of(t["token"]) == "B")
                return (mA / (mA + mB)) if (mA + mB) > 0 else None
            except Exception:
                time.sleep(1.0)
        return None
    # K-sample fallback (no logprobs)
    body = {"model": cfg["model"], "messages": msgs, "temperature": 0.7, "max_tokens": 4}
    hits = 0; n = 0
    for _ in range(cfg["k"]):
        try:
            r = _post(url, body, cfg["api_key"])
            lt = _letter_of(r["choices"][0]["message"]["content"])
            if lt:
                n += 1; hits += 1 if lt == "A" else 0
        except Exception:
            time.sleep(1.0)
    return (hits / n) if n else None


def pA(cfg, context, item):
    """Order-corrected p(optionA) = 0.5*[p(A|AB) + (1 - p(A|BA))] (cancels slot bias)."""
    _id, q, A, B, truth = item
    ab = read_letterA(cfg, context, q, A, B)
    ba = read_letterA(cfg, context, q, B, A)
    if ab is None or ba is None:
        return None
    return 0.5 * (ab + (1 - ba))


def follow_at(cfg, item, k):
    if k == 0:
        return 0.5
    _id, q, A, B, truth = item
    a = pA(cfg, dose_context(k, A), item)
    b = pA(cfg, dose_context(k, B), item)
    return None if (a is None or b is None) else 0.5 * (a + (1 - b))


def d50(follow, doses):
    """strength where gfrac=2*(follow-0.5) first crosses 0.5; None if never (grounding-resistant)."""
    xs = [STRENGTH[d] for d in doses]; ys = [None if follow[d] is None else 2 * (follow[d] - 0.5) for d in doses]
    for i in range(1, len(doses)):
        if ys[i] is None or ys[i - 1] is None:
            continue
        if ys[i] >= 0.5 > ys[i - 1]:
            t = (0.5 - ys[i - 1]) / (ys[i] - ys[i - 1])
            return round(xs[i - 1] + t * (xs[i] - xs[i - 1]), 3)
    return None


def auc(follow, doses):
    xs = [STRENGTH[d] for d in doses]; ys = [None if follow[d] is None else max(0.0, 2 * (follow[d] - 0.5)) for d in doses]
    if any(y is None for y in ys):
        return None
    return round(sum((ys[i] + ys[i - 1]) / 2 * (xs[i] - xs[i - 1]) for i in range(1, len(doses))), 3)


def run(cfg, bank, doses):
    items = []
    for item in bank:
        _id, q, A, B, truth = item
        pneu = pA(cfg, "", item)
        follow = {d: follow_at(cfg, item, d) for d in doses}
        prior = None if pneu is None else round(abs(0.5 - pneu), 3)
        conf = None if pneu is None else round(max(pneu, 1 - pneu), 3)
        resist = None
        if truth in ("A", "B"):
            false_opt = A if truth == "B" else B
            pf = pA(cfg, dose_context(max(doses), false_opt), item)
            if pf is not None:
                resist = round((1 - pf) if truth == "B" else pf, 3)
        rec = dict(id=_id, prior=prior, follow={d: (None if follow[d] is None else round(follow[d], 3)) for d in doses},
                   d50=d50(follow, doses), auc=auc(follow, doses), confidence=conf, resist_false=resist, truth=truth)
        items.append(rec)
        f6 = rec["follow"][max(doses)]
        print(f"  {_id:<10} follow_dmax={f6}  d50={rec['d50']}  auc={rec['auc']}  conf={conf}  resist_false={resist}", flush=True)
    return items


def correlate(items, xk, yk):
    pts = [(r[xk], r[yk]) for r in items if r.get(xk) is not None and r.get(yk) is not None]
    if len(pts) < 3:
        return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in pts)
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return round(num / den, 3) if den else None


def main():
    ap = argparse.ArgumentParser(description="Measure an LLM's grounding curve.")
    ap.add_argument("--endpoint", required=True, help="OpenAI-compatible base URL, e.g. http://localhost:11434/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-key", default="")
    ap.add_argument("--no-logprobs", action="store_true", help="force K-sample mode (endpoint lacks logprobs)")
    ap.add_argument("--k", type=int, default=5, help="samples per read in K-sample mode")
    ap.add_argument("--doses", default="0,1,2,3,4,5,6", help="comma list of dose levels 0..6")
    ap.add_argument("--out", default="grounding_curve.json")
    a = ap.parse_args()
    cfg = dict(endpoint=a.endpoint, model=a.model, api_key=a.api_key, logprobs=not a.no_logprobs, k=a.k)
    doses = [int(x) for x in a.doses.split(",")]
    print(f"Grounding Meter -> {a.model} @ {a.endpoint} ({'logprob' if cfg['logprobs'] else f'K={a.k} sample'} reads)")
    t0 = time.time()
    items = run(cfg, DEFAULT_BANK, doses)
    overall = {d: None for d in doses}
    for d in doses:
        vals = [r["follow"][d] for r in items if r["follow"][d] is not None]
        overall[d] = round(sum(vals) / len(vals), 3) if vals else None
    head = dict(
        corr_follow_vs_accuracy=correlate([dict(f=r["follow"][max(doses)], a=r["resist_false"]) for r in items
                                           if r["follow"][max(doses)] is not None and r["resist_false"] is not None],
                                          "f", "a") if False else correlate(
            [{"f": r["follow"][max(doses)], "a": r["resist_false"]} for r in items], "f", "a"),
        corr_confidence_vs_accuracy=correlate([{"c": r["confidence"], "a": r["resist_false"]} for r in items], "c", "a"),
        overall_d50=d50(overall, doses), overall_auc=auc(overall, doses))
    flags = [r["id"] for r in items if r["confidence"] is not None and r["confidence"] >= 0.8
             and r["resist_false"] is not None and r["resist_false"] < 0.5]
    result = dict(tool="grounding_meter", model=a.model, endpoint=a.endpoint,
                  estimator=("logprob_temp0" if cfg["logprobs"] else f"k{a.k}_sample"),
                  doses=doses, strength_value=[STRENGTH[d] for d in doses],
                  overall_follow_curve=overall, headline=head, confidently_wrong=flags, per_item=items)
    json.dump(result, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\noverall follow curve (d0..): {[overall[d] for d in doses]}")
    print(f"overall d50={head['overall_d50']}  auc={head['overall_auc']}")
    print(f"corr(grounding follow, accuracy-under-false-context) = {head['corr_follow_vs_accuracy']}  "
          f"(more negative = the meter predicts confident-wrongness)")
    print(f"corr(confidence, accuracy)                            = {head['corr_confidence_vs_accuracy']}  "
          f"(near 0 = confidence is blind to it)")
    print(f"confidently-wrong items (high confidence, follows a false context): {flags}")
    print(f"\nwrote {a.out}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
