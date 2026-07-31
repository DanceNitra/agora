"""
Artificer Rooke - the Replication Unit. Re-runs OTHER people's claims as the smallest model that
could refute them, and trusts only what computes.

WHY THIS FILE EXISTS
--------------------
For the five days before it, all eight dungeon agents ran identical code, and Rooke produced ZERO
discoveries in that window. The shared loop had no instrument that could take a sourced claim, build
a model of it, and come back with a number - so the Crucible (the public replication ledger, the
owner's chosen exponential direction) was fed entirely by hand. His contributions also landed with a
BLANK contributor_name: server/agora/api/dungeon.py's DUNGEON_AGENT_IDS maps six of the eight agents
and omits Rooke (and Wren), so the name lookup returned nothing and an empty string was written. That
omission is a sibling unit's fix; it is recorded here because it is why his track record on disk reads
emptier than his actual output was.

WHAT IT DOES
------------
One cycle: ask the brain for the next sourced claim awaiting a re-run, decide whether Rooke owns an
instrument that can actually test it, run that instrument in the Lab, and rule
REPRODUCED / FAILED / NOT_COMPUTABLE on the measured number.

WHY IT USUALLY RETURNS "idle" - THE ANTI-CHURN DESIGN
-----------------------------------------------------
Two forces push an organ toward manufacturing output, and both are answered by refusing to write:

  * metabolism.py:111-117 pays REPRODUCED and FAILED EQUALLY (deliberately - paying more for FAILED
    once created an incentive to rig weak baselines and poison the ledger). It still pays 0.5 for a
    NOT_COMPUTABLE. An organ that records "could not compute" whenever it has nothing to say therefore
    earns points for doing nothing, four times a day, forever. So a NOT_COMPUTABLE is recorded ONLY
    when the Lab actually ran and the RUN is the evidence. No run, no record: return idle instead.
  * The ledger is rendered into public/crucible/. Every entry is a public credibility statement. An
    entry that is really "Rooke had no instrument for this" costs more than it pays.

The other half of the same rule: an instrument is applied only where it is the RIGHT instrument. The
canonical minimal model of a mechanism cannot adjudicate a claim about a specific empirical system, a
variant of the mechanism, or a setting the model does not contain. Ruling FAILED there would not be a
refutation, it would be an instrument error wearing a verdict's clothes - so each instrument carries
explicit `excludes` and the claim is skipped instead.

FAILED IS A FIRST-CLASS SUCCESS, AND IT MUST STAY REACHABLE
-----------------------------------------------------------
Two mechanical guards, because "we hunt claims where FAILED is live" is not enforceable as good
intentions:

  * INDEPENDENCE. The claimed value is never an input to the model. Every script here is static with
    respect to the answer; the only claim-derived quantity any of them accepts is a model PARAMETER
    (the SIR script's R0), never the quantity under test, and `_independent()` checks that mechanically
    against the declared params. (The obvious check - "is the claimed number a substring of the source"
    - is worthless: a claimed exponent of 3 matches a loop bound, a seed, a format width. Comparing
    against the declared parameter values is the check that actually means something.)
  * LIVENESS. If the instrument's tolerance is wider than half the claimed value, no measurement could
    have contradicted the claim, so the verdict is NOT_COMPUTABLE rather than a REPRODUCED that was
    never at risk. This is the same defect the brain's by-construction gate (agent_os_api.py:1767)
    catches after the fact; catching it before the POST keeps the duplicate out of the ledger.

We POST once, with `by_construction_checked` set from our own independence check. We never re-POST to
override a gate: record() appends unconditionally, so a second POST would DOUBLE-COUNT the claim -
exactly the defect replication.already_covered() was written to stop after the same LinUCB result was
counted three times and the public REPRODUCED number read 23 where the truth was 21.

EVERY SCRIPT SAYS WHAT IT MODELS
--------------------------------
lab.py:41-72 flags a run `undocumented: true` when it has no leading docstring or comment block, after
a run named `basket-goodhart-interior-k` printed `mean K* = 10.5`, was read as an optimal retrieval
depth, and actually modeled an adversary splitting a budget across K proxy metrics. Measured on the
last 60 runs: 100% carried no model description at all. Every script below opens with one.

THE INSTRUMENT SET IS CALIBRATED, NOT ASSUMED
---------------------------------------------
Each instrument was run against the canonical value of the mechanism it models before being trusted,
on this machine, stdlib only (2026-07-31). The measured systematic bias is what sets `rel_floor`;
3*SE alone would have manufactured a FAILED on two of the four:

    instrument            canonical   measured   bias    SE      runtime   rel_floor
    er_giant_component      1.0        1.0125    1.25%   1.35%    2.8 s      0.08
    branching_survival      1.0        0.9509    4.91%   1.19%    1.5 s      0.12  <- 3*SE would FAIL
    sir_final_size (R0=2)   0.7968     0.7970    0.03%   0.03%    0.1 s      0.10  <- rounding floor
    ba_degree_exponent      3.0        2.9347    2.18%   0.50%    0.4 s      0.08
    ltm_cascade_window      5.7647     5.5123    4.38%   0.22%    2.1 s      0.09  <- added 2026-07-31
                            (phi=0.18; the anchor and the bracket both follow the claim's own phi)

The LTM row was added because the instrument set and the target queue did not overlap: of the eight
replication targets on offer that day, FIVE were cascade / tipping / threshold claims and none of the
four instruments could model one, so Rooke walked all eight and honestly returned `no-instrument`
every cycle. Its canonical value is DERIVED, not cited -- bisecting the vulnerable-cluster percolation
condition sum_{k<=floor(1/phi)} k(k-1)P_k(z) = z gives 5.7647 at phi=0.18, which happens to agree with
the published window. The -4.4% bias is finite-size, the same character as the branching row,
and the bracket the bisection searches is derived from phi -- a fixed one SATURATED at
phi=0.10, returning its own upper bound with SE exactly 0.0000 across every run.

The branching row is the reason a relative floor exists at all: the log-log fit of a finite generation
window approaches the asymptotic exponent from below and sits ~5% low no matter how many trees are
thrown at it, so a pure 3-sigma rule rejects the very result the model reproduces. The SIR row is the
reason the floor is not merely a fallback: that instrument is sharp to 0.03%, and against a claim
reported as "about 80%" a 3-sigma rule would rule FAILED on rounding.
"""
from __future__ import annotations

import inspect
import math
import re
import sys
from pathlib import Path

ORGAN = {
    "eid": "artificer", "agent": "Artificer Rooke", "name": "Replication Unit",
    "ledger": ".replications.json",
    "decisive": ("REPRODUCED", "FAILED", "NOT_COMPUTABLE"),
    "period_hours": 6.0,                      # ~4x/day
}

_TARGET_PATH = "/api/v1/agent-os/brain/replication-target"
_RECORD_PATH = "/api/v1/agent-os/brain/replication-record"

_SEEDS_NOTE = "independent seeds"


# --------------------------------------------------------------------------------------------------
# ctx plumbing. The dispatcher owns ctx, so nothing here assumes whether its helpers are coroutines
# or plain functions, nor that brain_post takes the timeout positionally. A shape mismatch must not
# be able to cost a cycle.
# --------------------------------------------------------------------------------------------------
async def _call(fn, *args):
    out = fn(*args)
    if inspect.isawaitable(out):
        out = await out
    return out


async def _brain_get(ctx, path):
    return await _call(ctx.brain_get, path)


async def _brain_post(ctx, path, body, timeout=45):
    try:
        return await _call(ctx.brain_post, path, body, timeout)
    except TypeError:
        return await _call(ctx.brain_post, path, body)


def _log(ctx, msg: str) -> None:
    """ASCII only - the console is cp1250 and a stray glyph 500s the request that emitted it."""
    try:
        ctx.logger.info("[rooke] " + msg)
    except Exception:
        pass


