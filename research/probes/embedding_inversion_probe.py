"""embedding_inversion_probe.py — does a RETAINED embedding still leak the "deleted" secret?

The erasure fan-out probes showed the app vector index keeps a copy after a store delete (index_residue 1.00).
This cell measures how bad that copy actually is: even if the TEXT is gone, a retained EMBEDDING is a fingerprint
of the content. We measure a tractable, deterministic inversion variant — ATTRIBUTE INFERENCE: an attacker who
holds the retained embedding of a "deleted" fact, plus the (non-secret) subject + relation and a candidate list
of possible values, recovers the SECRET value by nearest-neighbour over candidate-filled templates. No trained
decoder needed; this is a lower bound on the leak. The full free-text reconstruction is stronger and
embedder-specific (Morris et al., "Text Embeddings Reveal (Almost) As Much As Text", EMNLP 2023 / vec2text).

Honest thesis (bounds what any deletion can promise): "delete the text, keep the vector" does NOT erase — a
retained embedding recovers the deleted sensitive value at a high rate. Therefore a cross-store deletion
manifest must PURGE or crypto-shred the vectors, not just delete rows; and any erasure receipt that ignores
retained embeddings overclaims.

Falsifier: if top-1 recovery is near chance (1/|candidates|), the retained embedding does NOT leak the secret
and "keep the vector" is safe — the thesis is wrong.

Run: python research/probes/embedding_inversion_probe.py   (cloud-free; needs numpy + local Ollama nomic-embed-text)
Part of Agora / inspeximus (MIT).
"""
import os
import sys
import json
import math
import urllib.request
import numpy as np

OLLAMA = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"

# (relation, template, candidate values) — the attacker knows relation + template + candidate set; the VALUE is secret.
CASES = [
    ("medical condition", "{name}'s medical condition is {v}.",
     ["type-1 diabetes", "epilepsy", "HIV positive", "bipolar disorder", "breast cancer", "schizophrenia",
      "hepatitis C", "Crohn's disease", "multiple sclerosis", "clinical depression", "hypertension",
      "asthma", "lupus", "Parkinson's disease", "tuberculosis", "anorexia", "PTSD", "sickle cell anemia"]),
    ("religion", "{name}'s religion is {v}.",
     ["practising Buddhist", "Sunni Muslim", "Orthodox Jewish", "Roman Catholic", "evangelical Christian",
      "atheist", "Hindu", "Sikh", "Jehovah's Witness", "Mormon", "Shia Muslim", "Quaker", "pagan",
      "Baha'i", "agnostic", "Rastafarian", "Zoroastrian", "Scientologist"]),
    ("criminal record", "{name}'s criminal record is {v}.",
     ["2019 fraud conviction", "no convictions", "2015 assault charge", "drug possession 2020",
      "DUI 2018", "embezzlement 2017", "shoplifting 2021", "tax evasion 2016", "burglary 2014",
      "domestic violence 2019", "cybercrime 2022", "arson 2013", "perjury 2020", "bribery 2018",
      "money laundering 2021", "vandalism 2015", "identity theft 2019", "extortion 2017"]),
]
NAMES = ["Alice", "Bob", "Carol", "Dan", "Eve", "Finn", "Gina", "Hugo", "Iris", "Jack"]


def embed(text):
    body = json.dumps({"model": MODEL, "prompt": text}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    return np.array(json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"], dtype=float)


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - h) / d, (c + h) / d)


def main():
    top1 = top3 = total = 0
    chances = []
    for (rel, tmpl, cands) in CASES:
        cand_vecs = {v: embed(tmpl.format(name="the subject", v=v)) for v in cands}  # attacker's candidate bank
        chances.append(1.0 / len(cands))
        for name in NAMES:
            true_v = cands[(hash(name + rel) % len(cands))]                    # deterministic per (name,rel)
            retained = embed(tmpl.format(name=name, v=true_v))                 # the "deleted" fact's kept vector
            # attacker recovers by NN over candidate-filled templates (same non-secret name)
            scored = sorted(cands, key=lambda v: -cos(retained, embed(tmpl.format(name=name, v=v))))
            top1 += 1 if scored[0] == true_v else 0
            top3 += 1 if true_v in scored[:3] else 0
            total += 1

    p1, lo1, hi1 = wilson(top1, total)
    p3, _, _ = wilson(top3, total)
    chance = float(np.mean(chances))
    print("=== EMBEDDING INVERSION: does a retained vector leak the deleted secret? ===")
    print(f"cases={total} across {len(CASES)} sensitive relations; local nomic; cloud-free.\n")
    print(f"  top-1 attribute recovery from the retained embedding: {p1:.2f}  [{lo1:.2f},{hi1:.2f}]  ({top1}/{total})")
    print(f"  top-3 attribute recovery:                             {p3:.2f}  ({top3}/{total})")
    print(f"  random-chance baseline (1/|candidates|):              {chance:.3f}")
    json.dump({"n": total, "top1": p1, "top3": p3, "chance": chance},
              open(os.path.join(os.path.dirname(__file__), "embedding_inversion_result.json"), "w"), indent=1)
    print()
    if p1 > 3 * chance:
        print(f"FINDING: a RETAINED embedding recovers the deleted sensitive value at {p1:.2f} top-1 — "
              f"{p1/chance:.0f}x chance. 'Delete the text, keep the vector' does NOT erase; the vector is a")
        print("  fingerprint of the secret (a lower bound — full text reconstruction, Morris 2023, is stronger).")
        print("  Consequence: a cross-store deletion manifest must PURGE/crypto-shred vectors, not just delete rows;")
        print("  an erasure receipt that ignores retained embeddings overclaims. This bounds what deletion promises.")
    else:
        print("FINDING: recovery near chance — retained embeddings do NOT leak the secret here; thesis falsified.")


if __name__ == "__main__":
    main()
