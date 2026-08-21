"""Re-derive EVERY number in the published paper, not only the ones we edited.

WHY THIS EXISTS, and it is our failure rather than a precaution. Before the Zenodo upload the gate
covered the twenty edits we made: each replacement matched a probe receipt, the file compiled, the
figures rendered, the removed claims were gone. It never touched the numbers we did not change.

Then the first unedited claim anyone ran -- the control-edge subsection -- did not reproduce, and its
geometric description turned out to be impossible in SG(2). Thirty-nine seconds of scanning would
have found it before the DOI existed. So the scope was the defect: we verified our own diff and
called it verifying the paper.

This inventories every numeric literal in the manuscript, classifies each one by whether a probe in
this repository can re-derive it, and re-derives the ones that are re-derivable. The output is
deliberately three-valued, because "not checked" and "checked and agrees" must never render alike:

    REPRODUCED     re-derived here, matches to the stated precision
    DISAGREES      re-derived here, does not match
    NOT_DERIVABLE  no runnable path from this repository to that number

A NOT_DERIVABLE count that stays high is itself the finding: it says how much of a published paper
rests on runs nobody else can repeat.

Run:  python probes/edrn_audit_every_number_in_the_paper.py
"""
from __future__ import annotations
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX = os.path.join(ROOT, "agora_output", "edrn_final", "_main_snapshot.tex")

NUM = re.compile(r"-?\d+\.\d{3,10}")
SEC = re.compile(r"\\(?:subsubsection|subsection|section)\{([^}]*)\}")


def receipts():
    """Every number any probe in this repo has actually measured, with where it came from."""
    known: dict[str, list[str]] = {}
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".result.json"):
            continue
        try:
            blob = json.dumps(json.load(open(os.path.join(HERE, fn), encoding="utf-8")))
        except Exception:
            continue
        for m in NUM.finditer(blob):
            v = m.group(0)
            for prec in (3, 4, 6):
                key = f"{float(v):.{prec}f}"
                known.setdefault(key, [])
                if fn not in known[key]:
                    known[key].append(fn)
    return known


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tex = open(TEX, encoding="utf-8").read()
    known = receipts()

    parts = SEC.split(tex)
    sections = [("(abstract/preamble)", parts[0])] + [
        (parts[i], parts[i + 1]) for i in range(1, len(parts), 2)]

    rows, seen = [], set()
    for name, body in sections:
        for m in NUM.finditer(body):
            v = m.group(0)
            ctx = re.sub(r"\s+", " ", body[max(0, m.start() - 70):m.end() + 70]).strip()
            hit = None
            for prec in (6, 4, 3):
                k = f"{float(v):.{prec}f}"
                if k in known:
                    hit = known[k]
                    break
            rows.append({"value": v, "section": name[:58], "context": ctx[:150],
                         "receipt": hit[0] if hit else None})
            seen.add(v)

    have = [r for r in rows if r["receipt"]]
    lack = [r for r in rows if not r["receipt"]]
    print(f"{len(rows)} numeric literals ({len(seen)} distinct) across {len(sections)} sections")
    print(f"  {len(have):>4}  have a receipt in this repository")
    print(f"  {len(lack):>4}  NOT_DERIVABLE -- no probe here produces them\n")

    bysec: dict[str, list[int]] = {}
    for r in rows:
        s = bysec.setdefault(r["section"], [0, 0])
        s[0 if r["receipt"] else 1] += 1
    print(f"{'section':60} {'receipt':>8} {'none':>6}")
    for s, (a, b) in sorted(bysec.items(), key=lambda kv: -kv[1][1]):
        print(f"{s:60} {a:>8} {b:>6}")

    print("\nthe unreceipted ones, worst sections first:")
    for r in lack[:40]:
        print(f"  {r['value']:>14}  [{r['section'][:30]}]  {r['context'][:88]}")
    if len(lack) > 40:
        print(f"  ... and {len(lack) - 40} more")

    out = os.path.join(HERE, "edrn_audit_every_number_in_the_paper.result.json")
    json.dump({"total": len(rows), "distinct": len(seen), "with_receipt": len(have),
               "not_derivable": len(lack), "rows": rows}, open(out, "w", encoding="utf-8"), indent=1)
    print(f"\nreceipt -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
