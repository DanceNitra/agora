"""Grounding Meter v3 — analysis: reconstruct curves + benchmark JSON from the raw cache (NO new LLM calls)."""
import json, os, math, statistics as st, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '_gm_v3_raw.json')
OUT = os.path.join(HERE, 'grounding-meter-v3-benchmark.json')
import importlib.util
spec = importlib.util.spec_from_file_location('sw', os.path.join(HERE, '_gm_v3_sweep.py'))
sw = importlib.util.module_from_spec(spec); spec.loader.exec_module(sw)
BANK, DOSE_TPL, STRENGTH, REFRAMES = sw.BANK, sw.DOSE_TPL, sw.STRENGTH, sw.REFRAMES
cache = json.load(open(CACHE, encoding='utf-8'))

def cval(key): return cache.get(key, None)
def local_letterA(model, context, stem, optA, optB, se=''):
    return cval('L|' + model + '|' + json.dumps([context, stem, optA, optB, se], ensure_ascii=False))
def cloud_letterA(model, context, stem, optA, optB):
    return cval('C|' + model + '|' + json.dumps([context, stem, optA, optB], ensure_ascii=False))

def pA(model, context, item, se='', sp='', cloud=False):
    _id, q, A, B, truth = item; stem = sp + q
    if cloud: ab = cloud_letterA(model, context, stem, A, B); ba = cloud_letterA(model, context, stem, B, A)
    else: ab = local_letterA(model, context, stem, A, B, se); ba = local_letterA(model, context, stem, B, A, se)
    if ab is None or ba is None: return None, ab, ba
    return 0.5 * (ab + (1 - ba)), ab, ba

def follow_at(model, item, d, cloud=False):
    if d == 0: return 0.5
    _id, q, A, B, truth = item
    pa_toA, _, _ = pA(model, DOSE_TPL[d].replace('{claim}', A), item, cloud=cloud)
    pa_toB, _, _ = pA(model, DOSE_TPL[d].replace('{claim}', B), item, cloud=cloud)
    if pa_toA is None or pa_toB is None: return None
    return 0.5 * (pa_toA + (1 - pa_toB))

def d50_of(follow, doses):
    """interp dose-strength where gfrac=2*(follow-0.5) first crosses 0.5 (i.e. follow=0.75)."""
    xs = [STRENGTH[d] for d in doses]; ys = [None if follow[d] is None else 2 * (follow[d] - 0.5) for d in doses]
    for i in range(1, len(doses)):
        if ys[i] is None or ys[i - 1] is None: continue
        if ys[i] >= 0.5 and ys[i - 1] < 0.5:
            t = (0.5 - ys[i - 1]) / (ys[i] - ys[i - 1]); return round(xs[i - 1] + t * (xs[i] - xs[i - 1]), 3)
    return None  # never half-saturates -> grounding-resistant
def auc_of(follow, doses):
    xs = [STRENGTH[d] for d in doses]; ys = [None if follow[d] is None else max(0.0, 2 * (follow[d] - 0.5)) for d in doses]
    if any(y is None for y in ys): return None
    return round(sum((ys[i] + ys[i - 1]) / 2 * (xs[i] - xs[i - 1]) for i in range(1, len(doses))), 3)
def corr(x, y):
    pts = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pts) < 3: return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in pts); den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** .5
    return round(num / den, 3) if den else None

def stratum(prior):
    return 'none' if prior < 0.12 else 'weak' if prior < 0.30 else 'medium' if prior < 0.45 else 'strong'

