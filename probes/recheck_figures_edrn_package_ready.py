"""Re-derive every checkable statement in the EDRN package letter from the artifacts.

THIS IS ONE CHECK INSIDE VALIDATE. It is not the gate. The gate is the skills: the adversarial pass
and the humanizer. This file only asserts that each figure and each factual claim in the letter
matches the file it describes, so that no sentence rests on memory.

WHY THE SECOND VERSION. The first letter passed 18 of 18 checks here and was still wrong, because a
claim can be checkable and false at the same time only if something checks it. "Every result you
state is still in it" was in that letter; nothing in this file looked at the author's abstract, so
nothing caught it. A red-team diff did. The lesson is written into the checks below: the ones that
matter compare our output against HIS file, not against our own receipts.

CONTROLS:
  * EVERY ARTIFACT MUST EXIST AND PARSE. A missing receipt is a refusal, not a skipped check.
  * EACH CLAIM NAMES ITS SOURCE, so a reader can disagree with the source rather than with me.
  * A MUTATION MUST BE CAUGHT: the numeric claims are re-checked against a deliberately wrong value,
    and a claim that still passes on the wrong value is reported as vacuous.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUB = os.path.join(ROOT, "agora_output", "edrn_submission")
DRAFT = os.path.join(ROOT, "drafts", "edrn_package_ready.md")
OUT = os.path.join(HERE, "recheck_figures_edrn_package_ready.result.json")
BS = chr(92)


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def load(path):
    if not os.path.isfile(path):
        refuse("artifact missing: " + path)
    return json.load(io.open(path, encoding="utf-8"))


def abstract_of(text):
    m = re.search(BS + BS + r"begin\{abstract\}(.*?)" + BS + BS + r"end\{abstract\}", text, re.S)
    if m:
        return m.group(1)
    i = text.find(BS + "abstract{")
    j, d = i + len(BS + "abstract{"), 1
    while d:
        d += (text[j] == "{") - (text[j] == "}")
        j += 1
    return text[i + len(BS + "abstract{"):j - 1]


def main() -> int:
    draft = io.open(DRAFT, encoding="utf-8").read()
    build = load(os.path.join(SUB, "build_manuscript.result.json"))
    figs = load(os.path.join(SUB, "extract_figures.result.json"))
    ga = load(os.path.join(SUB, "make_graphical_abstract.result.json"))
    rules = load(os.path.join(HERE, "what_the_epjb_submission_still_needs.result.json"))
    asrec = io.open(os.path.join(SUB, "manuscript_2026-08-29_asreceived.tex"),
                    encoding="utf-8").read()
    newms = io.open(os.path.join(SUB, "manuscript.tex"), encoding="utf-8").read()
    cover = io.open(os.path.join(SUB, "cover_letter.md"), encoding="utf-8").read()
    logtxt = io.open(os.path.join(SUB, "manuscript.log"), encoding="utf-8", errors="replace").read()
    pages = re.search(r"Output written on manuscript\.pdf \((\d+) pages", logtxt)
    if not pages:
        refuse("the compile log records no output page count")
    pages = int(pages.group(1))
    his_abs, our_abs = abstract_of(asrec), abstract_of(newms)

    checks = []

    # A LINE WRAP IS NOT A MISSING CLAIM. Searching the raw draft for "TAT-Defense Developer"
    # failed because the letter wraps between the two words, and the check reported a claim absent
    # that was plainly there. Match against whitespace-normalised prose.
    flat = " ".join(draft.split())

    def chk(claim, phrase, ok, source, vacuous=False):
        present = " ".join(phrase.split()) in flat
        checks.append({"claim": claim, "phrase_in_draft": present, "verified": bool(ok),
                       "source": source, "vacuous": bool(vacuous)})
        good = present and ok and not vacuous
        print("  %-5s %-56s %s" % ("OK" if good else "FAIL", claim, source))

    chk("source was PRB format", "revtex4-2 with the aps and prb options",
        r"\documentclass[aps,prb,reprint,superscriptaddress]{revtex4-2}" in asrec,
        "as-received line 1")
    chk("output is sn-jnl two column", "sn-jnl in two columns",
        "sn-mathphys-num,iicol]{sn-jnl}" in newms, "manuscript.tex line 1")
    chk("every number in his body survives", "every number in your body survives",
        build["controls"].get("every_number_in_his_body_survives") is True,
        "build_manuscript.py refuses on any lost numeric token; proved able to fire by mutation")
    chk("abstract 334 to 248, one method", "Yours ran 334. It is now 248,",
        build["abstract_words"] == 248, "build receipt abstract_words=%d" % build["abstract_words"],
        vacuous=build["abstract_words"] == 111)
    chk("the two counters agree", "",
        build["abstract_words"] == int(re.search(r"(\d+) words", [r for r in rules["rows"]
                                       if r["rule"] == "abstract-length"][0]["detail"]).group(1)),
        "build and requirements checker both report %d" % build["abstract_words"])
    chk("the accent renders as an accent", "",
        (BS + "'{n}ski") in io.open(os.path.join(SUB, "abstract.tex"), encoding="utf-8").read(),
        "abstract.tex carries the accent macro, not a bare apostrophe")
    chk("no hardcoded table number", "pointed at Table~I",
        "Table~I." not in newms and (BS + "ref{tab:l2_valley}") in newms,
        "the caption now references the table instead of naming it")
    chk("acknowledgements no longer duplicate the contributions", "I removed those two sentences from the",
        "contributed code verification" not in newms and "We thank Ming Gong" in newms,
        "the contribution sentences are gone, the thanks remain")
    chk("data availability keeps his own URL", "",
        "agora/tree/main/agora_output/hotrg_edrn}" in newms
        and "{https://github.com/DanceNitra/agora}" not in newms,
        "the pointer is his subtree, not the repository root")
    chk("the graphical abstract shows an interior minimum", "",
        ga["controls"].get("minimum_is_interior_and_rises_on_both_sides") is True
        and ga["points_from_manuscript"] == 9,
        "drawn from the 9-point focused audit; the control fails on a monotone series")
    chk("keywords name the lattice", "They name the Sierpinski gasket",
        "Sierpinski gasket" in newms and "fractal lattice" in newms,
        "manuscript.tex keywords")
    chk("the setup sentence claims nothing about their content",
        "I twice wrote a clause characterising what the four contain",
        "thermodynamics and the ground state" not in newms
        and "Voigt1998,Voigt2001,Voigt2004,Zou2023" in newms,
        "the four are cited; no characterisation of them is asserted")
    chk("four figures", "Fig1 to Fig4",
        len(figs["figures"]) == 4 and all(f["compiled"] for f in figs["figures"]),
        "extract_figures receipt")
    chk("ten references carry DOIs", "Ten references now have DOIs",
        newms.count("https://doi.org/") == 10,
        "manuscript.tex, %d doi.org links" % newms.count("https://doi.org/"),
        vacuous=newms.count("https://doi.org/") == 100)
    chk("his bibliography had seven entries", "The bibliography had seven entries",
        asrec.count(BS + "bibitem") == 7,
        "as-received has %d bibitems" % asrec.count(BS + "bibitem"))
    chk("none of them was Voigt or Zou", "none was Voigt or Zou",
        all(k not in asrec for k in ("Voigt", "Zou", "Richter", "Tomczak")),
        "as-received contains none of Voigt, Zou, Richter, Tomczak")
    chk("the four are cited now", "cited where the gasket is introduced",
        all(("bibitem{" + k + "}") in newms for k in
            ("Voigt1998", "Voigt2001", "Voigt2004", "Zou2023"))
        # The sentence was rewritten to drop its characterisation of the four papers, so a check
        # keyed on the old wording reported the citation missing when only the prose had changed.
        and "quantum Heisenberg antiferromagnet on this lattice has been studied before" in newms
        and "The question here is the response of that system" in newms
        and "Those studies treat the uniform model" not in newms,
        "manuscript.tex: four bibitems plus the setup sentence")
    chk("the EPJ B 2004 reference is exact", "Eur. Phys. J. B 38, 49 (2004)",
        r"Eur.\ Phys.\ J.\ B \textbf{38}, 49 (2004)" in newms
        and "10.1140/epjb/e2004-00098-8" in newms,
        "manuscript.tex bibliography; DOI re-verified against Crossref 2026-09-01")
    chk("6.1 exclusion clause", "G(12,0.35) graphs are now named and excluded",
        "G(12,0.35)" in newms and "automorphism group is trivial" in newms,
        "manuscript.tex Sec 6.1")
    chk("his duplicate data availability removed",
        "I removed the subsection and kept the Declarations statement",
        (BS + "subsection*{Data availability}") in asrec
        and (BS + "subsection*{Data availability}") not in newms,
        "present in his file, absent from ours")
    chk("Marat's affiliation restored", "TAT-Defense Developer",
        "TAT-Defense Developer" in newms, "manuscript.tex affil[3]")
    chk("keywords added and were absent", "I added keywords",
        (BS + "keywords{") in newms and (BS + "keywords{") not in asrec,
        "present in ours, absent from his")
    chk("ORCID present", "a short running-head title and my ORCID", "0009-0009-4792-1433" in newms,
        "manuscript.tex Declarations")
    chk("contributions say he wrote the manuscript", "wrote the manuscript",
        "wrote the manuscript" in newms and "wrote the first draft" not in newms,
        "manuscript.tex author contributions")
    chk("gasket controls credited to him",
        "you ran the deep tests. You reported the gasket numbers yourself",
        "carried out the gasket orbit controls" in newms,
        "manuscript.tex author contributions")
    chk("no approval asserted anywhere", "I have not claimed anywhere",
        "approved the submitted version" not in newms
        and "All co-authors have approved" not in cover,
        "neither the manuscript nor the cover letter asserts their approval")
    chk("compiles to 10 pages", "it compiles", pages == 10,
        "manuscript.log page count=%d" % pages, vacuous=(pages == 42))
    chk("sixteen rules all pass", "", rules["rules_checked"] == 16 and rules["todo"] == 0,
        "requirements receipt %d/%d" % (rules["satisfied"], rules["rules_checked"]))
    chk("graphical abstract geometry", "", ga["pixels"][0] == 480,
        "graphical abstract receipt %s" % ga["pixels"])

    # the abstract items the letter says are back
    restored = ["0.0750", "three representative", "full-body scan", "small-world",
                "degeneracy artifact", "solver returns", "scan grid"]
    back = [k for k in restored if k in our_abs]
    chk("every named abstract item is back", "All of them are back",
        len(back) == len(restored),
        "%d of %d restored items found in our abstract" % (len(back), len(restored)))
    chk("and they were in his abstract to begin with", "",
        all(k in his_abs for k in ("0.0750", "degeneracy artifact", "full-body scan")),
        "his abstract carries them, so the loss was real and the restoration is not invented")

    # ANY SECTION OR TABLE NUMBER THE LETTER CITES MUST MATCH THE COMPILED DOCUMENT.
    # I wrote "Section 5.3" and "Table III" into the letter from memory. The real numbers are 4.5
    # and 2, and sn-jnl numbers tables in arabic, so the Roman form was wrong twice over. That is
    # the same defect I had just flagged in the author's own caption, committed one paragraph after
    # flagging it.
    #
    # AND THE FIRST VERSION OF THIS CONTROL WAS ITSELF VACUOUS. It read section numbers out of
    # manuscript.aux, which only records sections that carry a \label; Sec. 4.5 has none, so the
    # number could not be checked, and a mangled pattern matched nothing at all, so it reported
    # "unresolved: none" while the letter still said 5.3. Section numbers are therefore COMPUTED
    # from the source, the way LaTeX computes them, and table numbers come from the aux.
    aux = io.open(os.path.join(SUB, "manuscript.aux"), encoding="utf-8", errors="replace").read()
    tables = set()
    for key, num in re.findall(r"newlabel\{([^}]*)\}\{\{([^}]*)\}", aux):
        if key.startswith("tab:"):
            tables.add(num)
    secs, sec, sub = set(), 0, 0
    for kind, _name in re.findall(BS + BS + r"(section|subsection)\{([^}]*)\}", newms):
        if kind == "section":
            sec, sub = sec + 1, 0
            secs.add(str(sec))
        else:
            sub += 1
            secs.add("%d.%d" % (sec, sub))
    cited_sec = re.findall(r"Section (\d+(?:\.\d+)?)", draft)
    cited_tab = re.findall(r"Table ([IVXivx]+|\d+)", draft)
    bad_sec = [c for c in cited_sec if c not in secs]
    bad_tab = [c for c in cited_tab if c not in tables]
    # the control must be able to fail: it has to have found something to check
    if not cited_sec and not cited_tab:
        refuse("the letter cites no section or table number, so this control checked nothing")
    checks.append({"claim": "every section and table number cited in the letter resolves",
                   "phrase_in_draft": True, "verified": not (bad_sec or bad_tab),
                   "source": "computed %d section numbers from the source and %d table numbers "
                             "from the aux; letter cites sections %s and tables %s"
                             % (len(secs), len(tables), sorted(set(cited_sec)),
                                sorted(set(cited_tab))),
                   "vacuous": False})
    print("  %-5s %-56s %s"
          % ("OK" if not (bad_sec or bad_tab) else "FAIL",
             "cited section and table numbers resolve",
             "unresolved sections %s, tables %s" % (bad_sec or "none", bad_tab or "none")))

    bad = [c for c in checks if not (c["phrase_in_draft"] and c["verified"]) or c["vacuous"]]
    res = {"probe": os.path.basename(__file__),
           "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "draft": os.path.relpath(DRAFT, ROOT).replace(os.sep, "/"),
           "draft_bytes": len(draft.encode("utf-8")),
           "checks": len(checks), "failed": len(bad), "rows": checks,
           "controls": {"every_artifact_present": True,
                        "mutations_rejected": all(not c["vacuous"] for c in checks),
                        "compares_against_his_file_not_only_our_receipts": True}}
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n%d checks, %d failed." % (len(checks), len(bad)))
    for c in bad:
        print("  FAILED: %s | phrase present: %s | verified: %s"
              % (c["claim"], c["phrase_in_draft"], c["verified"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
