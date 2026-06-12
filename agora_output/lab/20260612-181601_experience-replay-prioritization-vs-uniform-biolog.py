"""
Deepen [1b915ef9]: is experience replay in RL a REAL shared mechanism with biological memory
consolidation (prioritized hippocampal reactivation during non-REM sleep), or a false friend?

The honest, testable core: biological consolidation is theorized to PRIORITIZE reactivation of
SALIENT (high-reward / surprising) experiences, not replay uniformly. If the computational benefit
of replay shares that mechanism, then PRIORITIZED replay (by reward magnitude / TD-error) should beat
UNIFORM replay — and, per our Operating-Point thesis, the advantage should be LARGEST exactly when
high-value experiences are RARE (the stressed regime), because that is when uniform sampling almost
never revisits them. A surface analogy would predict no such structured, stress-coupled gap.

Minimal model: a chain MDP where one rare transition carries a large reward. Tabular Q-learning with a
replay buffer; compare UNIFORM vs PRIORITIZED (sample ∝ |reward| + small eps) replay. Vary the rarity
of the high-value transition and measure sample-efficiency (updates to learn the optimal action).
"""
import numpy as np

rng = np.random.default_rng(20260612)

N_STATES = 8
GOAL_REWARD = 10.0
GAMMA = 0.95
ALPHA = 0.4
BUFFER = 2000
REPLAY_PER_STEP = 8


def run(prioritized: bool, rarity: float, steps: int = 6000) -> int:
    """rarity = probability that an episode even visits the high-reward terminal transition.
    Returns the step at which the optimal first action is reliably learned (or steps if never)."""
    Q = np.zeros((N_STATES, 2))            # 2 actions
    buf = []                                # (s,a,r,s2)
    learned_at = steps
    correct_streak = 0
    for t in range(steps):
        # generate one transition: action 1 from state 0 leads toward the goal chain
        s = rng.integers(0, N_STATES)
        a = rng.integers(0, 2)
        # the high-value transition: reaching the goal is rare (gated by `rarity`)
        if s == N_STATES - 2 and a == 1 and rng.random() < rarity:
            r, s2 = GOAL_REWARD, N_STATES - 1
        elif a == 1:
            r, s2 = 0.0, min(s + 1, N_STATES - 1)
        else:
            r, s2 = 0.0, max(s - 1, 0)
        buf.append((s, a, r, s2))
        if len(buf) > BUFFER:
            buf.pop(0)
        # replay
        if len(buf) >= REPLAY_PER_STEP:
            if prioritized:
                w = np.array([abs(x[2]) + 0.05 for x in buf])
                idx = rng.choice(len(buf), REPLAY_PER_STEP, p=w / w.sum())
            else:
                idx = rng.choice(len(buf), REPLAY_PER_STEP)
            for i in idx:
                s_, a_, r_, s2_ = buf[i]
                Q[s_, a_] += ALPHA * (r_ + GAMMA * Q[s2_].max() - Q[s_, a_])
        # has it learned that action 1 is better near the goal?
        if Q[N_STATES - 2, 1] > Q[N_STATES - 2, 0] + 0.5:
            correct_streak += 1
            if correct_streak >= 50 and learned_at == steps:
                learned_at = t
        else:
            correct_streak = 0
    return learned_at


print("=== Experience replay: uniform vs prioritized, as the high-value transition gets RARER ===")
print(f"{'rarity':>8} {'uniform steps':>14} {'prioritized steps':>18} {'speedup':>9}")
results = []
for rarity in [0.5, 0.2, 0.08, 0.03]:
    u = np.mean([run(False, rarity) for _ in range(6)])
    p = np.mean([run(True, rarity) for _ in range(6)])
    speed = u / max(p, 1)
    results.append((rarity, u, p, speed))
    print(f"{rarity:>8.2f} {u:>14.0f} {p:>18.0f} {speed:>8.2f}x")

print("\n=== Verdict ===")
# operating-point signature: prioritization speedup GROWS as the high-value transition gets rarer
speeds = [r[3] for r in results]
grows = speeds[-1] > speeds[0] + 0.3 and speeds[-1] > 1.3
if grows:
    print(f"REAL SHARED MECHANISM (structured, not surface): prioritized replay's advantage GROWS as")
    print(f"the salient experience gets rarer ({speeds[0]:.2f}x at rarity 0.5 -> {speeds[-1]:.2f}x at 0.03).")
    print("This is the same skeleton as biological prioritized reactivation of salient memories AND our")
    print("Operating-Point Trap: uniform sampling fails exactly when the high-value event is rare — the")
    print("regime where consolidation matters. The mapping is mechanistic at the level of value-")
    print("prioritized sampling under scarcity, not mere 'both reuse past data'.")
else:
    print(f"WEAK/SURFACE: prioritization speedup does not grow with rarity ({speeds[0]:.2f}->{speeds[-1]:.2f}x);")
    print("the replay<->consolidation link is a surface analogy at these parameters.")
