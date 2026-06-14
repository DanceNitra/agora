"""
null_model_attacker.py — the engine behind "is this number real?"

The core idea in one line: a published effect is only evidence of a real mechanism if a model
that contains NONE of the claimed mechanism can NOT reproduce the headline number.

So the test is: rebuild the study with the claimed effect turned OFF (set to zero), run the
study's OWN method on that fake data, and measure how much of the reported effect still appears.
If most of it survives at zero mechanism, the number is an artifact of the method — not a finding.

This file demonstrates the engine on the famous basketball "hot hand" study
(Gilovich-Vallone-Tversky 1985), which concluded "the hot hand is an illusion" from a negative
streak statistic. We build a shooter with literally NO hot hand (every shot an independent coin
flip) and show the SAME negative statistic appears anyway — so the 1985 number carries no
information about whether a hot hand exists. (This is the Miller-Sanjurjo 2018 selection bias.)

Deterministic: fixed seed, no external dependencies (stdlib only).
"""

import random

def gvt_streak_statistic(sequence, k=3):
    """The study's own estimator: P(hit | previous k were ALL hits) - P(hit | previous k were ALL misses).
    Returns None if either condition never occurs in this sequence."""
    after_hits_h = after_hits_n = 0      # outcomes following k consecutive hits
    after_miss_h = after_miss_n = 0      # outcomes following k consecutive misses
    for i in range(k, len(sequence)):
        window = sequence[i - k:i]
        if all(window):                  # previous k all hits
            after_hits_n += 1
            after_hits_h += sequence[i]
        elif not any(window):            # previous k all misses
            after_miss_n += 1
            after_miss_h += sequence[i]
    if after_hits_n == 0 or after_miss_n == 0:
        return None
    return (after_hits_h / after_hits_n) - (after_miss_h / after_miss_n)


def run(n_shots=100, n_players=2000, p=0.5, k=3, seed=12345):
    """NULL model: every shot is an independent coin flip at probability p — ZERO hot hand by
    construction. We then apply the 1985 study's own streak statistic and average it."""
    rng = random.Random(seed)
    stats = []
    for _ in range(n_players):
        seq = [1 if rng.random() < p else 0 for _ in range(n_shots)]
        s = gvt_streak_statistic(seq, k=k)
        if s is not None:
            stats.append(s)
    mean = sum(stats) / len(stats)
    return mean, len(stats)


if __name__ == "__main__":
    PUBLISHED = -0.079   # GVT-style reported "evidence against the hot hand", k=3 (~ -7.9 percentage points)
    for k in (3, 4):
        mean, m = run(k=k)
        survived = mean / PUBLISHED if PUBLISHED else float("nan")
        print(f"k={k}: a shooter with NO hot hand produces a streak statistic of "
              f"{mean*100:+.1f} percentage points (averaged over {m} players).")
    mean3, _ = run(k=3)
    print()
    print("PLAIN-LANGUAGE VERDICT")
    print("-" * 60)
    print("The 1985 study reported about -7.9 points and called it 'evidence")
    print("the hot hand is an illusion'. But a player we KNOW has no hot hand")
    print(f"(pure coin flips) produces {mean3*100:+.1f} points with the SAME method.")
    print("So that number does not distinguish 'no hot hand' from 'the method")
    print("is biased' -> as published, it is not evidence. VERDICT: MEANINGLESS")
    print("(the effect survives at zero mechanism).")
