"""Rule-parser-strength trust weight for a TEMPORAL metadata filter on LoCoMo — jacksonxly's time signal.

His point on time: "time is basically solved, don't use an LLM for it — a rule-based temporal expression
parser (SUTime/duckling) is the reliable signal." So for the TIME dimension the a-priori trust signal is
the RULE PARSER's resolution confidence: an unambiguous expression ("in July 2023") resolves to a clean
window and is trustworthy; a vague one ("recently", "last year" with no anchor) does not, so the filter
should back off there. This is the temporal analog of the alias-strength result (locomo_alias_strength_
weight.py) and, like it, tests through mnemo's SHIPPED soft `prefer` filter (recall(prefer=, prefer_trust=)).

Scope: the 243 answerable LoCoMo questions that CONTAIN a filterable temporal expression (15% of 1531;
the rest have no time constraint to filter on). A lightweight SUTime-lite regex parser resolves the
expression against the conversation's session dates to a target (year and/or month) with a confidence:
  month+year -> 1.0 ; year-only -> 0.7 ; month-only -> 0.6 ; vague relative / weekday -> 0.2 ; none -> 0.
Turns carry meta {year, month} from their session date (dia_id 'D<session>:<turn>').

Four arms, all via mnemo.recall(mode='hybrid'):
  no_filter    : recall(q)
  hard_where   : recall(q, where=<resolved window>)                 -- hard filter (deletes non-matching)
  soft_flat    : recall(q, prefer=<window>, prefer_trust=0.9)       -- always-trust the extraction (flat)
  soft_parser  : recall(q, prefer=<window>, prefer_trust=<parser_conf>)  -- weight by rule-parser strength

Metric: recall@20 overall (on these temporal-constraint Qs) + the HARM subset (the gold evidence turn is
NOT in the resolved window -- i.e. the time filter is misleading, e.g. an event discussed in a later
session). Reuses the warm cache.

FINDING (measured + method-audited 2026-07-02): soft filter with a rule-parser-resolved window is the
BEST arm (recall@20 0.751 vs 0.497 no-filter, +0.254) and soft >> hard on the harm subset (0.45 vs the
hard filter's 0.02, which deletes the answer) -- so jacksonxly's "use a rule parser for time; don't hard-
delete" holds strongly. BUT weighting by parser confidence TIES flat (0.747 vs 0.751, delta 0.004, n=250),
and the reason is NOT "the parser is uniformly reliable" -- it's COLLINEARITY: a vague expression resolves
to NO window (window_of -> None) so both soft arms fall back to no-filter identically on those 48 cases;
the confidence weight only ever acts on the already-high-confidence resolved windows (conf in {0.6,0.7,1.0}).
Window-PRESENCE already is the gate, so a separate confidence weight has nothing to add here. (Contrast the
entity/alias-strength probe, where reliability genuinely varied exact-vs-guess and weighting helped +0.084.)
This probe does NOT model a "resolved-but-uncertain" middle (a fuzzy low-confidence time window); testing
that would need mapping vague expressions to fuzzy windows. The residual harm (event dated in one session
but discussed in another) is orthogonal to extraction quality -- a different problem.
Run: LOCOMO_PATH=agora_output/lab/data/locomo10.json \
     LOCOMO_CACHE=agora_output/lab/data/locomo_confweighted_cache.json \
     python research/probes/locomo_temporal_parser_weight.py
"""
import json, re, ast, time, hashlib, os, urllib.request, collections, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus

DATA = os.environ.get("LOCOMO_PATH", "agora_output/lab/data/locomo10.json")
CACHE = os.environ.get("LOCOMO_CACHE", "agora_output/lab/data/locomo_confweighted_cache.json")
EMB_URL = "http://localhost:11434/api/embed"; K = 20; ANS = ("1", "2", "3", "4")
_t0 = time.time()
_cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
def _key(t): return hashlib.sha1(t[:2000].encode("utf-8")).hexdigest()
def _post(p):
    r = urllib.request.urlopen(urllib.request.Request(
        EMB_URL, data=json.dumps(p).encode(), headers={"Content-Type": "application/json"}), timeout=120)
    return json.loads(r.read())["embeddings"]
