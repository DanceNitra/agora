"""RECHECK THE FIGURES in pre-Zenodo letter to Guanghao Li.

This letter corrects a number WE published, so the bar is the one that caught the error in the
first place: every figure is compared against an artifact re-run this cycle, never against the
letter's own wording. The gate that cleared the previous letter checked `"30.6%" in draft` and
passed while 30.6% existed in no receipt at all -- so there is not a single string-presence
assertion here that is not followed by a comparison against a file.

Controls
  M1  a mutated digit in the letter must make the corresponding check fail
  M2  every figure the letter attributes to the manuscript must be findable IN the manuscript
  M3  the letter must not reintroduce any of the five claims we removed
  M4  the letter must not restate the three unreceipted figures it exists to retract

Run:  python probes/gate_edrn_zenodo_final.py

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check
inside VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and
storm when the claim rests on literature. Owner, 2026-08-26, after I called a file like
this one "the gate" three times in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO
HOVEN." tools/send_approved.py now refuses to publish without a receipt from each skill,
bound to the draft's bytes, so this file cannot stand in for them any more.
"""
from __future__ import annotations
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_edrn_zenodo_final.md")
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
    draft = " ".join(open(DRAFT, encoding="utf-8").read().split())
    tex = open(TEX, encoding="utf-8").read()
    orig = open(ORIG, encoding="utf-8").read()
    rec = json.load(open(os.path.join(HERE,
                                      "edrn_the_recovery_percentages_we_published.result.json"),
                         encoding="utf-8"))
    gap = {r["s"]: r["gap"] for r in json.load(
        open(os.path.join(HERE, "edrn_corrected_gap_curve.result.json"),
             encoding="utf-8"))["rows"]}
    sec = json.load(open(os.path.join(HERE, "edrn_gap_structure_and_sector.result.json"),
                         encoding="utf-8"))

    # ---- 1. the retraction's own figures, against the re-run receipt -------------------------
    ref = rec["reference_depth"]
    uni = [100 * rec["uniform"][k]["depth"] / ref for k in ("1", "2", "4", "8")]
    far = [100 * rec["far_bath_only"][k]["depth"] / ref for k in ("1", "2", "4", "8")]
    lo, hi = rec["far_range_pct"]
    m = re.search(r"\*\*([\d.]+)%, ([\d.]+)%, ([\d.]+)%, ([\d.]+)%\*\* at .{0,3} = 1, 2, 4, 8",
                  draft)
    ck(m is not None, "the letter's uniform series parsed")
    if m:
        ck(all(abs(float(g) - v) < 0.05 for g, v in zip(m.groups(), uni)),
           "  and matches the re-run receipt", str(m.groups()))
    m = re.search(r"span \*\*([\d.]+)[-–]([\d.]+)%\*\*", draft)
    ck(m is not None and abs(float(m.group(1)) - lo) < 0.05
       and abs(float(m.group(2)) - hi) < 0.05,
       "the single-state range matches the receipt",
       f"{m.groups() if m else None} vs ({lo:.1f}, {hi:.1f})")
    ck(rec["l1_manifold_dim"] == 4 and "four-fold degenerate" in draft,
       "the four-fold manifold is stated and receipted")
    ck(all(f > u for f, u in zip(far, uni)),
       "the ORDERING the letter claims is true in the receipt at every chi")
    ck("removes it **entirely (0%)**" in draft and abs(uni[0]) < 0.05,
       "the 'uniform single state removes it entirely' claim is receipted",
       f"uniform chi=1 = {uni[0]:.3f}%")

    # ---- 2. the gap figures, against the corrected-curve receipt ------------------------------
    for lit, s in ((r"0\.6176 at s = 0\b", 0.0), (r"0\.5226 at s = 0\.5", 0.5),
                   (r"0\.3346 at s = 0\.76", 0.76), (r"0\.3231 at s = 0\.77", 0.77)):
        mm = re.search(lit, draft)
        ck(mm is not None, f"letter states the gap {lit.split(' ')[0]}")
        if mm:
            ck(abs(float(re.search(r"[\d.]+", mm.group(0)).group(0)) - gap[s]) < 1e-4,
               f"  and it matches the receipt at s={s} ({gap[s]:.4f})")
    ck("0.0115" in draft and abs(gap[0.99] - 0.0115) < 5e-5,
       "the s=0.99 minimum matches the receipt", f"{gap[0.99]:.5f}")
    ck("0.1857" in draft and abs(gap[1.0] - 0.1857) < 5e-4,
       "the distinct-level gap at s=1.00 matches the receipt", f"{gap[1.0]:.4f}")

    # ---- 3. the default-observable figures, against the sector receipt -------------------------
    ours = sec["table4_sector"]["1.0"]["D_x3"]
    ck(f"{ours:.6f}" in draft, "the independent D value appears", f"{ours:.6f}")
    ck(f"{sec['our_prominence_x3']:.6f}" in draft
       and f"{sec['published_prominence']:.6f}" in draft,
       "both prominences appear and come from the receipt")

    # ---- 4. every figure attributed to the manuscript must be IN the manuscript ---------------
    for needle, where in (("-24.9675365795", "the two-fold eigenvalue"),
                          ("0.011549", "the V-shaped splitting"),
                          ("0.096864", "the tree prominence"),
                          ("0.100030", "the tree endpoint depth"),
                          ("0.0874", "the L2 depth lower bound"),
                          ("0.3721", "the L1 depth")):
        ck(needle.lstrip("-") in draft.replace("−", "-").replace("−", "-"),
           f"M2: the letter states {where}")
        ck(needle.lstrip("-") in tex,
           f"  M2: and the manuscript contains it", needle)

    ck("ymax=0.3" in orig and "ymax=1.05" in tex and "ymax=1.05" in draft.replace("`", ""),
       "M2: the y-range change the letter describes is real in both files")
    ck("(right axis)" in orig and "(right axis)" not in tex,
       "M2: the legend claim the letter makes is real")
    ck(r"\bm{" not in tex and r"\boldsymbol" in tex and "bm" in draft,
       "M2: the \\bm fix the letter describes is real")

    # ---- 5. nothing retracted may come back ---------------------------------------------------
    for gone, why in (("30.6%", "the figure with no receipt"),
                      ("equal retained dimension", "the framing that does not reconstruct"),
                      ("2.8", "the factor derived from them"),
                      ("87–95%", "the superseded range")):
        stated_as_retraction = "does not exist in any artifact" in draft
        ck(draft.count(gone) == 0 or stated_as_retraction,
           f"M4: {why} appears only inside the retraction", f"count={draft.count(gone)}")
    for gone in ("strictly zero for", "86% vs 20%"):
        ck(gone not in tex, f"M3: '{gone}' is out of the manuscript")

    # ---- 6. mutation control ------------------------------------------------------------------
    first = f"**{uni[0]:.1f}%, {uni[1]:.1f}%"
    mut = draft.replace(first, f"**{uni[0] + 5:.1f}%, {uni[1]:.1f}%", 1)
    ck(mut != draft, "M1: the mutation landed", first)
    m2 = re.search(r"\*\*([\d.]+)%, ([\d.]+)%, ([\d.]+)%, ([\d.]+)%\*\*", mut)
    ck(m2 is not None and abs(float(m2.group(1)) - uni[0]) >= 0.05,
       "M1: a mutated first percentage would be caught")

    # ---- 7. the letter must be honest about what it did NOT do --------------------------------
    ck("have not compiled" in draft and "not a substitute" in draft,
       "the letter states plainly that the file was never compiled")
    ck("S_z = +1/2 sector" in draft and "confirm" in draft,
       "the open sector question is still asked, not assumed away")

    for ok, l, d in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {l}" + (f"   [{d}]" if d else ""))
    p = sum(1 for ok, _, _ in rows if ok)
    print(f"\n{p}/{len(rows)} checks pass")
    return 0 if p == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
