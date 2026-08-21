"""Third correction pass: the truncation-control sentence, which is OURS, and which the second
pass left carrying three figures that no artifact in this repository produces.

WHAT WENT WRONG. The sign-off comment posted to the co-author on 20 August, and the manuscript
sentence built from it, state a "controlled version, at equal retained dimension (4096 states):
far-bath 86.6%, uniform 30.6%, a factor 2.8". Checked today:

  * `30.6%` appears in no receipt. The only persisted measurement of the uniform arm covers
    chi = 1, 2, 4, 8 and reports 0.0 / 0.0 / 11.1 / 24.5 percent.
  * The "equal retained dimension (4096 states)" framing does not reconstruct. Measured today,
    `build(2, chi=k)` retains exactly k states in the RG block, so a uniform arm at 4096 states
    is the UNTRUNCATED run, whose recovery is 100% by construction. The two schemes truncate
    different objects and cannot be equated by retained dimension at all.
  * `E_0 = -16.921463` is CORRECT -- measured today, dimension 32768, ground manifold four-fold --
    but it belongs to the three-block assembly from which L2 is built, not to the manuscript's
    L1 graph, whose ground energy the same paragraph gives as -9.000000. Two different objects
    were sharing one label in adjacent sentences.

WHAT THIS PASS DOES. Replaces the sentence with one whose every figure comes from
`probes/edrn_the_recovery_percentages_we_published.result.json` as re-run this cycle, quotes the
single-state figure as the range the receipt records rather than as a number, and states the
ordering -- which held at every chi in the run -- as the claim the test actually establishes.

The probe's own C5 control FAILS by design: the single-state figure is not stable. That is why it
is now written as a range with its cause, instead of being quoted as one number.
"""
from __future__ import annotations
import json

P = "agora_output/edrn_final/manuscript.tex"
R = json.load(open("probes/edrn_the_recovery_percentages_we_published.result.json",
                   encoding="utf-8"))
ref = R["reference_depth"]
far = [100 * R["far_bath_only"][k]["depth"] / ref for k in ("1", "2", "4", "8")]
uni = [100 * R["uniform"][k]["depth"] / ref for k in ("1", "2", "4", "8")]
lo, hi = R["far_range_pct"]
assert R["l1_manifold_dim"] == 4, R["l1_manifold_dim"]
assert all(f > u for f, u in zip(far, uni)), "the ordering that IS the claim does not hold"

OLD = (r"A truncation-control test on the impurity-explicit RG compares far-bath truncation "
       r"against uniform truncation \emph{at equal retained dimension} (4096 states): far-bath "
       r"$86.6\%$ against uniform $30.6\%$ recovery of the valley feature, a factor $2.8$. An "
       r"earlier statement of this test compared unequal retained dimensions and is superseded. "
       r"The single-state far-bath figure varies over $87$--$95\%$ across four runs because the "
       r"L1 ground manifold is four-fold degenerate ($E_0=-16.921463$), and the impurity "
       r"toolchain's defect is the appended corner-to-corner bond rather than edge $(0,6)$.")

NEW = (
    r"A truncation-control test on the impurity-explicit RG compares two truncation schemes "
    r"against the same untruncated L2 reference (valley depth $%0.6f$ on 18 bonds; untruncated "
    r"block dimension 4096), with one strength grid, one bond set and one depth definition. "
    r"Truncating only the far bath, keeping the defect neighbourhood explicit, recovers "
    r"$%0.1f\%%$, $%0.1f\%%$, $%0.1f\%%$ and $%0.1f\%%$ of the reference depth at "
    r"$\chi_B=1,2,4,8$; truncating every block uniformly recovers $%0.1f\%%$, $%0.1f\%%$, "
    r"$%0.1f\%%$ and $%0.1f\%%$ at the same $\chi$. The far-bath scheme exceeds the uniform "
    r"scheme at every $\chi$ tested, and that ordering---not any individual percentage---is what "
    r"the test establishes. The two schemes truncate different objects and cannot be equated by "
    r"retained dimension: far-bath $\chi_B=1$ retains 4096 of the 32768 states of the nine-factor "
    r"space, whereas uniform $\chi$ retains $\chi$ states of the RG block; the comparison above is "
    r"at equal $\chi$. The single-state far-bath figure must be given as a range rather than a "
    r"number: across four repeats it spans $%0.1f$--$%0.1f\%%$, because the three-block assembly "
    r"from which L2 is built (dimension 32768, ground energy $-16.921463$, and distinct from the "
    r"L1 graph above) has a four-fold degenerate ground manifold, so $\chi_B=1$ retains one "
    r"arbitrary vector out of it. An earlier statement of this test, quoting $86\%%$ against "
    r"$20\%%$, is superseded: the far-bath figure lies inside the measured range, but the $20\%%$ "
    r"does not reproduce---uniform single-state truncation removes the valley entirely. Note also "
    r"that the defect bond in this toolchain is the appended corner-to-corner bond rather than "
    r"edge $(0,6)$."
) % (ref, far[0], far[1], far[2], far[3], uni[0], uni[1], uni[2], uni[3], lo, hi)

text = open(P, encoding="utf-8", newline="").read()
n = text.count(OLD)
if n != 1:
    raise SystemExit(f"ANCHOR {'MISSING' if n == 0 else f'AMBIGUOUS ({n})'}")
open(P, "w", encoding="utf-8", newline="").write(text.replace(OLD, NEW, 1))
print("H1 truncation-control sentence rewritten against the re-run receipt")
print(f"   far-bath  {[round(x,1) for x in far]}")
print(f"   uniform   {[round(x,1) for x in uni]}")
print(f"   range     {lo:.1f}-{hi:.1f}%   reference {ref:.6f}")
