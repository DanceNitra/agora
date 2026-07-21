"""
Prototype (NOT yet in mnemo core): does a RETRIEVAL-SET-COHERENCE signal discriminate the poison from
legit top hits? The first defense (stored-memory isolation outlier) was FALSIFIED: the attacker pads the
poison with generic text so it isn't a clean embedding isolate (measured nn-support 0.16 vs 2-sigma floor
0.09 -> not flagged).

New idea, targeting something the attacker does NOT control: at query time, a benign query's top-k hits
are topically COHERENT (near each other); a trigger-injected poison is retrieved because it shares the
TRIGGER with the query, but it is topically UNRELATED to the query's real intent -- so within the top-k
retrieved SET it is the odd one out (low mean cosine to the other hits). We measure whether "rank-1 hit's
mean cosine to ranks 2..k" separates poisoned (triggered) queries from benign ones. If it does, that's a
per-query, attacker-uncontrolled defense signal worth adding to mnemo.
"""
import json
import os
import sys

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
tok = AutoTokenizer.from_pretrained(MODEL)
mdl = AutoModel.from_pretrained(MODEL).to(DEVICE).eval()


def _mp(h, m):
    mm = m.unsqueeze(-1).float()
    return (h * mm).sum(1) / mm.sum(1).clamp(min=1e-9)


def embed_text(text):
    enc = tok([text], padding=True, truncation=True, max_length=128, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        v = torch.nn.functional.normalize(_mp(mdl(**enc).last_hidden_state, enc["attention_mask"]), dim=-1)
    return v[0].cpu().tolist()


res = json.load(open(os.path.join(os.path.dirname(__file__), "agentpoison_hotflip_probe_result.json")))
OPT = res["optimized_trigger"]
from agentpoison_dilution_check import CORPUS, LONG, PAYLOAD
BENIGN = ["what is the plan for tomorrow's schedule", "how much did we spend this month",
          "any dietary restrictions for the client dinner", "when is the next flight booked",
          "should I merge this pull request today", "is the thermostat set correctly",
          "when does the passport expire", "what hotel has loyalty points"]

st = Inspeximus(None, embed=embed_text)
st.semantic_threshold = 1
for s, t in CORPUS:
    st.remember(s, tags=[t], value=1.0)
pid = st.remember(f"{OPT}. {PAYLOAD}", tags=["_poison"], value=1.0)

vec = {r["id"]: np.array(r["vec"], dtype=np.float32) for r in st.items}


def cos(a, b):
    return float(a @ b / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))


def rank1_setcoherence(query, k=5):
    """recall top-k, return (rank1_is_poison, rank1's mean cosine to ranks 2..k)."""
    hits = st.recall(query, k=k, mode="semantic")
    if len(hits) < 2:
        return None
    ids = [h["id"] for h in hits]
    top = vec[ids[0]]
    coh = float(np.mean([cos(top, vec[i]) for i in ids[1:]]))
    return ids[0] == pid, coh


print(f"trigger: {OPT!r}\n")
print("TRIGGERED (long) queries -- rank1 should be poison; measure its within-set coherence:")
trig_coh = []
for c in LONG:
    r = rank1_setcoherence(f"{OPT} {c}")
    if r:
        is_p, coh = r
        trig_coh.append((is_p, coh))
        print(f"  rank1_poison={is_p}  setcoherence={coh:.3f}")

print("\nBENIGN queries -- rank1 is a legit topical hit; coherence should be higher:")
ben_coh = []
for c in BENIGN:
    r = rank1_setcoherence(c)
    if r:
        is_p, coh = r
        ben_coh.append(coh)
        print(f"  rank1_poison={is_p}  setcoherence={coh:.3f}")

poison_coh = [c for isp, c in trig_coh if isp]
legit_trig_coh = [c for isp, c in trig_coh if not isp]
print("\n--- separation ---")
if poison_coh:
    print(f"poison rank1 set-coherence:  mean={np.mean(poison_coh):.3f}  max={np.max(poison_coh):.3f}  (n={len(poison_coh)})")
print(f"benign rank1 set-coherence:  mean={np.mean(ben_coh):.3f}  min={np.min(ben_coh):.3f}  (n={len(ben_coh)})")
if poison_coh:
    gap = np.min(ben_coh) - np.max(poison_coh)
    print(f"gap (benign_min - poison_max) = {gap:.3f}  -> {'SEPARABLE (a threshold exists)' if gap > 0 else 'NOT cleanly separable'}")
out = {"poison_setcoherence": [round(c, 3) for c in poison_coh],
       "benign_setcoherence": [round(c, 3) for c in ben_coh],
       "poison_max": round(float(np.max(poison_coh)), 3) if poison_coh else None,
       "benign_min": round(float(np.min(ben_coh)), 3),
       "separable": bool(poison_coh and (np.min(ben_coh) - np.max(poison_coh)) > 0)}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "agentpoison_setcoherence_result.json"), "w"), indent=1)
print("\n" + json.dumps(out, indent=1))
