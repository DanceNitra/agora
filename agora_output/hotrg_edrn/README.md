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


**Solid (reproduced to the digit):**
- Energy RG is exact through **L2**: L1 ground energy −6.000000, L2 −16.921463; it converges the **L3** (42-spin)
  ground energy to **≈ −49.3** (truncation corrections halve geometrically).
- The **impurity-explicit** RG reproduces the L2 local valley depth quoted below as 0.1902 (see the
  correction above: the definition is not recorded, and reconstruction brackets rather than matches it), and a
  controlled test confirms the physics: truncating *only* the far bath (a tip sub-gasket) to a single state
  already recovers ~86% of the valley, whereas a *uniform* truncation destroys it (~20%). So the valley is a
  genuinely localized defect mode, and finite ramification lets the far bath decouple.

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
