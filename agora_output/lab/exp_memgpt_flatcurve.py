"""CRUCIBLE replication — MemGPT 'paging keeps QA accuracy FLAT as corpus scales'. Smallest model: retriever pages
top-B from a corpus of size N; QA ~= P(paged the needed gold) x reader-factor (OUR measured oracle: single~0.95,
3-hop~0.91). Falsifier: flat holds SINGLE-hop, COLLAPSES MULTI-hop (hop-2/3 gold reached via a bridge entity NOT in
the query -> falls out of top-B as N grows; inherits CHAIN-FRAGILITY). CLOUD-FREE; EVERY string embedded ONCE (cache)."""
import json, random, urllib.request, time
_CACHE = {}
def embed(text):
    if text in _CACHE: return _CACHE[text]
    body = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
    r = urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/embeddings",
        data=body, headers={"Content-Type": "application/json"}), timeout=60)
    v = json.loads(r.read())["embedding"]; _CACHE[text] = v; return v
def cos(a, b):
    d = sum(x*y for x, y in zip(a, b)); na = sum(x*x for x in a)**.5; nb = sum(x*x for x in b)**.5
    return d/((na*nb) or 1)
def tok(rng): return "".join(rng.choice("bcdfghjklmnpqrstvwz")+rng.choice("aeiou") for _ in range(3))
RNG = random.Random(7); NS = [10, 50, 150, 250]; BUDGET = 8; QPER = 8
READER = {"single": 0.95, "multi": 0.91}
pool = [f"the ally of {tok(RNG)} is {tok(RNG)}" for _ in range(max(NS))]
singles = [( f"who is the keeper of {e0}", [f"the keeper of {e0} is {tok(RNG)}"]) for e0 in (tok(RNG) for _ in range(QPER))]
multis = []
for _ in range(QPER):
    e = [tok(RNG) for _ in range(4)]
    multis.append((f"who is the ally of the ally of the ally of {e[0]}", [f"the ally of {e[i]} is {e[i+1]}" for i in range(3)]))
t0 = time.time()
for s in pool + [q for q,_ in singles+multis] + [g for _,gs in singles+multis for g in gs]:
    embed(s)                                   # warm the cache ONCE
print(f"cached {len(_CACHE)} embeds in {time.time()-t0:.0f}s", flush=True)
def full_recall(q, gold, n_distract):
    qe = embed(q)
    cand = [(g, embed(g)) for g in gold] + [(p, embed(p)) for p in pool[:n_distract]]
    top = {t for t,_ in sorted(cand, key=lambda c: -cos(qe, c[1]))[:BUDGET]}
    return all(g in top for g in gold)
print(f"page budget B={BUDGET}, {QPER} q/type. recall = ALL gold pages in top-B.")
print(f"{'N':>5} | {'single recall':>13} {'single QA':>9} | {'multi recall':>12} {'multi QA':>8}")
res = []
for N in NS:
    sr = sum(full_recall(q,g,N-1) for q,g in singles)/QPER
    mr = sum(full_recall(q,g,N-3) for q,g in multis)/QPER
    res.append((N, sr, sr*READER["single"], mr, mr*READER["multi"]))
    print(f"{N:>5} | {sr:>13.2f} {sr*READER['single']:>9.2f} | {mr:>12.2f} {mr*READER['multi']:>8.2f}", flush=True)
s_flat = max(r[2] for r in res)-min(r[2] for r in res); m_drop = res[0][4]-res[-1][4]
print(f"\nsingle QA range {s_flat:.2f} (flat~0) | multi QA {res[0][4]:.2f}->{res[-1][4]:.2f} drop {m_drop:.2f}")
print(f"VERDICT: flat-curve {'HOLDS single-hop' if s_flat<0.1 else 'FAILS even single-hop'}; "
      f"{'COLLAPSES multi-hop -> claim REFUTED for multi-hop' if m_drop>0.2 else 'holds multi-hop too'}.")
json.dump({"NS":NS,"budget":BUDGET,"reader":READER,"rows":res}, open("agora_output/lab/memgpt_flatcurve_result.json","w"))