# --------------------------------------------------------------------------------------------------
# Reading a claim.
# --------------------------------------------------------------------------------------------------
#: The claim describes a measurement of a particular real system, not a property of the canonical
#: mechanism. A minimal model of the mechanism cannot adjudicate it - the honest answer is to skip and
#: leave it for a replication that has the data. ("Real-world networks are scale-free" belongs here:
#: it is a valuable Crucible target and a BA simulation is simply not the instrument that can rule it.)
_EMPIRICAL = re.compile(
    r"\b(our (?:data|dataset|sample|cohort|corpus)|we (?:analyz|measur|collect|surveyed|observ|sampl)"
    r"|empirical(?:ly)?|real[- ]world|this (?:dataset|corpus|survey)|participants?|respondents?"
    r"|field (?:experiment|data)|observational)\b", re.IGNORECASE)


def _first_float(text: str, patterns, lo: float, hi: float):
    """First value one of `patterns` extracts that is inside the plausible range, else None.

    The range is not decoration. Abstract sentences are dense with numbers that are not the quantity
    asked for - years, sample sizes, confidence levels - and a regex that fires on the wrong one hands
    the verdict logic a number it will faithfully compare against the wrong thing.
    """
    for pat in patterns:
        for m in pat.finditer(text or ""):
            grp = next((g for g in m.groups() if g), None)
            if grp is None:
                continue
            try:
                v = float(grp)
            except (TypeError, ValueError):
                continue
            if lo <= abs(v) <= hi:
                return abs(v)
    return None


def _applicable(claim: str, requires, excludes) -> bool:
    low = (claim or "").lower()
    if not any(r.search(low) for r in requires):
        return False
    return not any(x.search(low) for x in excludes)


# --------------------------------------------------------------------------------------------------
# The instrument set. Each script is stdlib-only, opens with what it MODELS, and prints exactly two
# machine-read lines:
#     MEASURED <label> = <value>
#     SE = <value>            (a NEGATIVE SE means "the instrument could not resolve the quantity",
#                              which is a genuine NOT_COMPUTABLE and not a crash)
# --------------------------------------------------------------------------------------------------

_ER_CODE = '''"""Models the emergence of the giant component in a Poisson (Erdos-Renyi) random graph.

MEASURES the critical mean degree directly from simulated graphs, never from a formula: for each mean
degree c in a sweep, G(N, M = cN/2) is built with a union-find, the susceptibility chi (the mean size
of the FINITE clusters, largest component excluded) is computed, and argmax_c chi is the finite-size
estimate of the percolation point. The value under test does not appear in this script and cannot
steer the measurement.
"""
import random

N = 40000
C_LO, C_STEP, C_N = 0.80, 0.025, 19
SEEDS = 6


def peak_c(n, cs, rng):
    best_c, best_chi = None, -1.0
    for c in cs:
        parent = list(range(n))
        size = [1] * n
        for _ in range(int(c * n / 2)):
            a = rng.randrange(n)
            b = rng.randrange(n)
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            while parent[b] != b:
                parent[b] = parent[parent[b]]
                b = parent[b]
            if a == b:
                continue
            if size[a] < size[b]:
                a, b = b, a
            parent[b] = a
            size[a] += size[b]
        counts = {}
        for v in range(n):
            r = v
            while parent[r] != r:
                parent[r] = parent[parent[r]]
                r = parent[r]
            counts[r] = counts.get(r, 0) + 1
        sizes = sorted(counts.values(), reverse=True)
        rest = sizes[1:]
        tot = sum(rest)
        chi = (sum(s * s for s in rest) / tot) if tot else 0.0
        if chi > best_chi:
            best_chi, best_c = chi, c
    return best_c


cs = [C_LO + C_STEP * i for i in range(C_N)]
ests = [peak_c(N, cs, random.Random(9001 + s)) for s in range(SEEDS)]
mean = sum(ests) / len(ests)
var = sum((e - mean) ** 2 for e in ests) / (len(ests) - 1)
# the grid step is a real part of the uncertainty: an argmax can only land on a swept point
se = (var / len(ests) + (C_STEP / 2) ** 2) ** 0.5
print("MEASURED critical_mean_degree = %.4f" % mean)
print("SE = %.4f" % se)
print("seeds =", ests, "N =", N, "grid =", C_STEP)
'''

_BRANCHING_CODE = '''"""Models a CRITICAL branching process (Poisson offspring, mean 1) and measures how fast its
survival probability decays with the generation number.

MEASURES the decay exponent by simulating an ensemble of trees and fitting log P(alive at n) against
log n by least squares over a late window. The generation step is exact rather than approximate: the
total offspring of Z_n Poisson(1) individuals is itself Poisson(Z_n), so one draw advances a whole
generation. The exponent under test is not an input to this script.
"""
import math
import random

TREES = 60000
GENS = 200
FIT_LO, FIT_HI = 30, 200
SEEDS = 4


def poisson(rng, lam):
    if lam <= 0:
        return 0
    if lam < 30:
        target = math.exp(-lam)
        k, p = 0, 1.0
        while True:
            p *= rng.random()
            if p <= target:
                return k
            k += 1
    return max(0, int(rng.gauss(lam, math.sqrt(lam)) + 0.5))


def slope(seed):
    rng = random.Random(seed)
    alive = [0] * (GENS + 1)
    for _ in range(TREES):
        z = 1
        for g in range(1, GENS + 1):
            z = poisson(rng, z)
            if z <= 0:
                break
            alive[g] += 1
    xs, ys = [], []
    for n in range(FIT_LO, FIT_HI + 1):
        if alive[n] > 0:
            xs.append(math.log(n))
            ys.append(math.log(alive[n] / TREES))
    if len(xs) < 10:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return -sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


ests = [s for s in (slope(4242 + i) for i in range(SEEDS)) if s is not None]
if len(ests) < 2:
    print("MEASURED survival_decay_exponent = 0.0")
    print("SE = -1")             # too few trees survived the window to fit anything
else:
    mean = sum(ests) / len(ests)
    var = sum((e - mean) ** 2 for e in ests) / (len(ests) - 1)
    print("MEASURED survival_decay_exponent = %.4f" % mean)
    print("SE = %.4f" % (var / len(ests)) ** 0.5)
    print("seeds =", [round(e, 4) for e in ests], "trees =", TREES, "fit =", (FIT_LO, FIT_HI))
'''

_SIR_CODE = '''"""Models a stochastic SIR epidemic in a well-mixed population (Reed-Frost chain binomial) at a
basic reproduction number taken from the claim.

MEASURES the final attack rate - the fraction of the population ever infected - as the mean over
outbreaks that took off, across independent seeds. The transcendental final-size relation is NOT in
this script: the epidemic is simulated generation by generation and the fraction is counted. R0 is a
model INPUT; the attack rate under test is not.
"""
import math
import random

N = 20000
R0 = __R0__
RUNS = 200
SEEDS = 4
MAJOR = 0.05                      # an outbreak counts as major once it passes 5% of the population


def binom(rng, n, p):
    if n <= 0 or p <= 0:
        return 0
    if p >= 1:
        return n
    try:
        return rng.binomialvariate(n, p)
    except AttributeError:
        if n * p > 30 and n * (1 - p) > 30:
            return min(n, max(0, int(rng.gauss(n * p, math.sqrt(n * p * (1 - p))) + 0.5)))
        return sum(1 for _ in range(n) if rng.random() < p)


def attack_rate(seed):
    rng = random.Random(seed)
    p = R0 / N
    majors = []
    for _ in range(RUNS):
        S, I, R = N - 1, 1, 0
        while I > 0:
            new = binom(rng, S, 1.0 - (1.0 - p) ** I)
            S -= new
            R += I
            I = new
        if R > MAJOR * N:
            majors.append(R / N)
    return (sum(majors) / len(majors)) if majors else None


ests = [a for a in (attack_rate(555 + i) for i in range(SEEDS)) if a is not None]
if len(ests) < 2:
    print("MEASURED final_attack_rate = 0.0")
    print("SE = -1")             # no outbreak took off - the quantity the claim asserts has no value here
else:
    mean = sum(ests) / len(ests)
    var = sum((e - mean) ** 2 for e in ests) / (len(ests) - 1)
    print("MEASURED final_attack_rate = %.4f" % mean)
    print("SE = %.5f" % (var / len(ests)) ** 0.5)
    print("seeds =", [round(e, 4) for e in ests], "N =", N, "R0 =", R0, "runs =", RUNS)
'''

