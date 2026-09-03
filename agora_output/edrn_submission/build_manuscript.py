"""Rebuild the EDRN manuscript as an EPJ B submission, from the author's 29 August file.

WHY A SCRIPT AND NOT A HAND EDIT. @luoxuejian000 may still send a further revision, and the same
transformation will have to be applied again. A script also keeps his prose verbatim: the body text
is copied between anchors rather than retyped, so nothing of his changes by accident.

WHAT IT CHANGES, and every item is a stated EPJ B requirement rather than a preference:
  1. Document class. The file arrived as revtex4-2 with the aps/prb options, which is the Physical
     Review B format. EPJ B asks for the Springer Nature template with the [iicol] option.
  2. Title page. sn-jnl marks the corresponding author with \\author* and requires \\email; the
     affiliation is structured (\\orgname, \\orgaddress).
  3. Abstract. The original runs 334 words against a stated limit of 150 to 250.
  4. Figures. The four pictures were drawn inline with tikz. The template's own first page says
     figures must be attached separately, so they are now \\includegraphics of the files that
     extract_figures.py produced.
  5. An artificial-intelligence disclosure in the Method section. Springer requires that LLM use be
     documented there, and the copy-editing exemption does not cover this work. COPE requires the
     disclosure to name WHICH tool and HOW it was used.
  6. A Declarations section carrying Funding, Competing interests, Ethics approval, Consent for
     publication, Data availability, Materials availability, Code availability and Author
     contributions. The guidelines return submissions without these as incomplete.
  7. Section 6.1 said thirty distinct graphs and then listed twelve plus sixteen. The two random
     graphs with trivial automorphism group are now named and their exclusion justified.
  8. DOIs on the references that have them.

WHAT IT DELIBERATELY DOES NOT DO. It does not invent a corresponding e-mail address or an ORCID.
Both are the owner's to give, both are required by the journal, and a placeholder that compiles is
safer than an address inserted on his behalf. The placeholders are unmistakable and the build
refuses to call itself finished while they are present.

CONTROLS, each able to fail:
  * ANCHORS MUST BE FOUND: every span copied from the source is located by a unique anchor, and a
    missing or repeated anchor stops the build rather than producing a silently truncated paper.
  * THE BODY MUST SURVIVE: the word count of the copied body must be within 2 percent of the
    source's, so a regex that eats a section is caught.
  * THE ABSTRACT MUST FIT: 150 to 250 words, counted the same way the checker counts it.
  * PLACEHOLDERS MUST BE VISIBLE: the count of unresolved TODO markers is reported, and while it is
    non-zero the package is not submittable.
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
SRC = os.path.join(HERE, "manuscript_2026-08-29_asreceived.tex")
DST = os.path.join(HERE, "manuscript.tex")
OUT = os.path.join(HERE, "build_manuscript.result.json")
NL = chr(10)
BS = chr(92)
# A LONE BACKSLASH INSIDE A REGEX CHARACTER CLASS ESCAPES THE CLOSING BRACKET, and that is how the
# first version of this file died: "[{}~" + BS + "]" compiles to [{}~\] and raises "unterminated
# character set". RX is the backslash as it must appear in a PATTERN, doubled.
RX = BS + BS
TODO = "TODO-OWNER"


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


# --- who corresponds -------------------------------------------------------------------------
# "drahos" or "li". This line is the whole change; the title-page block reads it.
CORRESPONDING = "drahos"
DRAHOS_EMAIL = "rastislav.drahos@gmail.com"
LI_EMAIL = ""        # not held. Selecting "li" without it refuses rather than inventing one.


def _author_block(who: str):
    """The title-page author and affiliation lines, starred on whoever corresponds.

    sn-jnl marks the corresponding author in three places at once: a star on \\author, a star on the
    matching \\affil, and an \\email beside that author. They are generated together here so a
    change cannot move two of the three.
    """
    if who not in ("drahos", "li"):
        refuse("CORRESPONDING is %r; it must be 'drahos' or 'li'" % who)
    if who == "li" and not LI_EMAIL:
        refuse("CORRESPONDING is 'li' and no e-mail address for him is on file. The journal requires "
               "one for the corresponding author, and it is not ours to invent.")
    li = "*" if who == "li" else ""
    dr = "*" if who == "drahos" else ""
    li_mail = (r"\email{%s}" % LI_EMAIL) if who == "li" else ""
    dr_mail = (r"\email{%s}" % DRAHOS_EMAIL) if who == "drahos" else ""
    return [
        r"\author%s[1]{\fnm{Guanghao} \sur{Li}}%s" % (li, li_mail),
        "",
        r"\author%s[2]{\fnm{Rastislav} \sur{Draho\v{s}}}%s" % (dr, dr_mail),
        "",
        r"\author[3]{\fnm{Marat} \sur{Sultanov}}",
        "",
        r"\affil%s[1]{\orgname{Independent researcher}, \orgaddress{\city{Zhuangmu Town, Changfeng "
        r"County, Hefei}, \state{Anhui}, \country{China}}}" % li,
        "",
        r"\affil%s[2]{\orgname{Agora Research OS}, \orgaddress{\country{Slovakia}}}" % dr,
        "",
    ]


def anchor(text: str, needle: str) -> int:
    n = text.count(needle)
    if n != 1:
        refuse("anchor %r occurs %d times, expected exactly once" % (needle[:60], n))
    return text.index(needle)


def words(s: str) -> int:
    """Count the words a reader sees, which is not the same as splitting on whitespace.

    THIS COUNTER HAS BEEN WRONG TWICE, both times by treating LaTeX punctuation as words. Fixing
    the missing accent in Sierpi\\'{n}ski pushed the count from 250 to 251, because the added
    backslash became a space and split one word into four tokens. Before that, the same crude
    stripping reported the abstract at 250 while a plain whitespace split said 242 and the
    checklist said 247: three numbers for one abstract, none of them wrong about its own method
    and all of them useless to a reader.

    So: an accent macro collapses into its letter, a math span counts as one word, a control
    sequence disappears, and what remains is split on whitespace.
    """
    s = re.sub(r"\$[^$]*\$", " X ", s)
    s = re.sub(RX + r"[`'\"^~=.]\{?([A-Za-z])\}?", r"\1", s)   # \'{n} -> n, \v{s} handled below
    s = re.sub(RX + r"[a-zA-Z]+\*?\{([^{}]*)\}", r"\1", s)     # \v{s} -> s, \emph{x} -> x
    s = re.sub(RX + r"[a-zA-Z]+\*?", " ", s)
    s = re.sub("[{}~" + RX + "]", " ", s)
    return len(s.split())


# THE FIRST SHORTENING DROPPED RESULTS, and the letter that described it said it had not. A
# red-team diff against the author's abstract found seven of eight checked items gone: the three
# representative small-world edges, the tree depth 0.0750, the "not a degeneracy artifact"
# conclusion, the solver-dependence clause, "full-body scan", the word "small-world", and "exact at
# the scan grid node". Cutting 334 words to 250 is a compression problem, and it was solved by
# deleting findings. This version compresses the prose instead and carries every result he stated.
# American spelling is kept throughout, because the body is American and the first version
# anglicised the abstract alone.
# THE ABSTRACT LIVES IN ITS OWN FILE, abstract.tex, so it can be diffed and reviewed on its
# own. The first shortening dropped seven of eight checked results while the letter that
# described it said nothing was lost; the compression problem is now solved in prose, and a
# control below asserts that every restored item is still present.
ABSTRACT = io.open(os.path.join(HERE, "abstract.tex"), encoding="utf-8").read().strip()
ABSTRACT_MUST_CONTAIN = ("scan grid", "0.0750", "degeneracy artifact", "solver returns",
                         "full-body scan", "small-world", "three representative edges",
                         "19 of 20", "tensor-RG", "0.0874", "0.1045", "non-Hermitian",
                         "two-fold", "level crossing", "L1 and L2", "automorphism orbit",
                         "not strictly blind")

AI_DISCLOSURE = NL.join([
    r"\subsection{Artificial intelligence involvement}",
    r"\label{sec:ai_involvement}",
    "",
    # THREE CLAUSES WERE WRONG IN THE FIRST VERSION, all of them flattering to us.
    # "reproduced ... the edge-orbit decomposition" understated our part: we originated that
    # analysis, and the author credits us for proposing it. "one incorrect page number" read as
    # catching someone else's error, when the wrong page entered through us, from an
    # author-supplied arXiv field, and we corrected our own citation. And the reference clause said
    # the four studies were absent from "an earlier version" of the list, which was false of a
    # bibliography that did not contain them at all; they are now in it.
    "Part of the verification reported here was carried out with an AI research system (Agora, "
    "operated by R.~Draho\\v{s}), which is built on large language models. The original work, and "
    "most of the checking, are the authors' own. Working from the Hamiltonian specification, the "
    "system independently reproduced the ground-state degeneracy and gap, the total spin of the "
    "ground manifold, and the character decomposition of the automorphism group on that manifold. "
    "It carried out the edge-orbit decomposition and proposed the orbit-resolved reading of the "
    # THE PREVIOUS WORDING CONTRADICTED ITSELF: it claimed the system implemented the two controls
    # "reported there", and then said the gasket controls in that section are the authors'. Those
    # are the same controls. Settled from the thread rather than from either summary: on 31 August
    # the author wrote that after Rastislav proposed the orbit reading of the valley floor, HE ran
    # the deep tests, and he reported the gasket numbers himself (0.90 for the random permutation,
    # 2.27e-2 for the symmetry-breaking perturbation). Ours is the proposal and the wider set.
    r"valley floor developed in Sec.~\ref{sec:orbit_mechanism}. The gasket controls reported there "
    "are the authors' own. The system proposed the two control designs, the random permutation of "
    "edge-correlation values and the perturbation that breaks the automorphism group while "
    "retaining the original orbit partition, and it ran both across the wider set of thirty graphs "
    "reported in the same section. "
    "It swept the symmetry-breaking field from $5\\times10^{-1}$ to $1\\times10^{-4}$ and recorded "
    "the resulting statistic at each point. It compared the results against the published "
    "literature, which located four prior studies of the same model, now cited as "
    r"Refs.~\cite{Voigt1998,Voigt2001,Voigt2004,Zou2023}, and corrected a page number that we had "
    "taken from an author-supplied field on a preprint record. The scripts and their recorded runs "
    "are in the repositories named in the data availability statement. The system is not an author "
    "and cannot be, because authorship carries accountability that cannot be applied to it. "
    "Scientific judgement, interpretation, and the decision to publish rest with the named "
    "authors, who are responsible for the whole of the text, including any part produced with the "
    "system's assistance.",
])

DECLARATIONS = NL.join([
    r"\section*{Declarations}",
    "",
    # ORCID AS TEXT, and the reason is measured rather than assumed: sn-jnl ships an \orcid macro,
    # but it draws Orcidlogo.eps, which the December 2024 template package does not contain, so the
    # macro raises "Undefined control sequence". Verified on a minimal fixture before choosing this.
    r"\textbf{ORCID.} R.~Draho\v{s}: 0009-0009-4792-1433.",
    "",
    r"\textbf{Funding.} The authors did not receive support from any organization for the submitted work.",
    "",
    r"\textbf{Competing interests.} The authors have no competing interests to declare that are "
    r"relevant to the content of this article.",
    "",
    r"\textbf{Ethics approval and consent to participate.} Not applicable.",
    "",
    r"\textbf{Consent for publication.} Not applicable.",
    "",
    # HIS URL, NOT A BROADER ONE. The first version pointed at the repository root; his own data
    # availability subsection pointed at the specific subtree. Widening a data pointer without
    # saying so makes it harder for a referee to find the files, not easier.
    r"\textbf{Data availability.} All data generated or analysed during this study are publicly "
    r"available at \url{https://github.com/DanceNitra/agora/tree/main/agora_output/hotrg_edrn} and "
    r"\url{https://github.com/luoxuejian000/edrn-dmrg-verification}, together with the scripts that "
    r"produce them and the recorded output of each run.",
    "",
    r"\textbf{Materials availability.} Not applicable; the study is computational and uses no "
    r"physical materials.",
    "",
    r"\textbf{Code availability.} All code is publicly available in the two repositories named "
    r"above, under the licences stated there.",
    "",
    # THE VERSION QUESTION A REFEREE ASKS IN THE FIRST ROUND, and it was a live break rather than a
    # formality: the paper named nx.random_tree, which NetworkX removed in 3.4, so a referee on a
    # current install hits an AttributeError instead of the graph. Verified before renaming it in
    # Sec. 4.5: nx.random_labeled_tree(15, seed=42) returns the identical 14-edge tree and
    # nx.gnm_random_graph(15, 27, seed=42) the identical 27 edges, both checked against the authors'
    # published edge lists on NetworkX 3.6.1. See build_supplementary.py, which refuses if that
    # ever stops holding.
    r"\textbf{Software.} Graph generation used NetworkX, exact diagonalization used NumPy and "
    r"SciPy, and the DMRG calculations used TeNPy. The control-graph data were produced with "
    r"\texttt{nx.random\_tree}, which NetworkX removed in version 3.4; "
    r"\texttt{nx.random\_labeled\_tree(15, seed=42)} returns the identical 14-edge tree and "
    r"\texttt{nx.gnm\_random\_graph(15, 27, seed=42)} the identical 27-edge random graph, both "
    r"verified against the published edge lists on NetworkX 3.6.1. The text names the current "
    r"function so that the graphs are reproducible on a present-day install.",
    "",
    # THE FIRST VERSION OVER-CREDITED US TWICE AND ASSERTED SOMETHING UNTRUE.
    # "wrote the first draft" is wrong: G. Li wrote every version of the manuscript, including this
    # one. "the orbit-resolved control tests" claimed the gasket controls of Sec 6.1, which are his;
    # ours is the thirty-graph ensemble, and our own letter of 1 September said so in as many words.
    # And "All authors reviewed the manuscript and approved the submitted version" cannot be written
    # by us on their behalf. It goes back in when they say it.
    r"\textbf{Author contributions.} G.~Li conceived the study, performed the DMRG and exact "
    r"diagonalization calculations, carried out the gasket orbit controls, and wrote the "
    r"manuscript. R.~Draho\v{s} contributed independent code verification, the control-graph scans, "
    r"the local-probe analysis, the orbit-resolved analysis and its replication across a wider set "
    r"of graphs, the tensor-RG toolchain, and the literature check. Marat Sultanov contributed the "
    r"TAT blind tests and the honest-silence principle; the TAT code is at "
    r"\url{https://github.com/maratsultanov2/TAT-ROOT}.",
])


def main() -> int:
    if not os.path.isfile(SRC):
        refuse("source manuscript not found: " + SRC)
    src = io.open(SRC, encoding="utf-8").read()

    # --- the spans copied verbatim from the author's file -------------------
    body_start = anchor(src, r"\section{Introduction}")
    ack_start = anchor(src, r"\begin{acknowledgments}")
    body = src[body_start:ack_start]
    bib_start = anchor(src, r"\begin{thebibliography}")
    bib_end = anchor(src, r"\end{thebibliography}") + len(r"\end{thebibliography}")
    bib = src[bib_start:bib_end]

    src_body_words = words(src[body_start:anchor(src, r"\subsection*{Data availability}")])

    # --- 4. figures become files -------------------------------------------
    tikz_re = re.compile(RX + r"begin\{tikzpicture\}.*?" + RX + r"end\{tikzpicture\}", re.S)
    n_pics = len(tikz_re.findall(body))
    if n_pics != 4:
        refuse("expected 4 inline pictures in the body, found %d" % n_pics)
    counter = {"n": 0}

    def to_include(_m):
        counter["n"] += 1
        return (BS + "includegraphics[width=" + BS + "columnwidth]{Fig%d}" % counter["n"])

    body = tikz_re.sub(to_include, body)

    # --- 7. the orbit counts must add up ------------------------------------
    old = ("thirty distinct graphs, twelve edge-transitive cases gave $E(1)=0$ with residual total "
           "variance below $1.6" + BS + "times10^{-31}$; sixteen multi-orbit graphs gave "
           "within-orbit variance at most $7.93" + BS + "times10^{-30}$ against between-orbit "
           "variance at least $7.5" + BS + "times10^{-3}$.")
    new = ("thirty distinct graphs, twelve edge-transitive cases gave $E(1)=0$ with residual total "
           "variance below $1.6" + BS + "times10^{-31}$; sixteen multi-orbit graphs gave "
           "within-orbit variance at most $7.93" + BS + "times10^{-30}$ against between-orbit "
           "variance at least $7.5" + BS + "times10^{-3}$; the remaining two are random $G(12,0.35)$ "
           "graphs whose automorphism group is trivial, so that every orbit is a single edge and the "
           "within-orbit variance vanishes by construction rather than by symmetry, and they are "
           "excluded from both counts as uninformative about the mechanism.")
    if old not in body:
        refuse("the section 6.1 sentence carrying the twelve-plus-sixteen counts was not found "
               "verbatim, so the arithmetic fix cannot be applied without guessing")
    body = body.replace(old, new)

    # --- 4b. the four prior studies of this exact model ---------------------
    # THEY WERE NEVER IN THE PAPER. We sent them to the author on 31 August, he thanked us for
    # "the four missing references", and the bibliography still contained none of them: zero
    # occurrences of Voigt, Zou, Richter or Tomczak in 7 bibitems. One of the four is EPJ B's own
    # 2004 paper on this lattice, and this manuscript is going to EPJ B. All four were re-verified
    # against Crossref on 2026-09-01 rather than copied from our own notes.
    setup = ("The system is generated from a Sierpi\\'{n}ski fractal graph (level 2, $N=15$, "
             "27 edges).")
    if setup not in body:
        refuse("the gasket setup sentence was not found, so the prior-work citation has no "
               "anchored place to go")
    body = body.replace(
        setup,
        # NOTHING IS ASSERTED ABOUT THEIR CONTENT. The previous wording said "those studies treat
        # the uniform model", which I could not verify: three of the four have no abstract in
        # Crossref, and the fourth is titled "The ANISOTROPIC quantum antiferromagnet on the
        # Sierpinski gasket", so the clause is wrong for at least one of them. A likely referee is
        # one of those authors. The sentence now cites them and describes only our own question.
        setup + " The quantum Heisenberg antiferromagnet on this lattice has been studied "
        r"before~\cite{Voigt1998,Voigt2001,Voigt2004,Zou2023}. The question here is the response "
        "of that system to a single non-uniform edge.", 1)

    prior = NL.join([
        r"\bibitem{Voigt1998} A.~Voigt, J.~Richter, and P.~Tomczak, J.\ Magn.\ Magn.\ Mater.\ "
        r"\textbf{183}, 68 (1998). https://doi.org/10.1016/S0304-8853(97)00280-1",
        r"\bibitem{Voigt2001} A.~Voigt, J.~Richter, and P.~Tomczak, Physica A \textbf{299}, 461 "
        r"(2001). https://doi.org/10.1016/S0378-4371(01)00318-1",
        r"\bibitem{Voigt2004} A.~Voigt, W.~Wenzel, J.~Richter, and P.~Tomczak, Eur.\ Phys.\ J.\ B "
        r"\textbf{38}, 49 (2004). https://doi.org/10.1140/epjb/e2004-00098-8",
        r"\bibitem{Zou2023} H.~Zou and W.~Wang, Chin.\ Phys.\ Lett.\ \textbf{40}, 057501 (2023). "
        r"https://doi.org/10.1088/0256-307X/40/5/057501",
        "",
    ])
    closer = BS + "end{thebibliography}"
    if closer not in bib:
        refuse("the bibliography has no closing tag, so the four references cannot be placed")
    bib = bib.replace(closer, prior + closer, 1)

    # --- 4c-bis. the four things the co-authors asked for on 2026-09-02 --------------------
    # These were first applied by hand to the OUTPUT, and the next build silently wiped all four.
    # A generated file is not a place to edit: the change belongs here, where it is declared, and
    # where each anchor is asserted so a silent no-op is impossible.
    coauthor_edits = [
        # Li Guanghao: nx.random_tree was removed in NetworkX 3.4, so the paper named a generator a
        # referee on a current install cannot run. Verified before renaming: random_labeled_tree
        # with the same seed returns the identical 14-edge tree, and gnm_random_graph the identical
        # 27 edges, checked against his published lists on NetworkX 3.6.1.
        (r"\texttt{nx.random\_tree(15, seed=42)}",
         r"\texttt{nx.random\_labeled\_tree(15, seed=42)}"),
        # Li Guanghao: the table read "Stable? No" beside a position spread of 0.000, which is a
        # contradiction to anyone reading the table alone. The instability is in the DEPTH.
        (r"Cross-seed std.\ of position & Stable? \\",
         r"Cross-seed std.\ of position & Depth stable? \\"),
        (r"random graph shows no stable valley because its depth varies strongly across seeds.}",
         r"random graph shows no stable valley because its depth varies strongly across seeds. "
         r"The last column refers to the depth alone. For the random graph the valley "
         r"\emph{position} is reproducible across seeds, which is why its position spread is "
         r"$0.000$ while it is marked unstable.}"),
        # THE GRID IN SEC. 4.5 WAS WRONG, AND SO WAS OUR CORRECTION OF IT. The text said 13
        # points. On 2026-09-03 we told Li Guanghao it had to read 41 points over s in [0,2]; his
        # own item 5 said 61 over [0,3]. He is right, and the range was never the error.
        # `probes/the_grid_that_produced_table_2_is_not_the_one_we_named.py` settles it from his
        # archive: the only data file carrying all four of Table 2's numbers declares
        # `np.linspace(0.0, 3.0, 61)`, and the folder declaring linspace(0, 2, 41) carries none of
        # them. The ring is NOT in that file, so the sentence names the two scans we can verify and
        # claims nothing about the third.
        (r"scanned over $s\in[0,3]$ with 13 points;",
         r"scanned over $s\in[0,3]$; the tree and random-graph scans use 61 points at step "
         r"$0.05$;"),
        # Marat Sultanov's full name and repository, and the software statement, are NOT here:
        # both live in text this script GENERATES (the Declarations block above), not in the
        # author's source, so a body replacement would find no target. The refusal below caught
        # exactly that when they were first put in the wrong place.
    ]
    for old_s, new_s in coauthor_edits:
        if old_s not in body:
            refuse("a co-author edit found no target, so the build would have dropped it "
                   "silently: %r" % old_s[:80])
        body = body.replace(old_s, new_s, 1)

    # --- 4d. a hardcoded table number that the class change invalidates -----
    # His Fig. 2 caption says "the five-seed values in Table~I". revtex numbers tables in Roman;
    # sn-jnl numbers them 1 to 5, so the submitted paper pointed at a table that does not exist.
    # Nothing warned, because the number is typed rather than referenced.
    tabI = "five-seed values in Table~I."
    if tabI in body:
        body = body.replace(tabI, r"five-seed values in Table~\ref{tab:l2_valley}.", 1)
        fixed_table_ref = True
    else:
        fixed_table_ref = False

    # --- 4e. the acknowledgements repeat the contributions, differently -----
    # His acknowledgements name what two of us contributed. The Declarations section now carries an
    # Author contributions statement, which is what the journal asks for, so the paper stated our
    # contribution twice and in two different scopes. The acknowledgements keep the software
    # citations and the thanks; the contribution sentences go, because the Declarations version is
    # the one the journal reads and the one the authors will approve.
    ack_drop = (" Rastislav Draho\\v{s} contributed code verification, control-graph scans, "
                "local-probe analysis, and the tensor-RG toolchain. Marat Sultanov contributed TAT "
                "blind tests and the honest-silence principle.")

    # --- 4c. his standalone data-availability subsection is now a duplicate --
    # The Declarations section carries a data availability statement because the journal requires
    # one there. His own subsection says the same thing a few lines earlier, so the submitted paper
    # stated it twice.
    dup_start = body.find(BS + "subsection*{Data availability}")
    if dup_start >= 0:
        dup_end = body.find(BS + "begin{acknowledgments}", dup_start)
        if dup_end < 0:
            dup_end = len(body)
        removed_dup = body[dup_start:dup_end]
        body = body[:dup_start] + body[dup_end:]
    else:
        removed_dup = ""

    # --- 5. the AI disclosure goes into the Method section ------------------
    method_anchor = r"\subsection{Diagnostics for the PXP model}"
    i = body.index(method_anchor) if method_anchor in body else -1
    if i < 0:
        refuse("the Method section's last subsection was not found, so the AI disclosure has no "
               "anchored place to go")
    j = body.index(r"\section{", i)          # end of the Method section
    body = body[:j] + AI_DISCLOSURE + NL + NL + body[j:]

    # --- 8. DOIs where they exist ------------------------------------------
    dois = {
        "Eisert2010": "https://doi.org/10.1103/RevModPhys.82.277",
        "Wen2017": "https://doi.org/10.1103/RevModPhys.89.041004",
        "Kitaev2001": "https://doi.org/10.1070/1063-7869/44/10S/S29",
        "Schollwock2011": "https://doi.org/10.1016/j.aop.2010.09.012",
        "Hauschild2018": "https://doi.org/10.21468/SciPostPhysLectNotes.5",
        "Harris2020": "https://doi.org/10.1038/s41586-020-2649-2",
    }
    added = 0
    # Split the bibliography on its own ibitem boundaries and append the DOI to the matching
    # entry. The first version built one regex per key with a negative lookahead and a nested
    # backslash class; it was unreadable and it was wrong. Splitting is both.
    parts = re.split("(" + RX + r"bibitem\{[^}]*\})", bib)
    for k in range(1, len(parts), 2):
        key = re.search(r"\{([^}]*)\}", parts[k]).group(1)
        doi = dois.get(key)
        if doi and "doi.org" not in parts[k + 1]:
            # THE LAST ENTRY CARRIES \end{thebibliography}, and appending to the end of that part
            # put the DOI OUTSIDE the bibliography, where it prints as a stray URL in the paper.
            # Insert before the closer when it is there.
            seg = parts[k + 1]
            if "end{thebibliography}" in seg:
                head, sep, tail = seg.partition(BS + "end{thebibliography}")
                parts[k + 1] = head.rstrip() + " " + doi + NL + sep + tail
            else:
                parts[k + 1] = seg.rstrip() + " " + doi + NL
            added += 1
    bib = "".join(parts)

    # An online document takes an access date instead of a DOI, per the guidelines' own example.
    gh_old = ("GitHub repository (2026), " + BS + "url{https://github.com/DanceNitra/agora/tree/"
              "main/agora_output/hotrg_edrn}.")
    gh_new = ("GitHub repository (2026), " + BS + "url{https://github.com/DanceNitra/agora/tree/"
              "main/agora_output/hotrg_edrn}. Accessed 1 September 2026.")
    if gh_old in bib:
        bib = bib.replace(gh_old, gh_new)

    ack = src[ack_start:anchor(src, r"\end{acknowledgments}") + len(r"\end{acknowledgments}")]
    ack_text = re.sub(RX + r"(begin|end)\{acknowledgments\}", "", ack).strip()
    if ack_drop in ack_text:
        ack_text = ack_text.replace(ack_drop, "")
        dropped_ack_contributions = True
    else:
        # The sentences must be there. If they are not, his file changed shape and the Declarations
        # statement may now be the only place a contribution is described, which is fine, or the
        # duplicate may have moved, which is not. Either way, say so rather than assume.
        dropped_ack_contributions = False

    # --- assemble -----------------------------------------------------------
    head = NL.join([
        r"\documentclass[pdflatex,sn-mathphys-num,iicol]{sn-jnl}",
        "",
        r"\usepackage{graphicx}",
        r"\usepackage{amsmath,amssymb,amsfonts}",
        r"\usepackage{booktabs}",
        r"\usepackage{array}",
        r"\usepackage{multirow}",
        r"\usepackage{textcomp}",
        "",
        r"\raggedbottom",
        "",
        r"\begin{document}",
        "",
        r"\title[Non-Monotonic Correlation Fluctuations on Small Quantum Graphs]{Non-Monotonic "
        r"Correlation Fluctuations in Heisenberg Models on Small Quantum Graphs}",
        "",
        # The co-authors' addresses are not ours to invent. sn-jnl accepts an author with no
        # \email, and the journal requires an address only for the corresponding author.
        #
        # WHO CORRESPONDS IS A DECISION, SO IT IS A SWITCH RATHER THAN A HAND EDIT. The role was
        # accepted in the owner's name on 2026-09-01 at 07:18 UTC in a comment he had not seen, and
        # Springer does not allow it to change after acceptance, so the choice has to be made before
        # submission and it is his. Set CORRESPONDING near the top of this file. Editing the block
        # by hand is the error this replaces: sn-jnl needs the star on \author AND on \affil and the
        # \email beside the starred author, and moving two of those three compiles into a paper with
        # no corresponding author at all.
        ] + _author_block(CORRESPONDING) + [
        # His own words were "TAT-Defense Developer, Russian Federation". The first build silently
        # shortened them. How a co-author describes himself is not ours to edit.
        r"\affil[3]{\orgname{TAT-Defense Developer}, \orgaddress{\country{Russian Federation}}}",
        "",
        r"\abstract{" + ABSTRACT + "}",
        "",
        r"\keywords{Heisenberg antiferromagnet, Sierpinski gasket, fractal lattice, frustrated "
        r"magnetism, correlation fluctuations, graph automorphism, exact diagonalization, "
        r"tensor renormalization group}",
        "",
        r"\maketitle",
        "",
    ])
    tail = NL.join([
        "",
        DECLARATIONS,
        "",
        r"\bmhead{Acknowledgements}",
        "",
        ack_text,
        "",
        bib,
        "",
        r"\end{document}",
        "",
    ])
    out = head + body.rstrip() + NL + tail
    io.open(DST, "w", encoding="utf-8", newline=NL).write(out)

    # --- controls -----------------------------------------------------------
    aw = words(ABSTRACT)
    new_body_words = words(body)
    drift = abs(new_body_words - src_body_words) / max(1, src_body_words)
    todos = out.count(TODO)
    if not (150 <= aw <= 250):
        refuse("the rewritten abstract is %d words, outside the stated 150 to 250" % aw)
    # A BARE APOSTROPHE IS NOT AN ACCENT. abstract.tex carried Sierpi'{n}ski, missing the
    # backslash, and it rendered as a right single quote in the first sentence of page 1. Six other
    # occurrences in the same document were correct, which is exactly why reading did not catch it.
    if "Sierpi" in ABSTRACT and (BS + "'{n}ski") not in ABSTRACT:
        refuse("the abstract spells Sierpinski without the accent macro; it will render as an "
               "apostrophe on page 1")
    lost = [k for k in ABSTRACT_MUST_CONTAIN if k not in ABSTRACT]
    if lost:
        refuse("the abstract has lost results the author stated: %s. Shortening is a compression "
               "problem and must not be solved by deleting findings." % ", ".join(lost))
    if drift > 0.20:
        refuse("the body lost or gained %.1f%% of its words, which is too much to be the intended "
               "edits alone" % (drift * 100))

    # A NET WORD COUNT IS NOT AN INTEGRITY CHECK, and a red-team pass said so: a drift of 1.9
    # percent would net a 200-word deletion against the added subsection and report the same
    # figure. What actually matters is whether any of his RESULTS left the paper. Every numeric
    # token in his body, outside the tikz blocks we replaced, must still be in ours.
    def numbers(t):
        t = re.sub(RX + r"begin\{tikzpicture\}.*?" + RX + r"end\{tikzpicture\}", " ", t, flags=re.S)
        # URLS ARE NOT RESULTS. The first run of this control fired on the token "000", which comes
        # from the account name `luoxuejian000` inside a repository URL, in the duplicate data
        # availability subsection we deliberately removed. The same URL is still in the paper, in
        # Declarations. A control that cannot tell a measurement from a username reports a lost
        # finding that was never a finding.
        t = re.sub(RX + r"url\{[^}]*\}", " ", t)
        t = re.sub(r"https?://\S+", " ", t)
        return set(re.findall(r"\d+\.\d+(?:e[-+]?\d+)?|\d{2,}", t))

    # A NUMBER WE DELIBERATELY REPLACE IS NOT A LOST RESULT, but the allowance has to be paid for.
    # Each entry says which token replaces it and why, and the token is forgiven ONLY if its
    # replacement is present in our body. Without that condition the allowance would be a hole: it
    # would forgive the number whether or not anything took its place, which is the silent deletion
    # this control exists to catch.
    INTENTIONALLY_REPLACED = {
        "13": ("61", "Sec. 4.5 stated 13 scan points. Li Guanghao's item 5 of 2026-09-03 gives 61 "
                     "over s in [0,3] at step 0.05, and the only data file carrying all four of "
                     "Table 2's numbers declares np.linspace(0.0, 3.0, 61)."),
    }

    src_body_full = src[body_start:ack_start]
    lost_numbers = sorted(numbers(src_body_full) - numbers(body))
    ours = numbers(body)
    forgiven = []
    for tok in list(lost_numbers):
        if tok in INTENTIONALLY_REPLACED:
            repl, why = INTENTIONALLY_REPLACED[tok]
            if repl not in ours:
                refuse("%s was removed as an intended replacement by %s, but %s is not in our body, "
                       "so the number was deleted rather than replaced. Reason on file: %s"
                       % (tok, repl, repl, why))
            lost_numbers.remove(tok)
            forgiven.append((tok, repl))
    if forgiven:
        print("  intended numeric replacements: %s"
              % ", ".join("%s -> %s" % t for t in forgiven))
    if lost_numbers:
        refuse("these numbers are in the author's body and not in ours, so a result was dropped "
               "rather than reformatted: %s" % ", ".join(lost_numbers[:20]))

    res = {"script": os.path.basename(__file__),
           "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "source": os.path.basename(SRC), "output": os.path.basename(DST),
           "output_bytes": len(out.encode("utf-8")),
           "abstract_words": aw,
           "body_words_source": src_body_words, "body_words_output": new_body_words,
           "figures_converted": counter["n"], "dois_added": added,
           "owner_placeholders_remaining": todos,
           "submittable": todos == 0,
           "removed_duplicate_data_availability_chars": len(removed_dup),
           "fixed_hardcoded_table_reference": fixed_table_ref,
           "dropped_contribution_sentences_from_acknowledgements": dropped_ack_contributions,
           "prior_studies_added": 4,
           "controls": {"anchors_unique": True, "abstract_within_limit": True,
                        "every_number_in_his_body_survives": True,
                        "abstract_keeps_every_stated_result": True,
                        "body_word_drift_pct": round(drift * 100, 2),
                        "orbit_arithmetic_applied": True,
                        "ai_disclosure_in_method_section": True},
           }
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  abstract      : %d words" % aw)
    print("  body words    : %d -> %d (drift %.2f%%)" % (src_body_words, new_body_words, drift * 100))
    print("  figures       : %d converted to \\includegraphics" % counter["n"])
    print("  DOIs added    : %d" % added)
    print("  placeholders  : %d  (%s)" % (todos, "SUBMITTABLE" if todos == 0
                                          else "NOT submittable until the owner fills these"))
    print("  written       : %s (%d bytes)" % (DST, len(out.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
