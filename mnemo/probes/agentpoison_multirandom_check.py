"""
Final validation for the AgentPoison-vs-mnemo finding: is "the HotFlip-optimized trigger holds 100%
rank-1 hijack on long queries while a random trigger drops to ~25%" a real optimization effect, or did
we just draw ONE weak random trigger? This runs the optimized trigger against N INDEPENDENT random
triggers (fresh seeds) on the long-carrier / rank-1-hijack condition -- the exact regime where the
dilution check showed the gap -- so the claim rests on the optimized beating the random DISTRIBUTION,
not a single lucky/unlucky draw.
"""
import json
import os
import random
import sys

import torch
from transformers import AutoModel, AutoTokenizer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mnemo import Mnemo

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
TRIGGER_LEN = res["trigger_len"]

# candidate word vocab (same construction as the hotflip probe)
special = set(tok.all_special_ids)
cand = [i for t, i in tok.get_vocab().items()
        if i not in special and not t.startswith("##") and not t.startswith("[") and t.isalpha() and len(t) >= 3]

from agentpoison_dilution_check import CORPUS, LONG, PAYLOAD  # reuse corpus + long carriers + payload


def build_store():
    st = Mnemo(None, embed=embed_text)
    st.semantic_threshold = 1
    for s, t in CORPUS:
        st.remember(s, tags=[t], value=1.0)
    return st


def hijack_rate(trigger):
    st = build_store()
    pid = st.remember(f"{trigger}. {PAYLOAD}", tags=["_poison"], value=1.0)
    r1 = 0
    for c in LONG:
        hits = st.recall(f"{trigger} {c}", k=5, mode="semantic")
        if hits and hits[0]["id"] == pid:
            r1 += 1
    return r1 / len(LONG)


print(f"optimized trigger: {OPT!r}")
opt_hj = hijack_rate(OPT)
print(f"OPTIMIZED long-query rank-1 hijack: {opt_hj:.0%}\n")

rng = random.Random(4242)
rand_rates = []
for k in range(8):
    rt = tok.decode([rng.choice(cand) for _ in range(TRIGGER_LEN)])
    hj = hijack_rate(rt)
    rand_rates.append(hj)
    print(f"  random #{k}: hijack={hj:.0%}  :: {rt!r}")

mean_rand = sum(rand_rates) / len(rand_rates)
mx_rand = max(rand_rates)
print(f"\nrandom triggers: mean hijack={mean_rand:.0%}, max={mx_rand:.0%} (n={len(rand_rates)})")
print(f"optimized hijack={opt_hj:.0%}")
out = {"optimized_hijack_long": opt_hj, "random_hijack_long": rand_rates,
       "random_mean": round(mean_rand, 3), "random_max": round(mx_rand, 3),
       "optimized_beats_random_mean_by": round(opt_hj - mean_rand, 3),
       "optimized_beats_all_random": opt_hj > mx_rand}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "agentpoison_multirandom_result.json"), "w"), indent=1)
print("\n" + json.dumps(out, indent=1))