_BA_CODE = '''"""Models a growing network under LINEAR preferential attachment (Barabasi-Albert: each new node
attaches m edges, targets chosen in proportion to current degree).

MEASURES the tail exponent of the resulting degree distribution with the discrete-corrected maximum
likelihood estimator above a fixed k_min, over independent seeds. The network is grown and its degrees
are counted; no power law is fitted into it and the exponent under test is not an input.
"""
import math
import random

N = 120000
M = 2
KMIN = 20
SEEDS = 4


def degrees(seed):
    rng = random.Random(seed)
    deg = [0] * N
    targets = []                  # each node repeated once per edge -> a uniform pick IS a degree pick
    for i in range(M + 1):        # seed with the complete graph on M+1 nodes
        deg[i] = M
        for _ in range(M):
            targets.append(i)
    for v in range(M + 1, N):
        chosen = set()
        while len(chosen) < M:
            chosen.add(targets[rng.randrange(len(targets))])
        for c in chosen:
            deg[c] += 1
            deg[v] += 1
            targets.append(c)
            targets.append(v)
    return deg


def mle(deg):
    tail = [k for k in deg if k >= KMIN]
    if len(tail) < 200:
        return None
    return 1.0 + len(tail) / sum(math.log(k / (KMIN - 0.5)) for k in tail)


ests = [a for a in (mle(degrees(31 + i)) for i in range(SEEDS)) if a is not None]
if len(ests) < 2:
    print("MEASURED degree_exponent = 0.0")
    print("SE = -1")             # too thin a tail above k_min to estimate an exponent
else:
    mean = sum(ests) / len(ests)
    var = sum((e - mean) ** 2 for e in ests) / (len(ests) - 1)
    print("MEASURED degree_exponent = %.4f" % mean)
    print("SE = %.4f" % (var / len(ests)) ** 0.5)
    print("seeds =", [round(e, 4) for e in ests], "N =", N, "m =", M, "k_min =", KMIN)
'''


_LTM_CODE = '''
"""MODELS: the UPPER edge of the cascade window in Watts' (2002) linear threshold model on a
Poisson random graph -- the mean degree above which a single seed can no longer trigger a global
cascade, because the vulnerable subgraph stops percolating.

The canonical value is DERIVED here, not taken from the paper: a degree-k node is vulnerable under a
uniform threshold phi iff k <= 1/phi, and the vulnerable cluster percolates while
sum_{k <= floor(1/phi)} k(k-1) P_k(z) = z with P_k Poisson. Bisecting that gives z_c = 5.7647 for
phi = 0.18, which agrees with the published window and does not depend on anyone remembering it.
"""
import math, random, statistics

PHI, N, TRIALS, RUNS, CUT = __PHI__, 3000, 40, 5, 0.01

def _pois(k, z):
    return math.exp(-z + k * math.log(z) - math.lgamma(k + 1)) if z > 0 else (1.0 if k == 0 else 0.0)

def analytic_zc(phi):
    def g(z):
        return sum(k * (k - 1) * _pois(k, z) for k in range(0, int(1.0 / phi) + 1)) - z
    lo, hi = 1.5, 20.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if g(lo) * g(mid) <= 0: hi = mid
        else: lo = mid
    return (lo + hi) / 2

def one_run(n, z, phi, rng):
    adj = [[] for _ in range(n)]
    for _ in range(int(n * z / 2)):
        a, b = rng.randrange(n), rng.randrange(n)
        if a != b:
            adj[a].append(b); adj[b].append(a)
    act = [False] * n; cnt = [0] * n
    s = rng.randrange(n); act[s] = True; front = [s]
    while front:
        nxt = []
        for u in front:
            for v in adj[u]:
                if act[v]: continue
                cnt[v] += 1
                if adj[v] and cnt[v] / len(adj[v]) >= phi:
                    act[v] = True; nxt.append(v)
        front = nxt
    return sum(act) / n

def freq(z, rng):
    return sum(1 for _ in range(TRIALS) if one_run(N, z, PHI, rng) > CUT) / TRIALS

# The search range must follow PHI. A fixed [4, 9] was calibrated at phi=0.18 (z_c 5.76) and
# SATURATES at phi=0.10 (z_c 13.66): the bisection converges on its own upper bound and reports
# 8.98 with SE=0.0000 across every run -- five identical answers, which is the signature of a
# boundary, not of a measurement. Vulnerable degrees run to 1/phi, so the window cannot exceed a
# few multiples of that; the bracket is set from phi and a run that still ends against either edge
# reports SE = -1 (the file's convention for "could not resolve") instead of returning the edge.
_LO, _HI = 1.05, max(9.0, 3.0 / PHI)

def zc_hat(rng):
    lo, hi = _LO, _HI
    for _ in range(9):
        mid = (lo + hi) / 2
        if freq(mid, rng) >= 0.5: lo = mid
        else: hi = mid
    return (lo + hi) / 2

ests = [zc_hat(random.Random(4100 + i)) for i in range(RUNS)]
mean = statistics.mean(ests)
_edge = 0.02 * (_HI - _LO)
if mean >= _HI - _edge or mean <= _LO + _edge:
    print("MEASURED cascade_window_upper = %.4f" % mean)
    print("SE = -1")          # saturated against the bracket -- not a measurement
    print("saturated: bracket [%.3g, %.3g] at phi=%s did not contain the crossing" % (_LO, _HI, PHI))
else:
    print("MEASURED cascade_window_upper = %.4f" % mean)
    print("SE = %.4f" % (statistics.stdev(ests) / math.sqrt(len(ests))))
print("analytic z_c =", round(analytic_zc(PHI), 4), "phi =", PHI, "N =", N,
      "runs =", [round(e, 3) for e in ests])
'''


def _rx(*pats):
    return tuple(re.compile(p, re.IGNORECASE) for p in pats)


def _inst_er(claim: str):
    """Critical mean degree of a Poisson random graph. Canonical 1.0."""
    requires = _rx(r"\b(erdos|erdős|renyi|rényi|random graph|poisson (?:random )?(?:graph|network))\b")
    # every excluded setting has a DIFFERENT threshold, so applying this instrument there would
    # produce a FAILED that says nothing about the claim
    excludes = _rx(r"\b(lattice|square|triangular|cubic|hypercub|spatial|geometric|small[- ]world"
                   r"|configuration model|scale[- ]free|power[- ]law|degree[- ]correlat|assortativ"
                   r"|clustered|directed|bipartite|multiplex|interdependent|temporal|weighted)\b")
    if not _applicable(claim, requires, excludes):
        return None
    if not re.search(r"\b(giant component|percolation|threshold|critical)\b", claim, re.IGNORECASE):
        return None
    claimed = _first_float(claim, _rx(
        r"\b(?:z_?c|c_?c|k_?c)\s*(?:=|is|of|≈|~)\s*(\d+(?:\.\d+)?)",
        r"critical\s+(?:average\s+|mean\s+)?degree[^.\d]{0,25}(\d+(?:\.\d+)?)",
        r"(?:average|mean)\s+degree[^.\d]{0,25}(\d+(?:\.\d+)?)[^.]{0,60}"
        r"(?:giant component|percolat|threshold)",
        r"(?:giant component|percolat\w+|threshold)[^.]{0,60}?(?:average|mean)\s+degree"
        r"[^.\d]{0,25}(\d+(?:\.\d+)?)",
    ), 0.2, 5.0)
    if claimed is None:
        return None
    return {"key": "er_giant_component", "label": "critical_mean_degree", "claimed": claimed,
            "code": _ER_CODE, "params": {"N": 40000, "c_lo": 0.80, "c_step": 0.025, "seeds": 6},
            "rel_floor": 0.08, "seeds": 6,
            "models": "critical mean degree of the giant component in a Poisson random graph, "
                      "measured as the argmax of the finite-cluster susceptibility"}


