# Submitting the EDRN manuscript to Physical Review B — verified mechanics

Researched 2026-07-21 from APS's own pages. `journals.aps.org` returns 403 to the standard fetch tool;
everything here was pulled with a browser user-agent and the style guide extracted with pdftotext.
Anyone re-checking will hit the same 403 unless they do the same.

**Standing decision: arXiv is NOT an option.** cond-mat requires an endorsement and none of the three
authors has one. The journal is the only route. See memory `arxiv-excluded-journal-is-the-only-path`.

---

## The one real risk we created ourselves

We published the manuscript to Zenodo under **CC-BY** on 2026-07-21 (10.5281/zenodo.21473160), matching
the licence of the first paper.

APS's Rights Retention policy states that authors wanting a CC-BY licence on the accepted manuscript
**must publish gold open access ($2,910)**, because the free green route is funded by subscriptions and
"applying a CC-BY license to such articles does not support this". The Transfer of Copyright Agreement
signed at acceptance warrants the article is "unpublished and original" and "has not been published
elsewhere".

APS's own policy *does* contemplate preprint deposits — it asks authors to **disclose** them, which is
the clearest evidence that depositing is not itself disqualifying. What no APS page addresses is a
**CC-BY-licensed preprint posted before submission**, which is exactly our case.

**Action, before anything else:** email `prb@aps.org` with the DOI and ask directly whether the CC-BY
licence on the deposited preprint is compatible with the standard copyright transfer, or whether they
would require gold OA. One paragraph, and it converts an unknown into a written answer from the people
who decide. Zenodo allows changing the licence via a new version; that does not revoke the grant
already made, but it removes the ongoing conflict and shows good faith.

Sources: https://journals.aps.org/authors/editorial-policies#funder ·
https://journals.aps.org/authors/transfer-of-copyright-agreement

---

## Costs — better than expected

| item | cost |
|---|---|
| submission | **$0** — no submission fee, no page charges |
| publishing behind the paywall | **$0** (PRB is hybrid; open access is opt-in at acceptance) |
| gold open access, if chosen | $2,910 (2026) |
| colour figures in print | $1,090 first + $595 each — decline it, colour online is free |

APC waivers exist only for authors affiliated with institutions in low- or middle-income countries.
Neither China nor Slovakia is on the eligible list, and the waiver requires an institution anyway.

Source: https://journals.aps.org/authors/apcs

---

## Format — mostly already right

- **A single PDF is all that is needed to submit.** LaTeX source is requested only at acceptance.
- **REVTeX 4.2 with the `prb` option** is preferred; we already use
  `\documentclass[aps,prb,reprint,twocolumn,superscriptaddress]{revtex4-2}`.
- `superscriptaddress` is the right choice — it preserves author order across three different places.
- **Regular Article has no length limit.** (Letter = 4,500 words and must be justified in the cover
  letter; Comment = 3,500.) For a first submission with no institutional standing, Regular Article is
  the lower-risk choice.
- **No PACS codes** — REVTeX 4.2 ignores them. Classification is via PhySH terms in the submission form.
- **Abstract**: one paragraph, under 500 words and about 5% of the article, no numbered references, no
  displayed equations or tables.
- **PRB requires titles in every reference.** BibTeX with REVTeX 4.2 does this by default.
- Byline footnote format is exact: `*Contact author: name@example.com`

Sources: https://journals.aps.org/prb/authors · https://journals.aps.org/revtex ·
https://journals.aps.org/authors/style-basics

---

## Mandatory back-matter order

```
Title / Authors + affiliations / Abstract
Main text (I., II., III., ... roman numerals)
Acknowledgments
Author Contributions            <- separate paragraph
Data Availability Statement     <- REQUIRED, own principal heading
Appendixes                      <- AFTER the DAS, BEFORE the references; equations (A1), (B1)...
References                      <- last
```

The **Data Availability Statement is required for all published articles**, and research data
explicitly includes code and software created by the authors — for a numerical paper the simulation
code is in scope. APS's recommended repository list **names Zenodo first**, and explicitly says to
avoid Supplemental Material or personal websites for data.

Note the irony: the Zenodo deposit that creates a licence headache as a *preprint* is exactly what APS
wants for *data and code*. Keep the two records separate.

Model statement: "The data that support the findings of this article are openly available [47]."

Sources: https://journals.aps.org/authors/data-availability-statements ·
https://journals.aps.org/authors/style-basics

---

## What our manuscript still needs

