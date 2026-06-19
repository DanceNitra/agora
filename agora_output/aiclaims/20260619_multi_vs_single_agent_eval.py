"""
AI-Claim Crucible flagship #1 — "Does multi-agent beat single-agent AT FIXED COST?"
====================================================================================
Pre-registered (agora_output/aiclaims/PREREGISTRATION_multi-vs-single-agent.md). One fixed base model
(deepseek-v4-flash); only the SCAFFOLD differs; cost = total tokens (usage). Tasks = K independent hard
sub-problems (multi-step arithmetic with a distractor) combined by sum; ground truth computed exactly.
 - SINGLE arm: solve all K in ONE context; self-consistency k samples; majority of the final sum.
 - MULTI arm: one worker per sub-problem (fresh context) + an aggregator call that sums. (Steelman: clean
   per-worker context is exactly the multi-agent folklore's claimed advantage.)
Compare accuracy vs avg total-tokens -> the Pareto frontier decides REPRODUCED/FAILED/NOT_COMPUTABLE.
"""
import json, re, os, time, urllib.request, argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
ENV = open(os.path.join(BASE, "..", "..", "agora-game-server", ".env"), "rb").read().decode("utf-8", "replace")
URL = re.search(r'DUNGEON_LLM_URL\s*=\s*"?([^"\r\n]+)', ENV).group(1).strip()
KEY = re.search(r'LLM_API_KEY\s*=\s*"?([^"\r\n]+)', ENV).group(1).strip()
MODEL = "deepseek-v4-flash"


def call(messages, max_tokens):
    body = {"model": MODEL, "temperature": 0.7, "max_tokens": max_tokens, "messages": messages}
    hdr = {"Content-Type": "application/json", "Authorization": "Bearer " + KEY}
    for _ in range(4):
        try:
            r = json.loads(urllib.request.urlopen(
                urllib.request.Request(URL, data=json.dumps(body).encode(), headers=hdr), timeout=120).read())
            txt = r["choices"][0]["message"].get("content") or ""
            tok = (r.get("usage") or {}).get("total_tokens", 0)
            return txt, int(tok)
        except Exception:
            time.sleep(2)
    return "", 0


def last_int(txt):
    # prefer "ANSWER: <n>", else the last integer in the text
    m = re.search(r"ANSWER:\s*(-?\d+)", txt, re.I)
    if m:
        return int(m.group(1))
    nums = re.findall(r"-?\d+", txt.replace(",", ""))
    return int(nums[-1]) if nums else None


def gen_subproblem(rng, steps):
    """A multi-step arithmetic chain with a distractor; returns (text, answer)."""
    val = rng.randint(2, 19)
    parts = [f"Start with {val}."]
    for _ in range(steps):
        op = rng.choice(["add", "subtract", "multiply by"])
        n = rng.randint(2, 9)
        if op == "add":
            val += n
        elif op == "subtract":
            val -= n
        else:
            val *= n
        parts.append(f"Then {op} {n}.")
    # distractor sentence (must be ignored)
    parts.insert(rng.randint(1, len(parts)), f"(Note: a red herring number {rng.randint(100,999)} appears here; ignore it.)")
    return " ".join(parts), val


def gen_task(rng, K, steps):
    subs = [gen_subproblem(rng, steps) for _ in range(K)]
    return {"subs": subs, "answer": sum(a for _, a in subs)}


def single_arm(task, k):
    """Solve all K sub-problems in one context, k self-consistency samples, majority of the final sum."""
    qs = "\n".join(f"{i+1}. {t}" for i, (t, _) in enumerate(task["subs"]))
    msg = [{"role": "user", "content":
            "Solve each of these independent sub-problems, then SUM all the sub-answers.\n" + qs +
            "\n\nThink step by step. End with exactly: ANSWER: <the total sum>"}]
    votes, tot = [], 0
    for _ in range(k):
        txt, tk = call(msg, 1600)
        tot += tk
        v = last_int(txt)
        if v is not None:
            votes.append(v)
    if not votes:
        return None, tot
    return Counter(votes).most_common(1)[0][0], tot


def multi_arm(task, wmax, kw=1):
    """One worker per sub-problem (fresh context) + an aggregator that sums the worker answers.
    kw = per-worker self-consistency samples (majority per worker) -> lets multi spend a HIGH budget."""
    tot = 0
    worker_ans = []
    for (t, _) in task["subs"]:
        wv = []
        for _ in range(kw):
            txt, tk = call([{"role": "user", "content": t + "\n\nThink step by step. End with exactly: ANSWER: <number>"}], wmax)
            tot += tk
            v = last_int(txt)
            if v is not None:
                wv.append(v)
        worker_ans.append(Counter(wv).most_common(1)[0][0] if wv else None)
    # aggregator (LLM, real cost): sum the sub-answers
    listing = ", ".join(str(a) for a in worker_ans)
    atxt, atk = call([{"role": "user", "content":
                       f"Sum these numbers and give the total. Numbers: {listing}\nEnd with exactly: ANSWER: <total>"}], 300)
    tot += atk
    return last_int(atxt), tot


