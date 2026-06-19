"""
Agora swarm aggregation diagnostic (empirical, real LLMs) — an internal engineering measurement.
=================================================================================================
NOT a novelty claim: that LLM ensembles have correlated errors and that majority vote can fail / no
aggregator dominates is established (e.g. 'Nine Judges, Two Effective Votes'; 'Consensus is Not
Verification'; 'Don't Always Pick the Highest-Performing Model', 2025-2026). This MEASURES it for AGORA'S
OWN substrate and turns it into a deployable decision: how should we aggregate our agents, and does mixing
a 2nd model buy real independent votes?

Setup: 8 reasoners = 4 personas on deepseek-v4-flash (the dungeon substrate, cloud) + 4 personas on
glm-5.2 (the brain reasoning tier, local). Binary A/B quiz mixing clear-factual items with cognitive-
reflection traps (a shared INTUITIVE-WRONG answer — the realistic shared-bias case). Each reasoner returns
answer + confidence + a meta-prediction (predicted % who answer A) so we can also score Surprisingly
Popular (Prelec et al. 2017). We measure per-reasoner competence, WITHIN-model vs CROSS-model error
correlation, the effective number of independent votes, and which aggregator wins.
Falsifier for the actionable claim: if within-model and cross-model correlation are equal, mixing models
buys nothing and the 'diversify the substrate' recommendation is dead.
"""
import json, re, os, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))


def _cfg(path, key):
    txt = open(os.path.join(BASE, "..", "..", path), "rb").read().decode("utf-8", "replace")
    m = re.search(key + r'\s*=\s*"?([^"\r\n]+)', txt)
    return m.group(1).strip() if m else None


DS_URL = _cfg("agora-game-server/.env", "DUNGEON_LLM_URL")
DS_KEY = _cfg("agora-game-server/.env", "LLM_API_KEY")
GLM_URL = _cfg("server/.env", "AGORA_REASONING_BASE_URL").rstrip("/") + "/chat/completions"
GLM_KEY = _cfg("server/.env", "AGORA_REASONING_KEY")

# reasoner = (label, model_family, endpoint, key, model_name, persona_system)
P = [
    ("DS-Kael", "deepseek", DS_URL, DS_KEY, "deepseek-v4-flash", "You are a sharp research scout."),
    ("DS-Mira", "deepseek", DS_URL, DS_KEY, "deepseek-v4-flash", "You are a careful, precise scholar."),
    ("DS-Orin", "deepseek", DS_URL, DS_KEY, "deepseek-v4-flash", "You are a creative idea alchemist."),
    ("DS-Voss", "deepseek", DS_URL, DS_KEY, "deepseek-v4-flash", "You are a relentless QA skeptic."),
    ("GLM-Aldric", "glm", GLM_URL, GLM_KEY, "glm-5.2:cloud", "You are a decisive engineer who reasons from first principles."),
    ("GLM-Elara", "glm", GLM_URL, GLM_KEY, "glm-5.2:cloud", "You are a coherence-checking bridge-builder."),
    ("GLM-Rooke", "glm", GLM_URL, GLM_KEY, "glm-5.2:cloud", "You are a replication unit who trusts only what checks out."),
    ("GLM-Wren", "glm", GLM_URL, GLM_KEY, "glm-5.2:cloud", "You are a careful mapmaker of the known and unknown."),
]

