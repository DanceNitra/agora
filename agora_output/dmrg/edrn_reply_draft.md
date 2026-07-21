@luoxuejian000 @maratsultanov2 @qingkong66

Both open items are done. Here is what I ran, what it changed, and what it did not.

## 1. The C normalization — settled from your own two scripts, not from my judgement

You asked me to decide. I would rather show you the line, because the answer was already in the
repository and neither of us had to guess.

Both scripts use the same formula:

    C = (Omega * edge_count) / (L * (L - 1) / 2)

They differ in how Omega is accumulated:

    predict1_topology_spin.py   bond = |<Cu Cdu>| + |<Cd Cdd>|            # SUM of the two spin channels
    game1_defect_scan.py:72     omega_sum += (bond_up + bond_dn) / 2.0    # MEAN of the two channels
    menu2_periodic.py:88        omega_sum += (bond_up + bond_dn) / 2.0    # MEAN, same as the scan

That single `/ 2.0` is the factor of two, and it is the whole of the apparent "48% drop": the open
chain was reported in the SUM convention and the ring in the MEAN convention, so a ring with one MORE
bond than the open chain appeared to have half the connectivity.

The check that settles it needs no new computation, only data we both already hold. The defect scan at
strength 1.0 **is** the uniform L=40 chain — no defect at all. It reports C = 0.479442. Twice that is
0.958884. `data/predict1_topology_spin.csv` at L=40 reports 0.9588847979. Identical to seven digits.

So: **the SUM convention throughout the paper.** Every C in the defect scan doubles. Nothing about the
physics changes; one convention replaces two.

## 2. The defect scan now carries a convergence check on every point

You asked whether I had the time. The machine was already warm, so here it is: all ten points of the
scan (L = 40 and L = 60), each at chi = 100, 200, 300, 400, in both sectors — 80 DMRG runs. Energies
extrapolated linearly in the discarded weight to dw -> 0, gaps rebuilt from extrapolated energies only,
A = gap * L. This is the same estimator as `u05_analysis.py` and the periodic-ring run, so the paper now
uses one method for every convergence statement it makes.

**Control first.** Before trusting any of it, our chi = 100 has to land on yours, or the two codes are
not running the same system:

| | A at chi = 100, L = 40, defect 0.5 |
|---|---|
| your published value | 5.469862 |
| our independent run | 5.469865 |

Agreement to six significant figures, from independent code. Everything below is therefore directly
comparable to your table.

**Result:**

| L | defect | A (chi=100) | A (dw->0) | shift | C published | C consistent |
|---|---|---|---|---|---|---|
| 40 | 0.5t | 5.469862 | 5.468911 | -0.0% | 0.475369 | 0.950738 |
| 40 | 0.8t | 4.366600 | 4.365966 | -0.0% | 0.478021 | 0.956042 |
| 40 | 1.0t | 3.066727 | 3.066952 | +0.0% | 0.479442 | 0.958884 |
| 40 | 1.2t | 1.910170 | 1.911226 | +0.1% | 0.480129 | 0.960258 |
| 40 | 1.5t | 0.965498 | 0.967034 | +0.2% | 0.480227 | 0.960454 |
| 60 | 0.5t | 5.738530 | 5.731919 | -0.1% | 0.479309 | 0.958618 |
| 60 | 0.8t | 4.642328 | 4.638317 | -0.1% | 0.481096 | 0.962192 |
| 60 | 1.0t | 3.139223 | 3.140287 | +0.0% | 0.482060 | 0.964120 |
| 60 | 1.2t | 1.801868 | 1.807700 | +0.3% | 0.482524 | 0.965048 |
| 60 | 1.5t | 0.827740 | 0.836125 | +1.0% | 0.482635 | 0.965270 |