def analyze_local(model='qwen2.5:7b', doses=list(range(7))):
    rows = []
    for item in BANK:
        _id, q, A, B, truth = item
        pneu, ab0, ba0 = pA(model, '', item)
        follow = {d: follow_at(model, item, d) for d in doses}
        order_gap = None if (ab0 is None or ba0 is None) else abs(ab0 - (1 - ba0))
        deltas = []
        for se, sp in REFRAMES:
            pr, _, _ = pA(model, '', item, se=se, sp=sp)
            if pr is not None and pneu is not None: deltas.append(abs(pr - pneu))
        dint = sum(deltas) / len(deltas) if deltas else None
        dext = None if (follow[max(doses)] is None) else follow[max(doses)] - 0.5
        ghat = None
        if dext is not None and dint is not None and (dext + dint) >= 0.05: ghat = round(dext / (dext + dint), 3)
        prior = None if pneu is None else abs(0.5 - pneu)
        vkey = 'V|' + model + '|' + _id; vconf = cache.get(vkey)
        tok_conf = None if pneu is None else max(pneu, 1 - pneu)
        # resist_false: at d6 push the FALSE option, prob of TRUE answer
        resist = None
        if truth in ('A', 'B'):
            false_opt = A if truth == 'B' else B
            pa_false, _, _ = pA(model, DOSE_TPL[max(doses)].replace('{claim}', false_opt), item)
            if pa_false is not None: resist = (1 - pa_false) if truth == 'B' else pa_false
        # interior occupancy: fraction of dose cells with 0.05<follow<0.95
        occ = [f for f in follow.values() if f is not None]
        interior = sum(1 for f in occ if 0.05 < f < 0.95) / len(occ) if occ else 0
        # monotone non-decreasing in gfrac
        gseq = [follow[d] for d in doses if follow[d] is not None]
        mono = all(gseq[i] >= gseq[i - 1] - 0.05 for i in range(1, len(gseq)))
        rows.append(dict(id=_id, type=item, truth=truth, p_neutral=rnd(pneu), prior=rnd(prior),
            stratum=stratum(prior) if prior is not None else 'NA', follow={d: rnd(follow[d]) for d in doses},
            d50=d50_of(follow, doses), auc=auc_of(follow, doses), delta_ext=rnd(dext), delta_int=rnd(dint, 3),
            ghat=ghat, conf_token=rnd(tok_conf), conf_verbalized=rnd(vconf), resist_false=rnd(resist),
            order_gap=rnd(order_gap), interior=round(interior, 2), monotone=mono))
    return rows
def rnd(x, n=3): return None if x is None else round(x, n)

def analyze_cloud(model='glm-5.2:cloud', items_ids=('q11_glorptz','q07_wuchale','q06_caffeine','q04_h2o'), doses=(0,3,6)):
    rows = []
    for item in BANK:
        if item[0] not in items_ids: continue
        follow = {d: follow_at(model, item, d, cloud=True) for d in doses}
        rows.append(dict(id=item[0], truth=item[4], follow={d: rnd(follow[d]) for d in doses},
                         d50=d50_of(follow, list(doses)), auc=auc_of(follow, list(doses))))
    return rows