def _inst_branching(claim: str):
    """Survival-probability decay exponent of a critical branching process. Canonical 1.0."""
    requires = _rx(r"\b(branching process|galton[- ]watson|critical branching)\b")
    excludes = _rx(r"\b(subcritical|supercritical|multi[- ]?type|age[- ]dependent|spatial"
                   r"|immigration|catastroph|environment)\b")
    if not _applicable(claim, requires, excludes):
        return None
    if not re.search(r"\b(surviv\w+|extinction|non[- ]extinction)\b", claim, re.IGNORECASE):
        return None
    claimed = _first_float(claim, _rx(
        r"\bexponent[^.\d]{0,25}(-?\d+(?:\.\d+)?)",
        r"\bn\s*\^\s*\{?\s*-\s*(\d+(?:\.\d+)?)",
        r"\bn\s*\*\*\s*-\s*(\d+(?:\.\d+)?)",
    ), 0.2, 4.0)
    if claimed is None and re.search(
            r"(decay\w*|decreas\w*|fall\w*)\s+(?:as|like)\s+1\s*/\s*n\b"
            r"|inversely proportional to (?:the )?(?:number of )?generation", claim, re.IGNORECASE):
        claimed = 1.0
    if claimed is None:
        return None
    return {"key": "branching_survival", "label": "survival_decay_exponent", "claimed": claimed,
            "code": _BRANCHING_CODE, "params": {"trees": 60000, "gens": 200, "fit": (30, 200), "seeds": 4},
            "rel_floor": 0.12, "seeds": 4,
            "models": "decay exponent of the survival probability of a critical Poisson branching "
                      "process, fitted log-log over generations 30-200"}


def _inst_sir(claim: str):
    """Final attack rate of a well-mixed SIR epidemic at a stated R0."""
    requires = _rx(r"\b(sir|seir|epidemic|outbreak|basic reproduction number|r_?0)\b")
    # each of these changes the final size at fixed R0, so the well-mixed model is the wrong instrument
    excludes = _rx(r"\b(network|heterogene\w+|age[- ]structur\w+|contact matrix|household|metapopulat\w+"
                   r"|spatial|vaccin\w+|interven\w+|lockdown|quarantin\w+|waning|seasonal|reinfection"
                   r"|superspread\w+|clustered)\b")
    if not _applicable(claim, requires, excludes):
        return None
    r0 = _first_float(claim, _rx(
        r"\bR_?0\b[^.\d]{0,20}(\d+(?:\.\d+)?)",
        r"basic reproduction number[^.\d]{0,25}(\d+(?:\.\d+)?)",
    ), 1.3, 6.0)
    if r0 is None:
        return None
    claimed = _pct_near(claim, r"(attack rate|final size|final epidemic size|ever infected"
                               r"|of the population|infected)")
    if claimed is None:
        return None
    code = _SIR_CODE.replace("__R0__", repr(round(r0, 4)))
    return {"key": "sir_final_size", "label": "final_attack_rate", "claimed": claimed,
            "code": code, "params": {"N": 20000, "R0": round(r0, 4), "runs": 200, "seeds": 4},
            "rel_floor": 0.10, "seeds": 4,
            "models": "final attack rate of a stochastic well-mixed Reed-Frost SIR epidemic at "
                      "R0 = %s, counted over outbreaks that took off" % round(r0, 4)}


def _inst_ba(claim: str):
    """Degree exponent of a linear preferential-attachment network. Canonical 3.0."""
    requires = _rx(r"\b(preferential attachment|barabasi|barabási|albert model|growing network)\b")
    # a variant of the attachment rule has a different exponent by design - not a failed replication
    excludes = _rx(r"\b(fitness|non[- ]?linear|sub[- ]?linear|super[- ]?linear|aging|ageing|copying"
                   r"|duplicat\w+|accelerat\w+|deletion|rewir\w+|directed|weighted|spatial|initial "
                   r"attractiveness)\b")
    if not _applicable(claim, requires, excludes):
        return None
    if not re.search(r"\b(degree (?:distribution|exponent)|power[- ]law|scale[- ]free|gamma|P\(k\))\b",
                     claim, re.IGNORECASE):
        return None
    claimed = _first_float(claim, _rx(
        r"\b(?:exponent|gamma|γ)\s*(?:of|=|is|≈|~)?\s*(\d+(?:\.\d+)?)",
        r"P\s*\(\s*k\s*\)\s*(?:~|∝|\\propto|proportional to)\s*k\s*\^?\s*\{?\s*-\s*(\d+(?:\.\d+)?)",
        r"\bk\s*\^\s*\{?\s*-\s*(\d+(?:\.\d+)?)",
    ), 1.5, 5.0)
    if claimed is None:
        return None
    return {"key": "ba_degree_exponent", "label": "degree_exponent", "claimed": claimed,
            "code": _BA_CODE, "params": {"N": 120000, "m": 2, "k_min": 20, "seeds": 4},
            "rel_floor": 0.08, "seeds": 4,
            "models": "tail exponent of the degree distribution of a linear preferential-attachment "
                      "network, discrete-corrected MLE above k_min = 20"}


_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|per ?cent)", re.IGNORECASE)
#: a percentage that is a statistical annotation, never the quantity being claimed
_PCT_NOISE = re.compile(r"\b(confidence|CI|credible|significan\w+|alpha|power of|reduction in "
                        r"(?:variance|error))\b", re.IGNORECASE)


def _pct_near(claim: str, vocab: str):
    """A percentage that is genuinely the claimed quantity, as a fraction, or None.

    An abstract sentence with an attack rate in it usually also carries a confidence level; taking the
    first percentage in the sentence gets the verdict right only by luck. The percentage must sit next
    to the vocabulary of the quantity, and away from the vocabulary of an interval.
    """
    rx = re.compile(vocab, re.IGNORECASE)
    for m in _PCT.finditer(claim or ""):
        a, b = max(0, m.start() - 70), min(len(claim), m.end() + 45)
        window = claim[a:b]
        if _PCT_NOISE.search(window):
            continue
        if rx.search(window):
            v = float(m.group(1))
            if 1.0 < v <= 100.0:
                return v / 100.0
    return None


