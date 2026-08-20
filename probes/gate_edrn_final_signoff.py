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

    print("OURS -- re-derived from the recovery receipt")
    check("reference 0.1902 is the receipt's own reference",
          abs(ref - 0.1902) < 5e-4 and "0.1902" in draft, f"{ref:.6f}")
    for chi, far_pct, uni_pct in ((1, 87, 0), (2, 96, 2), (4, 91, 13), (8, 100, 24)):
        f_d = rec["far_bath_only"][str(chi)]["depth"]
        u_d = rec["uniform"][str(chi)]["depth"]
        f_p, u_p = 100 * f_d / ref, 100 * u_d / ref
        check(f"chi={chi} far {f_pct_s(f_d)} = {far_pct}% and uniform = {uni_pct}%".replace(
                  "f_pct_s", ""),
              abs(round(f_p) - far_pct) <= 1 and abs(round(u_p) - uni_pct) <= 1
              and f"{f_d:.4f}" in draft and f"{u_d:.4f}" in draft,
              f"measured {f_p:.1f}% / {u_p:.1f}%")

    lo, hi = rec["far_range_pct"]
    check("the single-state figure is given as a RANGE 87-95%",
          "87%–95%" in draft and abs(round(lo) - 87) <= 1 and abs(round(hi) - 95) <= 1,
          f"measured {lo:.0f}-{hi:.0f}%")
    reps = sorted(rec["far_repeats"])
    check("all four repeat values are quoted",
          all(f"{r:.4f}" in draft for r in reps), ", ".join(f"{r:.4f}" for r in reps))
    check("the 4-fold degeneracy and its energy are quoted",
          rec.get("l1_manifold_dim") == 4 and "4-fold" in draft and "−16.921463" in draft,
          f"manifold dim {rec.get('l1_manifold_dim')}")
    check("18 bonds, radius-2, stated",
          rec["reference_bonds"] == 18 and "18 bonds" in draft and "radius-2" in draft,
          f"{rec['reference_bonds']} bonds")
    check("the old 20% is attributed to chi=8, not to a single state",
          "uniform truncation at χ=8" in draft and 20 <= 100 * rec["uniform"]["8"]["depth"] / ref <= 27)

    sz = json.load(open(SZERO, encoding="utf-8"))
    e0 = next(r["enhanced"] for r in sz if r["s"] == 0.0)
    e_eps = next(r["enhanced"] for r in sz if r["s"] == 1e-09)
    check("E(0)=0.246731 is real and agrees with E(s->0)",
          abs(e0 - 0.246731) < 5e-6 and abs(e0 - e_eps) < 1e-10 and "0.246731" in draft,
          f"E(0)={e0:.6f} vs E(1e-9)={e_eps:.6f}")

    print("\nTHEIRS -- checked against the manuscript file itself")
    body = gh(f"repos/{ISSUE}/contents/{MS_PATH}", ".content")
    if not body:
        check("fetched the manuscript", False, "gh unavailable -- cannot verify quotations")
    else:
        ms = base64.b64decode(body.replace("\n", "")).decode("utf-8", "replace")
        ms_flat = " ".join(ms.split())
        check("the 86%/20% sentence is quoted faithfully (LaTeX there, rendered here)",
              r"$86\%$ vs $20\%$ recovery of the valley feature" in ms_flat
              and "86% vs 20% recovery of the valley" in draft,
              "manuscript uses math mode; the quotation renders it")
        check("Table I really calls s=0 the uniform point",
              "uniform point $s=0$" in ms and "the uniform point s = 0" in draft)
        check("the paper really says s=1 is the uniform coupling elsewhere",
              "contradiction edge strength equals the uniform coupling" in ms_flat
              and "equals the uniform coupling" in draft)
        check("the section really is titled Universality",
              "Universality in a small-world graph" in ms_flat
              and "Universality in a small-world graph" in draft)
        check("the documentclass line is quoted exactly",
              "\\documentclass[aps,prb,reprint,superscriptaddress]{revtex4-2}" in ms_flat
              and "aps,prb,reprint,superscriptaddress" in draft)
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

    print("\nTHE ROOM")
    state = gh(f"repos/{ISSUE}/issues/2", ".state")
    last = gh(f"repos/{ISSUE}/issues/2/comments?per_page=100", ".[-1].id")
    check("issue is open", state == "open", f"state={state}")
    check("they still spoke last -- we owe the reply",
          last == str(LAST_THEIRS), f"last={last}, expected {LAST_THEIRS}")

    print("\nHYGIENE")
    check("we do not assert the target journal's rules",
          "I am not going to assert anything about a specific journal" in draft
          and "Chinese Physics Letters" not in draft,
          "journal mechanics unverified, so unstated")
    check("the reply leads with OUR error, not theirs",
          draft.index("My own number was wrong") < draft.index("a referee will find"))
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