def warmup(texts, batch=128, flush_every=10):
    miss, seen = [], set()
    for t in texts:
        k = _key(t)
        if k not in _cache and k not in seen: seen.add(k); miss.append(t)
    if not miss: print("warmup: all cached", flush=True); return
    print(f"warmup: {len(miss)} uncached", flush=True); nb = (len(miss)+batch-1)//batch
    for bi, i in enumerate(range(0, len(miss), batch)):
        ch = miss[i:i+batch]
        for c, v in zip(ch, _post({"model": "nomic-embed-text", "input": [c[:2000] for c in ch]})): _cache[_key(c)] = v
        if (bi+1) % flush_every == 0 or (bi+1) == nb: json.dump(_cache, open(CACHE, "w"))
def embed(t):
    v = _cache.get(_key(t))
    if v is None: v = _post({"model": "nomic-embed-text", "input": [t[:2000]]})[0]; _cache[_key(t)] = v
    return v
def gold_of(q, tset):
    e = q.get("evidence")
    try: ids = ast.literal_eval(e) if isinstance(e, str) else e
    except Exception: ids = []
    return [i for i in (ids or []) if i in tset]

MONTHS = {m: i+1 for i, m in enumerate(
    ["january","february","march","april","may","june","july","august","september","october","november","december"])}
MONW = "(" + "|".join(MONTHS) + ")"
RE_MY = re.compile(MONW + r"[,\s]+(\d{4})", re.I)          # "July 2023"
RE_YM = re.compile(r"(\d{4})[,\s]+" + MONW, re.I)
RE_MONTH = re.compile(r"\b" + MONW + r"\b", re.I)
RE_YEAR = re.compile(r"\b(20\d{2})\b")
RE_VAGUE = re.compile(r"\b(recently|latest|last|next|this|past|previous|ago|yesterday|today|tomorrow|"
                      r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)

def rule_parse(qtext):
    """SUTime-lite: resolve a temporal expression -> (year|None, month|None, confidence)."""
    m = RE_MY.search(qtext) or RE_YM.search(qtext)
    if m:
        g = m.groups()
        mon = next((MONTHS[x.lower()] for x in g if x and x.lower() in MONTHS), None)
        yr = next((int(x) for x in g if x and x.isdigit()), None)
        return (yr, mon, 1.0)
    y = RE_YEAR.search(qtext); mo = RE_MONTH.search(qtext)
    if y and mo: return (int(y.group(1)), MONTHS[mo.group(1).lower()], 1.0)
    if mo:  return (None, MONTHS[mo.group(1).lower()], 0.6)   # month, year unknown
    if y:   return (int(y.group(1)), None, 0.7)               # year only
    if RE_VAGUE.search(qtext): return (None, None, 0.2)       # vague relative -> low trust
    return (None, None, 0.0)

def parse_session_date(s):
    mo = RE_MONTH.search(s or ""); yr = RE_YEAR.search(s or "")
    return (int(yr.group(1)) if yr else None, MONTHS[mo.group(1).lower()] if mo else None)

def window_of(yr, mon):
    w = {}
    if yr is not None: w["year"] = yr
    if mon is not None: w["month"] = mon
    return w or None

D = json.load(open(DATA)); _all = []
for d0 in D:
    conv = d0["conversation"]; tset = set()
    for sk in [k for k in conv if re.fullmatch(r"session_\d+", k)]:
        for t in conv[sk]: _all.append(t["text"]); tset.add(t["dia_id"])
    for q in d0["qa"]:
        if str(q.get("category")) in ANS and gold_of(q, tset): _all.append(q["question"])
warmup(_all)

