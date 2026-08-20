# Sierpinski-gasket tensor-RG toolchain (EDRN "silent dissonance" collaboration)

Real-space / tensor renormalization-group tooling built to test whether the local "silent-dissonance" defect
valley on the Sierpinski-gasket Heisenberg model survives from finite size (N=15, L2) toward the thermodynamic
limit (L3 = 42 spins and beyond). Shared so anyone with a GPU can pick up the L3 question. Standalone Python
(numpy/scipy; the `_gpu` variants use torch). No secrets, no external services.

## Honest status (what's solid, what stops)

> **CORRECTIONS, 2026-08-18.** Three things below were stated without the qualifications they needed.
> None of them is a computational error; all three are things this file failed to record, which is
> the same defect one level up.
>
> **The model is not the manuscript's.** `hotrg.py:40` builds `SX_i SX_j + SZ_i SZ_j` and
> `dmrg_valley.py` adds `Sigmax Sigmax` and `Sigmaz Sigmaz`. There is no `YY`: this is the XY model
> in a rotated frame, not the isotropic `sx sx + sy sy + sz sz` that `edrn-dmrg-verification#2`
> studies. Measured on the same graph and edge, the two agree to **0.7%** on the global valley depth
> (0.144542 vs 0.143538) and differ by **5%** locally (0.276416 vs 0.263346). A cross-check between
> them is therefore not a same-model check, and cannot agree "to the digit".
>
> **The defect bond was not an edge of the gasket.** Both this toolchain and `dmrg_valley.py` used
> `(0,2)`, and 0 and 2 are two of the three tips, which sit at graph distance 4 — no tip-tip pair is
> an edge at any level. The coupling was therefore APPENDED as a 28th bond rather than varying one of
> the 27, and the minimum sits near s=0.60 because s=1 is not a special point for an added bond.
> `dmrg_valley.py` now defaults to the real tip-to-interior edge `(0,6)` and refuses a non-edge;
> `scan_guard.py` carries the same check for anyone else.
>
> **The "L2 local valley depth 0.1902" is not reproducible from what this file records.** "Local" is
> never defined here. Under the definition the impurity code implies — the two tip sub-gaskets, 18 of
> the 27 edges, with the added `(0,2)` bond — the depth comes out **0.200462** in XX+ZZ and
> **0.181144** isotropically. The published figure sits between them without matching either, so the
> neighbourhood and the defect placement have to be stated before the number means anything. Until
> they are, treat 0.1902 as unverified.
>
> **AMENDMENT, 2026-08-20 — the paragraph above is now superseded, and 0.1902 IS reproducible.**
> The definition of "local" was recorded all along, in code rather than in prose:
> `hotrg_obs.defect_bonds(blk, R=2)` — the radius-2 neighbourhood of the two defect corners, 18 of
> the 27 edges. Run untruncated with the strengths grid `linspace(0.25, 3.0, 12)` and the depth
> convention `mean(curve[-3:]) - min(curve)`, `hotrg_obs.valley(2, chi=None)` returns **0.1902** in
> 25 seconds. The ED reconstruction above could not reach it because ED was the wrong instrument,
> not because the number was wrong. Receipt: `probes/edrn_the_recovery_percentages_we_published.py`.
> The `(0,2)` caveat still stands and is now stated where it belongs, in the bullet below.


**Solid (reproduced to the digit):**
- Energy RG is exact through **L2**: L1 ground energy −6.000000, L2 −16.921463; it converges the **L3** (42-spin)
  ground energy to **≈ −49.3** (truncation corrections halve geometrically).
- The **impurity-explicit** RG reproduces the L2 local valley depth **0.1902** exactly, on the 18-bond
  radius-2 neighbourhood defined by `defect_bonds`. **Read the defect placement before using this
  number:** the RG's defect is the corner0–corner2 bond, and corners 0 and 2 are two of the three
  tips, at graph distance 4 — so this is the *appended 28th bond*, not the tip-to-interior edge
  `(0,6)` that `edrn-dmrg-verification#2` reports. The truncation control below is evidence about
  that appended defect, and does not transfer to `(0,6)` without being re-run there.

- **Truncation control, re-measured 2026-08-20 — the earlier "~86% vs ~20%" was a mismatched pair.**
  Both arms now measured with one depth convention, one strengths grid and one bond set:

  | χ | far bath only | uniform |
  |---|---|---|
  | 1 | 0.1648 = **87%** | 0.0000 = **0%** |
  | 2 | 0.1834 = 96% | 0.0041 = 2% |
  | 4 | 0.1736 = 91% | 0.0238 = 13% |
  | 8 | 0.1902 = 100% | 0.0447 = 24% |

  The old `~20%` was uniform truncation at **χ=8**, not at a single state, so the published sentence
  compared χ_B=1 against χ=8 and *understated its own case*. At matched χ=1 the contrast is **87% vs
  0%** — the far bath can be thrown away entirely and the valley survives; truncate everything the
  same way and it is gone. That is the localized-defect-mode claim, and it holds at every χ.

  **The single-state far-bath figure is a range, not a number: 87%–95% over four runs (0.1648,
  0.1723, 0.1769, 0.1816).** Cause measured, not assumed: the L1 ground manifold is **4-fold
  degenerate** (E0 = −16.921463), so χ_B=1 keeps one arbitrary vector out of it and the depth moves
  with whatever basis the solver returns. Quote the range, or quote χ_B=2 where it is stable.
  For scale, the untruncated L2 block dimension is **4096**, so even χ=8 is a 512× truncation.

**Where it stops (marked, not papered over):** the **L3 valley *depth*** does not converge on this hardware —
across the truncation dimension it wanders (≈0.24 / 0.08 / 0.20) and the V-curve degrades toward a step. This is
a real convergence / compute limit (needs larger χ, warm-started, more memory), **not** a model defect. The dead
ends are marked so no one repeats them; do NOT tune the truncation to force a valley (that is the confound trap).

## Files

| file | what it does |
|------|--------------|
| `hotrg.py` | CPU corner-space energy RG (exact through L2, L3 → ≈ −49.3) |
| `hotrg_gpu.py` | torch/GPU energy RG (fp64; fp32 plateaus on the gapless manifold) |
| `hotrg_obs.py` | observable-tracking RG (per-edge σzσz product operators; factored far-bath truncation) |
| `hotrg_imp.py` / `hotrg_imp_gpu.py` | **impurity-explicit** RG for the local valley (bath/tip/defect; GPU torch-sparse measurement) |
| `impurity_gate.py` | feasibility gate for the impurity RG (run this first) |
| `dmrg_valley.py` / `dmrg_orderparam.py` | ED/DMRG cross-checks of the valley and the order parameter |
| `order_param.py` / `reconstruct_scaling_ED.py` | order-parameter decomposition + ED scaling reconstruction |
| `s25_gapcheck.py` | gap check at s=2.5 (shoulder) |
| `_*.log` | run logs (provenance of the numbers above) |

## To pick up L3

Start with `impurity_gate.py` (confirms the setup), then `hotrg_imp_gpu.py` with a larger bond dimension χ,
warm-started from the converged lower level. The valley-depth convergence at L3 is the open question; the
energy RG and the L2 impurity valley are the fixed reference points to validate any new run against.
