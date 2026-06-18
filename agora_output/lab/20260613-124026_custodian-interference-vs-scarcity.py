
import numpy as np
rng = np.random.default_rng(7)
D=64; Q=200                      # 200 query topics, each with one TRUE target memory
targets = rng.standard_normal((Q,D)); targets/=np.linalg.norm(targets,axis=1,keepdims=True)
def precision_at1(store_vecs, store_is_target):
    # query = noisy version of each true target; retrieve nearest in store; hit if it's the target
    hits=0
    for qi in range(Q):
        q = targets[qi] + 0.35*rng.standard_normal(D); q/=np.linalg.norm(q)
        sims = store_vecs @ q
        j = int(np.argmax(sims))
        if store_is_target[j]==qi: hits+=1
    return hits/Q
rows=[]
for n_distract in [0,200,1000,3000,8000]:
    # distractors: many are NEAR-DUPLICATES of real targets (interference grows with volume)
    if n_distract>0:
        base = targets[rng.integers(0,Q,n_distract)]
        dist = base + 0.30*rng.standard_normal((n_distract,D)); dist/=np.linalg.norm(dist,axis=1,keepdims=True)
    else:
        dist = np.zeros((0,D))
    # KEEP-ALL: targets + all distractors (violates scarcity invariant)
    allv = np.vstack([targets,dist]); allt=np.array([i for i in range(Q)]+[-1]*n_distract)
    p_all = precision_at1(allv,allt)
    # GOVERNED: value-curate — prune near-duplicate low-value distractors (keep only the targets)
    p_gov = precision_at1(targets,np.arange(Q))
    rows.append((Q+n_distract,round(p_all,3),round(p_gov,3)))
print("store_size  keep_all_P@1  governed_P@1")
for s,a,g in rows: print(f"{s:>9}     {a:.3f}        {g:.3f}")
# verdict numbers
big = rows[-1]
print(f"\nAt {big[0]} items: keep_all={big[1]:.3f} vs governed={big[2]:.3f}  (gap {big[2]-big[1]:+.3f})")
print("governed precision is FLAT in store size:", all(abs(r[2]-rows[0][2])<0.02 for r in rows))