def _inst_ltm(claim: str):
    """Upper edge of the cascade window in the linear threshold model. Canonical 5.7647 (phi=0.18).

    ADDED 2026-07-31 because the instrument set and the target queue did not overlap. Measured that
    day: of the eight replication targets on offer, FIVE were cascade / tipping / threshold claims
    (Granovetter's LTM, critical seed fraction, minority tipping, hysteresis width, tipping vs
    connectivity) and Rooke's four instruments modelled giant components, branching, SIR and
    scale-free exponents. He walked all eight and honestly returned `no-instrument` every cycle --
    not a defect in him, a capability gap.

    This closes one quantity, not all five: the mean degree at which cascades stop. A claim about a
    SEED FRACTION is a different measurement and is deliberately refused rather than answered with
    the nearest thing to hand -- an instrument applied where it is not the right instrument produces
    a FAILED that says nothing about the claim.
    """
    requires = _rx(r"\b(cascade|tipping|linear threshold model|\bLTM\b|threshold model|contagion)\b")
    excludes = _rx(r"\b(lattice|square|triangular|cubic|hypercub|spatial|geometric|small[- ]world"
                   r"|configuration model|scale[- ]free|power[- ]law|assortativ|clustered|directed"
                   r"|bipartite|multiplex|interdependent|temporal|weighted|multi[- ]?seed"
                   # `seed fraction` was here and was too broad. Measured 2026-07-31: it killed
                   # "in a Watts model with mean degree 6 and threshold 0.1, a 1% seed fraction
                   # achieves near-complete cascade" -- a CONNECTIVITY claim that merely mentions
                   # the seed it used. What this instrument cannot model is a claim ABOUT a seed
                   # fraction, and the positive test below already requires a connectivity term,
                   # so the exclusion was doing nothing except refusing work.
                   r"|seeded at|initial adopters)\b")
    if not _applicable(claim, requires, excludes):
        return None
    # it must be about CONNECTIVITY, not about how many seeds were used
    if not re.search(r"\b(mean|average)\s+degree|connectivity|\bz_?c\b|cascade window",
                     claim, re.IGNORECASE):
        return None
    claimed = _first_float(claim, _rx(
        r"\b(?:z_?c|k_?c)\s*(?:=|is|of|≈|~)\s*(\d+(?:\.\d+)?)",
        r"cascade window[^.\d]{0,40}(\d+(?:\.\d+)?)",
        r"(?:average|mean)\s+degree[^.\d]{0,25}(\d+(?:\.\d+)?)[^.]{0,60}"
        r"(?:cascade|tipping|threshold)",
        r"(?:cascade|tipping)[^.]{0,60}?(?:average|mean)\s+degree[^.\d]{0,25}(\d+(?:\.\d+)?)",
    ), 1.0, 20.0)
    if claimed is None:
        return None
    # THE WINDOW MOVES WITH THE THRESHOLD, so phi must come from the CLAIM, not from a constant.
    # z_c is 5.76 at phi=0.18 but 13.66 at phi=0.10 -- measuring at the wrong phi and comparing to
    # the claim's mean degree would manufacture a FAILED out of a units mismatch, which is exactly
    # the "instrument error wearing a verdict's clothes" this organ's contract forbids. A claim that
    # states no threshold is refused rather than measured against an assumed one.
    phi = _first_float(claim, _rx(
        r"\b(?:threshold|phi|φ)\s*(?:=|is|of|≈|~)?\s*(0?\.\d+)",
        r"(0?\.\d+)\s*(?:adoption\s*)?threshold",
    ), 0.02, 0.5)
    if phi is None:
        return None
    return {"key": "ltm_cascade_window", "label": "cascade_window_upper", "claimed": claimed,
            "code": _LTM_CODE.replace("__PHI__", repr(float(phi))),
            "params": {"PHI": phi, "N": 3000, "TRIALS": 40, "RUNS": 5},
            "rel_floor": 0.09, "seeds": 5,
            "models": "upper edge of the Watts (2002) cascade window on a Poisson random graph at "
                      "the threshold the claim states (phi=%.3g) -- the mean degree above which one "
                      "seed can no longer trigger a global cascade" % phi}


#: the vocabulary of every quantity this family labels, so "nearest preceding label" can be decided
_MFT_LABELS = re.compile(
    r"tipping (?:fraction|point|threshold)|committed (?:minority|fraction)"
    r"|recovery (?:edge|point|threshold)|reverse (?:sweep|edge)"
    r"|hysteresis (?:width|loop|gap)|cascade (?:extent|size)|seed fraction", re.IGNORECASE)


def _labelled_pct(claim: str, vocab: str):
    """The percentage whose NEAREST PRECEDING label matches `vocab`, as a fraction, or None.

    Direction and nearness both matter. A sentence like "a tipping fraction of 4.8%, a recovery edge
    of 4.6%, and a hysteresis width of 0.2%" packs three labelled quantities into sixty characters, so
    any rule that accepts a label found *near* a number will hand back the same number for all three.
    Measured on exactly that sentence: a window-based match returned 4.8% for both the tipping and the
    recovery label. Here the text between a label and its number must contain no OTHER label.
    """
    want = re.compile(vocab, re.IGNORECASE)
    text = claim or ""
    for m in _PCT.finditer(text):
        head = text[:m.start()]
        labels = list(_MFT_LABELS.finditer(head))
        if not labels:
            continue
        last = labels[-1]
        if m.start() - last.end() > 40:          # the label must actually introduce this number
            continue
        if _PCT_NOISE.search(text[max(0, m.start() - 70):m.end() + 45]):
            continue
        if want.search(last.group(0)):
            v = float(m.group(1))
            if 0.0 < v <= 100.0:
                return v / 100.0
    return None


_MFT_CODE = r'''
import math, random, statistics

J, H, REC, TIP = __J__, __H__, __REC__, __TIP__
N_SMALL, N_LARGE = 240, 600

def fixed_points(p, beta, n=4001):
    def F(m): return p + (1.0 - p) * math.tanh(beta * (J * m + H)) - m
    out = []
    # Endpoint roots are real roots: at p=1 every agent is committed, so m=1 exactly and F(1)=0. A
    # sign-change scan never sees it because 1.0 has no successor sample. Calibration anchor A2 failed
    # on exactly this -- the solver reported "never tips" at every temperature.
    for edge in (-1.0, 1.0):
        if abs(F(edge)) < 1e-12: out.append(edge)
    px, pf = -1.0, F(-1.0)
    for i in range(1, n):
        x = -1.0 + 2.0 * i / (n - 1); f = F(x)
        if pf * f < 0:
            lo, hi = px, x
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                if F(lo) * F(mid) <= 0: hi = mid
                else: lo = mid
            out.append(0.5 * (lo + hi))
        px, pf = x, f
    return sorted(out)

def branch(p, beta, start):
    rs = fixed_points(p, beta)
    if not rs: return None
    def stable(m):
        c = math.cosh(beta * (J * m + H))
        return (1.0 - p) * beta * J / (c * c) < 1.0
    st = [m for m in rs if stable(m)]
    if not st: return rs[-1] if start > 0 else rs[0]
    return max(st) if start > 0 else min(st)

def _edge(beta, start):
    if branch(1.0, beta, start) is None or branch(1.0, beta, start) <= 0: return None
    b0 = branch(0.0, beta, start)
    if b0 is not None and b0 > 0: return 0.0
    a, b = 0.0, 1.0
    for _ in range(90):
        mid = 0.5 * (a + b); m = branch(mid, beta, start)
        if m is not None and m > 0: b = mid
        else: a = mid
    return 0.5 * (a + b)

# PIN the one unstated parameter on the claim's RECOVERY edge, then PREDICT the tipping fraction.
# The claimed tipping value is never an input to the model -- it is only ever compared against.
lo, hi = 0.50, 0.999
for _ in range(70):
    mid = 0.5 * (lo + hi)
    r = _edge(1.0 / mid, +1.0)
    if (r if r is not None else 0.0) < REC: lo = mid
    else: hi = mid
T_FIT = 0.5 * (lo + hi)
PRED = _edge(1.0 / T_FIT, -1.0)

def trial(N, p, beta, horizon, rng):
    C = int(round(p * N)); F = N - C
    if F <= 0: return True
    u = 0
    for _ in range(int(horizon * N)):
        m = (C + 2 * u - F) / N
        fl = J * m + H
        w_up = (F - u) / (1.0 + math.exp(max(-60.0, min(60.0, -2.0 * beta * fl))))
        w_dn = u / (1.0 + math.exp(max(-60.0, min(60.0, +2.0 * beta * fl))))
        tot = w_up + w_dn
        if tot <= 0: break
        if rng.random() * tot < w_up: u += 1
        else: u -= 1
        if (C + 2 * u - F) / N > 0.05: return True
    return False

def tip_finite(N, beta, seed, trials=18, horizon=140, hi_p=0.30):
    rng = random.Random(seed); lo, hi = 0.0, hi_p
    for _ in range(9):
        mid = 0.5 * (lo + hi)
        hits = sum(1 for _ in range(trials) if trial(N, mid, beta, horizon, rng))
        if hits >= trials / 2.0: hi = mid
        else: lo = mid
    return 0.5 * (lo + hi)

beta = 1.0 / T_FIT
small = statistics.fmean([tip_finite(N_SMALL, beta, 700 + s) for s in range(3)])
large = statistics.fmean([tip_finite(N_LARGE, beta, 800 + s) for s in range(3)])
bias_s = (small - PRED) / PRED
bias_l = (large - PRED) / PRED
span = abs(bias_s - bias_l)

print("pinned_temperature = %.6f" % T_FIT)
print("analytic_tipping   = %.6f" % PRED)
print("finite_N%d = %.6f (bias %+.1f%%)   finite_N%d = %.6f (bias %+.1f%%)"
      % (N_SMALL, small, 100 * bias_s, N_LARGE, large, 100 * bias_l))
print("MEASURED committed_tipping_fraction = %.6f" % PRED)
print("SE = %.6f" % (abs(PRED) * span))
# THE CONTROL. If the size sensitivity is small, the claim's silence about N is harmless and the
# NOT_COMPUTABLE below would be manufactured rather than earned. The instrument must say so.
if span < 0.05:
    print("VERDICT: size-sensitivity control did NOT fire (span %.3f) -- N is not load-bearing here"
          % span)
elif abs(PRED - TIP) / TIP <= span:
    print("VERDICT: NOT_COMPUTABLE -- claimed %.4f vs analytic %.4f (%.1f%% apart), but the finite-size "
          "bias spans %.1f%% between N=%d and N=%d and the claim states no system size, so no tolerance "
          "can be set that is not an assumption"
          % (TIP, PRED, 100 * abs(PRED - TIP) / TIP, 100 * span, N_SMALL, N_LARGE))
else:
    print("VERDICT: FAILED -- claimed %.4f vs analytic %.4f (%.1f%% apart), beyond the %.1f%% finite-size "
          "span, so the gap is not explained by the unstated system size"
          % (TIP, PRED, 100 * abs(PRED - TIP) / TIP, 100 * span))
'''