def run(n_tasks, K, steps, single_ks, multi_wmaxes, seed0=1):
    import random
    rng = random.Random(seed0)
    tasks = [gen_task(rng, K, steps) for _ in range(n_tasks)]
    configs = ([("single", k) for k in single_ks] +
               [("multi", (w if isinstance(w, tuple) else (w, 1))) for w in multi_wmaxes])
    results = {}
    for kind, param in configs:
        if kind == "single":
            fn = (lambda t, p=param: single_arm(t, p)); label = f"single(k={param})"
        else:
            wmax, kw = param
            fn = (lambda t, wm=wmax, k=kw: multi_arm(t, wm, k)); label = f"multi(wmax={wmax},kw={kw})"
        correct, toks = 0, []
        with ThreadPoolExecutor(max_workers=3) as ex:
            out = list(ex.map(lambda t: (fn(t), t["answer"]), tasks))
        for (ans, tk), truth in out:
            toks.append(tk)
            if ans == truth:
                correct += 1
        acc = correct / n_tasks
        se = (acc * (1 - acc) / n_tasks) ** 0.5
        avg_tok = sum(toks) / len(toks)
        results[label] = {"acc": acc, "se": se, "avg_tokens": avg_tok, "kind": kind}
        print(f"  {label:<16} acc={acc:.3f} (SE {se:.3f})  avg_tokens={avg_tok:.0f}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--tighten", action="store_true")
    x = ap.parse_args()
    if x.tighten:
        # Fair HIGH-END comparison: single self-consistency frontier (k=1,3,5) vs multi at mid budget
        # AND multi with per-worker self-consistency (kw=3) so multi also gets a high budget.
        print("=== TIGHTEN (n=24, same tasks) — fair high-end: multi+worker-SC vs single-SC ===")
        res = run(24, K=8, steps=10, single_ks=[1, 3, 5], multi_wmaxes=[(1400, 1), (700, 3)], seed0=1)
        pts = [(v["avg_tokens"], v["acc"], v["se"], lab, v["kind"]) for lab, v in res.items()]
        frontier, best = [], -1
        for c, a, s, lab, kind in sorted(pts, key=lambda p: p[0]):
            if a > best:
                frontier.append((c, a, s, lab, kind)); best = a
        print("\nPareto frontier (cost-ascending):")
        for c, a, s, lab, kind in frontier:
            print(f"  {lab:<22} {a:.3f} @ {c:.0f} tok")
        peak = max(pts, key=lambda p: p[1])
        print(f"\nhighest accuracy: {peak[3]} = {peak[1]:.3f} @ {peak[0]:.0f} tok")
        mh = res.get("multi(wmax=700,kw=3)"); s5 = res.get("single(k=5)")
        if mh and s5:
            print(f"HIGH-END head-to-head: multi+SC {mh['acc']:.3f}@{mh['avg_tokens']:.0f}  vs  "
                  f"single-SC(k=5) {s5['acc']:.3f}@{s5['avg_tokens']:.0f}")
        raise SystemExit
    if x.resolve:
        # Clean equal-cost comparison on ONE task set: cheap-multi (matched to single-k1 cost) +
        # the single frontier + a mid multi. Proper Pareto verdict (no crude heuristic).
        print("=== RESOLVE (n=24, K=8 steps=10, same tasks) — clean equal-cost Pareto ===")
        res = run(24, K=8, steps=10, single_ks=[1, 3, 5], multi_wmaxes=[200, 1400], seed0=1)
        pts = [(v["avg_tokens"], v["acc"], v["se"], lab, v["kind"]) for lab, v in res.items()]
        # Pareto frontier (max acc for <= cost): a point is on it if nothing cheaper-or-equal has higher acc
        pts_sorted = sorted(pts, key=lambda p: p[0])
        frontier, best = [], -1
        for c, a, s, lab, kind in pts_sorted:
            if a > best:
                frontier.append((c, a, s, lab, kind)); best = a
        print("\nPareto frontier (cost-ascending):")
        for c, a, s, lab, kind in frontier:
            print(f"  {lab:<16} {a:.3f} @ {c:.0f} tok")
        multi_on = [f for f in frontier if f[4] == "multi"]
        single_on = [f for f in frontier if f[4] == "single"]
        top_acc_kind = max(pts, key=lambda p: p[1])[4]
        print(f"\nmulti on frontier: {len(multi_on)} | single on frontier: {len(single_on)} | highest-accuracy arm: {top_acc_kind}")
        # equal-cost test at the cheap end: single(k=1) vs multi(wmax=200)
        s1 = res.get("single(k=1)"); m200 = res.get("multi(wmax=200)")
        if s1 and m200:
            d = m200["acc"] - s1["acc"]; pooled = (s1["se"]**2 + m200["se"]**2) ** 0.5
            print(f"\nEqual-cost (~{(s1['avg_tokens']+m200['avg_tokens'])/2:.0f} tok): multi {m200['acc']:.2f} vs single {s1['acc']:.2f} "
                  f"-> delta {d:+.2f} ({d/pooled:+.1f} SE)")
        raise SystemExit
    if x.pilot:
        print("=== PILOT v2 (n=8, K=8 steps=10 — harder, to induce single-agent interference) ===")
        run(8, K=8, steps=10, single_ks=[1, 3], multi_wmaxes=[700])
    else:
        print("=== FULL: multi-vs-single agent at fixed cost (n=20, K=8 steps=10) ===")
        res = run(20, K=8, steps=10, single_ks=[1, 3], multi_wmaxes=[600, 1400])
        # verdict: does multi dominate the single Pareto frontier?
        singles = [(v["avg_tokens"], v["acc"], v["se"]) for k, v in res.items() if v["kind"] == "single"]
        multis = [(v["avg_tokens"], v["acc"], v["se"]) for k, v in res.items() if v["kind"] == "multi"]
        dominates = any(all(ma > sa + ss for st, sa, ss in singles if st <= mt + 1) for mt, ma, mse in multis)
        beaten = any(any(sa >= ma - mse for st, sa, ss in singles if st <= mt + 1) for mt, ma, mse in multis)
        print("\nVERDICT:", "REPRODUCED (multi dominates at fixed cost)" if dominates and not beaten
              else "FAILED (single matches/beats multi at equal $/task)")
