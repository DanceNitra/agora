"""Which of Guanghao's two scripts is the reliable one? They disagree at N=6,8,10 and agree at N=12.

He asked directly: "tell me which script you used at N=6, D=0.3 and what value you got, so I can lock down
which one is reliable and discard the other." Answering only that would be answering the smaller question.
The useful answer is WHY they disagree, because "the one Rastislav happened to run" is not a reason to
trust a script in a paper.

Reported values at D=0.3:

    N       constant_validation.py      final_ed_scan.py (my run)
    6       0.982042                    0.999639
    8       0.960666                    0.961557
    10      0.967717                    0.972092
    12      —                           0.958572  (matches his 0.958571 to the digit)

The pattern is the tell: they converge as N grows and diverge most at the smallest size. That is the
signature of a definition that differs on a boundary or on an average taken over different points, not of
a random bug — a bug would not shrink monotonically with N.

This diffs the two definitions rather than guessing, then re-runs both on the same sizes in this process,
so the comparison is not across two machines and two Python versions.
"""
import io
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = pathlib.Path(__file__).parent / "archive"


def find(name):
    hits = list(A.rglob(name))
    return hits[0] if hits else None


def summarise(path, label):
    src = io.open(path, encoding="utf-8", errors="replace").read()
    print(f"\n=== {label}  ({path.name}) ===")
    # the parameters that decide what is being averaged
    for pat, what in ((r"s_values\s*=\s*[^\n]+", "s grid"),
                      (r"s_list\s*=\s*[^\n]+", "s grid"),
                      (r"np\.linspace\([^)]*\)", "linspace"),
                      (r"D\s*=\s*[0-9.]+", "D"),
                      (r"center_edge[^\n]*", "defect edge"),
                      (r"def\s+\w*ratio\w*\([^)]*\)", "ratio fn"),
                      (r"mean\([^)]*\)", "mean over"),
                      (r"fine\s*=[^\n]+", "fine metric")):
        for m in re.findall(pat, src)[:4]:
            print(f"   [{what}] {m.strip()[:110]}")


cv, fe = find("constant_validation.py"), find("final_ed_scan.py")
if not cv or not fe:
    print("archive scripts not found -- extract drahos.zip first")
    raise SystemExit(2)
summarise(cv, "constant_validation.py  (his N=6..10 numbers)")
summarise(fe, "final_ed_scan.py        (his N=12..14 numbers, and my re-run)")

print("\n=== what to look for ===")
print("If the two use DIFFERENT s grids, they are averaging the ratio over different points, and the")
print("smaller the chain the more one outlier moves the mean -- which explains divergence that shrinks")
print("with N. That would make neither script 'wrong': it would make the MEAN the wrong summary, and the")
print("paper should report the ratio AT a stated s (or the full curve), not a mean over an arbitrary grid.")