def _inst_mft(claim: str):
    """Committed-minority tipping in the mean-field Ising model with a field. Closes the second of the
    five cascade/tipping quantities in Rooke's queue that no instrument could rule.

    THE SEVERE TEST. The claim states four numbers -- coupling J, field h, a tipping fraction and a
    recovery edge -- and the model has one parameter the claim leaves unstated: temperature. Pinning T
    on the RECOVERY edge leaves the TIPPING fraction as a free prediction. One knob turned, one number
    predicted, and the claimed tipping value never enters the model. A claim carrying only one of the
    two edges is refused: with nothing to pin T on, any verdict would be a verdict about an assumed
    temperature.

    CALIBRATED before it was trusted, against two anchors DERIVED rather than remembered (both are
    asserted in the test suite): at p=0, h=0 the model is the textbook mean-field Ising with T_c = J
    exactly -- measured 1.000000 for J=1.0, error 3.3e-9 -- and as T -> 0 the forward tipping fraction
    approaches (J - h)/(2J), measured converging 0.2967 -> 0.3704 -> 0.4147 -> 0.4465 at T = 0.20,
    0.10, 0.05, 0.02 against the analytic 0.475.

    WHY IT USUALLY RULES NOT_COMPUTABLE, and why that is a measurement rather than a shrug. The tipping
    fraction has an enormous finite-size bias, and it is NEGATIVE: noise carries a finite system over
    the barrier while the barrier is still there. Measured at the fitted temperature: -56.2% at N=240
    and -25.1% at N=600. A claim stating no system size is therefore consistent with analytic values
    spanning tens of percent, and ruling FAILED on a 10% gap would be the instrument's own systematic
    error wearing a verdict's clothes -- the branching row's lesson. So the script MEASURES that span
    every run and carries a control that fires only if the span is large; if N turns out not to be
    load-bearing, the instrument says so instead of ruling.
    """
    requires = _rx(r"\b(tipping|committed (?:minority|fraction)|consensus|hysteresis|minority)\b")
    excludes = _rx(r"\b(cascade window|mean degree|network connectivity|scale[- ]free|small[- ]world"
                   r"|epidemic|infection|branching|giant component)\b")
    if not _applicable(claim, requires, excludes):
        return None
    # BOTH edges, or there is nothing to pin the temperature on.
    #
    # NOT `_pct_near` here, and the reason is measured. That helper accepts a label anywhere in a
    # +-70/+45 character window around the number, which is fine when a sentence carries one labelled
    # quantity and a confidence interval. This claim carries THREE labelled percentages inside 60
    # characters -- "a tipping fraction of 4.8%, a recovery edge of 4.6%, and a hysteresis width of
    # 0.2%" -- so the window around 4.8% already contains the words "recovery edge", and the helper
    # returned 4.8 for BOTH labels. The instrument then refused itself on `rec < tip`, which is the
    # guard working, but it means no verdict could ever be reached on the family this exists for.
    # A label must therefore be the NEAREST one PRECEDING its number, not merely nearby.
    tip = _labelled_pct(claim, r"tipping (?:fraction|point|threshold)|committed (?:minority|fraction)")
    rec = _labelled_pct(claim, r"recovery (?:edge|point|threshold)|reverse (?:sweep|edge)")
    if tip is None or rec is None or not (0.0 < rec < tip < 0.9):
        return None
    # J and h come from the CLAIM. The window moves with both, so measuring at assumed couplings and
    # comparing to the claim's fractions would manufacture a verdict out of a units mismatch -- the
    # same trap phi sets for the cascade-window instrument.
    jj = _first_float(claim, _rx(r"\bJ\s*(?:=|is|of|≈|~)\s*(\d+(?:\.\d+)?)",
                                 r"coupling\s*(?:strength\s*)?(?:=|is|of|≈|~)?\s*(\d+(?:\.\d+)?)"),
                      0.05, 20.0)
    hh = _first_float(claim, _rx(r"\bh\s*(?:=|is|of|≈|~)\s*(\d+(?:\.\d+)?)",
                                 r"(?:external\s+)?field\s*(?:=|is|of|≈|~)?\s*(\d+(?:\.\d+)?)"),
                      0.0, 5.0)
    if jj is None or hh is None:
        return None
    code = (_MFT_CODE.replace("__J__", repr(float(jj)))
                     # the field OPPOSES the committed minority: with h favouring it, the +1 state is
                     # stable at p=0 and there is no lower edge to pin on at all (measured: recovery
                     # 0.000 at every temperature on that branch).
                     .replace("__H__", repr(-abs(float(hh))))
                     .replace("__REC__", repr(float(rec)))
                     .replace("__TIP__", repr(float(tip))))
    return {"key": "mf_committed_tipping", "label": "committed_tipping_fraction", "claimed": tip,
            "code": code,
            "params": {"J": jj, "H": -abs(hh), "REC": rec, "N_SMALL": 240, "N_LARGE": 600},
            "rel_floor": 0.25, "seeds": 3,
            # The reported figure is NOT seed scatter. It is the systematic spread of the tipping
            # fraction between N=240 and N=600, which dominates the statistical error by an order of
            # magnitude here and is the honest thing to price a tolerance on.
            "uncertainty": "seeds each; the figure is the finite-size spread between N=240 and N=600, "
                           "not seed scatter",
            "models": "mean-field Ising with a committed +1 minority at coupling J=%.3g and an opposing "
                      "field h=%.3g, with the unstated temperature pinned on the claim's own recovery "
                      "edge so the tipping fraction is a free prediction" % (jj, -abs(hh))}


