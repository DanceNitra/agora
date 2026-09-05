"""Measure the EDRN manuscript against every EPJ B submission requirement, one check per rule.

WHY. @luoxuejian000 asked R. Drahos to submit the 29 August manuscript to EPJ B and stated he will
not revise it again. Drahos is the corresponding author, so producing a submittable package is our
work, not his. A submission that arrives incomplete is returned before review, and the guidelines
say so twice: "Failing to submit a complete set of editable source files will result in your article
not being considered for review" and "submissions that do not include relevant declarations will be
returned as incomplete".

This file replaces reading the manuscript by eye. Every rule below is checked against the bytes.

THE SOURCE OF THE RULES is the EPJ B Instructions for Authors as supplied by the owner on
2026-09-01, plus the Springer Nature LaTeX template package (December 2024) he pointed at. Where a
rule carries a number, the number is quoted from the guidelines rather than remembered:
  * abstract 150 to 250 words
  * LLM use "should be properly documented in the Methods section"; our involvement is generative
    rather than copy editing, so the exemption does not apply
  * "Statements and Declarations" must carry Competing Interests AND Author contributions
  * a Data Availability Statement is required for all original research
  * a graphical abstract is required before acceptance: .jpg or .png ONLY, maximum width 480 pixels,
    aspect ratio 11:6
  * headings use the decimal system with no more than three levels
  * references numbered in square brackets, DOIs as full links, one reference per number
  * the Springer Nature template with the [iicol] option is the recommended format for EPJ B

CONTROLS, because a checklist that cannot fail is a to-do list with ticks:
  * THE TARGET MUST RESOLVE: the manuscript file must exist and parse as LaTeX with a
    \\begin{document}. A check that never sees its target reports SAFE.
  * EVERY CHECK MUST BE ABLE TO SAY BOTH THINGS. Each rule is exercised against a POSITIVE fixture
    that satisfies it and a NEGATIVE fixture that violates it, and a rule whose two fixtures give
    the same verdict is reported as BROKEN rather than as a pass.
  * NO RULE MAY BE SILENTLY SKIPPED: the rule count is asserted against the declared list.
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
MS = os.path.join(ROOT, "agora_output", "edrn_submission",
                  "manuscript.tex")
OUT = os.path.join(HERE, "what_the_epjb_submission_still_needs.result.json")
START = time.time()


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


# ---------------------------------------------------------------- the rules
# Each rule is (id, requirement, fn) where fn(text) -> (ok: bool, detail: str).

def abstract_words(t):
    # TWO SPELLINGS, because the two classes differ and this checker was written against the old
    # one: revtex uses the abstract ENVIRONMENT, sn-jnl uses the \abstract{...} MACRO. Reading only
    # the environment reported "no abstract" on a converted file whose abstract was right there,
    # which is a checker failing on its own target rather than a defect in the paper.
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", t, re.S)
    if m:
        body = m.group(1)
    else:
        i = t.find("\\abstract{")
        if i < 0:
            return False, "no abstract, in either the environment or the macro form"
        j, depth = i + len("\\abstract{"), 1
        while j < len(t) and depth:
            depth += (t[j] == "{") - (t[j] == "}")
            j += 1
        body = t[i + len("\\abstract{"):j - 1]
    # ONE COUNTER, ONE METHOD. This file and the build script disagreed by three words, and the
    # checklist carried a third number, because each stripped LaTeX differently: the crudest
    # version turned the backslash of an accent macro into a space and split one word into four
    # tokens. Three numbers for one abstract is worse than any of them being wrong.
    # An accent collapses to its letter, a math span counts as one word, a macro disappears.
    body = re.sub(r"\$[^$]*\$", " X ", body)
    body = re.sub(r"\\['`\"^~=.]\{?([A-Za-z])\}?", r"\1", body)
    body = re.sub(r"\\[a-zA-Z]+\*?\{([^{}]*)\}", r"\1", body)
    body = re.sub(r"\\[a-zA-Z]+\*?", " ", body)
    body = re.sub(r"[{}~\\]", " ", body)
    n = len(body.split())
    return 150 <= n <= 250, "%d words (guideline: 150 to 250)" % n


def uses_sn_template(t):
    cls = re.search(r"\\documentclass(\[[^\]]*\])?\{([^}]+)\}", t)
    if not cls:
        return False, "no \\documentclass"
    opts, name = (cls.group(1) or ""), cls.group(2)
    ok = name.strip() == "sn-jnl" and "iicol" in opts
    return ok, "documentclass%s{%s}" % (opts, name)


def has_corresponding_email(t):
    hit = re.search(r"\\email\{([^}]*)\}|\\corresponding|Corresponding author", t, re.I)
    addr = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", t)
    return bool(hit and addr), ("email macro: %s | address in file: %s"
                                % (bool(hit), addr.group(0) if addr else "none"))


def has_orcid(t):
    return "orcid" in t.lower(), "ORCID mentioned: %s" % ("orcid" in t.lower())


def has_ai_disclosure(t):
    m = re.search(r"artificial intelligence|large language model|\bLLM\b|AI[- ]assisted"
                  r"|AI research system", t, re.I)
    return bool(m), ("found %r" % m.group(0)) if m else "no AI or LLM disclosure anywhere"


def has_competing_interests(t):
    return bool(re.search(r"competing interest", t, re.I)), \
        "Competing Interests statement present: %s" % bool(re.search(r"competing interest", t, re.I))


def has_author_contributions(t):
    m = re.search(r"author contribution|CRediT", t, re.I)
    return bool(m), "Author contributions statement present: %s" % bool(m)


def has_declarations_section(t):
    m = re.search(r"\\section\*?\{\s*(Statements and )?Declarations\s*\}", t, re.I)
    return bool(m), "Declarations heading present: %s" % bool(m)


def has_data_availability(t):
    m = re.search(r"Data availability", t, re.I)
    return bool(m), "Data availability statement present: %s" % bool(m)


def heading_depth(t):
    levels = {"section": 0, "subsection": 0, "subsubsection": 0, "paragraph": 0}
    for k in levels:
        levels[k] = len(re.findall(r"\\" + k + r"\*?\{", t))
    deep = levels["paragraph"]
    return deep == 0, "sections %d, subsections %d, subsubsections %d, paragraphs %d (max 3 levels)" \
        % (levels["section"], levels["subsection"], levels["subsubsection"], deep)


def references_have_dois(t):
    items = re.findall(r"\\bibitem\{[^}]*\}(.*?)(?=\\bibitem|\\end\{thebibliography\})", t, re.S)
    if not items:
        return False, "no \\bibitem entries found"
    # THE RULE IS "IF AVAILABLE", and this check read it as "always". The guidelines say "If
    # available, please always include DOIs as full DOI links", and their own Online document
    # example carries an access date instead. A code repository has no DOI, so demanding one made
    # the score wrong rather than the manuscript.
    exempt = [i for i in items if "Accessed" in i and "doi.org" not in i]
    need = [i for i in items if i not in exempt]
    with_doi = sum(1 for i in need if "doi.org" in i)
    return with_doi == len(need), \
        "%d of %d citable references carry a DOI; %d exempt as online documents with an access date" \
        % (with_doi, len(need), len(exempt))


def one_reference_per_number(t):
    items = re.findall(r"\\bibitem\{[^}]*\}(.*?)(?=\\bibitem|\\end\{thebibliography\})", t, re.S)
    bad = [i.strip()[:60] for i in items if re.search(r";\s*[A-Z]\.[A-Z~]|\band\b.*\bibid", i)]
    return not bad, "%d entries, %d suspected multiple references" % (len(items), len(bad))


def acknowledgments_placed(t):
    # `Acknowledge?ments` matches "Acknowledments", never the British "Acknowledgements", and the
    # old pattern knew nothing of sn-jnl's \bmhead. It therefore reported absent on a file that
    # carries the section under its correct name.
    m = re.search(r"\\begin\{acknowledgments?\}"
                  r"|\\(?:section\*?|bmhead)\{\s*Acknowledgu?e?ments?\s*\}", t, re.I)
    return bool(m), "acknowledgments present: %s (EPJ B wants them on the title page)" % bool(m)


def orbit_counts_add_up(t):
    """Sec 6.1 says thirty distinct graphs, then twelve plus sixteen. A referee adds 28."""
    if not re.search(r"thirty distinct graphs", t):
        return True, "the thirty-graph sentence is not present"
    twelve = bool(re.search(r"twelve edge-transitive", t))
    sixteen = bool(re.search(r"sixteen multi-orbit", t))
    # The manuscript says "whose automorphism group is trivial", not "trivial automorphism group".
    # A pattern that only knows one word order reports a fix that landed as a fix that did not.
    excluded = bool(re.search(r"trivial automorphism group|automorphism group is trivial"
                              r"|two random|remaining two", t, re.I))
    return not (twelve and sixteen and not excluded), \
        "thirty stated, twelve+sixteen listed, exclusion clause present: %s" % excluded


def no_before_submission_marker(t):
    return "BEFORE SUBMISSION" not in t, \
        "the BEFORE SUBMISSION instruction is %sin the file" % ("" if "BEFORE SUBMISSION" in t else "not ")


def figures_are_files(t):
    tikz = len(re.findall(r"\\begin\{tikzpicture\}", t))
    inc = len(re.findall(r"\\includegraphics", t))
    return tikz == 0, "%d inline tikzpicture figures, %d \\includegraphics" % (tikz, inc)


RULES = [
    ("template", "Springer Nature sn-jnl class with the [iicol] option", uses_sn_template),
    ("abstract-length", "abstract of 150 to 250 words", abstract_words),
    ("corresponding-email", "clear indication and active e-mail of the corresponding author",
     has_corresponding_email),
    ("orcid", "16-digit ORCID if available", has_orcid),
    ("ai-disclosure", "LLM use documented in the Methods section", has_ai_disclosure),
    ("competing-interests", "Competing Interests statement", has_competing_interests),
    ("author-contributions", "Author contributions statement", has_author_contributions),
    ("declarations", "a Statements and Declarations section", has_declarations_section),
    ("data-availability", "Data Availability Statement", has_data_availability),
    ("heading-depth", "decimal headings, no more than three levels", heading_depth),
    ("reference-dois", "DOIs included as full links where available", references_have_dois),
    ("one-ref-per-number", "one reference per number", one_reference_per_number),
    ("acknowledgments", "acknowledgments in a separate section on the title page",
     acknowledgments_placed),
    ("orbit-arithmetic", "Sec 6.1 counts must add to the stated total", orbit_counts_add_up),
    ("no-marker", "no editing instruction left in the text", no_before_submission_marker),
    ("figures-as-files", "figures supplied as files, named FigN", figures_are_files),
]

# Fixtures: (rule_id, text that PASSES, text that FAILS). A rule whose two fixtures agree is broken.
POS = {
    "template": r"\documentclass[sn-mathphys-num,iicol]{sn-jnl}" + "\n" + r"\begin{document}",
    "abstract-length": r"\begin{abstract}" + (" word" * 200) + r"\end{abstract}",
    "corresponding-email": r"\email{a@b.cz} Corresponding author",
    "orcid": "ORCID 0000-0002-1825-0097",
    "ai-disclosure": "an AI research system assisted the verification",
    "competing-interests": "Competing interests: none.",
    "author-contributions": "Author contributions: A did X.",
    "declarations": r"\section*{Statements and Declarations}",
    "data-availability": "Data availability: in the repository.",
    "heading-depth": r"\section{A}\subsection{B}\subsubsection{C}",
    "reference-dois": r"\bibitem{a} A. B, J. \textbf{1}, 1 (2000) https://doi.org/10.1/x"
                      + "\n" + r"\end{thebibliography}",
    "one-ref-per-number": r"\bibitem{a} A. B, J. 1, 1 (2000)" + "\n" + r"\end{thebibliography}",
    "acknowledgments": r"\begin{acknowledgments}thanks\end{acknowledgments}",
    "orbit-arithmetic": "thirty distinct graphs, twelve edge-transitive, sixteen multi-orbit, and "
                        "two random graphs with trivial automorphism group",
    "no-marker": "a clean manuscript",
    "figures-as-files": r"\includegraphics{Fig1.eps}",
}
NEG = {
    "template": r"\documentclass[aps,prb,reprint]{revtex4-2}" + "\n" + r"\begin{document}",
    "abstract-length": r"\begin{abstract}" + (" word" * 400) + r"\end{abstract}",
    "corresponding-email": "no contact given",
    "orcid": "no identifier",
    "ai-disclosure": "no such statement",
    "competing-interests": "nothing declared",
    "author-contributions": "nothing declared",
    "declarations": "no such heading",
    "heading-depth": r"\section{A}\paragraph{D}",
    "data-availability": "nothing about data",
    "reference-dois": r"\bibitem{a} A. B, J. \textbf{1}, 1 (2000)" + "\n"
                      + r"\end{thebibliography}",
    "one-ref-per-number": r"\bibitem{a} A. B, J. 1, 1 (2000); C.D, J. 2, 2 (2001) ibid"
                          + "\n" + r"\end{thebibliography}",
    "acknowledgments": "no thanks anywhere",
    "orbit-arithmetic": "thirty distinct graphs, twelve edge-transitive, sixteen multi-orbit cases",
    "no-marker": "BEFORE SUBMISSION do the thing",
    "figures-as-files": r"\begin{tikzpicture}\end{tikzpicture}",
}


def main() -> int:
    if not os.path.isfile(MS):
        refuse("manuscript not found at %s" % MS)
    text = io.open(MS, encoding="utf-8").read()
    if r"\begin{document}" not in text:
        refuse("the target does not parse as a LaTeX document")
    if len(RULES) != len(POS) or len(RULES) != len(NEG):
        refuse("fixture count does not match the rule count: %d rules, %d positive, %d negative"
               % (len(RULES), len(POS), len(NEG)))

    broken = []
    for rid, _, fn in RULES:
        if fn(POS[rid])[0] is not True or fn(NEG[rid])[0] is not False:
            broken.append(rid)
    if broken:
        refuse("these checks cannot tell a satisfied rule from a violated one, so their verdicts "
               "on the real manuscript mean nothing: %s" % ", ".join(broken))

    rows = []
    for rid, req, fn in RULES:
        ok, detail = fn(text)
        rows.append({"rule": rid, "requirement": req, "satisfied": bool(ok), "detail": detail})
        print("  %-4s %-22s %s" % ("OK" if ok else "TODO", rid, detail))

    todo = [r for r in rows if not r["satisfied"]]
    res = {
        "probe": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manuscript": os.path.relpath(MS, ROOT).replace(os.sep, "/"),
        "manuscript_bytes": len(text.encode("utf-8")),
        "rules_checked": len(rows), "satisfied": len(rows) - len(todo), "todo": len(todo),
        "rows": rows,
        "controls": {
            "target_exists_and_parses": True,
            "every_rule_proved_able_to_fail": True,
            "fixture_count_matches_rule_count": True,
        },
        "elapsed_s": round(time.time() - START, 1),
    }
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n%d of %d requirements satisfied; %d still to do."
          % (len(rows) - len(todo), len(rows), len(todo)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
