"""fair_conflict.py — the FAIR adversarial-conflict experiment the stress-claim gate demanded.

Fixes every flaw the gate found in adversarial_conflict.py:
 (skeptik)  ALL systems get RAW TEXT — inspeximus derives (key, object) itself via an LLM extractor (deepseek, the
            same tier mem0 uses for extraction). No spoon-fed structure. Isolates inspeximus's GATE, not its input.
 (method)   ALL systems scored by the SAME instrument: retrieve context -> one neutral LLM judge "current value?"
            -> compare to truth. No substring-on-store-surface asymmetry that manufactured mem0's 10%.
 (skeptik)  Poison tested EXACT and PARAPHRASED (does the guard survive a reworded re-assertion?).
 (blindspot) BOTH arms measured: POISON-rejection AND LEGIT-update-adoption, on the same subjects. A guard that
            rejects poison must not also reject genuine corrections; we report both (the frontier, not a corner).
 (priorart) The defense is textbook (anti-replay / trust-sensitive belief revision / TMS); we credit it and only
            measure whether inspeximus occupies a better operating point than mem0 under a fair contract.

Arms per subject (key K, stale A, correction B):
  POISON arm:  raw "A"  ->  raw "B" (correction)  ->  raw "A" or paraphrase(A) (poison, newest).  Truth = B.
  LEGIT  arm:  raw "A"  ->  raw "B"               ->  raw "C" (a genuine NEW correction, newest).   Truth = C.
Metric per system per arm = fraction the judged current value == the arm's truth.

RUN (free, inspeximus+naive):  python research/probes/fair_conflict.py --systems inspeximus,naive --n 40 --poison exact
RUN (with mem0):          python research/probes/fair_conflict.py --systems inspeximus,naive,mem0 --n 30 --poison paraphrase
"""
import os, sys, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "mab_official"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "inspeximus_pypi"))
import run_inspeximus_official as H
from inspeximus import Inspeximus


def _llm(prompt, temp=0.0, maxtok=800):   # deepseek-v4-flash is a REASONING model: a tight cap yields EMPTY content
    import urllib.request
    body = json.dumps({"model": H.ANSWERER, "temperature": temp, "max_tokens": maxtok,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    for a in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                H.BASE + "/chat/completions", data=body,
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + H.KEY}), timeout=120)
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception:
            if a == 3:
                return ""
            time.sleep(3)


def llm_extract(text):
    """RAW TEXT -> (key, object). Same kind of extraction mem0 does; deepseek. Deterministic key = subject::relation
    so a re-statement of the same fact (even reworded) maps to the SAME key -> inspeximus's gate can see the retired value."""
    p = ('Extract the subject-relation KEY and the VALUE from this fact. The KEY must be the same for any '
         'restatement of the same fact (canonical "subject :: relation", no value). Reply ONLY compact JSON '
         '{"key":"...","object":"..."}.\n\nFact: ' + text)
    out = _llm(p)
    try:
        s = out[out.find("{"):out.rfind("}") + 1]
        d = json.loads(s)
        k, o = str(d.get("key", "")).strip(), str(d.get("object", "")).strip()
        return (k, o) if k and o else None
    except Exception:
        return None


import math
def _cos(a, b):
    s = sum(x * y for x, y in zip(a, b)); na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return s / (na * nb + 1e-9)


def make_semantic_extractor(threshold=0.80):
    """The FIX for paraphrase-brittleness: resolve a new fact's (subject::relation) key to an EXISTING key by
    EMBEDDING similarity instead of exact string match, so 'X born in' and 'X birthplace' converge to one key ->
    inspeximus's supersession/echo_guard finally engages on reworded conflicts. Deterministic given the embedder."""
    keys = []  # (key_str, emb)
    def ex(text):
        raw = llm_extract(text)
        if not raw:
            return None
        cand, val = raw
        e = H._embed([cand])[0]
        best, bs = None, -1.0
        for ks, ke in keys:
            c = _cos(e, ke)
            if c > bs:
                bs, best = c, ks
        if best is not None and bs >= threshold:
            return (best, val)                               # reuse existing key -> paraphrase converges
        keys.append((cand, e))
        return (cand, val)
    return ex


def judge_current(ctx, subject):
    """The ONE shared instrument for every system: what does this memory say is CURRENT?"""
    p = ("Based ONLY on the memory below, what is the CURRENT value? A value may have been corrected and an OLD "
         "value re-stated later; the correction is authoritative, a re-appearing old value is stale. Answer with "
         f"just the value.\n\nMemory:\n{ctx}\n\nQuestion: {subject}?\nAnswer:")
    return _llm(p, ).rsplit("Answer:", 1)[-1].strip()


def val_of(fact, key):
    v = fact[len(key):] if fact.startswith(key) else fact
    return v.strip().strip(".").strip()


def paraphrase(fact):
    out = _llm("Reword this sentence, keeping the exact same meaning and the same named value. Reply with ONLY the "
               "reworded sentence.\n\n" + fact)
    return out.strip().strip('"') or fact


def pairs(sample, n):
    facts, _q, _g = H.load(sample)
    from collections import OrderedDict
    byk = OrderedDict()
    for f in facts:
        byk.setdefault(H.key_of(f), []).append(f)
    conf = [(k, v[0], v[-1]) for k, v in byk.items() if len(v) >= 2 and len(set(v)) >= 2]
    return conf[:n]