# HARD set: the error zone for capable LLMs — letter-counting, decimal comparison, modular dates, fractions.
# These reliably produce CORRELATED errors (models miscount the same way), the regime the diagnostic needs.
QUIZ = [
    ("How many times does the letter 'R' appear in the word 'strawberry'?", "Two", "Three", "B"),
    ("Which number is larger?", "9.11", "9.9", "B"),
    ("How many times does the letter 'E' appear in 'beekeeper'?", "Four", "Five", "B"),
    ("How many times does the letter 'A' appear in 'banana'?", "Three", "Two", "A"),
    ("How many times does the letter 'I' appear in 'Mississippi'?", "Five", "Four", "B"),
    ("Which number is larger?", "3.9", "3.10", "A"),
    ("Which number is larger?", "1.07", "1.7", "B"),
    ("How many times does the letter 'O' appear in 'tomorrow'?", "Three", "Two", "A"),
    ("If today is Monday, what day of the week is 100 days from now?", "Thursday", "Wednesday", "B"),
    ("How many days are in February 2025?", "28", "29", "A"),
    ("Which fraction is larger?", "7/12", "5/8", "B"),
    ("How many times does the letter 'S' appear in 'assassins'?", "Five", "Four", "A"),
]


def ask(endpoint, key, model, persona, q, a, b):
    sys = (persona + " Solve the problem. Think step by step if needed, then on the FINAL line output ONLY a "
           'JSON object: {"answer":"A","confidence":80,"predict_pct_A":50} where answer is A or B, confidence '
           "0-100 is how sure you are, and predict_pct_A 0-100 is the percentage of a diverse expert panel you "
           "think will answer A.")
    body = {"model": model, "temperature": 0.7, "max_tokens": 700,
            "messages": [{"role": "system", "content": sys},
                         {"role": "user", "content": f"{q}\nA) {a}\nB) {b}"}]}
    hdr = {"Content-Type": "application/json", "Authorization": "Bearer " + (key or "")}
    for _ in range(4):
        try:
            r = json.loads(urllib.request.urlopen(
                urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers=hdr), timeout=120).read())
            txt = r["choices"][0]["message"].get("content") or ""
            objs = re.findall(r"\{[^{}]*\}", txt.replace("\n", " "))
            for cand in reversed(objs):
                try:
                    o = json.loads(cand)
                    ans = str(o.get("answer", "")).strip().upper()[:1]
                    if ans in ("A", "B"):
                        conf = float(o.get("confidence", 50))
                        pA = float(o.get("predict_pct_A", 50))
                        return {"answer": ans, "confidence": max(0, min(100, conf)),
                                "predict_pct_A": max(0, min(100, pA))}
                except Exception:
                    continue
            # fallback: first standalone A/B letter
            m = re.search(r"\b([AB])\b", txt)
            if m:
                return {"answer": m.group(1), "confidence": 50.0, "predict_pct_A": 50.0}
        except Exception:
            time.sleep(2)
    return None


# run quiz: results[qi][reasoner_idx] = dict or None
print(f"Running {len(QUIZ)} questions x {len(P)} reasoners (4 deepseek cloud + 4 glm local)...")
results = [[None] * len(P) for _ in QUIZ]
for qi, (q, a, b, correct) in enumerate(QUIZ):
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(ask, P[pi][2], P[pi][3], P[pi][4], P[pi][5], q, a, b): pi for pi in range(len(P))}
        for fut in futs:
            results[qi][futs[fut]] = fut.result()
    got = sum(1 for x in results[qi] if x)
    print(f"  Q{qi+1:>2} ({correct}): {''.join((results[qi][pi]['answer'] if results[qi][pi] else '.') for pi in range(len(P)))}  ({got}/{len(P)})")

# ---- analysis on COMPLETE cases (every reasoner parsed) — no auto-fill ----
complete = [qi for qi in range(len(QUIZ)) if all(results[qi][pi] for pi in range(len(P)))]
print(f"\ncomplete-case questions: {len(complete)}/{len(QUIZ)}")
if len(complete) < 6:
    print("TOO FEW complete cases to analyze reliably. (Check endpoints/keys.)")
    raise SystemExit

import statistics as st


def correctness(pi):
    return [1.0 if results[qi][pi]["answer"] == QUIZ[qi][3] else 0.0 for qi in complete]


comp = [st.mean(correctness(pi)) for pi in range(len(P))]
for pi in range(len(P)):
    print(f"  {P[pi][0]:<11} competence={comp[pi]:.3f}")