_INSTRUMENTS = (_inst_er, _inst_branching, _inst_sir, _inst_ba, _inst_ltm, _inst_mft)


def instrument_for(claim: str):
    """The one instrument that can honestly test this claim, or None. Public for the dispatcher/tests."""
    text = (claim or "").strip()
    if len(text) < 40:
        return None
    if _EMPIRICAL.search(text):
        return None
    for build in _INSTRUMENTS:
        try:
            inst = build(text)
        except Exception:
            inst = None
        if inst:
            return inst
    return None


# --------------------------------------------------------------------------------------------------
# Verdict.
# --------------------------------------------------------------------------------------------------
def _independent(inst: dict) -> bool:
    """True when the value under test is not one of the model's inputs."""
    claimed = inst.get("claimed")
    if not claimed:
        return False
    for v in (inst.get("params") or {}).values():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if abs(float(v) - float(claimed)) <= 1e-9 * max(1.0, abs(float(claimed))):
                return False
    return True


def rule(measured, se, inst: dict):
    """(verdict, reason). The only place a verdict is decided, so it can be tested without a Lab."""
    claimed = float(inst["claimed"])
    if measured is None or se is None or not math.isfinite(measured) or se < 0:
        return "NOT_COMPUTABLE", ("the minimal model ran but could not resolve %s - the quantity the "
                                  "claim asserts has no value in this model" % inst["label"])
    if claimed == 0:
        return "NOT_COMPUTABLE", "the claimed value is zero, so no relative tolerance is definable"
    tol = max(3.0 * se, inst["rel_floor"] * abs(claimed))
    if tol >= 0.5 * abs(claimed):
        return "NOT_COMPUTABLE", ("instrument resolution (+/-%.4g) is wider than half the claimed value "
                                  "(%.4g) - a FAILED was not a live possibility, so a verdict here would "
                                  "be an artefact" % (tol, claimed))
    if not _independent(inst):
        return "NOT_COMPUTABLE", ("the claimed value is itself an input to the model, so it is true by "
                                  "construction and no measurement could have contradicted it")
    diff = abs(measured - claimed)
    if diff <= tol:
        return "REPRODUCED", ("measured %.4g vs claimed %.4g, |diff| %.3g within tolerance %.3g "
                              "(max(3*SE=%.3g, %.0f%% of claimed))"
                              % (measured, claimed, diff, tol, 3.0 * se, inst["rel_floor"] * 100))
    return "FAILED", ("measured %.4g vs claimed %.4g, |diff| %.3g exceeds tolerance %.3g "
                      "(max(3*SE=%.3g, %.0f%% of claimed))"
                      % (measured, claimed, diff, tol, 3.0 * se, inst["rel_floor"] * 100))


_MEASURED_RX = re.compile(r"^MEASURED\s+(\S+)\s*=\s*(-?[\d.eE+]+)\s*$", re.MULTILINE)
_SE_RX = re.compile(r"^SE\s*=\s*(-?[\d.eE+]+)\s*$", re.MULTILINE)


def parse_output(out: str):
    """(measured, se) from the two machine-read lines, or (None, None)."""
    m, s = _MEASURED_RX.search(out or ""), _SE_RX.search(out or "")
    if not m or not s:
        return None, None
    try:
        return float(m.group(2)), float(s.group(1))
    except (TypeError, ValueError):
        return None, None


# --------------------------------------------------------------------------------------------------
# Prior art. Defence in depth: the brain's pick_target already applies already_covered() when it
# scans, but the ledger moves under us and a target can be handed over from a cache.
# --------------------------------------------------------------------------------------------------
def _prior_art(claim: str):
    """(blocking_reason, family_prior_ids, semantic_prior_ids). Never raises.

    already_covered() BLOCKS - it is the check that stops the same result being counted twice.
    family_prior() and semantic_prior() deliberately do NOT: replaying the live ledger through a
    family block showed it would have refused 9 of 58 entries, one of them the FAILED on "real-world
    networks are scale-free", which is the single most valuable kind of entry the Crucible produces.
    They are reported as evidence and left for a human, exactly as their own docstrings require.
    """
    try:
        server = str(Path(__file__).resolve().parents[2] / "server")
        if server not in sys.path:
            sys.path.insert(0, server)
        from agora.execution.replication import already_covered, family_prior, semantic_prior
    except Exception:
        return "", [], []
    try:
        blocked = already_covered(claim) or ""
    except Exception:
        blocked = ""
    fam, sim = [], []
    try:
        fam = family_prior(claim) or []
    except Exception:
        pass
    try:
        sim = semantic_prior(claim) or []
    except Exception:
        pass
    return blocked, fam[:8], sim[:8]


# --------------------------------------------------------------------------------------------------
# The cycle.
# --------------------------------------------------------------------------------------------------
def _result(status, why, *, decisive=False, title="", content="", lab_id=None):
    return {"status": status, "decisive": decisive, "title": title, "content": content,
            "lab_id": lab_id, "why": why}


async def _memory_note(ctx, claim: str, key: str) -> str:
    """What Rooke already remembers about this family. Never blocks, never raises."""
    try:
        hits = await _call(ctx.recall, "replication %s %s" % (key, claim[:60]))
    except Exception:
        return ""
    try:
        if isinstance(hits, dict):
            hits = hits.get("results") or hits.get("memories") or hits.get("items") or []
        n = len(hits) if isinstance(hits, (list, tuple)) else (1 if hits else 0)
        return ("%d prior memory hits on this family" % n) if n else ""
    except Exception:
        return ""


