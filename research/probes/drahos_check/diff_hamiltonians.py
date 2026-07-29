"""Do the two scripts build the SAME Hamiltonian? Everything else in them is already identical.

Guanghao's two scripts disagree at N=6,8,10 and agree to six digits at N=12. Checked in order:
  fine_diagnosis (the metric)  -- byte-identical
  the s grid, the defect edge  -- identical
  diagnose / eigensolver       -- identical (eigsh, k=5, which='SA', states[:,0])
so the only place left is the Hamiltonian construction, and if THOSE differ one of them is physically
wrong, which matters far more than which number goes in the table.
"""
import difflib
import io
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = pathlib.Path(__file__).parent / "archive"


def ham(name):
    p = next(A.rglob(name))
    s = io.open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"def graph_to_hamiltonian\w*\(.*?\n(?=\ndef |\Z)", s, re.S)
    return (m.group(0) if m else "").splitlines()


a, b = ham("constant_validation.py"), ham("final_ed_scan.py")
print(f"constant_validation: {len(a)} lines   final_ed_scan: {len(b)} lines\n")


def norm(lines):
    """Compare CODE, not formatting: strip comments, blank lines and whitespace."""
    out = []
    for ln in lines:
        ln = re.sub(r"#.*$", "", ln).strip()
        if ln:
            out.append(re.sub(r"\s+", " ", ln))
    return out


na, nb = norm(a), norm(b)
d = list(difflib.unified_diff(na, nb, "constant_validation", "final_ed_scan", lineterm="", n=1))
if not d:
    print("HAMILTONIANS ARE IDENTICAL once comments and whitespace are removed.")
    print("Then the two scripts compute the same thing, and the disagreement at N=6,8,10 is not a")
    print("definition difference -- it is the eigensolver returning a DIFFERENT ground vector between")
    print("runs, which happens exactly when the ground state is near-degenerate. That is the same")
    print("mechanism as the s=0.38 anomaly, and it is testable: measure the gap.")
else:
    print("THEY DIFFER:")
    for ln in d[:60]:
        print("  " + ln)
