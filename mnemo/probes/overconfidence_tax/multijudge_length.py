"""Multi-judge replication of the length-confound (defense for outreach): do CURRENT frontier judges
from different families also track length, or was that just the 2023 GPT-4 votes?

3 independent current judges (2026): Claude Opus 4.8 (Anthropic, API), deepseek-v4-pro (DeepSeek, ollama
cloud), glm-5.2 (Z.AI, ollama cloud). Each judges the SAME MT-Bench pairs (lmsys/mt_bench_human_judgments,
turn-1), presentation order randomized to neutralize position bias. Per judge we measure:
  - agreement with the human winner (does it reproduce the famous ~80%?)
  - % of verdicts that pick the LONGER answer  <-- the length-tracking signal (released GPT-4 = 73.5%)
If all 3 current frontier judges pick the longer answer well above 50%, the confound is multi-family,
current, and not an artifact of one old/weak model. Pre-registered: each judge picks-longer >= 60%.
"""
import io, json, re, time, urllib.request, random
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

HJ = "https://huggingface.co/datasets/lmsys/mt_bench_human_judgments/resolve/refs%2Fconvert%2Fparquet/default/human/0000.parquet"
N_PAIRS = 100
SEED = 11

def env(key):
    t = open("server/.env", encoding="utf-8", errors="replace").read()
    m = re.search(key + r'\s*=\s*"?([^"\r\n]+)', t)
    return m.group(1).strip() if m else None

ANTHROPIC_KEY = env("ANTHROPIC_API_KEY")

def first_user(conv):
    for m in conv:
        if m.get("role") == "user":
            c = m.get("content", "")
            return c if isinstance(c, str) else str(c)
    return ""
def first_asst(conv):
    for m in conv:
        if m.get("role") == "assistant":
            c = m.get("content", "")
            return c if isinstance(c, str) else str(c)
    return ""

def load_pairs():
    raw = urllib.request.urlopen(HJ, timeout=180).read()
    df = pd.read_parquet(io.BytesIO(raw))
    df = df[(df["turn"] == 1) & (df["winner"].isin(["model_a", "model_b"]))]
    # majority human winner per (qid, model_a, model_b)
    grp = defaultdict(list); texts = {}
    for r in df.itertuples():
        k = (r.question_id, r.model_a, r.model_b)
        grp[k].append(r.winner)
        if k not in texts:
            texts[k] = (first_user(r.conversation_a), first_asst(r.conversation_a), first_asst(r.conversation_b))
    pairs = []
    for k, ws in grp.items():
        q, ra, rb = texts[k]
        if not ra or not rb or not q: continue
        maj = Counter(ws).most_common(1)[0][0]
        pairs.append({"q": q, "ra": ra, "rb": rb, "human": maj,
                      "longer": "model_a" if len(ra) > len(rb) else ("model_b" if len(rb) > len(ra) else None)})
    rng = random.Random(SEED); rng.shuffle(pairs)
    return [p for p in pairs if p["longer"]][:N_PAIRS]

PROMPT = ("[User question]\n{q}\n\n[Answer A]\n{a}\n\n[Answer B]\n{b}\n\n"
          "Which answer is better overall? Respond with ONLY the single letter A or B.")

def parse_ab(txt):
    if not txt: return None
    m = re.findall(r"\b([AB])\b", txt.strip().upper())
    return m[-1] if m else None

