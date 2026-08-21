"""Structural lint for the EDRN manuscript, and a number-by-number check against receipts.

There is no TeX toolchain on this machine, so the file CANNOT be compiled here and this
is not a substitute for compiling it. What it can do is catch the classes of error that a
compile would catch cheaply -- an unbalanced environment, a \\ref with no \\label, a \\cite
with no \\bibitem, a command whose package was never loaded -- plus the class a compile
would NOT catch: a plotted curve that lies outside its own axis range, which renders as a
legend entry with no line.

That last one is not hypothetical. The received manuscript plotted D_default (values
0.937-0.969) on an axis capped at ymax=0.3, and labelled it "right axis" on a plot that
had no right axis. It would have compiled cleanly and shown nothing.

Every number the corrected file states about the gap or the default observable is then
compared against the probe receipts re-run this cycle.
"""
from __future__ import annotations
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "agora_output", "edrn_final", "manuscript.tex")
ORIG = os.path.join(ROOT, "agora_output", "edrn_final", "manuscript_asreceived.tex")
rows: list[tuple[bool, str, str]] = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    t = open(TEX, encoding="utf-8").read()
    orig = open(ORIG, encoding="utf-8").read()
    gap = {r["s"]: r["gap"] for r in json.load(
        open(os.path.join(ROOT, "probes", "edrn_corrected_gap_curve.result.json"),
             encoding="utf-8"))["rows"]}
    sec = json.load(open(os.path.join(ROOT, "probes",
                                      "edrn_gap_structure_and_sector.result.json"),
                         encoding="utf-8"))

    # --- structure -----------------------------------------------------------------------
    cb = Counter(re.findall(r"\\begin\{([A-Za-z]+\*?)\}", t))
    ce = Counter(re.findall(r"\\end\{([A-Za-z]+\*?)\}", t))
    bad = {k: (cb[k], ce[k]) for k in set(cb) | set(ce) if cb[k] != ce[k]}
    ck(not bad, "every environment is balanced", str(bad) if bad else "")
    labels = set(re.findall(r"\\label\{([^}]+)\}", t))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", t))
    ck(not (refs - labels), "every \\ref has a \\label", str(sorted(refs - labels)))
    cites: set[str] = set()
    for x in re.findall(r"\\cite\{([^}]+)\}", t):
        cites.update(c.strip() for c in x.split(","))
    bibs = set(re.findall(r"\\bibitem\{([^}]+)\}", t))
    ck(not (cites - bibs), "every \\cite has a \\bibitem", str(sorted(cites - bibs)))
    ck(t.count("{") == t.count("}"), "braces balance",
       f"{t.count('{')} open vs {t.count('}')} close")

    pre = t.split(r"\begin{document}")[0]
    loaded: set[str] = set()
    for x in re.findall(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", pre):
        loaded.update(y.strip() for y in x.split(","))
    for cmd, pkg in (("boldsymbol", "amsmath"), ("toprule", "booktabs"), ("ding", "pifont"),
                     ("addplot", "pgfplots"), ("includegraphics", "graphicx"), ("bm", "bm")):
        used = re.search(r"\\" + cmd + r"[\s{\[]", t) is not None
        ck(not used or pkg in loaded, f"\\{cmd} is used only if {pkg} is loaded",
           f"used={used} loaded={pkg in loaded}")

    # --- the render trap: every plotted point must lie inside its axis range ---------------
    off = []
    for ax in re.finditer(r"\\begin\{axis\}\[(.*?)\](.*?)\\end\{axis\}", t, re.S):
        opts, body = ax.group(1), ax.group(2)
        ym = re.search(r"ymin=([-\d.]+)", opts)
        yM = re.search(r"ymax=([-\d.]+)", opts)
        if not (ym and yM):
            continue
        lo, hi = float(ym.group(1)), float(yM.group(1))
        for pt in re.finditer(r"\(([-\d.]+),([-\d.]+)\)", body):
            y = float(pt.group(2))
            if y < lo or y > hi:
                off.append((pt.group(0), lo, hi))
    ck(not off, "every plotted point lies inside its own axis range",
       f"{len(off)} points outside, e.g. {off[:2]}" if off else "")
    off_o = 0
    for ax in re.finditer(r"\\begin\{axis\}\[(.*?)\](.*?)\\end\{axis\}", orig, re.S):
        opts, body = ax.group(1), ax.group(2)
        ym, yM = re.search(r"ymin=([-\d.]+)", opts), re.search(r"ymax=([-\d.]+)", opts)
        if ym and yM:
            off_o += sum(1 for pt in re.finditer(r"\(([-\d.]+),([-\d.]+)\)", body)
                         if not (float(ym.group(1)) <= float(pt.group(2)) <= float(yM.group(1))))
    ck(off_o > 0, "CONTROL: the same check finds the defect in the received file",
       f"{off_o} points were off-scale before the fix")

    # --- the numbers we changed, against the receipts ---------------------------------------
    m = re.search(r"\(0\.0,([\d.]+)\)\(0\.1,([\d.]+)\)\(0\.2,([\d.]+)\)\(0\.3,([\d.]+)\)\(0\.4,([\d.]+)\)\s*\n"
                  r"\(0\.5,([\d.]+)\)\(0\.6,([\d.]+)\)\(0\.7,([\d.]+)\)\(0\.76,([\d.]+)\)\(0\.77,([\d.]+)\)", t)
    ck(m is not None, "the gap figure's low-s points parsed")
    if m:
        want = [gap[s] for s in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.76, 0.77)]
        got = [float(x) for x in m.groups()]
        ck(all(abs(a - b) < 0.0006 for a, b in zip(got, want)),
           "and every one matches the measured curve", f"{got[:3]}... vs {[round(w,3) for w in want[:3]]}...")
    for lit, val in ((r"\$0\.6176\$ at \$s=0\$", gap[0.0]),
                     (r"\$0\.5226\$ at \$s=0\.5\$", gap[0.5]),
                     (r"\$0\.3346\$ at \$s=0\.76\$", gap[0.76]),
                     (r"\$0\.3231\$ at \$s=0\.77\$", gap[0.77])):
        mm = re.search(lit, t)
        ck(mm is not None, f"text states {lit.split('$')[1]}")
        if mm:
            stated = float(re.search(r"[\d.]+", mm.group(0)).group(0))
            ck(abs(stated - val) < 0.0001, f"  and it matches the receipt ({val:.4f})")
    mm = re.search(r"the gap to the next distinct level, \$([\d.]+)\$", t)
    ck(mm is not None and abs(float(mm.group(1)) - gap[1.0]) < 0.0005,
       "the s=1.00 distinct-level gap matches the receipt",
       f"{mm.group(1) if mm else None} vs {gap[1.0]:.4f}")
    mm = re.search(r"gives \$([\d.]+)\$ at \$s=1\.00\$, a prominence of \$([\d.]+)\$ against \$([\d.]+)\$", t)
    ck(mm is not None, "the independent default-observable values parsed")
    if mm:
        ck(abs(float(mm.group(1)) - sec["table4_sector"]["1.0"]["D_x3"]) < 1e-6
           and abs(float(mm.group(2)) - sec["our_prominence_x3"]) < 1e-6
           and abs(float(mm.group(3)) - sec["published_prominence"]) < 1e-6,
           "  and all three match the sector receipt", str(mm.groups()))

    # --- the truncation paragraph: OURS, and every figure must come from the re-run receipt ---
    rec = json.load(open(os.path.join(ROOT, "probes",
                                      "edrn_the_recovery_percentages_we_published.result.json"),
                         encoding="utf-8"))
    rref = rec["reference_depth"]
    rfar = [100 * rec["far_bath_only"][k]["depth"] / rref for k in ("1", "2", "4", "8")]
    runi = [100 * rec["uniform"][k]["depth"] / rref for k in ("1", "2", "4", "8")]
    rlo, rhi = rec["far_range_pct"]
    # The manuscript writes a percent sign as a backslash-escaped `\%`; the pattern must match
    # that literal backslash, or it silently finds nothing and the check reports on an absence.
    PCT = r"\$([\d.]+)\\%\$"
    mm = re.search(rf"recovers {PCT}, {PCT}, {PCT} and {PCT} of the reference depth", t)
    ck(mm is not None, "the far-bath percentages parsed")
    if mm:
        ck(all(abs(float(g) - v) < 0.05 for g, v in zip(mm.groups(), rfar)),
           "  and all four match the re-run receipt", str(mm.groups()))
    mm = re.search(rf"uniformly recovers {PCT}, {PCT}, {PCT} and {PCT}", t)
    ck(mm is not None, "the uniform percentages parsed")
    if mm:
        ck(all(abs(float(g) - v) < 0.05 for g, v in zip(mm.groups(), runi)),
           "  and all four match the re-run receipt", str(mm.groups()))
    mm = re.search(rf"spans \$([\d.]+)\$--{PCT}", t)
    ck(mm is not None and abs(float(mm.group(1)) - rlo) < 0.05
       and abs(float(mm.group(2)) - rhi) < 0.05,
       "the single-state range matches the receipt",
       f"{mm.groups() if mm else None} vs ({rlo:.1f}, {rhi:.1f})")
    mm = re.search(r"untruncated L2 reference \(valley depth \$([\d.]+)\$", t)
    ck(mm is not None and abs(float(mm.group(1)) - rref) < 1e-6,
       "the reference depth matches the receipt")
    ck(all(f > u for f, u in zip(rfar, runi)),
       "the ORDERING the sentence claims holds in the receipt at every chi")
    ck(rec["l1_manifold_dim"] == 4 and "four-fold degenerate ground manifold" in t,
       "the four-fold manifold is stated and receipted")
    # MUTATION CONTROL: a wrong percentage in the text must make the checks above fail.
    first = f"recovers ${rfar[0]:.1f}" + "\\%$"
    mut = t.replace(first, f"recovers ${rfar[0] + 2:.1f}" + "\\%$", 1)
    ck(mut != t, "CONTROL: the mutation actually landed on the sentence", first)
    mm2 = re.search(rf"recovers {PCT}", mut)
    ck(mm2 is not None and abs(float(mm2.group(1)) - rfar[0]) >= 0.05,
       "CONTROL: a mutated first percentage would be caught by the check above")

    # --- claims that must be GONE ------------------------------------------------------------
    for gone, why in ((r"strictly zero for $s\lesssim0.76$", "the unreproducible zeros"),
                      (r"$86\%$ vs $20\%$", "the superseded truncation comparison"),
                      (r"\sim0.001", "the solver-dependent height"),
                      (r"(right axis)", "the legend naming an axis that does not exist"),
                      (r"\section{Universality", "the universality claim the paper disclaims")):
        ck(gone not in t, f"removed: {why}")
        ck(gone in orig, f"  CONTROL: it really was in the received file ({why})")

    ck(len(t) > 20000, "the file is still a whole manuscript", f"{len(t)} chars")
    ck("Draho" in t and "Sultanov" in t and "Guanghao Li" in t, "all three authors still present")

    for ok, l, d in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {l}" + (f"   [{d}]" if d else ""))
    p = sum(1 for ok, _, _ in rows if ok)
    print(f"\n{p}/{len(rows)} checks pass")
    print("\nNOTE: there is no TeX toolchain here. This file has NOT been compiled.")
    return 0 if p == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
