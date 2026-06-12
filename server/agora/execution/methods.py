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
import re
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".methods.json"

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
}


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
    _save(items[-200:])
    return {"status": "ok", **entry}


async def match_and_run(theme: str, requester: str = "") -> dict:
    """Map a free-text hypothesis theme onto a template + params via the cheap LLM, then run it.
    Agents supply only the THEME; the LLM supplies only PARAMETERS — never code."""
    import asyncio as _aio
    from agora.execution.llm_client import call_llm
    cat = "\n".join(f"- {c['name']}: {c['description'][:180]} | params: "
                    f"{', '.join(c['params'])}" for c in catalog())
    sysmsg = ("You match research hypotheses to experiment templates. Reply ONLY JSON: "
              '{"template":"<name or none>","params":{...},"why":"<8 words>"} . '
              "Pick 'none' unless the hypothesis GENUINELY fits a template's mechanism.")
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
        return {"status": "no_match", "raw": raw[:160]}
    try:
        d = json.loads(m.group(0))
    except Exception:
        return {"status": "no_match"}
    tpl = (d.get("template") or "").strip()
    if tpl not in TEMPLATES:
        return {"status": "no_match", "why": d.get("why", "")}
    res = await _aio.to_thread(run_method, tpl, d.get("params") or {}, theme, requester)
    res["why"] = d.get("why", "")
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