def call_claude(q, a, b):
    body = json.dumps({"model": "claude-opus-4-8", "max_tokens": 5,
                       "messages": [{"role": "user", "content": PROMPT.format(q=q[:8000], a=a[:12000], b=b[:12000])}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                                 headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    for i in range(3):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=60).read())
            return parse_ab(r["content"][0]["text"])
        except Exception:
            if i == 2: return None
            time.sleep(3 * (i + 1))

def call_ollama(model, q, a, b):
    body = json.dumps({"model": model, "stream": False,
                       "messages": [{"role": "user", "content": PROMPT.format(q=q[:8000], a=a[:12000], b=b[:12000])}],
                       "options": {"temperature": 0, "num_predict": 2500}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", data=body, headers={"Content-Type": "application/json"})
    for i in range(3):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=180).read())
            return parse_ab(r["message"]["content"])
        except Exception:
            if i == 2: return None
            time.sleep(3 * (i + 1))

JUDGES = {
    "claude-opus-4.8": lambda q, a, b: call_claude(q, a, b),
    "deepseek-v4-pro": lambda q, a, b: call_ollama("deepseek-v4-pro:cloud", q, a, b),
    "glm-5.2":        lambda q, a, b: call_ollama("glm-5.2:cloud", q, a, b),
}

PICKLONG = {}   # name -> {pair_idx: bool picked_longer}

def judge_all(name, fn, pairs):
    rng = random.Random(SEED + abs(hash(name)) % 1000)
    def work(i, p):
        swap = rng.random() < 0.5                       # randomize A/B presentation
        a_txt, b_txt = (p["rb"], p["ra"]) if swap else (p["ra"], p["rb"])
        pick = fn(p["q"], a_txt, b_txt)
        if pick not in ("A", "B"): return None
        chosen = ("model_b" if swap else "model_a") if pick == "A" else ("model_a" if swap else "model_b")
        return {"i": i, "chosen": chosen, "human": p["human"], "longer": p["longer"]}
    rows = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for f in as_completed([ex.submit(work, i, p) for i, p in enumerate(pairs)]):
            r = f.result()
            if r: rows.append(r)
    n = len(rows)
    agree_h = sum(r["chosen"] == r["human"] for r in rows) / n
    nlong = sum(r["chosen"] == r["longer"] for r in rows)
    PICKLONG[name] = {r["i"]: (r["chosen"] == r["longer"]) for r in rows}
    return {"judge": name, "n": n, "nlong": nlong, "agree_human": round(agree_h, 3),
            "picks_longer": round(nlong / n, 3)}

def main():
    pairs = load_pairs()
    print("loaded %d MT-Bench pairs (turn-1, human-decided, length-imbalanced)" % len(pairs), flush=True)
    print("released GPT-4 baseline (2023): picks-longer 73.5% | length-only-vs-human 68.1%\n")
    out = []
    for name, fn in JUDGES.items():
        t0 = time.time()
        r = judge_all(name, fn, pairs); r["secs"] = round(time.time() - t0)
        out.append(r)
        print("  %-16s n=%d | agrees-with-human %.3f | PICKS-LONGER %.3f (%d/%d)  (%ds)"
              % (name, r["n"], r["agree_human"], r["picks_longer"], r["nlong"], r["n"], r["secs"]), flush=True)
    # cross-judge overlap: do they pick longer on the SAME pairs? (bug-check vs the identical-count flag)
    names = list(PICKLONG)
    common = set(PICKLONG[names[0]])
    for nm in names[1:]: common &= set(PICKLONG[nm])
    all3_long = sum(1 for i in common if all(PICKLONG[nm][i] for nm in names))
    print("\n[bug-check] pairs judged by all 3: %d | all-3-pick-longer on: %d" % (len(common), all3_long))
    for a in range(len(names)):
        for b in range(a+1, len(names)):
            agree = sum(1 for i in common if PICKLONG[names[a]][i]==PICKLONG[names[b]][i])
            print("   overlap %s vs %s: agree-on-longer-or-not %d/%d" % (names[a], names[b], agree, len(common)))
    pl = [r["picks_longer"] for r in out]
    print("\nMEASURED: current frontier judges picking the LONGER answer — %s" %
          ", ".join("%s %.0f%%" % (r["judge"], r["picks_longer"]*100) for r in out))
    print("VERDICT:", "CONFIRMED multi-family + current (all judges pick longer >=60%) — the length confound is not a 2023/single-model artifact"
          if all(x >= 0.60 for x in pl) else "MIXED — see per-judge")
    json.dump(out, open("multijudge_length_result.json", "w"), indent=1)

if __name__ == "__main__":
    main()
