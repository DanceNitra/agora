"""Apply the corrections agreed in the 20 August sign-off to the EDRN manuscript.

Every edit is anchored on an exact string that must be present, so a silent no-op is
impossible; every replacement number comes from a probe receipt re-run this cycle, not
from the sign-off text. Run from the repo root.
"""
from __future__ import annotations
import json
import sys

P = "agora_output/edrn_final/manuscript.tex"
GAP = {r["s"]: r["gap"] for r in
       json.load(open("probes/edrn_corrected_gap_curve.result.json", encoding="utf-8"))["rows"]}
applied: list[str] = []
text = open(P, encoding="utf-8", newline="").read()


def sub(old: str, new: str, tag: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f"ANCHOR MISSING: {tag}\n---\n{old[:200]}\n---")
    if text.count(old) != 1:
        raise SystemExit(f"ANCHOR AMBIGUOUS ({text.count(old)} sites): {tag}")
    text = text.replace(old, new, 1)
    applied.append(tag)


# --- F1  the gap figure's plotted data: the zeros below 0.76 are not reproducible ---------
sub(
    "(0.0,0.000)(0.1,0.000)(0.2,0.000)(0.3,0.000)(0.4,0.000)\n"
    "(0.5,0.000)(0.6,0.000)(0.7,0.000)(0.76,0.000)(0.77,0.323)\n"
    "(0.8,0.286)(0.85,0.219)(0.9,0.145)(0.95,0.067)(0.99,0.012)\n"
    "(1.0,0.186)",
    ("(0.0,%.3f)(0.1,%.3f)(0.2,%.3f)(0.3,%.3f)(0.4,%.3f)\n"
     "(0.5,%.3f)(0.6,%.3f)(0.7,%.3f)(0.76,%.3f)(0.77,%.3f)\n"
     "(0.8,%.3f)(0.85,%.3f)(0.9,%.3f)(0.95,%.3f)(0.99,%.3f)\n"
     "(1.0,%.3f)") % tuple(GAP[s] for s in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7,
                                            0.76, 0.77, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0)),
    "F1 gap figure data")
sub("    ymin=0, ymax=0.35,", "    ymin=0, ymax=0.70,", "F1b gap figure y-range")

# --- F2  the gap figure caption ------------------------------------------------------------
sub(
    r"The gap is strictly zero for $s\lesssim0.76$, opens abruptly at $s\approx0.77$ to $0.323$, then decreases to a minimum of $0.0115$ at $s=0.99$ before rising to $0.186$ at $s=1.00$.",
    r"Computed in the $S_z=+1/2$ sector as the gap to the next \emph{distinct} level. The gap is non-zero throughout: it decreases monotonically from $0.6176$ at $s=0$ to a minimum of $0.0115$ at $s=0.99$, and the step across $s=0.76\to0.77$ is $0.0115$ rather than a discontinuity. At $s=1.00$ the ground level is exactly two-fold, and the plotted $0.1857$ is the gap to the next distinct level.",
    "F2 gap figure caption")

# --- F3  the gap paragraph ------------------------------------------------------------------
sub(
    r"The gap is strictly zero for $s\lesssim0.76$, opens abruptly to $0.323$ at $s=0.77$, then decreases to $0.0115$ at $s=0.99$ before rising to $0.186$ at $s=1.00$.",
    r"Measured in this sector the gap is non-zero across the entire scan: $0.6176$ at $s=0$, $0.5226$ at $s=0.5$, $0.3346$ at $s=0.76$ and $0.3231$ at $s=0.77$, decreasing monotonically to $0.0115$ at $s=0.99$. The step across $s=0.76\to0.77$ is $0.0115$: the gap does not open at $s=0.77$, it has been open throughout and is closing toward $s=1$. At $s=1.00$ the ground level is exactly two-fold---two eigenvalues at $-24.9675365795$ with splitting $6\times10^{-14}$---and the quoted $0.186$ is the gap to the next distinct level, $0.1857$.",
    "F3 gap text")

sub(
    r"At $s=1.000$, the multi-seed gap in this sector exhibits a large spread, with some seeds finding near-zero gap and others a gap near $0.19$; this seed-dependent spread arises from near-degeneracy---not exact crossing---and is responsible for the scatter in valley depth.",
    r"At $s=1.000$ the seed-to-seed spread in the reported gap---some seeds near zero, others near $0.19$---is the solver returning either the degenerate partner or the next distinct level. The crossing is exact rather than near-degenerate: the splitting closes as a symmetric V, $0.011549$, $0.001092$, $0.000000$, $0.001077$, $0.010084$ across $s=0.990\ldots1.010$. Both ground states carry total spin $S=1/2$, so the two-fold degeneracy is orbital---the $D_3$ symmetry of the uniform gasket---and it is what produces the scatter in valley depth.",
    "F3b degeneracy sentence")

