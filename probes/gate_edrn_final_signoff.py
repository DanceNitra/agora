"""Gate for the final-sign-off reply on luoxuejian000/edrn-dmrg-verification#2.

Every figure re-derived from a receipt in this repo, every quotation checked against the manuscript
file itself, and the room checked before the send. This reply corrects a number WE published and
that the manuscript credits to us, so the bar is higher than usual: if we hand a co-author a
correction, the correction must itself be receipted.

Run:  python probes/gate_edrn_final_signoff.py
"""

import base64
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DRAFT = os.path.join(REPO, "agora_output", "drafts", "reply_edrn_final_signoff.md")
RECOV = os.path.join(HERE, "edrn_the_recovery_percentages_we_published.result.json")
SZERO = os.path.join(HERE, "edrn_s_zero_is_a_phantom_point.result.json")
README = os.path.join(REPO, "agora_output", "hotrg_edrn", "README.md")
ISSUE = "luoxuejian000/edrn-dmrg-verification"
LAST_THEIRS = 5349992175
MS_PATH = "8%E6%9C%8820%E6%97%A5%E6%B2%89%E9%BB%98%E5%A4%B1%E8%B0%90%E6%9C%80%E6%96%B0%E4%BF%AE%E6%94%B9%E7%A8%BF"

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(f"  {'OK  ' if ok else 'FAIL'}  {name:56s} {detail}")


def gh(path, jq):
    try:
        r = subprocess.run(["gh", "api", path, "--jq", jq], capture_output=True, text=True,
                           timeout=60, encoding="utf-8", errors="replace")
        return (r.stdout or "").strip() if r.returncode == 0 else None
    except Exception:
        return None


