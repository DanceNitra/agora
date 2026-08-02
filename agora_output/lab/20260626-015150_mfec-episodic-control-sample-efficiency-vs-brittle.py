"""
Replication: "Sample-Efficient RL with Maximum Entropy Mellowmax Episodic Control"
(Sarrico, Arulkumaran, Agostinelli et al.) — smallest model of the paper's CORE mechanism.

CLAIM (mechanism under test): a non-parametric EPISODIC memory that stores the MAX observed
discounted return per (state,action) (Model-Free Episodic Control, Blundell 2016) assigns credit
in ONE shot and therefore learns a good policy from far FEWER goal-reaching experiences than an
incremental parametric value learner (tabular Q-learning here standing in for the slow deep value
net, which must bootstrap credit back one TD step at a time). That is the "sample efficiency".

DESIGN — exploration is HELD IDENTICAL so we isolate CREDIT ASSIGNMENT, not exploration luck:
both learners are fed the EXACT SAME uniform-random trajectories (off-policy). The only difference
is how each USES the data: EC = max-return memory; QL = one-step TD bootstrap. A small step cost
makes the optimal policy the shortest path and gives a clean value gap.

PRE-COMMITTED FALSIFIERS (written before running):
  F1 (sample-efficiency): on identical data, if Episodic Control's greedy policy does NOT become
     goal-reaching in fewer episodes (median over seeds) than Q-learning for EVERY chain length,
     the credit-assignment sample-efficiency mechanism FAILS to replicate.
  F1b (widening): the credit-assignment gap (QL_episodes - EC_episodes) should GROW with chain
     length N (TD must propagate over more steps). If it does not grow, the mechanism is weaker
     than claimed.
  F2 (brittleness corollary): the SAME max-return rule should overestimate under stochastic
     rewards. On a risky-vs-safe choice where the risky arm has the LOWER mean but a HIGHER max,
     if Episodic Control does NOT pick the worse arm more often than averaging Q-learning, then
     "max-return memory is brittle to noise" is FALSE (EC would be unconditionally dominant).

Pure-numpy, CPU, cloud-free. No LLM.
"""
import numpy as np

GAMMA = 0.99
STEP_COST = -0.02   # makes shortest path optimal + a clean value gap


# ----------------------------- Agents -----------------------------
class QLearner:
    name = "Q-learning (one-step TD bootstrap / parametric stand-in)"

    def reset(self, n_states):
        self.Q = np.zeros((n_states, 2))
        self.alpha = 0.5

    def update(self, traj):
        for (s, a, r, ns, done) in traj:
            target = r + (0.0 if done else GAMMA * np.max(self.Q[ns]))
            self.Q[s, a] += self.alpha * (target - self.Q[s, a])

    def greedy(self, s):
        # tie / unseen (both 0) -> argmax picks left(0); a clamped-left at start counts as unsolved
        return int(np.argmax(self.Q[s]))


class EpisodicControl:
    name = "Episodic Control (max-return memory / MFEC)"

    def reset(self, n_states):
        self.Q = np.full((n_states, 2), -np.inf)

    def _vals(self, s):
        return np.where(np.isfinite(self.Q[s]), self.Q[s], -1e9)

    def update(self, traj):
        G = 0.0
        for (s, a, r, ns, done) in reversed(traj):
            G = r + GAMMA * G
            if G > self.Q[s, a]:
                self.Q[s, a] = G  # MAX over observed returns (one-shot credit)

    def greedy(self, s):
        return int(np.argmax(self._vals(s)))


# --------------------- Exp A: shared-trajectory chain ---------------------
def chain_step(s, a, N):
    ns = s + 1 if a == 1 else s - 1
    ns = max(0, min(N - 1, ns))
    done = (ns == N - 1)
    r = 1.0 if done else STEP_COST
    return ns, r, done


def greedy_solves(agent, N):
    s = 0
    for _ in range(4 * N):
        a = agent.greedy(s)
        ns = s + 1 if a == 1 else s - 1
        ns = max(0, min(N - 1, ns))
        if ns == N - 1:
            return True
        if ns == s:      # clamped & stuck (greedy left at state 0) -> undecided
            return False
        s = ns
    return False