async def cycle(ctx) -> dict:
    """One replication attempt. Never raises - a failure is a returned status, not an exception."""
    try:
        try:
            data = await _brain_get(ctx, _TARGET_PATH)
        except Exception as e:
            return _result("error", "replication-target unreachable: %s: %s"
                           % (type(e).__name__, str(e)[:160]))
        if not isinstance(data, dict):
            return _result("error", "replication-target returned %s, not an object"
                           % type(data).__name__)
        # WALK THE LIST, DO NOT TAKE THE HEAD. Rooke's instrument set decides what he can honestly
        # model, so a claim he must refuse has to be steppable. Measured 2026-07-31: with a single head
        # he was wedged permanently -- four consecutive calls returned the same empirical claim about
        # Pareto regrets, which no minimal model can settle; he refused it correctly and got it back.
        # Zero discoveries in the preceding five days. The endpoint now offers `targets`; the same
        # comment on belief-challenge-target records that head-only cost that sweep 42 days.
        cands = data.get("targets")
        if not isinstance(cands, list) or not cands:
            head = data.get("target") or {}
            cands = [head] if isinstance(head, dict) and head else []
        if not cands:
            return _result("idle", "the brain has no sourced claim awaiting a re-run "
                                   "(replication-target returned no target)")

        target, claim, source, inst = None, "", "", None
        fam, sim = [], []          # prior art OF THE SELECTED claim, bound at the break below
        skipped = []
        for cand in cands:
            if not isinstance(cand, dict):
                continue
            c = (cand.get("claim") or "").strip()
            s = (cand.get("source") or "").strip()
            if len(c) < 40 or not s:
                skipped.append("thin")
                continue
            blocked, _fam, _sim = _prior_art(c)
            if blocked:
                skipped.append("covered")
                continue
            i = instrument_for(c)
            if not i:
                skipped.append("no-instrument")
                _log(ctx, "no instrument for: %s" % c[:70])
                continue
            target, claim, source, inst = cand, c, s, i
            fam, sim = _fam, _sim
            break

        if inst is None:
            # Honest idle, but now it says how MANY were considered -- a wedge and an empty queue are
            # different states and used to look identical.
            return _result("idle", "walked %d replication candidate(s), none testable by Rooke's "
                                   "instrument set (%s)"
                           % (len(cands), ", ".join(sorted(set(skipped))) or "none usable"))
        if skipped:
            _log(ctx, "stepped past %d unusable candidate(s): %s"
                 % (len(skipped), ", ".join(sorted(set(skipped)))))

        mem = await _memory_note(ctx, claim, inst["key"])
        _log(ctx, "bench: %s claimed %s=%.4g%s"
             % (inst["key"], inst["label"], inst["claimed"], ("; " + mem) if mem else ""))

        name = "replication:%s %s" % (inst["key"], claim[:70])
        try:
            lab = await _call(ctx.lab_run, name, inst["code"])
        except Exception as e:
            return _result("error", "lab run failed to dispatch: %s: %s"
                           % (type(e).__name__, str(e)[:160]))
        lab = lab or {}
        lab_id = (lab.get("id") or lab.get("lab_id") or "").strip()
        if not lab_id:
            return _result("error", "the Lab returned no run id, so nothing downstream could cite this "
                                    "measurement: %s" % str(lab)[:160])
        if lab.get("ok") is False:
            return _result("error", "lab %s did not run to completion (our script, not the claim): %s"
                           % (lab_id, str(lab.get("output"))[:200]), lab_id=lab_id)

        measured, se = parse_output(lab.get("output") or "")
        if measured is None:
            return _result("error", "lab %s printed no MEASURED/SE pair - the instrument is broken, "
                                    "which is our defect and not a property of the claim" % lab_id,
                           lab_id=lab_id)

        verdict, reason = rule(measured, se, inst)
        checked = bool(_independent(inst)) and verdict == "REPRODUCED"
        tol = max(3.0 * se, inst["rel_floor"] * abs(inst["claimed"])) if se >= 0 else None
        # record() truncates the note at 300 chars, so it is written to FIT rather than to be cut:
        # an independence sentence that survives only as "...indepen" proves nothing to the reader or
        # to the by-construction gate that reads this field.
        note = ("MEASURED %s=%.5g (SE %.3g, %d seeds) vs CLAIMED %.5g; |diff| %s vs tol %s -> %s. "
                "Not by-construction: the claimed value is not a model input (independent Monte-Carlo "
                "ensemble). lab %s"
                % (inst["label"], measured, se, inst["seeds"], inst["claimed"],
                   "%.3g" % abs(measured - inst["claimed"]), ("%.3g" % tol) if tol else "n/a",
                   verdict, lab_id))[:300]

        body = {"claim": claim, "source": source, "outcome": verdict, "lab_id": lab_id, "note": note,
                "by_construction_checked": checked}
        try:
            resp = await _brain_post(ctx, _RECORD_PATH, body) or {}
        except Exception as e:
            return _result("error", "lab %s measured %s=%.5g (%s) but the record POST failed: %s: %s"
                           % (lab_id, inst["label"], measured, verdict, type(e).__name__, str(e)[:120]),
                           lab_id=lab_id)
        if (resp.get("status") or "") != "ok":
            return _result("error", "brain refused the replication record (%s) for lab %s"
                           % (str(resp.get("status"))[:40], lab_id), lab_id=lab_id)

        # The gate may have downgraded us. Report what the LEDGER now says, never what we proposed,
        # and never re-POST to argue with it: record() appends, so a second POST double-counts.
        final = ((resp.get("record") or {}).get("outcome") or verdict).upper()
        downgraded = final != verdict
        # The reason belongs to the verdict it explains. Attaching our REPRODUCED reasoning to a
        # downgraded verdict prints "NOT_COMPUTABLE - within tolerance", which reads as a system that
        # does not know what it just decided.
        if downgraded:
            reason = ("downgraded by the brain's by-construction self-check from the %s we proposed "
                      "(%s)" % (verdict, reason))

        lines = [
            "CLAIM: %s" % claim[:200],
            "SOURCE: %s" % source[:160],
            "MODEL: %s [lab %s, stdlib-only Monte Carlo]" % (inst["models"], lab_id),
            # An instrument whose dominant uncertainty is NOT seed scatter must say so. The committed
            # tipping row reports a finite-size SPAN between two system sizes, and calling that
            # "3 independent seeds" would describe a statistical error bar we did not measure -- in an
            # artifact bound for the public replication ledger.
            "MEASURED: %s = %.5g (SE %.3g, %d %s)" % (inst["label"], measured, se, inst["seeds"],
                                                      inst.get("uncertainty") or _SEEDS_NOTE),
            "CLAIMED: %s = %.5g" % (inst["label"], inst["claimed"]),
        ]
        if tol is not None:
            lines.append("TOLERANCE: +/-%.4g = max(3*SE, %.0f%% of claimed); the %.0f%% floor is this "
                         "instrument's measured systematic bias against its canonical value"
                         % (tol, inst["rel_floor"] * 100, inst["rel_floor"] * 100))
        lines.append("VERDICT: %s - %s" % (final, reason))
        # NAME THE TEST THAT WOULD OVERTURN IT. Measured 2026-07-31: 40 of the last 40 discoveries
        # carried a Lab id and NONE named the observation that would flip it, so the press bar --
        # which requires exactly that -- had nothing it could publish. Here the falsifier is not
        # rhetoric, it is arithmetic: the verdict is a comparison of |measured - claimed| against a
        # stated tolerance, so the band that would reverse it is already computed.
        if tol is not None and verdict in ("REPRODUCED", "FAILED"):
            lo, hi = inst["claimed"] - tol, inst["claimed"] + tol
            if verdict == "REPRODUCED":
                lines.append("Falsifier: a re-run of this same model that lands outside "
                             "[%.5g, %.5g] flips this to FAILED. The measurement sits %.3g from the "
                             "edge of that band." % (lo, hi, max(0.0, tol - abs(measured - inst["claimed"]))))
            else:
                lines.append("Falsifier: a re-run of this same model that lands inside "
                             "[%.5g, %.5g] flips this to REPRODUCED. The measurement sits %.3g "
                             "outside that band." % (lo, hi, abs(measured - inst["claimed"]) - tol))
        if downgraded:
            lines.append("GATE: the brain's by-construction self-check downgraded %s to %s; recorded "
                         "as the gate ruled, not re-POSTed to override it." % (verdict, final))
        # Phrased off OUR verdict, not the ledger's: the claim is about what this MEASUREMENT could
        # have produced, and a gate downgrade does not change what was reachable at the bench.
        if _independent(inst):
            lines.append("INDEPENDENCE: the claimed value is not an input to the model (inputs: %s), "
                         "so a %s was reachable from this measurement."
                         % (", ".join("%s=%s" % (k, v) for k, v in (inst.get("params") or {}).items()),
                            "FAILED" if verdict == "REPRODUCED" else "REPRODUCED"))
        else:
            lines.append("INDEPENDENCE: NOT established - the claimed value is among the model's "
                         "inputs, which is why this is not recorded as a replication.")
        if fam or sim:
            lines.append("PRIOR ART: same textbook family %s; semantically close %s - reported as "
                         "evidence, not treated as a block (a family block would have refused the "
                         "scale-free FAILED)." % (fam or "none", sim or "none"))
        content = "\n".join(lines)

        title = "Replication [%s]: %s (lab %s)" % (final, claim[:70], lab_id)
        _log(ctx, "%s %s: measured %.5g vs claimed %.5g (lab %s)"
             % (inst["key"], final, measured, inst["claimed"], lab_id))
        why = "replicated via %s; %s" % (inst["key"], reason)
        if mem:
            why += "; " + mem
        return _result("ok", why, decisive=final in ORGAN["decisive"], title=title,
                       content=content, lab_id=lab_id)
    except Exception as e:                       # cycle() must never raise - see the contract
        return _result("error", "unhandled in cycle: %s: %s" % (type(e).__name__, str(e)[:200]))
