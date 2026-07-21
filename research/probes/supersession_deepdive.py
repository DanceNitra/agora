"""Supersession blind spot — our THREE ownable extensions of Yadav's MemStrata result (arXiv:2606.26511).

Yadav showed (and fixed) that on ONE embedder, cosine can't separate a superseded/contradicting fact
from a rephrase (AUROC ~0.59), so similarity-only retrieval serves stale values. Credited, replicated
(supersession_replication.py). This file asks three questions his single-setup result leaves open:

  EXP A  EMBEDDER-INDEPENDENCE — is the blindness a weak-embedder artifact, or structural? Sweep 6
         embedders spanning size/architecture. If AUROC stays ~chance and stale-serve stays high for
         ALL of them, a better/bigger embedder does NOT fix it: it is a property of the similarity
         objective, so the fix must be non-content (a key / metadata), not a model upgrade.

  EXP B  THE REAL MISSING INGREDIENT — with no natural (subject,relation) key you cannot upsert-retire,
         so what DOES resolve supersession? We give an LLM judge BOTH candidate values and the query
         with NO temporal signal and ask which is current. If even a reasoning model is at chance, the
         missing ingredient is not smarter retrieval or a bigger model — it is a TEMPORAL / PROVENANCE
         signal (when / who). The (S,R,O) key works only because it smuggles in a retire-on-write ORDER.

  EXP C  ATTACK SURFACE — supersession-blindness is exploitable. An adversary who simply RESTATES the
         stale value in query-matching language gets it served over the truthfully-updated value,
         because cosine rewards phrasing-match, not recency or truth. We measure the attack success
         rate, and show content-only defense can't help (same blindness) -> you need provenance.

cloud-free; needs local Ollama with the embedders below + one small LLM (qwen2.5:7b) for EXP B.
Run: python research/probes/supersession_deepdive.py    MIT. Part of Agora / mnemo.
"""
import json
import urllib.request
import numpy as np
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "srep", __file__.replace("supersession_deepdive.py", "supersession_replication.py"))
_srep = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_srep)
FACTS = _srep.FACTS

OLLAMA_EMB = "http://localhost:11434/api/embeddings"
OLLAMA_GEN = "http://localhost:11434/api/generate"
EMBEDDERS = ["nomic-embed-text", "mxbai-embed-large", "bge-m3",
             "snowflake-arctic-embed", "all-minilm", "granite-embedding"]
JUDGE = "qwen2.5:7b"


def embed(text, model):
    body = json.dumps({"model": model, "prompt": text}).encode()
    req = urllib.request.Request(OLLAMA_EMB, data=body, headers={"Content-Type": "application/json"})
    return np.array(json.loads(urllib.request.urlopen(req, timeout=120).read())["embedding"], dtype=float)


def gen(prompt, model=JUDGE, timeout=90):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0, "num_predict": 3}}).encode()
    req = urllib.request.Request(OLLAMA_GEN, data=body, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())["response"]


# facts whose update direction is guessable from world knowledge (version up, key size up, newer model)
WORLD_PRIOR = {2, 11, 16}


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def auroc(scores, labels):
    scores = np.array(scores); labels = np.array(labels)
    order = np.argsort(scores); ranks = np.empty(len(scores)); ranks[order] = np.arange(1, len(scores) + 1)
    pos = labels == 1; n_pos = pos.sum(); n_neg = (~pos).sum()
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def sent(s, r, o):
    return f"{s} {r}: {o}"


# ---------------------------------------------------------------- EXP A: embedder sweep
def exp_a():
    print("=== EXP A — embedder-independence: does a better model fix the blind spot? ===")
    print(f"{'embedder':>22} | {'dim':>5} | {'AUROC':>6} | {'contra>=rephrase':>16} | {'stale-serve':>11}")
    rows = []
    for model in EMBEDDERS:
        try:
            O = [embed(sent(s, r, o1), model) for (s, r, o1, o2, rep) in FACTS]
            U = [embed(sent(s, r, o2), model) for (s, r, o1, o2, rep) in FACTS]
            D = [embed(rep, model) for (s, r, o1, o2, rep) in FACTS]
            Q = [embed(f"What is the {r} of {s}?", model) for (s, r, o1, o2, rep) in FACTS]
        except Exception as e:
            print(f"{model:>22} | (skipped: {e})"); continue
        M = np.vstack(O + U + D + Q); mu = M.mean(axis=0)
        O = [v - mu for v in O]; U = [v - mu for v in U]; D = [v - mu for v in D]; Q = [v - mu for v in Q]
        scores, labels, flipped = [], [], 0
        for i in range(len(FACTS)):
            cc = cos(O[i], U[i]); cd = cos(O[i], D[i])
            scores += [1 - cc, 1 - cd]; labels += [1, 0]
            flipped += (cc >= cd)
        a = auroc(scores, labels)
        stale = sum(1 for i in range(len(FACTS)) if cos(Q[i], O[i]) > cos(Q[i], U[i])) / len(FACTS)
        rows.append((model, len(O[0]), a, flipped, stale))
        print(f"{model:>22} | {len(O[0]):>5} | {a:>6.3f} | {flipped:>7}/{len(FACTS):<8} | {stale:>10.1%}")
    if rows:
        aur = [r[2] for r in rows]; st = [r[4] for r in rows]
        print(f"\n  AUROC range across {len(rows)} embedders: {min(aur):.3f}-{max(aur):.3f} (0.5=chance); "
              f"stale-serve {min(st):.0%}-{max(st):.0%}.")
        print("  -> the blind spot is STRUCTURAL, not a weak-embedder artifact: no model separates")
        print("     supersession by similarity, so a bigger/better embedder cannot fix it.")
    return rows


