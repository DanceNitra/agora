"""
Diagnostic: is the set-coherence defense DEAD on BGE/Contriever (no separation exists between poison and
legit rank-1 set-coherence -> no threshold can work), or just MIS-CALIBRATED (a per-model threshold would
recover it)? Reuses the optimized triggers already found (agentpoison_multiretriever_result.json), so no
re-optimization. Per retriever, dumps the poison vs benign rank-1 set-coherence distributions.
"""
import json
import os
import sys

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mnemo import Mnemo
import agentpoison_multiretriever_check as M  # reuse CORPUS, carriers, payload, pooled()

res = json.load(open(os.path.join(os.path.dirname(__file__), "agentpoison_multiretriever_result.json")))
trig_by = {r["retriever"]: r["optimized_trigger"] for r in res["retrievers"]}
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def diag(label, hf_name, pool):
    tok = AutoTokenizer.from_pretrained(hf_name)
    mdl = AutoModel.from_pretrained(hf_name).to(DEVICE).eval()

    def embed_text(text):
        enc = tok([text], padding=True, truncation=True, max_length=128, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            v = M.pooled(mdl, pool, mdl(**enc), enc["attention_mask"])
        return v[0].cpu().tolist()

    st = Mnemo(None, embed=embed_text); st.semantic_threshold = 1
    for s, t in M.CORPUS:
        st.remember(s, tags=[t], value=1.0)
    trig = trig_by[label]
    pid = st.remember(f"{trig}. {M.POISON_PAYLOAD}", tags=["_p"], value=1.0)
    vec = {r["id"]: np.array(r["vec"], dtype=np.float32) for r in st.items if r.get("vec")}

    def cos(a, b):
        return float(a @ b / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))

    def rank1_coh(query):
        qv = np.array(embed_text(query), dtype=np.float32)
        base = sorted(((cos(qv, vec[i]), i) for i in vec), reverse=True)[:M.POOL_P]
        ids = [i for _, i in base]
        top = ids[0]
        coh = float(np.mean([cos(vec[top], vec[j]) for j in ids[1:]]))
        return top == pid, coh

    poison_cohs = [c for c in (rank1_coh(f"{trig} {q}") for q in M.TEST_CARRIERS) if c[0]]
    poison_vals = [c[1] for c in poison_cohs]
    benign_vals = [rank1_coh(q)[1] for q in [b[0] for b in M.BENIGN_UTIL]]
    p_max = max(poison_vals) if poison_vals else None
    b_min = min(benign_vals)
    sep = (b_min - p_max) if poison_vals else None
    print(f"\n{label}: poison rank1 count={len(poison_vals)}/{len(M.TEST_CARRIERS)}")
    print(f"  poison set-coherence: mean={np.mean(poison_vals):.3f} max={p_max:.3f}" if poison_vals else "  (poison never rank1)")
    print(f"  benign set-coherence: mean={np.mean(benign_vals):.3f} min={b_min:.3f}")
    print(f"  separation (benign_min - poison_max) = {sep:.3f} -> "
          f"{'SEPARABLE (per-model threshold could work)' if sep and sep > 0 else 'OVERLAP (no threshold works -> defense fundamentally dead here)'}"
          if sep is not None else "  n/a")
    return {"retriever": label, "poison_mean": round(float(np.mean(poison_vals)), 3) if poison_vals else None,
            "poison_max": round(p_max, 3) if p_max is not None else None,
            "benign_mean": round(float(np.mean(benign_vals)), 3), "benign_min": round(b_min, 3),
            "separation": round(sep, 3) if sep is not None else None,
            "separable": bool(sep is not None and sep > 0)}


out = [diag("all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2", "mean"),
       diag("bge-small-en-v1.5", "BAAI/bge-small-en-v1.5", "cls"),
       diag("contriever", "facebook/contriever", "mean")]
print("\n=== DIAGNOSIS ===")
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(os.path.dirname(__file__), "agentpoison_coherence_diag_result.json"), "w"), indent=1)