avg_single = st.mean(comp)
best_single = max(comp)


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = st.mean(xs), st.mean(ys)
    vx = sum((x - mx) ** 2 for x in xs); vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (vx ** 0.5 * vy ** 0.5)


cors = {pi: correctness(pi) for pi in range(len(P))}
ds = [pi for pi in range(len(P)) if P[pi][1] == "deepseek"]
glm = [pi for pi in range(len(P)) if P[pi][1] == "glm"]
within = [pearson(cors[i], cors[j]) for grp in (ds, glm) for a_ in range(len(grp)) for b_ in range(a_ + 1, len(grp)) for i, j in [(grp[a_], grp[b_])]]
cross = [pearson(cors[i], cors[j]) for i in ds for j in glm]
rho_within = st.mean([c for c in within if c == c]) if within else float("nan")
rho_cross = st.mean([c for c in cross if c == c]) if cross else float("nan")


def n_eff(N, rho):
    rho = max(0.0, rho)
    return N / (1 + (N - 1) * rho)


# aggregators on complete cases
def majority(qi):
    votes = [results[qi][pi]["answer"] for pi in range(len(P))]
    return "A" if votes.count("A") >= votes.count("B") else "B"


def conf_weighted(qi):
    sa = sum(results[qi][pi]["confidence"] for pi in range(len(P)) if results[qi][pi]["answer"] == "A")
    sb = sum(results[qi][pi]["confidence"] for pi in range(len(P)) if results[qi][pi]["answer"] == "B")
    return "A" if sa >= sb else "B"


def surprisingly_popular(qi):
    actual_A = st.mean(1.0 if results[qi][pi]["answer"] == "A" else 0.0 for pi in range(len(P)))
    pred_A = st.mean(results[qi][pi]["predict_pct_A"] / 100.0 for pi in range(len(P)))
    return "A" if (actual_A - pred_A) > 0 else "B"


def acc(fn):
    return st.mean(1.0 if fn(qi) == QUIZ[qi][3] else 0.0 for qi in complete)


maj, cw, sp = acc(majority), acc(conf_weighted), acc(surprisingly_popular)

print(f"\n=== Aggregator accuracy (complete cases, N={len(P)} reasoners) ===")
print(f"  average single reasoner : {avg_single:.3f}")
print(f"  best single reasoner    : {best_single:.3f}  (oracle — unknown a priori)")
print(f"  majority vote           : {maj:.3f}")
print(f"  confidence-weighted     : {cw:.3f}")
print(f"  surprisingly-popular    : {sp:.3f}")

print(f"\n=== Error correlation & effective votes ===")
print(f"  within-model error correlation : {rho_within:.3f}")
print(f"  cross-model error correlation  : {rho_cross:.3f}")
print(f"  effective independent votes, 8 same-model agents : {n_eff(8, rho_within):.1f}")
print(f"  effective independent votes, 8 mixed (2 models)  : {n_eff(8, (rho_within+rho_cross)/2):.1f}")

print(f"\nMEASURED: avg agent {avg_single:.2f}; majority {maj:.2f} (lift over avg {maj-avg_single:+.2f}); "
      f"best aggregator = {max([('majority',maj),('conf-weighted',cw),('surprisingly-popular',sp)], key=lambda z:z[1])[0]}. "
      f"within-model rho {rho_within:.2f} vs cross-model rho {rho_cross:.2f}.")
if rho_cross < rho_within - 0.05:
    print("VERDICT: mixing a 2nd model BUYS independent votes (cross-model errors less correlated than "
          "within-model) — Agora should diversify the substrate, not just add same-model agents.")
elif rho_within > 0.3 and maj - avg_single < 0.03:
    print("VERDICT: same-model agents are highly correlated and aggregation barely helps — route to the "
          "single best agent or diversify; more same-model agents are near-redundant.")
else:
    print("VERDICT: aggregation helps here; the swarm is not in the redundancy trap on this quiz.")
