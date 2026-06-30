"""Severe-test of the mnemo hybrid-recall upgrade: does mnemo's mode='hybrid' (lexical+semantic RRF)
actually beat mode='lexical' and mode='semantic' on real agent memory (LoCoMo)? Fresh store per mode
(recall mutates value). Embedder = nomic (raw), batch-pre-embedded. 3 conversations."""
import json, re, ast, sys, urllib.request
sys.path.insert(0, "mnemo")
from mnemo import Mnemo

D = json.load(open("agora_output/lab/data/locomo10.json"))[:3]
EMB = "http://localhost:11434/api/embed"
def batch_embed(texts):
    out = {}; uniq = list(dict.fromkeys(texts))
    for i in range(0, len(uniq), 64):
        ch = uniq[i:i+64]
        b = json.dumps({"model": "nomic-embed-text", "input": [t[:2000] for t in ch]}).encode()
        r = urllib.request.urlopen(urllib.request.Request(EMB, data=b, headers={"Content-Type":"application/json"}), timeout=120)
        for t, v in zip(ch, json.loads(r.read())["embeddings"]): out[t] = v
    return out
def gold(q, tset):
    e = q.get("evidence")
    try: ids = ast.literal_eval(e) if isinstance(e, str) else e
    except: ids = []
    return [i for i in (ids or []) if i in tset]

# pre-embed
alltext = []
for D0 in D:
    conv = D0["conversation"]
    for sk in [k for k in conv if re.fullmatch(r"session_\d+", k)]:
        for t in conv[sk]: alltext.append(t["text"])
    for q in D0["qa"]:
        if str(q.get("category")) in ("1","2","3","4"): alltext.append(q["question"])
print(f"embedding {len(set(alltext))} unique texts...", flush=True)
VEC = batch_embed(alltext)

MODES = ["lexical", "semantic", "hybrid"]
agg = {m: [] for m in MODES}
for D0 in D:
    conv = D0["conversation"]; turns = {}
    for sk in [k for k in conv if re.fullmatch(r"session_\d+", k)]:
        for t in conv[sk]: turns[t["dia_id"]] = t["text"]
    tset = set(turns)
    qs = [q for q in D0["qa"] if str(q.get("category")) in ("1","2","3","4") and gold(q, tset)]
    for mode in MODES:
        m = Mnemo(embed=lambda t: VEC.get(t[:2000]) or VEC.get(t))
        m.semantic_threshold = 0          # force the auto path to engage embedder/hybrid
        id2dia = {}
        for dia, txt in turns.items():
            rid = m.remember(txt, mtype="semantic"); id2dia[rid] = dia
        for q in qs:
            g = set(gold(q, tset)); ng = len(g)
            res = m.recall(q["question"], k=20, mode=mode)
            got = {id2dia.get(x.get("id")) for x in res}
            agg[mode].append(len(g & got) / ng)
print(f"\nmnemo recall@20 on LoCoMo (3 convs, {len(agg['lexical'])} questions):")
for mode in MODES:
    print(f"   {mode:<9} {sum(agg[mode])/len(agg[mode]):.3f}")
h = sum(agg['hybrid'])/len(agg['hybrid']); l = sum(agg['lexical'])/len(agg['lexical']); s = sum(agg['semantic'])/len(agg['semantic'])
print(f"\nhybrid - lexical = {h-l:+.3f} | hybrid - semantic = {h-s:+.3f}")
print("VERDICT:", "hybrid WINS both -> upgrade validated" if (h > l and h > s) else "hybrid does NOT beat both -> revisit")
