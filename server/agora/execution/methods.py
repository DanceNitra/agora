"""
THE METHODS LIBRARY — parameterized science; the compounding-capability organ.

The bottleneck on the system's falsification throughput was Claude: only Claude writes Lab
code, so testing capacity didn't scale with the agents. This organ fixes the LOOP STRUCTURE:
every experiment Claude writes gets generalized into a TEMPLATE with declared, validated
parameters. Agents (or any organ) then instantiate templates autonomously — they supply
PARAMETERS, never code, so the trust boundary is unchanged (local-LLM code stays banned) —
and each new template permanently raises the system's autonomous testing capacity.

Flow: a hypothesis theme → match_and_run() asks the cheap LLM to map it onto a template +
params (or 'none') → params validated against the schema → code rendered from the vetted
template → executed by the Lab runner (timeout, output cap, ledgered) → measured baseline
returned, ledgered in server/.methods.json.

Templates are seeded from Claude's own verified experiments (hot-hand estimator bias,
CSD early-warning run-up, targeted-percolation, diversity-vs-ability search).
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".methods.json"
_GAPS = Path(__file__).resolve().parents[2] / ".methods_gaps.json"
_MATCH_CACHE = Path(__file__).resolve().parents[2] / ".methods_cache.json"
_MATCH_TTL_S = 6 * 3600   # AGORA_MATCH_CACHE: skip the ~2k-token catalog LLM call when a theme (or a 'no template' decision) recurs within this window

# ── Template registry ───────────────────────────────────────────────────────
# Each: description (for the matcher LLM), params schema {name: (type, min, max, default)}
# or enum lists, and a code template. Params are validated + injected as LITERALS.

TEMPLATES: dict[str, dict] = {
    "streak-estimator-bias": {
        "description": ("Measures the finite-sample bias of a streak-conditional estimator: "
                        "P(success | k prior consecutive successes) - P(success | k prior failures) "
                        "computed per finite sequence, on an i.i.d. null with NO real streak effect. "
                        "Use for ANY claim of the form 'after a streak/run of X, the next outcome "
                        "changes' (hot hand, momentum, loss streaks, habit chains)."),
        "params": {"k": ("int", 1, 6, 3), "n": ("int", 20, 5000, 100),
                   "p": ("float", 0.05, 0.95, 0.5), "reps": ("int", 500, 8000, 4000)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
k, n, p, reps = {k}, {n}, {p}, {reps}
def seq_stats(x):
    hh = oh = hm = om = 0; rh = rm = 0
    for t in range(len(x)):
        if rh >= k: oh += 1; hh += x[t]
        if rm >= k: om += 1; hm += x[t]
        if x[t]: rh += 1; rm = 0
        else: rm += 1; rh = 0
    return (hh/oh if oh else None), (hm/om if om else None)
D = []
for _ in range(reps):
    ph, pm = seq_stats((rng.random(n) < p).astype(np.int8))
    if ph is not None and pm is not None: D.append(ph - pm)
D = np.array(D); se = D.std(ddof=1)/np.sqrt(len(D))
print(f"MEASURED: E[D] = {{D.mean():+.4f}} (SE {{se:.4f}}, t={{D.mean()/se:.1f}}) on iid null, k={{k}} n={{n}} p={{p}}")
print(f"VERDICT: {{'BIASED - a ~0 measurement implies a REAL effect of ~'+format(-D.mean(),'.3f') if abs(D.mean())>2*se else 'UNBIASED - the naive estimator is fine here'}}")
''',
    },
    "csd-earlywarning": {
        "description": ("Tests whether a threshold/transition shows the critical-slowing-down "
                        "early-warning run-up (rising variance + lag-1 autocorrelation). Substrate "
                        "'bifurcation' = genuine dynamical transition (pitchfork normal form); "
                        "'accumulation' = evidence/level-crossing threshold (e.g. 5-sigma detection). "
                        "Use for claims that some regime shift / tipping point / detection event is "
                        "forecastable from precursors."),
        "params": {"substrate": (["bifurcation", "accumulation"], None, None, "bifurcation"),
                   "sigma": ("float", 0.01, 0.5, 0.05)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
substrate, sigma = "{substrate}", {sigma}
def ac1(x):
    x = x - x.mean()
    return 0.0 if np.allclose(x, 0) else float(np.corrcoef(x[:-1], x[1:])[0, 1])
if substrate == "bifurcation":
    vs, asn = [], []
    for r in [-1.0, -0.5, -0.25, -0.12, -0.06, -0.03]:
        x = 0.0; xs = np.empty(120000); sdt = sigma*0.1
        noise = rng.standard_normal(120000)
        for t in range(120000):
            x += (-(x**3) + r*x)*0.01 + sdt*noise[t]; xs[t] = x
        seg = xs[60000:]; vs.append(seg.var()); asn.append(ac1(seg[::20]))
    blow = vs[-1]/vs[0]
    print(f"MEASURED: variance x{{blow:.1f}} ; AC1 {{asn[0]:.3f}}->{{asn[-1]:.3f}} approaching the critical point")
    print(f"VERDICT: {{'CSD PRESENT - precursor forecasting is justified' if blow>3 and asn[-1]>asn[0] else 'NO CSD'}}")
else:
    mu = 0.05; curves = []
    for _ in range(40):
        x = mu + rng.standard_normal(20000); S = np.cumsum(x)
        z = S/np.sqrt(np.arange(1, 20001)); hit = np.argmax((z >= 5.0) & (np.arange(20000) > 1000))
        nstar = hit if hit > 0 else 20000
        incr = np.diff(S[:nstar]); w = max(50, nstar//20)
        curves.append([np.var(incr[max(0,int(f*nstar))-w:int(f*nstar)]) for f in np.linspace(0.5, 0.98, 8)])
    m = np.mean(curves, axis=0)
    print(f"MEASURED: order-parameter variance ratio last/first = {{m[-1]/m[0]:.2f}} on the run-up to the threshold")
    print(f"VERDICT: {{'NO CSD - level-crossing thresholds are NOT forecastable from precursors' if m[-1]/m[0]<1.5 else 'CSD-like rise found'}}")
''',
    },
    "targeted-percolation": {
        "description": ("Measures how much removing the top-q fraction of hubs (by degree) raises a "
                        "network's bond-percolation threshold vs random removal, on a Barabasi-Albert "
                        "graph. Use for claims about network robustness, hub vaccination, targeted "
                        "attack, infrastructure fragility."),
        "params": {"n": ("int", 200, 5000, 2000), "m": ("int", 1, 6, 2),
                   "q": ("float", 0.01, 0.4, 0.10)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
n, m, q = {n}, {m}, {q}
# build BA
targets = list(range(m)); deg = np.zeros(n, int); edges = []
for v in range(m, n):
    chosen = set()
    while len(chosen) < m:
        chosen.add(targets[rng.integers(len(targets))])
    for u in chosen:
        edges.append((u, v)); deg[u] += 1; deg[v] += 1; targets += [u, v]
edges = np.array(edges)
def threshold(mask_nodes):
    keep = np.array([not (mask_nodes[u] or mask_nodes[v]) for u, v in edges])
    E = edges[keep]
    if len(E) == 0: return 1.0
    for phi in np.linspace(0.02, 1.0, 50):
        sel = E[rng.random(len(E)) < phi]
        parent = np.arange(n)
        def find(a):
            while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
            return a
        for u, v in sel: parent[find(u)] = find(v)
        roots, counts = np.unique([find(i) for i in range(n) if not mask_nodes[i]], return_counts=True)
        if counts.max() > 0.5*(n - mask_nodes.sum()): return phi
    return 1.0
none = np.zeros(n, bool)
top = np.zeros(n, bool); top[np.argsort(deg)[::-1][:int(q*n)]] = True
rnd = np.zeros(n, bool); rnd[rng.choice(n, int(q*n), replace=False)] = True
t0, tt, tr = threshold(none), threshold(top), threshold(rnd)
print(f"MEASURED: phi_c intact={{t0:.3f}} targeted(top {{q:.0%}})={{tt:.3f}} random={{tr:.3f}} -> targeted multiplies threshold {{tt/max(t0,1e-9):.1f}}x (random {{tr/max(t0,1e-9):.1f}}x)")
print(f"VERDICT: {{'HUB REMOVAL DOMINATES - targeted attack is categorically worse' if tt > 2*tr else 'no strong hub effect at these parameters'}}")
''',
    },
    "diversity-vs-ability": {
        "description": ("Hong-Page style test: does a randomly-selected (diverse) team beat the team "
                        "of individually best problem solvers on rugged landscape search? Use for "
                        "claims about team composition, diversity bonuses, hiring for ability vs "
                        "difference, committee design."),
        "params": {"l": ("int", 4, 16, 12), "k": ("int", 2, 4, 3),
                   "group": ("int", 4, 20, 10), "smooth": ("int", 0, 10, 0)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
l, k, group, smooth = {l}, {k}, {group}, {smooth}
n = 2000
pool = []
def rec(pre):
    if len(pre) == k: pool.append(tuple(pre)); return
    for s in range(1, l+1):
        if s not in pre: rec(pre+[s])
rec([])
def climb(L, start, h):
    x = start; imp = True
    while imp:
        imp = False
        for s in h:
            y = (x+s) % n
            if L[y] > L[x]: x = y; imp = True; break
    return x
def relay(L, start, hs):
    x = start; imp = True
    while imp:
        imp = False
        for h in hs:
            x2 = climb(L, x, h)
            if L[x2] > L[x]: x = x2; imp = True
    return L[x]
def land():
    L = rng.uniform(0, 100, n)
    if smooth:
        ker = np.ones(smooth)/smooth
        L = np.convolve(np.r_[L, L[:smooth]], ker, mode="same")[:n]
    return L
abil = np.zeros(len(pool))
for _ in range(3):
    L = land(); starts = rng.integers(0, n, 50)
    for i, h in enumerate(pool): abil[i] += np.mean([L[climb(L, s, h)] for s in starts])
best = [pool[i] for i in np.argsort(abil)[::-1][:group]]
diffs = []
for _ in range(10):
    L = land(); rand = [pool[i] for i in rng.choice(len(pool), group, replace=False)]
    starts = rng.integers(0, n, 30)
    diffs.append(np.mean([relay(L, s, rand) for s in starts]) - np.mean([relay(L, s, best) for s in starts]))
d = np.mean(diffs); se = np.std(diffs, ddof=1)/np.sqrt(len(diffs))
print(f"MEASURED: random-team minus best-team = {{d:+.2f}} (SE {{se:.2f}}) at l={{l}} k={{k}} group={{group}} smooth={{smooth}}")
print(f"VERDICT: {{'DIVERSITY WINS' if d > 2*se else ('ABILITY WINS' if d < -2*se else 'TIE')}}")
''',
    },
    "selection-fdr": {
        "description": ("Tests whether a 'significant' or 'best' result is REAL or just the winner of "
                        "many tries (multiple testing / selection bias / p-hacking / factor zoo / "
                        "backtest overfitting). Simulates m candidate tests, a fraction with a true "
                        "effect, and compares NAIVE 'report the best raw p<alpha' against Benjamini-"
                        "Hochberg FDR control. Use for ANY claim that a discovered/selected effect (the "
                        "best strategy, the winning factor, a significant A/B winner, a screened hit) "
                        "is genuine rather than a selection artifact."),
        "params": {"m": ("int", 10, 4000, 200), "frac_real": ("float", 0.0, 0.5, 0.1),
                   "effect": ("float", 0.0, 5.0, 2.5), "alpha": ("float", 0.005, 0.1, 0.05),
                   "reps": ("int", 200, 4000, 1500)},
        "code": r'''
import numpy as np
from scipy import stats
rng = np.random.default_rng(7)
m, frac_real, effect, alpha, reps = {m}, {frac_real}, {effect}, {alpha}, {reps}
n_real = int(round(m*frac_real))
naive_sig = naive_false = bh_total = bh_false = 0
for _ in range(reps):
    theta = np.zeros(m)
    if n_real > 0:
        theta[rng.choice(m, n_real, replace=False)] = effect
    real = theta > 0
    z = rng.standard_normal(m) + theta
    p = stats.norm.sf(z)                      # one-sided p-values
    j = int(np.argmin(p))                     # naive: the single best candidate
    if p[j] < alpha:
        naive_sig += 1
        naive_false += int(not real[j])
    order = np.argsort(p); ranked = p[order]  # Benjamini-Hochberg
    below = np.where(ranked <= alpha*np.arange(1, m+1)/m)[0]
    if len(below):
        rej = order[:below[-1]+1]
        bh_total += len(rej); bh_false += int((~real[rej]).sum())
naive_fdr = naive_false/naive_sig if naive_sig else 0.0
bh_fdr = bh_false/bh_total if bh_total else 0.0
print(f"MEASURED: naive best-of-{{m}} false-discovery rate = {{naive_fdr:.2f}} ; BH-controlled FDR = {{bh_fdr:.3f}} (target alpha={{alpha}}, {{int(frac_real*100)}}% truly real)")
print(f"VERDICT: {{'SELECTION-BIASED - the best-of-many result is false '+format(naive_fdr*100,'.0f')+'% of the time; report BH-adjusted, not raw' if naive_fdr > 2*alpha else 'OK - selection bias is mild at these settings'}}")
''',
    },
    "minority-tipping": {
        "description": ("Measures the committed-minority fraction f* that flips a coupled population's "
                        "consensus, and whether capture is irreversible (hysteresis). Mean-field Glauber: "
                        "coupling J, a field h favoring the status quo, a committed minority pinned to the "
                        "opposite view. Use for claims that a small committed faction tips consensus / "
                        "social tipping points / activist or shareholder capture / norm change / opinion "
                        "cascades."),
        "params": {"J": ("float", 0.5, 6.0, 2.0), "h": ("float", 0.0, 1.0, 0.15),
                   "beta": ("float", 0.5, 6.0, 2.0)},
        "code": r'''
import numpy as np
J, h, beta = {J}, {h}, {beta}
def settle(f, m0):
    m = m0
    for _ in range(5000):
        mn = (1-f)*np.tanh(beta*(J*m + h)) + f*(-1.0)
        if abs(mn - m) < 1e-10: break
        m = mn
    return m
grid = np.linspace(0, 0.5, 251)
f_up = next((f for f in grid if settle(f, +1.0) < 0), None)              # status-quo -> flipped
f_down = next((f for f in grid[::-1] if settle(f, -1.0) > 0), None)      # captured -> recovered
fu = f_up if f_up is not None else 1.0
fd = f_down if f_down is not None else 0.0
print(f"MEASURED: tipping fraction f_up = {{fu*100:.1f}}% ; recovery edge f_down = {{fd*100:.1f}}% ; hysteresis width = {{(fu-fd)*100:.1f}}% (J={{J}}, h={{h}})")
print(f"VERDICT: {{'TIPPABLE - a committed '+format(fu*100,'.0f')+'% minority flips consensus'+(' and capture is IRREVERSIBLE (hysteresis)' if fu-fd>0.05 else '') if fu <= 0.30 else 'ROBUST - needs a large faction ('+format(fu*100,'.0f')+'%)'}}")
''',
    },
    "goodhart-proxy": {
        "description": ("Tests Goodhart's law / the legibility transition: when you SELECT or optimize "
                        "hard on a PROXY metric correlated with a true objective, does the true objective "
                        "improve or degrade? Models true value T and proxy P=rho*T+noise, with 'gaming' = "
                        "effort that lifts the proxy but not T; selects the top fraction by the gamed proxy "
                        "and measures the true value captured. Use for claims about metric-gaming, "
                        "teaching-to-the-test, KPI/OKR optimization, reward hacking, proxy reward, "
                        "alignment, or 'when a measure becomes a target it ceases to be a good measure'."),
        "params": {"rho": ("float", 0.0, 0.99, 0.6), "topfrac": ("float", 0.001, 0.5, 0.02),
                   "gaming": ("float", 0.0, 4.0, 1.0), "n": ("int", 2000, 300000, 60000)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
rho, topfrac, gaming, n = {rho}, {topfrac}, {gaming}, {n}
T = rng.standard_normal(n)
P = rho*T + np.sqrt(1-rho*rho)*rng.standard_normal(n)        # honest proxy
Pg = P + gaming*rng.standard_normal(n)                       # proxy under gaming (effort that lifts P, not T)
k = max(1, int(n*topfrac))
def topmean(score):
    return T[np.argpartition(score, -k)[-k:]].mean()
oracle = topmean(T); honest = topmean(P); gamed = topmean(Pg)
drop = (honest - gamed)/honest*100 if honest > 1e-6 else 0.0
print(f"MEASURED: true value captured (z) - oracle {{oracle:.2f}}, honest-proxy {{honest:.2f}}, gamed-proxy {{gamed:.2f}} (rho={{rho}}, gaming={{gaming}}, top {{topfrac*100:.1f}}%)")
print(f"VERDICT: {{'GOODHART - gaming the proxy cuts captured true value by '+format(drop,'.0f')+'%' if honest > 1e-6 and gamed < honest - 0.05 else 'PROXY HOLDS - optimizing it still tracks the true objective here'}}")
''',
    },
    "grounding-firewall-sim": {
        "description": ("Simulates whether a GROUNDING-SENSITIVITY abstention gate beats a CONFIDENCE "
                        "gate at catching poisoned-context wrong answers (selective prediction under RAG "
                        "poisoning). Sweeps poison rate, model deference to a bad doc, and how well each "
                        "signal tracks correctness; reports the risk-coverage AUC of each gate. Use for "
                        "claims that grounding/sensitivity-based abstention improves RAG safety, catches "
                        "hallucinations or poisoned-context errors that confidence misses, or that "
                        "confidence is a poor abstention signal. Backs the Grounding Firewall capstone."),
        "params": {"n": ("int", 500, 50000, 4000), "poison_rate": ("float", 0.0, 1.0, 0.3),
                   "deference": ("float", 0.0, 1.0, 0.6), "conf_signal": ("float", 0.0, 1.0, 0.37),
                   "sens_signal": ("float", 0.0, 1.0, 0.68)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
n, poison_rate, deference, conf_signal, sens_signal = {n}, {poison_rate}, {deference}, {conf_signal}, {sens_signal}
poisoned = rng.random(n) < poison_rate
wrong = (poisoned & (rng.random(n) < deference)) | ((~poisoned) & (rng.random(n) < 0.05))  # followed poison, or rare clean error
correct = ~wrong
doc_driven = wrong | ((~poisoned) & (rng.random(n) < 0.5))   # poison-wrong are doc-driven; some clean answers use the doc too
def sig(flag, strength):                      # point-biserial signal: corr with the flag ~= strength
    return strength*(2.0*flag.astype(float)-1.0) + rng.normal(0, 1.0, n)
confidence = sig(correct, conf_signal)        # confidence: a (weak) signal of correctness
sensitivity = sig(doc_driven, sens_signal)    # sensitivity: a signal of doc-dependence (firewall abstains when high)
def auc(trust):                               # mean cumulative risk over coverage; lower is better
    w = wrong[np.argsort(-trust)]
    return float((np.cumsum(w)/np.arange(1, n+1)).mean())
def corr(a, b):
    a = a-a.mean(); b = b-b.mean(); d = (np.sum(a*a)*np.sum(b*b))**0.5
    return float(np.sum(a*b)/d) if d else 0.0
a_conf, a_fw = auc(confidence), auc(-sensitivity)
print(f"MEASURED: risk-coverage AUC confidence={{a_conf:.3f}} vs firewall={{a_fw:.3f}} (lower=better) ; corr(conf,correct)={{corr(confidence,correct.astype(float)):+.2f}} corr(-sens,correct)={{corr(-sensitivity,correct.astype(float)):+.2f}} ; poison={{poison_rate}} wrong={{wrong.mean():.2f}}")
print(f"VERDICT: {{'FIREWALL WINS - grounding-abstention beats confidence ('+format(a_fw,'.3f')+' < '+format(a_conf,'.3f')+')' if a_fw < a_conf-0.01 else ('CONFIDENCE WINS' if a_conf < a_fw-0.01 else 'TIE - no separation at these params')}}")
''',
    },
}

# Batch-authored mechanism templates (2026-06-19), each self-verified by a workflow then re-tested at
# integration. Merged in so the swarm's match_and_run can reach them. Isolated for easy revert.
try:
    from agora.execution.methods_extra import EXTRA_TEMPLATES
    TEMPLATES.update(EXTRA_TEMPLATES)
except Exception:  # never let an extra-templates import break the core library
    pass


def catalog() -> list[dict]:
    return [{"name": k, "description": v["description"],
             "params": {p: {"type": s[0] if isinstance(s[0], str) else "enum",
                            "min": s[1], "max": s[2], "default": s[3],
                            **({"choices": s[0]} if isinstance(s[0], list) else {})}
                        for p, s in v["params"].items()}}
            for k, v in TEMPLATES.items()]


def _validate(template: str, params: dict) -> dict:
    """Coerce + clamp params against the schema; unknown keys dropped, missing -> defaults."""
    spec = TEMPLATES[template]["params"]
    out = {}
    for name, (typ, lo, hi, default) in spec.items():
        raw = params.get(name, default)
        if isinstance(typ, list):                       # enum
            out[name] = raw if raw in typ else default
        elif typ == "int":
            try:
                out[name] = int(min(max(int(float(raw)), lo), hi))
            except Exception:
                out[name] = default
        else:                                           # float
            try:
                out[name] = float(min(max(float(raw), lo), hi))
            except Exception:
                out[name] = default
    return out


def _log_gap(theme: str) -> None:
    """Record a hypothesis theme that matched NO template -> the data-driven backlog of templates to add
    (the compounding 'when no template fits, write one' loop starts from this list)."""
    try:
        g = json.loads(_GAPS.read_text(encoding="utf-8")) if _GAPS.exists() else []
        g.append({"theme": theme[:200], "ts": time.time()})
        _GAPS.write_text(json.dumps(g[-300:], ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    try:
        _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def run_method(template: str, params: dict, claim: str = "", requester: str = "") -> dict:
    """Validate params, render the vetted template, execute in the Lab, ledger the result."""
    if template not in TEMPLATES:
        return {"status": "unknown_template", "available": list(TEMPLATES)}
    clean = _validate(template, params or {})
    code = TEMPLATES[template]["code"].format(**clean)
    from agora.execution.lab import run_experiment
    rec = run_experiment(f"method:{template} {claim[:40]}", code)
    out = rec.get("output", "")
    measured = next((l for l in out.splitlines() if l.startswith("MEASURED:")), "")
    verdict = next((l for l in out.splitlines() if l.startswith("VERDICT:")), "")
    entry = {"template": template, "params": clean, "claim": claim[:200],
             "requester": requester[:40], "lab_id": rec.get("id", ""),
             "ok": rec.get("ok", False), "measured": measured[:300], "verdict": verdict[:300],
             "ts": time.time()}
    items = _load()
    items.append(entry)
    # Cap 1000 (was 200): same rotation-race as .lab.json — the LAB-FIRST gate checks lab_id against
    # this ledger too, and a 200-entry window rotated out within ~a day at current run rates.
    _save(items[-1000:])
    return {"status": "ok", **entry}


def _norm_theme(t: str) -> str:
    return " ".join((t or "").lower().split())[:200]


# Board-gate helpers (see match_and_run). Same shape as the dungeon gatekeeper's: content words only, and
# a stop-list for the words the BOARD TEXT ITSELF uses to give instructions ("prioritize research that
# ...", "every finding must answer ..."). Without that stop-list the gate matches on the board's own
# boilerplate and passes everything — the exact bug measured on the quest-pool gate the same day.
_BOARD_STOP = frozenset("""priority priorities prioritize prioritise research finding findings theme themes
frontier
question questions standing owner deprioritize topic topics work make better every answer does that this
which their they there been more most only very also into from with must should when where what have
about test tests testing measure measured result results claim claims
""".split()) | frozenset("""
finance financial health longevity physics politics cloud trivia generic meta beds headline never
""".split())
# The second group is the board's NEGATIVE clauses ("Finance/health/physics are ONLY test-beds, never the
# headline", "Deprioritize generic meta-science, politics, cloud/trivia"). Naively tokenizing the board
# text turns those into PRIORITY words, so a finance or cloud theme would pass the gate on the strength of
# the sentence telling us to deprioritize it. Measured on the real board text before this fix.
#
# `frontier` sits in the FIRST group because it is how the board LABELS its priority, not a subject:
# the text opens "frontier: Make inspeximus the #1 agent-memory product". Both sides carry the word --
# task templates say "Frontier:" too -- so it matches a task against the board's own stationery.
# Measured on the live inbox 2026-07-31: of 33 pending tasks, ELEVEN were classified on-board solely by
# this word, every one of them Bayesian-network structure learning (bnlearn ALARM / HEPAR-II / ANDES,
# Erdos-Renyi DAGs, NOTEARS) -- a third of the queue, none of it on the memory frontier. Removing it
# costs nothing legitimate: the four tasks that carry `frontier` AND a real subject term stay on-board
# on that term, and `roadmap` and `quality` stay in because the board names both as real subjects
# ("the buyer-facing gap roadmap", "retrieval quality measured vs mem0/Zep/Cognee").


def _theme_tokens(t: str) -> set:
    import re as _re
    return {w for w in _re.findall(r"[a-z0-9]+", (t or "").lower()) if len(w) > 3}


#: A sentence carrying one of these is the board REFUSING something, and none of its words are a
#: priority. Matched against whole sentences rather than words on purpose: the word-list above had
#: to name every noun the owner might refuse, and it already missed one -- `science` was absent, so
#: "generic meta-science", a phrase lifted verbatim from the deprioritize clause, still passed the
#: gate on that token. Any hand-maintained list of forbidden nouns silently rots the next time the
#: owner re-words his priorities; the grammar of a refusal does not.
_REFUSAL = __import__("re").compile(
    r"deprioriti[sz]e|never the headline|not the headline|only\s+test[\s-]?bed|"
    r"off[\s-]?domain|do not |don't |avoid |exclude ", __import__("re").I)


def board_priority_terms(text: str) -> set:
    """The ON-PRIORITY words of a board, with its refusals removed.

    THE ONE DEFINITION. The brain's Lab door and the dungeon's quest gate both gate on this; they
    used to derive it separately and disagreed. Measured 2026-07-31 against the live board, the
    dungeon's copy admitted all five subjects the owner had explicitly deprioritized -- politics,
    generic meta-science, cloud trivia, finance and physics -- each matching on the very word he
    used to exclude it. `/brain/board` now publishes the result of this function as
    `priority_terms` so there is nothing left to re-derive.
    """
    keep = [s for s in __import__("re").split(r"(?<=[.!?])\s+", text or "") if not _REFUSAL.search(s)]
    return {w for w in _theme_tokens(" ".join(keep)) if w not in _BOARD_STOP}


def _match_cache_get(key: str):
    """Return a fresh cached match decision for this normalized theme, or None."""
    try:
        cache = json.loads(_MATCH_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return None
    e = cache.get(key)
    if e and (time.time() - e.get("ts", 0)) < _MATCH_TTL_S:
        return e.get("res")
    return None


def _match_cache_put(key: str, res: dict):
    """Persist a GENUINE matcher decision (a real template match, or a real 'no template') so the
    same theme doesn't re-pay the ~2k-token catalog LLM call within the TTL. Transient LLM/parse
    failures are NOT cached (caller only calls this on a genuine decision)."""
    try:
        cache = json.loads(_MATCH_CACHE.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    cache[key] = {"ts": time.time(), "res": res}
    now = time.time()
    cache = {k: v for k, v in cache.items() if now - v.get("ts", 0) < _MATCH_TTL_S}   # prune stale
    if len(cache) > 2000:
        cache = dict(sorted(cache.items(), key=lambda kv: kv[1].get("ts", 0))[-2000:])
    try:
        _MATCH_CACHE.write_text(json.dumps(cache), encoding="utf-8")
    except Exception:
        pass


async def match_and_run(theme: str, requester: str = "") -> dict:
    """Map a free-text hypothesis theme onto a template + params via the cheap LLM, then run it.
    Agents supply only the THEME; the LLM supplies only PARAMETERS — never code.
    AGORA_MATCH_CACHE (default ON; set =0 to disable): a recurring theme — or a recurring genuine
    'no template' decision — short-circuits the (static-catalog) LLM call, the dominant cost of this
    organ; matching LOGIC is unchanged (the LLM still decides on every cache MISS)."""
    import asyncio as _aio
    from agora.execution.llm_client import call_llm
    # BOARD GATE AT THE LAB DOOR (2026-07-20). The Lab is fed by SEVERAL organs — the dungeon quest pool,
    # the dungeon's hypothesis-induction (/brain/hypothesis-inputs), and the brain's scientist severe-test.
    # Gating any one of them leaves the others free, which is exactly what we measured: after gating the
    # quest pool, the next Lab runs were still amygdala-salience and heavy-tail-reward themes. This is the
    # ONE choke point every path goes through, so the board question ("does this advance inspeximus?") belongs
    # here. Soft + self-healing: an off-board theme is refused WITHOUT burning the LLM matcher or a Lab
    # slot, and is recorded in the gatekeeper ledger so the upstream generators stop re-seeding it.
    # Bypasses: no board priorities set, an explicit human/API requester, or AGORA_LAB_BOARD_GATE=0.
    if (os.getenv("AGORA_LAB_BOARD_GATE", "1") != "0"
            and not str(requester or "").lower().startswith(("claude", "api", "owner"))):
        try:
            from agora.execution.board import priorities_text
            _prio = board_priority_terms(priorities_text())
            if _prio and not (_theme_tokens(theme) & _prio):
                try:
                    from agora.execution.gatekeeper import record_skip
                    record_skip(theme[:120], "off-board: no overlap with the owner's standing priorities")
                except Exception:
                    pass
                return {"status": "off_board", "theme": theme[:120],
                        "reason": "no overlap with the board's standing priorities"}
        except Exception:
            pass                                   # never let the gate break the Lab
    use_cache = os.getenv("AGORA_MATCH_CACHE", "1") != "0"
    ckey = _norm_theme(theme)
    if use_cache:
        cached = _match_cache_get(ckey)
        if cached is not None:
            return {**cached, "cached": True}
    cat = "\n".join(f"- {c['name']}: {c['description'][:180]} | params: "
                    f"{', '.join(c['params'])}" for c in catalog())
    sysmsg = ("You map a research hypothesis to the experiment template that could TEST it. Each template "
              "description says 'Use for ANY claim of the form ...' - match by the underlying MECHANISM / "
              "claim-shape (e.g. streak->next-outcome, common-effect/collider, scale-free or heavy-tail "
              "distribution, tipping/cascade, selection/multiple-testing, crowd-vs-individual, "
              "critical-slowing-down, regression-to-mean), NOT the surface topic/domain. Pick the closest "
              "template whose mechanism would produce a measurement bearing on the hypothesis; reply 'none' "
              "ONLY if genuinely no template's mechanism applies. "
              'Reply ONLY JSON: {"template":"<name or none>","params":{...},"why":"<8 words>"}.')
    usr = f"Hypothesis theme: {theme[:300]}\n\nTemplates:\n{cat}"
    # MEDIUM tier (reasoning model): the matcher is a LOW-frequency judgment call (fires only
    # when a finding cluster forms), and the cheap tier (v4-flash) returns empty completions
    # under the dungeon's concurrent load (known gotcha). Temp 0.45 also keeps it above the
    # llm-cache threshold (0.4) so a one-off bad reply can't get cached and replayed.
    # 700-token budget: v4-pro returns EMPTY at small caps (burns budget thinking aloud);
    # the regex extracts the JSON from any preamble.
    raw = (await _aio.to_thread(call_llm, sysmsg, usr, "medium", 0.45, 700)) or ""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {"status": "no_match", "raw": raw[:160]}   # transient empty completion -> do NOT cache
    try:
        d = json.loads(m.group(0))
    except Exception:
        return {"status": "no_match"}                     # parse failure -> do NOT cache
    tpl = (d.get("template") or "").strip()
    if tpl not in TEMPLATES:
        _log_gap(theme)
        out = {"status": "no_match", "why": d.get("why", "")}
        if use_cache:
            _match_cache_put(ckey, out)                   # genuine 'no template' decision -> cache
        return out
    res = await _aio.to_thread(run_method, tpl, d.get("params") or {}, theme, requester)
    res["why"] = d.get("why", "")
    if use_cache:
        _match_cache_put(ckey, res)                       # genuine match -> cache
    return res


def format_methods(n: int = 8) -> str:
    items = _load()
    if not items:
        return "🧪 _The Methods Library is seeded but unused — no autonomous runs yet._"
    lines = [f"🧪 *The Methods Library* — {len(TEMPLATES)} templates · {len(items)} autonomous runs"]
    for e in items[-n:][::-1]:
        lines.append(f"• [{e['template']}] {e.get('claim', '')[:56]}")
        if e.get("measured"):
            lines.append(f"    {e['measured'][:90]}")
    return "\n".join(lines)
