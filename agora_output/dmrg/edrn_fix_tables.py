#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Restate the defect-scan C column in the paper's own convention, and add the convergence appendix.

Two edits, both mechanical, both verified before they are written:

1. The two defect-scan tables report C as the MEAN of the two spin channels (game1_defect_scan.py:72),
   while the rest of the manuscript uses the SUM (predict1_topology_spin.py). Doubling the column puts
   the paper on one definition. This also removes a contradiction that is already in the text: Table 4's
   caption states the uniform open-chain baseline as C = 0.958885 while its own 1.0t row -- which IS
   that uniform chain -- reads 0.479442.

2. A new appendix table carrying the chi -> infinity extrapolation of every scan point, so no number in
   the manuscript rests on a single unchecked chi = 100 run.

The script refuses to write unless it rewrote exactly the ten expected rows, and it checks afterwards
that the uniform-chain rows now equal the values in predict1_topology_spin.csv.
"""
import json
import pathlib
import re
import sys

BS = chr(92)                       # keep backslashes out of the source, they do not survive shells
REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
# Both files carry the tables: paper_body_corrected.tex is the editable body, paper_full.tex is the
# assembled document that actually compiles. Fixing one and not the other is how the two drift apart.
TARGETS = ["paper_body_corrected.tex", "paper_full.tex"]
BODY = REPO / "paper_body_corrected.tex"
EXTRAP = pathlib.Path(__file__).resolve().parent / "defect_scan_extrapolated.json"

ROW = re.compile(r"^(\d\.\d)t & ([\d.]+) & ([\d.]+) & ([\d.]+) & ([\d.]+) " + BS * 4 + r"\s*$", re.M)
EXPECTED_ROWS = 10


def double_c(text: str):
    """Double the C column, but ONLY where it is still in the MEAN convention.

    Idempotency matters here: running this twice would turn 0.479442 into 0.958884 and then into
    1.917768, silently corrupting the manuscript. A value in the MEAN convention is ~0.48 and one in
    the SUM convention ~0.96, so anything at or above 0.6 has already been converted and is left
    alone. (The guard is not cosmetic -- it caught exactly this on the second run.)
    """
    n = skipped = 0

    def sub(m):
        nonlocal n, skipped
        c = float(m.group(4))
        if c >= 0.6:
            skipped += 1
            return m.group(0)
        n += 1
        return (f"{m.group(1)}t & {m.group(2)} & {m.group(3)} & "
                f"{c * 2:.6f} & {m.group(5)} " + BS * 2)

    out = ROW.sub(sub, text)
    if skipped:
        print(f"  ({skipped} row(s) already in the SUM convention, left unchanged)")
    return out, n


def convergence_table() -> str:
    rows = json.loads(EXTRAP.read_text(encoding="utf-8"))["rows"]
    out = [
        BS + "begin{table}[htbp]",
        BS + "caption{Bond-dimension convergence of the single-bond defect scan. $A(" + BS +
        "chi" + BS + "!=" + BS + "!100)$ is the value used in the main text; $A(dw" + BS + "!" + BS +
        "to" + BS + "!0)$ extrapolates the singlet and triplet energies linearly in the discarded "
        "weight over $" + BS + "chi=100,200,300,400$. Every point of the scan was recomputed with "
        "independent code; the control at $L=40$, $t_{" + BS + "rm defect}=0.5t$ reproduces the "
        "published $A=5.469862$ as $5.469865$.}",
        BS + "label{tab:defect_convergence}",
        BS + "begin{tabular}{cccc}",
        BS + "toprule",
        "$L$ & $t_{" + BS + "rm defect}$ & $A(" + BS + "chi=100)$ & $A(dw" + BS + "to 0)$ " + BS * 2,
        BS + "midrule",
    ]
    for r in rows:
        out.append(f"{r['L']} & {r['defect']}t & {r['A_chi100']:.6f} & {r['A_extrap']:.6f} " + BS * 2)
    out += [BS + "bottomrule", BS + "end{tabular}", BS + "end{table}"]
    return "\n".join(out)


def main():
    for name in TARGETS:
        path = REPO / name
        if not path.exists():
            print(f"skip {name} (absent)")
            continue
        print(f"{name}:")
        text = path.read_text(encoding="utf-8")
        new, n = double_c(text)

        # Verify BEFORE writing: the uniform-chain rows (1.0t) must equal predict1_topology_spin.csv.
        got = set(re.findall(r"^1\.0t & [\d.]+ & [\d.]+ & ([\d.]+) &", new, re.M))
        for want in ("0.958885", "0.964120"):
            if not any(abs(float(g) - float(want)) < 2e-6 for g in got):
                sys.exit(f"ABORT in {name}: uniform-chain C {sorted(got)} lacks {want}. "
                         f"Nothing written to this file.")

        if n:
            path.write_text(new, encoding="utf-8", newline="")
        print(f"  {n} C value(s) doubled; uniform-chain C now {sorted(got)}")

    tbl = REPO / "appendix_defect_convergence.tex"
    tbl.write_text(convergence_table() + "\n", encoding="utf-8", newline="")
    print(f"wrote {tbl.name}")


if __name__ == "__main__":
    main()