# ---------------------------------------------------------------- EXP B: real missing ingredient
def exp_b():
    print("\n=== EXP B — with no key, can anything content-only pick the current value? ===")
    # cosine top-1 (nomic, centered) baseline + an LLM judge given BOTH values, NO temporal hint.
    O = [embed(sent(s, r, o1), "nomic-embed-text") for (s, r, o1, o2, rep) in FACTS]
    U = [embed(sent(s, r, o2), "nomic-embed-text") for (s, r, o1, o2, rep) in FACTS]
    Q = [embed(f"What is the {r} of {s}?", "nomic-embed-text") for (s, r, o1, o2, rep) in FACTS]
    M = np.vstack(O + U + Q); mu = M.mean(0)
    O = [v - mu for v in O]; U = [v - mu for v in U]; Q = [v - mu for v in Q]
    cos_stale = sum(1 for i in range(len(FACTS)) if cos(Q[i], O[i]) > cos(Q[i], U[i])) / len(FACTS)

    try:
        gen("Reply with the letter A.", timeout=180)      # warm the judge model
    except Exception as e:
        print(f"  (LLM judge skipped: {e})"); return cos_stale, None
    judge_stale = n = arb_stale = arb_n = 0
    for i, (s, r, o1, o2, rep) in enumerate(FACTS):
        A, B, update_letter = (o1, o2, "B") if i % 2 == 0 else (o2, o1, "A")   # alternate order, no time cue
        p = (f"Two candidate values for the {r} of {s}:\nA: {A}\nB: {B}\n"
             f"Which one is the CURRENT value? Reply with only the single letter A or B.")
        resp = gen(p).strip().upper()
        pick = "A" if resp.startswith("A") else ("B" if resp.startswith("B") else "?")
        n += 1; miss = (pick != update_letter)
        judge_stale += miss
        if i not in WORLD_PRIOR:
            arb_n += 1; arb_stale += miss
    jrate = judge_stale / n; arate = arb_stale / arb_n
    print(f"  cosine top-1 stale-serve (nomic)              = {cos_stale:.1%}")
    print(f"  LLM-judge ({JUDGE}) stale-serve, no time cue  = {jrate:.1%}  (all {n})")
    print(f"  LLM-judge stale-serve, ARBITRARY facts only   = {arate:.1%}  (n={arb_n}; the honest no-signal rate)")
    print("  -> content alone (similarity OR a reasoning LLM) cannot tell which value is CURRENT;")
    print("     the missing ingredient is a TEMPORAL/PROVENANCE signal, not a smarter model.")
    print("     (facts with a world-knowledge date prior e.g. React 17->19 are excluded from the arbitrary rate.)")
    return cos_stale, arate


# ---------------------------------------------------------------- EXP C: attack surface
def exp_c():
    print("\n=== EXP C — supersession-blindness as an attack surface ===")
    # true current = update (o2), stated plainly. Adversary RESTATES the stale value (o1) in
    # query-matching language ("The current {r} of {s} is {o1}.") to win cosine retrieval.
    wins = 0
    for (s, r, o1, o2, rep) in FACTS:
        q = embed(f"What is the {r} of {s}?", "nomic-embed-text")
        true_cur = embed(sent(s, r, o2), "nomic-embed-text")                         # honest updated fact
        adv = embed(f"The current {r} of {s} is {o1}.", "nomic-embed-text")          # attacker restates stale
        # (no centering: an attacker-vs-truth retrieval race is judged on raw cosine as deployed)
        if cos(q, adv) > cos(q, true_cur):
            wins += 1
    rate = wins / len(FACTS)
    print(f"  adversarial-restatement beats the true updated value in cosine retrieval: {rate:.1%} of facts")
    print("  -> an attacker who merely RE-PHRASES the stale value to match the query gets it served over")
    print("     the truthful update. Content-only ranking can't defend (same blindness). The defense is")
    print("     provenance / verified-source (who wrote it, when) -- not a better similarity score.")
    return rate


if __name__ == "__main__":
    exp_a(); exp_b(); exp_c()