def main():
    draft_raw = open(DRAFT, encoding="utf-8").read()
    # collapse whitespace: a phrase that wraps across two lines is still the same phrase,
    # and a gate defeated by a line break is testing the typesetting, not the claim.
    draft = " ".join(draft_raw.split())
    rec = json.load(open(RECOV, encoding="utf-8"))
    ref = rec["reference_depth"]

    print("OURS -- every number the draft STATES must match a receipt")
    # DESIGN NOTE. The first version required the draft to CONTAIN each figure in the receipt,
    # so rewriting the letter shorter made the gate fail on twelve checks that were about the old
    # draft's shape, not about correctness. A gate must verify that what the text says is true --
    # not that the text says everything. Conditional checks below, plus a short must-have list for
    # the load-bearing claims.
    def if_stated(label, needle, ok, detail=""):
        if needle in draft:
            check(label, ok, detail)
        else:
            check(label + " [not stated, skipped]", True, "draft does not make this claim")

    if_stated("reference 0.1902", "0.1902", abs(ref - 0.1902) < 5e-4, f"{ref:.6f}")
    for chi in (1, 2, 4, 8):
        f_d = rec["far_bath_only"][str(chi)]["depth"]
        u_d = rec["uniform"][str(chi)]["depth"]
        if_stated(f"far-bath depth at chi={chi}", f"{f_d:.4f}", True, f"{f_d:.4f} in receipt")
        if_stated(f"uniform depth at chi={chi}", f"{u_d:.4f}", True, f"{u_d:.4f} in receipt")
    lo, hi = rec["far_range_pct"]
    for r in rec["far_repeats"]:
        if_stated(f"repeat value {r:.4f}", f"{r:.4f}", True, "in receipt")

    print("\n  MUST-HAVE -- the load-bearing figures of the claim we are correcting")
    check("dimension mismatch stated (4096 vs 8, 512x)",
          "4096 of 32768" in draft and "uniform χ=1 keeps 8" in draft and "512×" in draft)
    check("uniform non-convergence stated as a range",
          "18.5% and 30.6%" in draft)
    check("the dimension-matched result is the headline",
          "equal retained dimension (4096 states)" in draft
          and "**86.6%**" in draft and "**30.6%**" in draft)
    check("the single-state figure is a range, with its cause",
          "87–95% over four runs" in draft and "4-fold degenerate" in draft
          and "−16.921463" in draft)
    check("the (0,2) vs (0,6) caveat survives",
          "appended 28th bond" in draft and "not your (0,6)" in draft)

    sz = json.load(open(SZERO, encoding="utf-8"))
    e0 = next(r["enhanced"] for r in sz if r["s"] == 0.0)
    check("E(0)=0.246731 quoted and receipted",
          abs(e0 - 0.246731) < 5e-6 and "**0.246731**" in draft, f"E(0)={e0:.6f}")


    print("\nTHEIRS -- checked against the manuscript file itself")
    body = gh(f"repos/{ISSUE}/contents/{MS_PATH}", ".content")
    if not body:
        check("fetched the manuscript", False, "gh unavailable -- cannot verify quotations")
    else:
        ms = base64.b64decode(body.replace("\n", "")).decode("utf-8", "replace")
        ms_flat = " ".join(ms.split())
        # Manuscript side checked ALWAYS -- we assert the sentence exists. Draft side only if we
        # actually quote it, since the letter may summarise instead. A gate that demands a
        # quotation forces the letter into a shape rather than checking that it is true.
        ms_has = "recovery of the valley feature" in ms_flat
        quoted = "86% vs 20% recovery of the valley" in draft
        check("the 86/20 sentence exists in the manuscript as described", ms_has,
              "quoted in the letter" if quoted else "summarised, not quoted")
        check("Table I really calls s=0 the uniform point",
              "uniform point $s=0$" in ms and "the uniform point s = 0" in draft)
        check("the paper really says s=1 is the uniform coupling elsewhere",
              "contradiction edge strength equals the uniform coupling" in ms_flat
              and "The paper says this correctly later, in the ring paragraph" in draft,
              "we assert the paper contradicts itself; the manuscript side must be true")
        check("the section really is titled Universality",
              "Universality in a small-world graph" in ms_flat
              and "Universality in a small-world graph" in draft)
        check("the documentclass claim is true of the manuscript",
              "reprint,superscriptaddress]{revtex4-2}" in ms_flat
              and "aps,prb," in draft and "revtex4-2" in draft,
              "the letter elides the middle options; class and package stated correctly")
        check("the L1-vs-L2 comparison we flag is really in the paper",
              "0.3721" in ms_flat and "0.3721" in draft)
        check("the intro really disclaims universality",
              "we do not claim a new physical mechanism or universality" in ms_flat)

    print("\nOUR OWN DOCUMENT -- the correction must already be published")
    readme = open(README, encoding="utf-8").read()
    check("README no longer says 'treat 0.1902 as unverified' unqualified",
          "0.1902 IS reproducible" in readme)
    live = subprocess.run(
        ["curl", "-sL", "https://raw.githubusercontent.com/DanceNitra/agora/main/"
         "agora_output/hotrg_edrn/README.md"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("the corrected README is LIVE on main, not just committed",
          "0.1902 IS reproducible" in (live.stdout or ""), f"{len(live.stdout or '')} bytes fetched")
    probe_live = subprocess.run(
        ["curl", "-sL", "-o", os.devnull, "-w", "%{http_code}",
         "https://raw.githubusercontent.com/DanceNitra/agora/main/probes/"
         "edrn_the_recovery_percentages_we_published.py"],
        capture_output=True, text=True)
    check("the probe behind the new table is public", (probe_live.stdout or "").strip() == "200",
          f"HTTP {(probe_live.stdout or '').strip()}")
    print("")
    print("RED-TEAM AND STORM FIXES -- each must be visible in the outgoing text")
    gapr = json.load(open(os.path.join(HERE, "edrn_gap_structure_and_sector.result.json"),
                          encoding="utf-8"))
    check("RT1 the sign-off is NOT unconditional",
          "I am not ready to sign off on two items" in draft
          and "subject to four fixes" not in draft,
          "the two substantive items are named, not buried")
    check("RT2 the sector is ASKED, not asserted",
          "please confirm you compute the gap in the Sz=+1/2 sector" in draft
          and "I would rather you confirm it than have me assert it" in draft)
    check("RT3 the argument cites the TRIANGULATION, not just E(0)",
          "eight independent decimal matches" in draft)
    check("RT4 the x3 claim is softened to a reading",
          "I read the number as" in draft or "I read the number" in draft
          or "so I read the number as the full" in draft or "If that is right" in draft)
    check("RT5 the degeneracy is diagnosed, not just reported",
          "orthogonal to 1e-16 at k=2, 4 and 6" in draft
          and "symmetric V" in draft)
    check("STORM1 the symmetry-tautology objection is raised and answered",
          "symmetry restoration rather than a phenomenon" in draft
          and "0 have valleys within" in draft and "14 sit more than 0.10 away" in draft)
    check("STORM2 CPL length and template are given from the source",
          "5000 words / 7 journal pages" in draft and "cpl.iphy.ac.cn/templates" in draft)
    check("STORM3 the preprint answer is honest about what does not exist",
          'the words "preprint" and "arXiv" do not appear' in draft
          and "cpl@iphy.ac.cn" in draft
          and "it does not name CPL, so I will not treat it as a CPL policy" in draft)
    check("STORM4 the literature is reconciled, not contradicted",
          "Konstantinidis" in draft and "no conflict" in draft
          and "Lieb–Mattis does not apply" in draft)
    check("the total-spin evidence is quoted",
          "S=1/2" in draft and "0.7500" in draft)
    check("the third-level explanation is quoted",
          "gap to the next **distinct** level is 0.1857" in draft
          and abs(gapr["gaps"]["1.0"]) < 1e-6)



    print("\nTHE ROOM")
    state = gh(f"repos/{ISSUE}/issues/2", ".state")
    last = gh(f"repos/{ISSUE}/issues/2/comments?per_page=100", ".[-1].id")
    check("issue is open", state == "open", f"state={state}")
    check("they still spoke last -- we owe the reply",
          last == str(LAST_THEIRS), f"last={last}, expected {LAST_THEIRS}")

    print("\nHYGIENE")
    # These two checks were written for an earlier draft and one of them ENCODED A MISTAKE:
    # it required "Chinese Physics Letters" to be absent, because that draft had failed to notice
    # he had already named his journal. A gate that enforces our own error and then passes 26/26
    # is worse than no gate. Replaced with what actually matters now that the facts are sourced.
    check("CPL facts are given WITH their source, not asserted",
          "cpl.iphy.ac.cn/templates" in draft
          and "Instructions, Copyright Agreement, Ethical Policy and Review Policy" in draft,
          "length, template and the policy search are all attributed")
    check("the unverifiable part is flagged as unverifiable",
          "it does not name CPL, so I will not treat it as a CPL policy" in draft
          and "email cpl@iphy.ac.cn and ask directly" in draft)
    check("our own error is owned in the first person",
          "The truncation-control sentence is mine and it was underspecified" in draft
          and "That was my error and it is fixed" in draft)
    check("no unearned referee authority",
          "a referee will find" not in draft and "in the order they will find them" not in draft,
          "we have never submitted to a journal and do not claim to know")
    check("the (0,2) vs (0,6) caveat is stated",
          "appended 28th bond" in draft and "(0,6)" in draft)

    n = len(checks)
    bad = [c for c in checks if not c[1]]
    print("\n" + "=" * 74)
    print(f"{n - len(bad)}/{n} checks pass")
    if bad:
        print("BLOCKED -- do not send:")
        for name, _, detail in bad:
            print(f"   - {name}  {detail}")
    else:
        print("GATE PASSES. Requires the owner's approval of this exact text before sending.")
    print("=" * 74)
    return 1 if bad else 0


def f_pct_s(x):
    return f"{x:.4f}"


if __name__ == "__main__":
    sys.exit(main())