METHODS = ("no_filter", "hard_where", "soft_flat", "soft_parser")
per_q = {m: [] for m in METHODS}; harm = {m: [] for m in METHODS}
n_tempo = conf_hist = 0; conf_counts = collections.Counter(); wrongwin = 0; t0 = time.time()
for ci, d0 in enumerate(D):
    conv = d0["conversation"]
    sess_date = {}   # session number -> (year, month)
    for k in conv:
        mm = re.fullmatch(r"session_(\d+)_date_time", k)
        if mm: sess_date[int(mm.group(1))] = parse_session_date(conv[k])
    turns = []
    for sk in sorted([k for k in conv if re.fullmatch(r"session_\d+", k)], key=lambda s: int(s.split("_")[1])):
        snum = int(sk.split("_")[1]); yr, mon = sess_date.get(snum, (None, None))
        for t in conv[sk]: turns.append((t["dia_id"], t["text"], yr, mon))
    m = Inspeximus(embed=embed); m.semantic_threshold = 1; dia2id = {}
    for dia, txt, yr, mon in turns:
        dia2id[dia] = m.remember(txt, meta={"year": yr, "month": mon, "dia": dia})
    id2dia = {v: k for k, v in dia2id.items()}; turnset = set(dia2id)
    def dia_year_month(dia):
        rid = dia2id.get(dia); r = next((x for x in m.items if x["id"] == rid), None)
        return (r["meta"]["year"], r["meta"]["month"]) if r else (None, None)
    base_val = {r["id"]: (r["value"], r["last_access"]) for r in m.items}
    def restore():
        for r in m.items: r["value"], r["last_access"] = base_val[r["id"]]
    def rec(qtext, **kw):
        restore(); return set(id2dia[h["id"]] for h in m.recall(qtext, k=K, mode="hybrid", **kw) if h["id"] in id2dia)
    qs = [q for q in d0["qa"] if str(q.get("category")) in ANS and gold_of(q, turnset)]
    for q in qs:
        yr, mon, conf = rule_parse(q["question"])
        win = window_of(yr, mon)
        if win is None and conf == 0.0:      # no temporal expression at all -> out of scope for this probe
            continue
        n_tempo += 1; conf_counts[conf] += 1
        g = set(gold_of(q, turnset)); ng = len(g)
        # is the gold evidence actually inside the resolved window? (if not, the filter is misleading = harm)
        gold_in_win = win is not None and all(
            (win.get("year") in (None, dia_year_month(gi)[0])) and (win.get("month") in (None, dia_year_month(gi)[1]))
            for gi in g)
        wrong = win is not None and not gold_in_win
        wrongwin += wrong
        nf = rec(q["question"])
        hw = rec(q["question"], where=win) if win else nf
        sf = rec(q["question"], prefer=win, prefer_trust=0.9) if win else nf
        sp = rec(q["question"], prefer=win, prefer_trust=conf) if win else nf
        vals = {"no_filter": len(g & nf)/ng, "hard_where": len(g & hw)/ng,
                "soft_flat": len(g & sf)/ng, "soft_parser": len(g & sp)/ng}
        for mm in METHODS: per_q[mm].append(vals[mm])
        if wrong:
            for mm in METHODS: harm[mm].append(vals[mm])
    print(f"  conv {ci}: {len(qs)} Q ({t0 and time.time()-t0:.0f}s)", flush=True)
json.dump(_cache, open(CACHE, "w"))

def mean(x): return sum(x)/len(x) if x else float("nan")
def boot(dl, it=10000, seed=17):
    r = random.Random(seed); n = len(dl); s = [mean([dl[r.randrange(n)] for _ in range(n)]) for _ in range(it)]
    s.sort(); return s[int(.025*it)], s[int(.975*it)]
base = per_q["no_filter"]
print(f"\n=== LoCoMo temporal rule-parser trust weight (recall@{K}, temporal-constraint Qs n={n_tempo}) ===")
print(f"parser confidence dist: {dict(conf_counts)} | gold-outside-resolved-window (harm) n={wrongwin}")
print(f"\n{'method':<13}{'recall@20':>10}{'delta':>9}")
for mm in METHODS:
    r = mean(per_q[mm])
    if mm == "no_filter": print(f"{mm:<13}{r:>10.3f}{'--':>9}")
    else:
        dl = [per_q[mm][i]-base[i] for i in range(len(base))]; lo, hi = boot(dl)
        print(f"{mm:<13}{r:>10.3f}{mean(dl):>+9.3f}   CI[{lo:+.3f},{hi:+.3f}]")
print(f"\nHARM SUBSET recall@{K} (gold turn outside the resolved window; baseline=no_filter):")
for mm in METHODS: print(f"  {mm:<13}{mean(harm[mm]):.3f}  n={len(harm[mm])}")
out = {"k": K, "n_temporal_q": n_tempo, "harm_n": wrongwin, "parser_conf_dist": {str(k): v for k, v in conf_counts.items()},
       "recall@20": {mm: round(mean(per_q[mm]), 4) for mm in METHODS},
       "harm_subset": {mm: {"mean": round(mean(harm[mm]), 4) if harm[mm] else None, "n": len(harm[mm])} for mm in METHODS}}
json.dump(out, open("research/probes/locomo_temporal_parser_weight_result.json", "w"), indent=1)
print("\nsaved: research/probes/locomo_temporal_parser_weight_result.json")
