"""
Insight backbone for Lee & Spekkens (2015): causal discovery via algebraic feasibility uses the
INEQUALITY constraints a structure implies, which conditional-independence (CI) testing discards.

Cleanest witness = the instrumental-variable model  Z -> X -> Y  with a latent confounder U on
(X,Y), Z _||_ U. Among the observed variables {Z,X,Y} this structure implies NO conditional
independence at all (Z->X->Y makes Z,Y dependent; conditioning on the collider X keeps them
dependent via U). So a CI-based discovery method has *nothing to test* and can never reject the IV
model. Yet the model is refutable: Pearl's instrumental inequality bounds the reachable
distributions, and a distribution outside that semialgebraic set falsifies it.

We measure the falsifying power CI testing entirely lacks:
  (a) random valid IV models (response-function mixtures) should ALL satisfy the inequality;
  (b) among random faithful joint distributions P(X,Y|Z) (which CI testing passes unconditionally),
      what fraction does the instrumental inequality reject?
"""
import numpy as np

rng = np.random.default_rng(11)


def instrumental_ok(p0, p1, tol=1e-12):
    """p_z = [P(X=0,Y=0|z), P(0,1|z), P(1,0|z), P(1,1|z)] for z=0,1.
    Pearl instrumental inequality: for each x, sum_y max_z P(x,y|z) <= 1."""
    # index: (x,y) -> 0:(0,0) 1:(0,1) 2:(1,0) 3:(1,1)
    x0 = max(p0[0], p1[0]) + max(p0[1], p1[1])   # x=0: y=0 and y=1
    x1 = max(p0[2], p1[2]) + max(p0[3], p1[3])   # x=1
    return x0 <= 1 + tol and x1 <= 1 + tol


def rand_simplex(n):
    e = -np.log(rng.random(n))
    return e / e.sum()


# (a) valid IV models: U picks a pair (response of X to Z, response of Y to X); always reachable.
# X response types r in {const0, const1, identity(Z), not(Z)}; Y response types s wrt X likewise.
def x_of(r, z):  # 4 deterministic functions of z
    return [0, 1, z, 1 - z][r]
def y_of(s, x):
    return [0, 1, x, 1 - x][s]

valid_viol = 0
NV = 20000
for _ in range(NV):
    w = rand_simplex(16).reshape(4, 4)  # P(r,s)
    p0 = np.zeros(4); p1 = np.zeros(4)
    for r in range(4):
        for s in range(4):
            for z, p in ((0, p0), (1, p1)):
                x = x_of(r, z); y = y_of(s, x)
                p[2 * x + y] += w[r, s]
    if not instrumental_ok(p0, p1):
        valid_viol += 1

# (b) random faithful distributions: independent random P(X,Y|Z=0), P(X,Y|Z=1).
def has_no_ci(p0, p1, thr=0.03):
    """Reject near-CI cases so 'faithful' is honest: require Z–X, Z–Y, and X–Y all dependent."""
    P = np.vstack([0.5 * p0, 0.5 * p1])           # P(Z,X,Y), P(Z) uniform; rows z=0,1
    PZ = P.sum(1)                                  # [0.5,0.5]
    PX = np.array([P[:, [0, 1]].sum(), P[:, [2, 3]].sum()])    # X=0,1
    PY = np.array([P[:, [0, 2]].sum(), P[:, [1, 3]].sum()])    # Y=0,1
    # Z-X dependence
    PZX = np.array([[P[z, [0, 1]].sum(), P[z, [2, 3]].sum()] for z in range(2)])
    zx = np.abs(PZX - np.outer(PZ, PX)).max()
    PZY = np.array([[P[z, [0, 2]].sum(), P[z, [1, 3]].sum()] for z in range(2)])
    zy = np.abs(PZY - np.outer(PZ, PY)).max()
    PXY = np.array([[P[:, 2 * x + y].sum() for y in range(2)] for x in range(2)])
    xy = np.abs(PXY - np.outer(PX, PY)).max()
    return min(zx, zy, xy) > thr

N, faithful, rej = 200000, 0, 0
for _ in range(N):
    p0 = rand_simplex(4); p1 = rand_simplex(4)
    if not has_no_ci(p0, p1):
        continue
    faithful += 1
    if not instrumental_ok(p0, p1):
        rej += 1

print(f"(a) valid IV models violating the instrumental inequality: {valid_viol}/{NV} "
      f"({100*valid_viol/NV:.3f}%)  <- expect ~0")
print(f"(b) faithful random distributions (no CI to test): {faithful}/{N}")
print(f"    rejected by the instrumental INEQUALITY: {rej}/{faithful} "
      f"({100*rej/faithful:.1f}%)")
print(f"    CI testing rejects: 0/{faithful} (0.0%)  <- the IV model implies no CI among Z,X,Y")
print(f"\nInequality-only falsifying power on faithful data: {100*rej/faithful:.1f} percentage points "
      f"that CI testing is structurally blind to.")
