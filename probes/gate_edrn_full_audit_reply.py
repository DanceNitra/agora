"""Gate the full-audit letter to Guanghao Li.

This letter tells a co-author that one subsection of a paper published three hours ago does not
reproduce. Every figure in it therefore comes from a receipt written this cycle, and the counts are
recomputed from the receipts rather than copied from the prose that reported them.

Run:  python probes/gate_edrn_full_audit_reply.py
"""
from __future__ import annotations
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_edrn_full_audit.md")
rows: list[tuple[bool, str, str]] = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))


def load(name):
    return json.load(open(os.path.join(HERE, name), encoding="utf-8"))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    d = " ".join(open(DRAFT, encoding="utf-8").read().split())

    a = load("edrn_rederive_the_tables.result.json")
    b = load("edrn_rederive_tables_1_2_5.result.json")
    o = load("edrn_two_of_the_papers_own_open_items.result.json")
    cells = [c for c in a["cells"] + b["cells"] if c["table"] != "CONTROL"]

    rep = sum(1 for c in cells if c["verdict"] == "REPRODUCED")
    dis = sum(1 for c in cells if c["verdict"] == "DISAGREES")
    nd = sum(1 for c in cells if c["verdict"] == "NOT_DERIVABLE")
    ck(rep + dis == 60 and "57 of the 60" in d,
       "the 'X of Y recomputable' pair matches the receipts", f"{rep} reproduced of {rep+dis}")
    ck(rep == 57, "57 reproduced", str(rep))
    ck(nd == 16 and "Sixteen cells" in d, "16 not derivable", str(nd))

    t4 = [c for c in a["cells"] if c["table"] == "IV"]
    ck(len(t4) == 40 and all(c["verdict"] == "REPRODUCED" for c in t4)
       and "40 of 40" in d, "Table IV is 40/40", f"{len(t4)} cells")
    t5 = [c for c in b["cells"] if c["table"] == "V"]
    ck(len(t5) == 6 and all(c["verdict"] == "REPRODUCED" for c in t5)
       and "6 of 6" in d, "Table V is 6/6", f"{len(t5)} cells")
    for p in ("0.124449", "0.008856", "0.061969"):
        ck(p in d and any(f"{c['recomputed']:.6f}" == p for c in t5 if c["recomputed"]),
           f"prominence {p} is in the receipt")

    ring = next((c for c in b["cells"] if c["cell"] == "ring depth (single)"), None)
    ck(ring and abs(ring["recomputed"] - 0.077072) < 1e-6 and "0.0771" in d,
       "the ring depth quoted is the recomputed one", f"{ring['recomputed']:.6f}" if ring else "-")
    ck("0.0993 ± 0.0286" in d, "and their own multi-seed figure is quoted beside it")

    ck(o["flat_edges"] == [] and "No edge is flat" in d, "zero flat edges, from the receipt")
    ck("3.4×10⁻²" in d and "6.9×10⁻³" in d, "both range figures present")
    v = o["viii_smallworld_edge_7_8"]
    ck(abs(v["min_new_range"] + 0.1) < 1e-9 and "s = −0.1" in d and v["interior"],
       "the (7,8) interior minimum matches the receipt")
    ck("0.246731" in d and abs(a["calibration_E0"] - 0.246731) < 5e-6,
       "the calibration anchor is real")

    ck("Table I" in d and "1.0000" in d, "Table I positions mentioned")
    ck("cannot be reproduced by any reader" in d,
       "the tree/random rows are named as unreproducible, which is the reproducibility finding")
    ck("my error, not a disagreement" in d,
       "the ring comparison is owned rather than reported as a defect")
    ck("That was the gap in my own process" in d,
       "the letter says why this was not caught before the upload")

    low = d.lower()
    for w in ("however", "moreover", "furthermore", "delve", "leverage", "crucial",
              "load-bearing", "honest"):
        ck(w not in low, f"humanizer: no '{w}'")
    ck(len(d) < 4200, "length is under the cap set after jason-sachs", f"{len(d)} chars")

    last = subprocess.run(["gh", "api", "--paginate",
                           "repos/luoxuejian000/edrn-dmrg-verification/issues/2/comments",
                           "--jq", "[.[] | .id] | last"], capture_output=True, text=True)
    # Report the newest id rather than pinning one -- a hardcoded id needs editing after every
    # comment, and editing a gate to make it pass is how it stops being a gate.
    ck(last.returncode == 0 and last.stdout.strip().isdigit(),
       "read the thread (newest id reported, not pinned)", last.stdout.strip())
    print("   (newest comment id on the thread: " + last.stdout.strip() + ")")

    for ok, l, dt in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {l}" + (f"   [{dt}]" if dt else ""))
    p = sum(1 for ok, _, _ in rows if ok)
    print(f"\n{p}/{len(rows)} checks pass")
    return 0 if p == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
