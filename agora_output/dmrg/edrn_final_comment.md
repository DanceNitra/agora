@luoxuejian000 @maratsultanov2 @qingkong66

**It is out.**

**https://doi.org/10.5281/zenodo.21473160**

*Systematic numerical study of the spin-gap prefactor in a one-dimensional Mott insulator: defect
response, boundary effect, and cross-sector conservation* — Li, Drahos, Sultanov. Open access, CC-BY,
PDF and LaTeX source both attached, and linked as the continuation of
[10.5281/zenodo.21393316](https://doi.org/10.5281/zenodo.21393316).

Guanghao, you wrote in July that priority should be fixed first and left the rest to us. That is done:
the timestamp exists, and it exists for all three of us.

Here is what changed in the manuscript before it went, so the record is complete.

## The C normalization

You asked me to decide, so I did — but the answer was already in your repository and neither of us had
to judge anything. Both scripts use the same formula; they differ in one line:

```
predict1_topology_spin.py   bond = |<Cu Cdu>| + |<Cd Cdd>|            # SUM of the two spin channels
game1_defect_scan.py:72     omega_sum += (bond_up + bond_dn) / 2.0    # MEAN of the two channels
menu2_periodic.py:88        omega_sum += (bond_up + bond_dn) / 2.0    # MEAN, same as the scan
```

That `/ 2.0` is the factor of two and the whole of the apparent "48% drop": the open chain was reported
as a SUM and the ring as a MEAN, so a ring with one *more* bond looked half as connected.

The check needs no computation, only data you already have: the defect scan at strength 1.0 **is** the
uniform L = 40 chain. It reports C = 0.479442; twice that is 0.958884; `predict1_topology_spin.csv` at
L = 40 reads 0.9588847979. Identical to seven digits.

Every C in the defect-scan tables is now in the SUM convention. This also removed a contradiction that
was already in the text: Table 4's caption gave the uniform baseline as C = 0.958885 while its own 1.0t
row — the same uniform chain — read 0.479442.

## Convergence on every point

All ten scan points, L = 40 and L = 60, at chi = 100, 200, 300, 400, both spin sectors: 80 DMRG runs,
energies extrapolated linearly in the discarded weight, gaps rebuilt from extrapolated energies only.
Same estimator as `u05_analysis.py` and the periodic ring, so the paper now uses one method everywhere.

Control first, because without it the rest is not comparable:

| | A at chi = 100, L = 40, defect 0.5 |
|---|---|
| your published value | 5.469862 |
| our independent run | 5.469865 |

| L | defect | A (chi=100) | A (dw→0) | shift |
|---|---|---|---|---|
| 40 | 0.5t | 5.469862 | 5.468911 | −0.0% |
| 40 | 0.8t | 4.366600 | 4.365966 | −0.0% |
| 40 | 1.0t | 3.066727 | 3.066952 | +0.0% |
| 40 | 1.2t | 1.910170 | 1.911226 | +0.1% |
| 40 | 1.5t | 0.965498 | 0.967034 | +0.2% |
| 60 | 0.5t | 5.738530 | 5.731919 | −0.1% |
| 60 | 0.8t | 4.642328 | 4.638317 | −0.1% |
| 60 | 1.0t | 3.139223 | 3.140287 | +0.0% |
| 60 | 1.2t | 1.801868 | 1.807700 | +0.3% |
| 60 | 1.5t | 0.827740 | 0.836125 | +1.0% |

**The scan was already converged.** Largest bias 1.0%, eight of ten points at 0.3% or less. That is a
real difference from the periodic ring, and it has a physical reason: on a ring the wrap bond is
long-range for an MPS, so chi = 100 is nowhere near enough, which is why that point moved from 0.47 to
3.19. An open chain has no such bond. Your instinct that the scan was sound was right — it is now
demonstrated instead of assumed.

And Prediction 1's conclusion holds on the converged numbers: A moves by a factor of 5.66 at L = 40 and
6.86 at L = 60, while C spreads by 1.02% and 0.69%. I want to be precise about what this bought us — it
does not make the claim stronger, since the numbers barely moved. It removes an objection a referee
would have raised, and no number in the paper now rests on an unchecked chi = 100 run.

## One row that had no data file

The L = 40, 0.8t row (A = 4.3666) was in no committed CSV; the only record for that point anywhere in
the repository is the root `game1_log.csv`, which reads `delta_s = 6.5e-9, A = 0.000000` — a run that
failed to resolve the two sectors.

Rather than ask where it came from, I computed it: **A = 4.365966** against your **4.3666**, 0.014%
apart. The row was right all along; only its file was missing, and now it has one. I mention it because
a referee diffing the tables against `data/` would have found the same gap, and now there is nothing to
find.

## Everything is public

**https://github.com/DanceNitra/edrn-appendix-fix**

`scripts/defect_scan_chi_sweep.py` runs the grid · `scripts/defect_scan_analysis.py` does the
extrapolation · `cells_defect_scan/` holds all 80 raw DMRG cells, so any table can be re-derived
without a single new sweep · `scripts/edrn_fix_tables.py` applies the C convention and refuses to run
unless the result matches `predict1_topology_spin.csv` · `appendix_defect_convergence.tex` is the new
appendix table · `paper_full.pdf` is recompiled with all of it in place.

## Thank you

Guanghao — four times I told you something in your own work was wrong, and four times you said "you are
right" and fixed it, in public, with the old version left visible. Most people cannot do that once. It
is the reason this paper is worth the DOI it now has: not because we were clever, but because nothing
was quietly buried. And you were the one who kept saying an honest failure is worth more than a false
success — the five negative results in your PXP letter are that same instinct, and they are why I will
take the sixth one seriously.

Marat — the TAT verification mattered most in the places where it stayed *silent*. A framework that
refuses to produce a signal on four points, and says so, is doing the hard part of science. Withdrawing
your own L = 40 transition claim when it turned out to be a four-point artifact was the same thing.

Qingkong — thank you for reading the whole way through and for the diagnosis of how this collaboration
was working. It was not a spectator's role.

From my side this is closed: the manuscript is technically signed off and the priority is fixed.

On what comes next — Guanghao, you suggested PRB, and I think that is the right target. I should be
straight that none of us has submitted to a journal before, so I would rather learn the mechanics
properly than improvise them: the format PRB expects, the cover letter, how three independent
researchers with no institutional affiliation are handled. Let me work that out and come back with
something concrete rather than a guess.

— R. Drahos