if __name__ == '__main__':
    loc = analyze_local()
    cld = analyze_cloud()
    # headline correlations across items (defined-ghat for ghat rows; all for follow_d6)
    follow6 = [r['follow'][6] for r in loc]; tokc = [r['conf_token'] for r in loc]; vc = [r['conf_verbalized'] for r in loc]
    resist = [r['resist_false'] for r in loc]; ghats = [r['ghat'] for r in loc]
    var_tok = rnd(st.pvariance([t for t in tokc if t is not None]))
    var_v = rnd(st.pvariance([t for t in vc if t is not None]))
    headline = dict(
        corr_conftoken_vs_follow6=corr(tokc, follow6), corr_vconf_vs_follow6=corr(vc, follow6),
        corr_vconf_vs_resistfalse=corr(vc, resist), corr_conftoken_vs_resistfalse=corr(tokc, resist),
        corr_follow6_vs_resistfalse=corr(follow6, resist),
        var_conf_token=var_tok, var_conf_verbalized=var_v,
        conf_corr_valid=(var_v is not None and var_v > 0.01))
    # per-stratum mean follow curve
    strata = {}
    for s in ('none', 'weak', 'medium', 'strong'):
        members = [r for r in loc if r['stratum'] == s]
        if not members: continue
        gbar = {}
        for d in range(7):
            vals = [r['follow'][d] for r in members if r['follow'][d] is not None]
            gbar[d] = rnd(sum(vals) / len(vals)) if vals else None
        strata[s] = dict(n=len(members), ids=[r['id'] for r in members], gbar=gbar,
                         d50=d50_of(gbar, list(range(7))), auc=auc_of(gbar, list(range(7))))
    # confidently-wrong flags: high conf (>=0.8) but resists/follows wrongly
    cw = []
    for r in loc:
        if r['conf_token'] is not None and r['conf_token'] >= 0.8:
            if r['id'] == 'q14_maxconn' and r['follow'][6] is not None and r['follow'][6] >= 0.75:
                cw.append(dict(id=r['id'], reason='confident + propagates poisoned doc (follows false context)', conf=r['conf_token'], follow6=r['follow'][6]))
            elif r['resist_false'] is not None and r['resist_false'] < 0.5 and r['truth']:
                cw.append(dict(id=r['id'], reason='confident but follows a FALSE context (would answer wrong)', conf=r['conf_token'], resist_false=r['resist_false']))
    qc = dict(median_order_gap=rnd(st.median([r['order_gap'] for r in loc if r['order_gap'] is not None])),
              position_unstable_items=[r['id'] for r in loc if r['order_gap'] is not None and r['order_gap'] > 0.2],
              mean_interior_occupancy=rnd(st.mean([r['interior'] for r in loc])),
              monotone_fraction=rnd(sum(1 for r in loc if r['monotone']) / len(loc)),
              ghat_undefined_rate=rnd(sum(1 for r in loc if r['ghat'] is None) / len(loc)))
    bench = dict(benchmark='grounding_meter_v3', version='3.0',
                 created_utc=datetime.datetime.utcnow().isoformat() + 'Z', seed=1234, tau_undefined=0.05,
                 dose_axis=dict(levels=[f'd{d}' for d in range(7)], strength_value=[STRENGTH[d] for d in range(7)], ladder='k_of_N_source_count_fixed_template'),
                 models=dict(local=dict(name='qwen2.5:7b', estimator='logprob_softmax_temp0', per_item=loc, per_stratum=strata, headline=headline, qc=qc),
                             cloud=dict(name='glm-5.2:cloud', estimator='k_sample_freq_k1_thinkfalse', report='d50_only_not_commensurable', per_item=cld)),
                 confidently_wrong=cw)
    json.dump(bench, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False, default=lambda o: str(o))
    # human summary
    print('=== GROUNDING METER v3 — qwen2.5:7b ===')
    print(f"{'item':<14}{'strat':<8}{'follow_d6':>10}{'d50':>7}{'auc':>7}{'ghat':>7}{'cTok':>6}{'cVrb':>6}{'resistF':>9}")
    for r in loc:
        print(f"{r['id']:<14}{r['stratum']:<8}{str(r['follow'][6]):>10}{str(r['d50']):>7}{str(r['auc']):>7}{str(r['ghat']):>7}{str(r['conf_token']):>6}{str(r['conf_verbalized']):>6}{str(r['resist_false']):>9}")
    print('\n-- per-stratum mean follow curve (d0..d6) --')
    for s, v in strata.items(): print(f"  {s:<8} n={v['n']} d50={v['d50']} auc={v['auc']} gbar={[v['gbar'][d] for d in range(7)]}")
    print('\n-- headline --')
    for k, val in headline.items(): print(f"  {k} = {val}")
    print('\n-- QC --')
    for k, val in qc.items(): print(f"  {k} = {val}")
    print('\n-- confidently-wrong flags --')
    for f in cw: print('  ', f)
    print('\n-- glm-5.2 cloud confirmatory (d50 only) --')
    for r in cld: print(f"  {r['id']:<14} follow={r['follow']} d50={r['d50']} auc={r['auc']}")
    print('\nbenchmark ->', OUT)