def episodes_to_solve_shared(N, episodes=250, seeds=12, horizon=300):
    ec_hits, ql_hits = [], []
    for seed in range(seeds):
        rng = np.random.default_rng(1000 + seed)
        ec, ql = EpisodicControl(), QLearner()
        ec.reset(N); ql.reset(N)
        ec_hit = ql_hit = episodes  # censored
        for ep in range(episodes):
            # ONE shared uniform-random trajectory, given to BOTH learners
            traj = []
            s = 0
            for _ in range(horizon):
                a = int(rng.integers(2))
                ns, r, done = chain_step(s, a, N)
                traj.append((s, a, r, ns, done))
                s = ns
                if done:
                    break
            ec.update(traj); ql.update(traj)
            if ec_hit == episodes and greedy_solves(ec, N):
                ec_hit = ep + 1
            if ql_hit == episodes and greedy_solves(ql, N):
                ql_hit = ep + 1
            if ec_hit < episodes and ql_hit < episodes:
                break
        ec_hits.append(ec_hit); ql_hits.append(ql_hit)
    return np.array(ec_hits), np.array(ql_hits)


# --------------------- Exp B: risky-vs-safe (stochastic reward) ---------------------
def risky_safe(agent_cls, episodes=400, seeds=200, h=3.0, p_high=0.2, eps=0.25):
    safe_mean = 1.0
    risky_mean = p_high * h
    correct = 0
    for seed in range(seeds):
        rng = np.random.default_rng(7000 + seed)
        ag = agent_cls(); ag.reset(1)
        for _ in range(episodes):
            # forced balanced exploration so EC reliably observes the risky max
            a = int(rng.integers(2)) if rng.random() < eps else ag.greedy(0)
            r = safe_mean if a == 0 else (h if rng.random() < p_high else 0.0)
            ag.update([(0, a, r, 0, True)])
        if ag.greedy(0) == 0:  # picked SAFE = correct
            correct += 1
    return correct / seeds, safe_mean, risky_mean


# ----------------------------- Run -----------------------------
print("=== Exp A: identical random data, EC vs QL — episodes until greedy policy reaches goal ===")
print("(exploration held identical; difference is credit assignment only)")
print(f"{'N':>4} | {'EC (med [IQR])':>18} | {'QL (med [IQR])':>18} | {'gap(QL-EC)':>10} | {'speedup':>8}")
rows = []
for N in (6, 10, 14):
    ec, ql = episodes_to_solve_shared(N)
    mec, mql = np.median(ec), np.median(ql)
    gap = mql - mec
    spd = mql / max(mec, 1e-9)
    rows.append((N, mec, mql, gap, spd))
    print(f"{N:>4} | {mec:5.0f} [{np.percentile(ec,25):.0f},{np.percentile(ec,75):.0f}]"
          f"      | {mql:5.0f} [{np.percentile(ql,25):.0f},{np.percentile(ql,75):.0f}]"
          f"      | {gap:10.0f} | {spd:7.1f}x")

f1_core = all(r[1] < r[2] for r in rows)
gaps = [r[3] for r in rows]
f1_widen = gaps[-1] > gaps[0]
print(f"\ncredit-assignment gap by N: {[int(g) for g in gaps]}  -> widens with N: {f1_widen}")
print(f"F1 (EC fewer episodes, all N): {f1_core}   F1b (gap widens with N): {f1_widen}")

print("\n=== Exp B: risky-vs-safe — correct-arm (SAFE) selection rate over seeds ===")
ec_corr, sm, rm = risky_safe(EpisodicControl)
ql_corr, _, _ = risky_safe(QLearner)
print(f"safe mean={sm}, risky mean={rm:.2f} (risky max=3.0); correct = SAFE")
print(f"Episodic Control picks SAFE (correct): {ec_corr:.0%}   -> wrong {1-ec_corr:.0%}")
print(f"Q-learning      picks SAFE (correct): {ql_corr:.0%}   -> wrong {1-ql_corr:.0%}")
f2 = (1 - ec_corr) > (1 - ql_corr)
print(f"F2 (max-return brittle under noise) CONFIRMED: {f2}")

print("\n=== VERDICT ===")
if f1_core and f2:
    print("REPRODUCED (regime-specific). Episodic memory's one-shot max-return credit assignment is "
          f"sample-efficient on identical data (EC reaches a good policy ~{rows[-1][4]:.0f}x faster at "
          f"N={rows[-1][0]}; the gap {'widens' if f1_widen else 'does not widen'} with horizon), but the "
          "SAME max-return rule is brittle under stochastic rewards: it systematically prefers the "
          f"high-variance WORSE arm ({1-ec_corr:.0%} wrong vs QL {1-ql_corr:.0%}). Speed and value-"
          "correctness trade off — consistent with the known max-operator overestimation (van Hasselt 2010).")
elif f1_core:
    print("REPRODUCED: sample-efficiency holds on identical data; F2 brittleness did not trigger.")
else:
    print("FAILED: on identical data, episodic max-return credit assignment was NOT more "
          "sample-efficient than one-step TD.")
