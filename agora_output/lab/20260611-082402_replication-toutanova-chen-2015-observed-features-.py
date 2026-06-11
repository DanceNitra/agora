import numpy as np
rng = np.random.default_rng(53)

# Replicate Toutanova-Chen (2015): a simple OBSERVED-features model matches/beats LATENT-feature
# (embedding) models on knowledge-base completion. Build a synthetic KB with planted COMPOSITIONAL
# structure (r3 tends to hold when an r1->r2 path exists), then compare link-prediction AUC of:
#   (A) observed model: features = [direct edge, 2-hop path count, degree product]  (logistic-ish)
#   (B) latent model:   low-rank SVD reconstruction of the relation-aggregated adjacency
N, R = 200, 6
def build():
    A = np.zeros((R, N, N))
    for r in range(R-1):
        idx = rng.random((N, N)) < 0.02
        A[r] = idx.astype(float)
    # compositional: r_last holds where an r0->r1 path exists (plus noise)
    comp = (A[0] @ A[1] > 0).astype(float)
    A[R-1] = ((comp + (rng.random((N, N)) < 0.01)) > 0).astype(float)
    np.fill_diagonal(A.sum(0), 0)
    return A

def auc(scores, labels):
    order = np.argsort(-scores)
    lab = labels[order]
    pos = lab.sum(); neg = len(lab) - pos
    if pos == 0 or neg == 0: return 0.5
    tp = np.cumsum(lab); fp = np.cumsum(1 - lab)
    return np.trapz(tp / pos, fp / neg)

def evaluate():
    A = build()
    r = R - 1                                   # predict the compositional relation
    pos = np.argwhere(A[r] > 0)
    neg = np.argwhere(A[r] == 0)
    neg = neg[rng.choice(len(neg), len(pos), replace=False)]
    pairs = np.vstack([pos, neg]); labels = np.r_[np.ones(len(pos)), np.zeros(len(pos))]
    # hold out half the positives from the graph the models see
    seen = A.copy(); hide = pos[rng.random(len(pos)) < 0.5]
    seen[r][hide[:,0], hide[:,1]] = 0
    deg = seen.sum(0).sum(1)
    path2 = seen[0] @ seen[1]                    # OBSERVED 2-hop path counts (the key feature)
    # (A) observed: weighted sum of [2-hop path, direct any-rel edge, degree product] (fixed weights)
    anyedge = (seen.sum(0) > 0).astype(float)
    obs = np.array([2.0*path2[i,j] + 0.5*anyedge[i,j] + 0.001*deg[i]*deg[j] for i,j in pairs])
    # (B) latent: low-rank SVD of the aggregate adjacency, score by reconstruction
    M = seen.sum(0)
    U,S,Vt = np.linalg.svd(M, full_matrices=False)
    k = 20; rec = (U[:,:k]*S[:k]) @ Vt[:k]
    lat = np.array([rec[i,j] for i,j in pairs])
    return auc(obs, labels), auc(lat, labels)

obs_aucs, lat_aucs = zip(*[evaluate() for _ in range(20)])
print("Toutanova-Chen (2015): observed-features vs latent-features for KB completion")
print(f"(synthetic KB, N={N}, {R} relations, compositional target, 20 trials)\n")
print(f"  OBSERVED-features model AUC: {np.mean(obs_aucs):.3f} +/- {np.std(obs_aucs):.3f}")
print(f"  LATENT (SVD) model      AUC: {np.mean(lat_aucs):.3f} +/- {np.std(lat_aucs):.3f}")
d = np.mean(obs_aucs) - np.mean(lat_aucs)
print(f"  difference (obs - lat): {d:+.3f}")
print("\nReading: if the observed-features AUC MATCHES or EXCEEDS the latent model, the claim")
print("reproduces - simple path/degree features rival embeddings on compositional KB completion.")
