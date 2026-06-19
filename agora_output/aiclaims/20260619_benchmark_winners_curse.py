"""
AI-Claim Crucible #2 — "The leaderboard winner's score is a reliable estimate of its true performance."
========================================================================================================
Claim (universal benchmarking practice): you evaluate N models/configs on a benchmark, the top scorer wins,
and you report ITS score as that model's performance + treat the winner as the truly-best model.
Counter (winner's curse / selection-on-the-max; the regression-to-the-mean of leaderboards): the reported
best-OBSERVED score systematically OVERSTATES the winner's true score, the gap GROWS with the number of
candidates and the eval noise, and the observed winner is often NOT the truly-best model.

Clean, DETERMINISTIC computational model (no LLM stochasticity — the lesson from entry #1): N models with
true accuracies clustered within sigma_true; each measured with eval noise sigma_eval (finite test set +
run-to-run variance). Pick argmax(observed). Measure (a) inflation = observed_winner - true_winner;
(b) regret = true_best - true_winner (did we even pick the best?); (c) P(observed winner == true best),
as a function of N and sigma_eval. Verdict FAILED if the reported score is biased upward and the winner is
frequently not the true best at realistic settings.
"""
import numpy as np

RNG = np.random.default_rng(0)


def trial(N, sigma_true, sigma_eval, reps=40000):
    rng = RNG
    true = rng.normal(0.70, sigma_true, size=(reps, N))      # true accuracies, clustered (top models are close)
    obs = true + rng.normal(0.0, sigma_eval, size=(reps, N))  # finite-test-set + run-to-run eval noise
    win = obs.argmax(axis=1)
    r = np.arange(reps)
    true_win = true[r, win]
    obs_win = obs[r, win]
    true_best = true.max(axis=1)
    inflation = float(np.mean(obs_win - true_win))            # winner's-curse upward bias of the reported score
    regret = float(np.mean(true_best - true_win))             # how much true accuracy you lose by trusting the obs-winner
    p_true_best = float(np.mean(np.isclose(true_win, true_best)))
    return inflation, regret, p_true_best


# eval noise grounded in benchmark reality: binomial SE = sqrt(p(1-p)/T) for a T-item benchmark.
for T in (1000, 200, 50):
    print(f"  benchmark eval-noise SE for T={T} items at p=0.70: {np.sqrt(0.70*0.30/T):.3f}")
print()

sigma_true = 0.04          # top models cluster within ~4% true accuracy (realistic for a crowded leaderboard)
print(f"=== Winner's curse on a leaderboard (true-accuracy spread sigma_true={sigma_true}) ===")
print(f"  {'N models':>9} {'eval_SE':>8} {'inflation':>10} {'regret':>8} {'P(picked true best)':>20}")
worst = None
for N in (5, 20, 50, 100):
    for se in (0.03, 0.06):
        infl, reg, pbest = trial(N, sigma_true, se)
        print(f"  {N:>9} {se:>8.2f} {infl:>+10.3f} {reg:>+8.3f} {pbest:>19.1%}")
        if worst is None or pbest < worst[4]:
            worst = (N, se, infl, reg, pbest)

# headline at a very realistic crowded-leaderboard setting
infl, reg, pbest = trial(50, sigma_true, 0.06)
print(f"\nMEASURED: at N=50 models, true spread {sigma_true}, eval-noise SE 0.06 (~ a 50-200 item benchmark): "
      f"the reported winner's score is inflated by {infl:+.3f} (winner's curse); the 'winner' is the truly-best "
      f"model only {pbest:.0%} of the time; trusting it costs {reg:.3f} true accuracy vs the real best.")

print()
if infl > 0.01 and pbest < 0.7:
    print("VERDICT: FAILED. The leaderboard winner's reported score is a BIASED (upward) estimate of its true "
          "performance, and the observed winner is frequently NOT the truly-best model — both effects grow with "
          "the number of candidates and the eval noise. 'Report the top scorer's number as its performance' is "
          "winner's curse: the SOTA bar is systematically overstated. (Deterministic model; no LLM noise — "
          "exactly the clean computational core that the multi-vs-single claim lacked.)")
else:
    print("VERDICT: REPRODUCED — the reported winner's score is unbiased and the winner is the true best.")
