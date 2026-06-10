
import sys, json, time, glob, os
sys.path.insert(0, r'C:/Users/Danculus/agora/server')
import numpy as np

# (1) Flywheel-closure latency: time from question open -> deepened
fw = json.load(open(r'C:/Users/Danculus/agora/server/.flywheel.json', encoding='utf-8'))
now = time.time()
deepened = [q for q in fw if q.get('status')=='deepened' and q.get('deepened_ts')]
closure = [(q['deepened_ts']-q.get('ts',q['deepened_ts']))/86400 for q in deepened]
open_q = [q for q in fw if q.get('status')=='open']
open_age = [(now-q.get('ts',now))/86400 for q in open_q]
print('FLYWHEEL: %d open, %d deepened' % (len(open_q), len(deepened)))
if closure: print('  closure latency days: mean=%.2f n=%d' % (sum(closure)/len(closure), len(closure)))
if open_age: print('  open-question age days: mean=%.2f max=%.2f' % (sum(open_age)/len(open_age), max(open_age)))

# (2) Inter-artifact semantic-distance variance among Agora's own artifacts
meta = json.load(open(r'C:/Users/Danculus/agora/server/.semantic_cache/meta.json', encoding='utf-8'))
vecs = np.load(r'C:/Users/Danculus/agora/server/.semantic_cache/vectors.npy')
idx = [i for i,m in enumerate(meta) if 'Agora Agents' in m.get('path','') and
       any(m['path'].split('/')[-1].startswith(p) for p in ('insight','hypothesis','dialectic','dossier'))]
print('ARTIFACTS indexed:', len(idx))
if len(idx) >= 4:
    V = vecs[idx]
    sims = V @ V.T
    iu = np.triu_indices(len(idx), k=1)
    dists = 1.0 - sims[iu]
    print('  pairwise semantic distance: mean=%.4f var=%.5f std=%.4f n_pairs=%d' % (
        dists.mean(), dists.var(), dists.std(), len(dists)))
    print('BASELINE RECORDED %s: closure_mean_d=%.2f dist_var=%.5f' % (
        time.strftime('%Y-%m-%d'), (sum(closure)/len(closure) if closure else -1), dists.var()))