**The scan was already converged.** The largest chi = 100 bias anywhere in it is 1.0%, at L = 60,
1.5t, and eight of the ten points move by 0.3% or less. This is a real
difference from the periodic ring, and it has a physical reason rather than a lucky one: on a ring the
wrap bond is long-range for the MPS, so chi_PBC ~ chi_OBC^2 and chi = 100 is nowhere near enough — which
is why that point moved from A = 0.47 to A = 3.19. An open chain has no such bond. Your instinct that
the scan was sound was right; it is now demonstrated rather than assumed.

**And the conclusion of Prediction 1 survives on converged numbers.** On the extrapolated values A
moves by a factor of 5.66 at L = 40 and 6.86 at L = 60, while C in the consistent normalization
spreads by 1.02% and 0.69% respectively. That is the A-C decoupling, now resting on ten points that
each carry a convergence check instead of ten single-chi values.

I want to be precise about what this does and does not buy. It does not make the claim stronger — the
numbers barely moved, which is the point. It removes an objection a referee would have raised, and it
means no number in the manuscript now rests on an unchecked chi = 100 run.

## 3. One row in the table had no data file behind it — and it turned out to be right

While setting the grid up I noticed the manuscript's L = 40, 0.8t row (Delta_s = 0.109164, A = 4.3666,
C = 0.478021) is not in any committed CSV. `data/game1_log.csv` holds only 0.5, 1.0, 1.2 and 1.5, and
the single L = 40 / 0.8 record anywhere in the repository is the root `game1_log.csv`:

    L,U,defect,delta_s,A,C
    40,4.0,0.8,0.0000000065,0.000000,0.9588848000

which is a run that failed to resolve the two spin sectors: Delta_s ~ 6.5e-9, A = 0.

Rather than ask you where the number came from, I computed it. Our independent extrapolation gives
**A = 4.365966** against the manuscript's **4.3666** — a difference of 0.014%.

So the row was correct all along; what was missing was its file, almost certainly a good run whose CSV
was never committed. It now has one: the eight raw cells behind that value are in the repository with
the other seventy-two. I mention it only because a referee who diffs the tables against the data
directory would have found the same gap, and now there is nothing to find.

## 4. Marat's two files

Marat, thank you — both settled as you asked. The CERN data is out of the paper, and the U = 2 spin gap
table stays on our own DMRG run. Nothing further is open on your side.

## 5. What I have done with it, and the sign-off

Nothing is open on your side. You both handed these decisions to me, so I have made them rather than
pass them back:

- Every C in the defect-scan tables is restated in the SUM convention, so the paper uses one
  definition throughout. This also fixes a contradiction that was already there: Table 4's caption
  gives the uniform open-chain baseline as C = 0.958885 while its own 1.0t row — which IS that
  uniform chain — reads 0.479442. One convention removes it.
- The convergence data goes in as a new short appendix table rather than as extra columns, so the
  main tables stay readable. If you would rather have it inline, say so and I will move it — but do
  not hold the submission for that.
- The regenerated LaTeX, both scripts and all 80 raw cells are pushed, so nobody has to open
  Overleaf again.

With that, **the manuscript is technically signed off from my side.** Guanghao, it is ready to submit
whenever you are.

Everything above is already pushed and reproducible:
https://github.com/DanceNitra/edrn-appendix-fix

- `scripts/defect_scan_chi_sweep.py` runs the grid
- `scripts/defect_scan_analysis.py` does the extrapolation and prints the table above
- `cells_defect_scan/` holds all 80 raw DMRG cells, so anyone can redo the fit without running a
  single sweep
- `scripts/edrn_fix_tables.py` applies the C convention and refuses to run if the result would not
  match `predict1_topology_spin.csv`
- `appendix_defect_convergence.tex` is the new appendix table, and `paper_full.pdf` is recompiled
  with everything in place

Separately, Guanghao — I have read your PXP letter and the "silent detuning" result. I will not mix it
into a submission thread; I will reply on it properly once this paper is signed. Two things I can say
now: reporting five negative results before the positive one is the right way round, and the caveat you
listed first, that you have only L = 18, is the one I would attack first as well.

— R. Drahos