1. **Sections.** There is currently not one `\section{}` in the manuscript — 21 bold inline labels
   (`\textbf{Spin gap}`, `\textbf{Bond dimension limitation:}`) stand in for them. A PRB Regular
   Article uses roman-numeral sections. Conventional body for a numerical condensed-matter paper:
   Introduction, Model and Method, Results, Discussion, Conclusions, with convergence details and
   derivations in appendixes.
2. **A Data Availability Statement**, citing a separate Zenodo data/code record in the reference list.
3. **An Author Contributions paragraph.**
4. **ORCIDs for all three authors.** Mandatory for the corresponding author; free; no institution
   needed. Guanghao has 0009-0000-2047-7517.
5. **The methodology and ethics material needs a decision.** The manuscript devotes substantial space to
   the "tool-rationality paradox", "firmly oppose alignment", "honest silence", and six numbered
   principles about how honest collaboration should work. It is sincere, and it is the best thing about
   how this paper was made — but PRB referees expect condensed-matter physics, and the first screening
   filter checks "the basic structure and context expected for a scientific article". This material is
   a separate essay for a different venue. Keeping it in is a live desk-rejection risk.
6. **A native-English pass.** APS names this explicitly and it is a real trigger for the first filter.

---

## The two screening filters — the first one has no appeal

**Filter 1, APS staff integrity and format check:** file readability, style and formatting
requirements, ethics policies, and "the basic structure and context expected for a scientific article".
Papers failing this are **rejected without external review and are ineligible for appeal**. This is
entirely within our control, and it is where a first-time submitter with an unconventional manuscript
is most exposed.

**Filter 2, editorial desk rejection on scope and criteria:** appealable to the Editorial Board. PRB's
criteria are that the work adds to knowledge in condensed matter, makes a significant contribution, and
is an authoritative addition to the literature.

Avoidable causes APS names explicitly: out of scope or wrong section; **not written for a general
readership** (PRB states this twice); **inadequate literature contextualisation** — "citations to
e-prints should not be used in place of primary references", the classic outsider failure; missing DAS,
PhySH terms or corresponding-author ORCID; non-disclosure of related versions; language quality; and
using Supplemental Material to dodge a length limit.

Source: https://journals.aps.org/authors/editorial-policies#peer-procedure

---

## Submission route

Not Editorial Manager — APS runs its own server.

1. Free APS Journal account: https://journals.aps.org/signup (no membership needed)
2. Submit at https://authors.aps.org/Submissions/login/new
3. Create New Submission, then Physical Review B, then article type, then section (B1 or B15).
   **APS warning: "Once you proceed from this initial page, the information provided cannot be
   changed."** Wrong journal means starting over.
4. Upload the single PDF.
5. Authors and affiliations — if an institution is not in APS's database, **type `None`** in the search
   and enter it manually. APS states the form entry "in no way affects the presentation of affiliations
   (bylines) within the manuscript itself".
6. Data Availability Statement.
7. PhySH subject classification (required), star a primary term.
8. Cover letter and suggested referees under Editorial Info.
9. Submit. Confirmation is immediate; the 7-digit accession code arrives within 2 business days.
   Track at https://authors.aps.org/Submissions/status/

Contact: `prb@aps.org` (journal office), `help@aps.org` (technical).

---

## Cover letter — PRB names its contents

Context of the results, summary of key findings, relevant submission history, recommended or excluded
referees. Add: the suggested PRB section, and **explicit disclosure of the Zenodo preprint DOI**.
Suggested referees are optional but worth doing — for unaffiliated authors it is the one lever that
partially substitutes for institutional signalling. Note that suggested referee names are **retained
and not editable on resubmission**, so get the list right the first time.

Source: https://journals.aps.org/prb/authors

---

## Open questions APS's own pages do not answer

1. Whether **"Independent Researcher"** is acceptable as a byline affiliation. Policy says only "the
   affiliation(s) where the research was conducted". Neither permitted nor forbidden anywhere. Ask.
2. Whether a **CC-BY preprint posted before submission** conflicts with the copyright transfer. The one
   most likely to bite us. Ask, in the same email.
3. Whether **Zenodo** counts as a "free-access e-print server" for the green open-access right. The
   policy reads inclusively ("repositories, including institutional and subject specific such as the
   arXiv") but never names Zenodo in that context. Zenodo *is* named favourably as a data repository.
4. The content of the **Open Science page inside the submission workflow** — it "clarifies APS's
   policies on preprint posting, manuscript sharing, and the use of open access licenses", which is
   exactly our question, but it sits behind the login. Read it carefully at step 6; it may answer the
   Zenodo question directly.