# --- F4  the default-control figure did not render: the curve sat outside the y-range -------
sub("    ymin=0.1, ymax=0.3,\n    grid=both,\n    legend pos=north east,",
    "    ymin=0.1, ymax=1.05,\n    grid=both,\n    legend pos=south east,",
    "F4 default-control figure y-range (the D curve was entirely off-scale)")
sub(r"\addlegendentry{$D_{\text{default}}$ (right axis)}",
    r"\addlegendentry{$D_{\text{default}}$}",
    "F4b legend named a right axis that was never defined")

# --- F5  the truncation sentence, which is ours and was under-specified --------------------
sub(
    r"A truncation-control test on the impurity-explicit RG shows $86\%$ vs $20\%$ recovery of the valley feature when the far bath is truncated to a single state versus uniform truncation, suggesting that the feature is not purely global.",
    r"A truncation-control test on the impurity-explicit RG compares far-bath truncation against uniform truncation \emph{at equal retained dimension} (4096 states): far-bath $86.6\%$ against uniform $30.6\%$ recovery of the valley feature, a factor $2.8$. An earlier statement of this test compared unequal retained dimensions and is superseded. The single-state far-bath figure varies over $87$--$95\%$ across four runs because the L1 ground manifold is four-fold degenerate ($E_0=-16.921463$), and the impurity toolchain's defect is the appended corner-to-corner bond rather than edge $(0,6)$.",
    "F5 our own truncation sentence")

# --- F6  Table I caption: s=1 is the uniform point, not s=0 --------------------------------
sub(r"Valley depth is defined as $E(0)-E(s=1.0)$, where $E(0)$ is the enhanced diagnosis at the uniform point $s=0$.",
    r"Valley depth is defined as $E(0)-E(s=1.0)$, where $E(0)$ is the enhanced diagnosis at $s=0$, i.e.\ with the contradiction edge removed. Note that $s=1$ is the uniform point, where every bond carries the same coupling. The five depths are derived from $E(0)$ and the valley values in the same rows, so they are one measurement plus arithmetic rather than five independent determinations.",
    "F6 Table I caption: uniform point + depths are derived")

# --- F7  Eq. (4) names one component while the table reports the full dot product ----------
sub(r"This observable is non-zero under SU(2) symmetry and varies with $s$.",
    r"This observable is non-zero under SU(2) symmetry and varies with $s$. Under SU(2), $\langle\sigma^x\sigma^x\rangle=\langle\sigma^y\sigma^y\rangle=\langle\sigma^z\sigma^z\rangle$, and the values tabulated in Sec.~\ref{sec:default_control} are the full $\langle\bm{\sigma}_i\cdot\bm{\sigma}_j\rangle$, i.e.\ three times the single component defined here.",
    "F7 Eq. (4) factor of three")

# --- F8  two definitions of depth coexist ---------------------------------------------------
sub(r"comparable to the L2 depth ($0.0998$ to $0.1045$)",
    r"larger than the L2 depth ($0.0874$ to $0.1045$ across the five seeds of Table~\ref{tab:l2_valley})",
    "F8 L1 vs L2 depth range and 'comparable'")
sub(r"The topographic prominence is defined as the drop below the lower of the two maxima flanking the valley over the full scan range. This definition avoids the need for a local baseline and is directly comparable across edges.",
    r"The topographic prominence is defined as the drop below the lower of the two maxima flanking the valley over the full scan range. This definition avoids the need for a local baseline and is directly comparable across edges. Note that it differs from the depth convention of Table~\ref{tab:l2_valley} and Table~\ref{tab:control_graphs}, which use the scan-endpoint baseline $E(0)-E(\min)$; the two are close where both apply---for the tree, prominence $0.096864$ against endpoint depth $0.100030$---but they are not the same quantity and should not be compared across tables.",
    "F8b prominence vs endpoint-depth conventions")

# --- F9  the section title claims universality the paper disclaims --------------------------
sub(r"\section{Universality in a small-world graph}",
    r"\section{A small-world graph: full edge survey}",
    "F9 section title vs the paper's own disclaimer")

open(P, "w", encoding="utf-8", newline="").write(text)
print(f"{len(applied)} edits applied:")
for a in applied:
    print("  ", a)
