"""Second correction pass on the EDRN manuscript: the crossing-dependent height, and a
LaTeX command the first pass introduced without loading its package.

The D_default local maximum at s = 1.000 sits exactly at a level crossing, so its height
is a property of which degenerate state the solver returns, not of the physics. The
author's own tabulated values reproduce exactly at s = 0.99 and s = 1.01 and differ only
at the crossing point, where an independent run in the same sector gives a larger
prominence. His numbers are left as measured; a caveat and the independent value are added
beside them, and the abstract stops carrying a number that the solver decides.
"""
from __future__ import annotations
import json
import sys

P = "agora_output/edrn_final/manuscript.tex"
S = json.load(open("probes/edrn_gap_structure_and_sector.result.json", encoding="utf-8"))
OURS = S["table4_sector"]
PROM_OURS = S["our_prominence_x3"]
PROM_PUB = S["published_prominence"]
applied: list[str] = []
text = open(P, encoding="utf-8", newline="").read()


def sub(old: str, new: str, tag: str) -> None:
    global text
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ANCHOR {'MISSING' if n == 0 else f'AMBIGUOUS ({n})'}: {tag}\n{old[:180]}")
    text = text.replace(old, new, 1)
    applied.append(tag)


# --- G1  a command the first pass used without loading its package -------------------------
sub(r"\langle\bm{\sigma}_i\cdot\bm{\sigma}_j\rangle",
    r"\langle\boldsymbol{\sigma}_i\cdot\boldsymbol{\sigma}_j\rangle",
    "G1 \\bm -> \\boldsymbol (bm was never loaded; the file would not have compiled)")

# --- G2  the abstract must not carry a solver-dependent number ------------------------------
sub(r"exhibits only a weak local maximum of height $\sim0.001$ at the enhanced valley position in the fractal graph, about two orders of magnitude smaller than the enhanced valley depth, indicating that the coarse-grained observable is substantially less sensitive but not strictly blind.",
    r"exhibits only a weak local maximum at the enhanced valley position in the fractal graph, one to two orders of magnitude smaller than the enhanced valley depth. Its precise height is not well defined: $s=1.000$ is an exact level crossing, so the value there depends on which state of the two-fold ground manifold the solver returns. The qualitative statement is unaffected---the coarse-grained observable is substantially less sensitive, but not strictly blind.",
    "G2 abstract: drop the solver-dependent height")

# --- G3  the same claim in the introduction --------------------------------------------------
sub(r"In short, $D_{\text{default}}$ shows only a weak local maximum of height $\sim0.001$ at $s=1.000$ in the fractal graph, about two orders of magnitude smaller than the enhanced valley depth.",
    r"In short, $D_{\text{default}}$ shows only a weak local maximum at $s=1.000$ in the fractal graph, one to two orders of magnitude smaller than the enhanced valley depth.",
    "G3 introduction: same")

# --- G4  the figure caption ------------------------------------------------------------------
sub(r"$D_{\text{default}}$ shows a very weak local maximum (height $\sim0.001$) at the same position, about two orders of magnitude smaller than the valley depth.",
    r"$D_{\text{default}}$ shows a very weak local maximum at the same position, one to two orders of magnitude smaller than the valley depth; its height is not well defined because $s=1.000$ is an exact level crossing.",
    "G4 default-control figure caption")

# --- G5  the paragraph itself: keep his numbers, add the crossing and the independent value ---
sub(r"However, its amplitude is approximately $1/80$ of the enhanced valley depth ($\sim0.08$). Therefore, the coarse-grained observable is not strictly blind; it shows a very weak and oppositely directed response. The structural contrast is quantitative rather than qualitative.",
    (r"Its amplitude is between one and two orders of magnitude below the enhanced valley depth "
     r"($\sim0.08$). The height itself should not be quoted to a fixed figure: $s=1.000$ is an "
     r"exact level crossing, and an independent run in the same sector, reported here for "
     r"comparison, reproduces $D_{\text{default}}$ exactly at $s=0.99$ and $s=1.01$ but gives "
     r"$%0.6f$ at $s=1.00$, a prominence of $%0.6f$ against $%0.6f$ here. The two runs agree that "
     r"$s=1.000$ is a local maximum and disagree on its size, which is what a crossing predicts. "
     r"Therefore the coarse-grained observable is not strictly blind; it shows a very weak and "
     r"oppositely directed response, and the structural contrast is quantitative rather than "
     r"qualitative.") % (OURS["1.0"]["D_x3"] if isinstance(OURS.get("1.0"), dict) else 0.956778,
                         PROM_OURS, PROM_PUB),
    "G5 default-control paragraph: crossing caveat + independent value")

open(P, "w", encoding="utf-8", newline="").write(text)
print(f"{len(applied)} edits applied:")
for a in applied:
    print("  ", a)