def truth_hit(ans, truth_val, other_val):
    a = (ans or "").lower()
    return (truth_val.lower() in a) and (other_val.lower() not in a)


# ---- systems: each takes the ordered RAW writes, returns the judged current-value answer ----
def sys_inspeximus(subject, writes, hardened=False, extractor=None):
    m = Inspeximus(path=None); m.echo_guard = True
    m.extractor = extractor if extractor is not None else llm_extract  # semantic extractor passed FRESH per subject
    if hardened:
        m.supersede_requires_corroboration = True
    for w in writes:
        m.remember(w)                                        # RAW text; inspeximus extracts key+object itself
    ctx = "\n".join(h["text"] for h in m.recall(subject, k=6))
    return judge_current(ctx, subject)


def sys_naive(subject, writes):
    m = Inspeximus(path=None); m.echo_guard = False
    for i, w in enumerate(writes):
        m.remember(w, key=f"row-{i}")                        # no supersession; all writes kept
    ctx = "\n".join(h["text"] for h in m.recall(subject, k=6))
    return judge_current(ctx, subject)


def sys_mem0(mem, uid, subject, writes):
    for w in writes:
        H._mem0_add(mem, w, uid)
    sr = mem.search(subject, filters={"user_id": uid}, top_k=10)
    rows = sr.get("results", sr) if isinstance(sr, dict) else sr
    ctx = "\n".join((x.get("memory") or x.get("text") or str(x)) for x in (rows or []))
    return judge_current(ctx, subject)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="inspeximus,naive")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--poison", default="exact", choices=["exact", "paraphrase"])
    ap.add_argument("--extractor", default="plain", choices=["plain", "semantic"],
                    help="semantic = embedding-resolved keys (fixes paraphrase-brittleness)")
    ap.add_argument("--runs", type=int, default=1, help="repeat the whole measurement R times (verification)")
    ap.add_argument("--sample", default="sh_6k")
    a = ap.parse_args()
    ps = pairs(a.sample, a.n); n = len(ps)
    syslist = a.systems.split(",")
    print(f"FAIR conflict (raw-text contract, shared LLM judge) · poison={a.poison} · n={n} · systems={syslist}", flush=True)

    # precompute write sequences per subject. POISON arm re-asserts retired A. LEGIT arm adds a genuinely NEW
    # value D (never retired) that a good store SHOULD adopt — the fair dual that measures false-rejection cost.
    subjects = []
    for (k, A, B) in ps:
        pois = A if a.poison == "exact" else paraphrase(A)
        vA, vB = val_of(A, k), val_of(B, k)
        dnew = _llm(f'Give ONE different, plausible, DIFFERENT value for "{k.rstrip(" .")}" — NOT "{vA}" and NOT '
                    f'"{vB}". Reply with ONLY the value, no sentence.').strip().strip('."')
        if not dnew or dnew.lower() in (vA.lower(), vB.lower()):
            dnew = "an unrelated placeholder value"
        D_fact = f"{k} {dnew}." if not k.endswith(" ") else f"{k}{dnew}."
        subjects.append({"k": k, "A": A, "B": B, "pois": pois, "Df": D_fact,
                         "vA": vA, "vB": vB, "vD": dnew})

    out = {}
    mem = None
    if "mem0" in syslist:
        import importlib
        adv = importlib.import_module("adversarial_conflict")
        mem = adv._mem0_own()

    def one_run(run_id):
        r = {}
        for label in ["poison", "legit"]:
            for s in syslist:
                hit = 0
                for i, d in enumerate(subjects):
                    if label == "poison":
                        writes = [d["A"], d["B"], d["pois"]]; truth, other = d["vB"], d["vA"]
                    else:
                        writes = [d["A"], d["B"], d["Df"]]; truth, other = d["vD"], d["vB"]
                    if s == "inspeximus":
                        ex = make_semantic_extractor() if a.extractor == "semantic" else None
                        ans = sys_inspeximus(d["k"], writes, extractor=ex)
                    elif s == "naive":
                        ans = sys_naive(d["k"], writes)
                    elif s == "mem0":
                        ans = sys_mem0(mem, f"r{run_id}{label}{i}", d["k"], writes)
                    else:
                        continue
                    hit += truth_hit(ans, truth, other)
                r[f"{s}_{label}"] = hit / n
                print(f"  run{run_id} {label:6s} {s:10s}: {hit}/{n} = {hit/n:.0%}", flush=True)
        return r

    runs = [one_run(rr) for rr in range(a.runs)]
    for key in runs[0]:
        vals = [r[key] for r in runs]
        out[key] = {"mean": round(sum(vals) / len(vals), 3), "runs": [round(v, 2) for v in vals],
                    "spread": round(max(vals) - min(vals), 3)}
    print("\n=== SUMMARY (mean over runs) ===")
    for key, v in out.items():
        print(f"  {key:18s}: mean {v['mean']:.0%}  runs {v['runs']}  spread {v['spread']:.0%}")
    json.dump({"n": n, "poison": a.poison, "extractor": a.extractor, "runs": a.runs,
               "contract": "raw-text (all systems extract)", "instrument": "shared LLM judge 'current value?'",
               "results": out}, open(os.path.join(HERE, f"fair_conflict_{a.poison}_{a.extractor}_result.json"), "w"), indent=1)
    print("\nsaved fair_conflict result.")


if __name__ == "__main__":
    main()
